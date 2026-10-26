"""Read-only local manifest directory observations, bound to exact read bytes.

No root approval, runtime invocation, manifest mutation, recovery or Drive
authorization is supplied. Callers must provide a trusted/qualified local root.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import os
from pathlib import Path
import stat

from Common.LatestManifestSelection import (
    LatestManifestSelectionError, ManifestCandidate, _validate_context,
    parse_manifest_filename, select_latest_manifest,
)
from Common.validate_aggregation_artifacts import validate_referenced_artifacts


@dataclass(frozen=True)
class ReadManifestSelection:
    filename: str
    run_id: str
    status: str
    sha256: str
    content: bytes = field(repr=False)


class ManifestDirectoryReadError(ValueError):
    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _reject(reason):
    raise ManifestDirectoryReadError(reason) from None


def _reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _signature(info):
    # Windows 3.12 stat/fstat ctime can differ; compare explicit birthtime.
    stamp = getattr(info, "st_birthtime_ns", info.st_ctime_ns) if os.name == "nt" else info.st_ctime_ns
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, stamp


def _chain(directory):
    result = []
    for component in (directory, *directory.parents):
        info = component.lstat()
        if _reparse(info) or not stat.S_ISDIR(info.st_mode):
            _reject("manifest_directory_untrusted")
        result.append((info.st_dev, info.st_ino))
    return tuple(result)


def _scan(directory, chain, maximum_entries=None):
    if _chain(directory) != chain:
        _reject("manifest_directory_changed")
    with os.scandir(directory) as entries:
        names = []
        for entry in entries:
            # Stop before retaining/inspecting an unbounded namespace. Count
            # every entry, including malformed and foreign-scope names.
            if maximum_entries is not None and len(names) >= maximum_entries:
                _reject("manifest_entry_limit_exceeded")
            names.append(entry.name)
        names.sort()
    observations = {}
    for name in names:
        info = (directory / name).lstat()
        if _reparse(info) or not stat.S_ISREG(info.st_mode):
            _reject("manifest_entry_untrusted")
        # All entries must follow the defined manifest basename grammar.
        parse_manifest_filename(name)
        observations[name] = _signature(info)
    return observations


def _read_stable(path, expected, directory, chain):
    if _chain(directory) != chain:
        _reject("manifest_directory_changed")
    before = path.lstat()
    if _reparse(before) or not stat.S_ISREG(before.st_mode):
        _reject("manifest_entry_untrusted")
    if _signature(before) != expected:
        _reject("manifest_candidate_changed")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or _signature(opened) != expected:
            _reject("manifest_candidate_changed")
        blocks, byte_count = [], 0
        while True:
            block = stream.read(min(65536, before.st_size-byte_count+1))
            if not block:
                break
            byte_count += len(block)
            if byte_count > before.st_size:
                _reject("manifest_candidate_changed")
            blocks.append(block)
        content = b"".join(blocks)
        finished = os.fstat(stream.fileno())
    after = path.lstat()
    if (_reparse(after) or not stat.S_ISREG(after.st_mode)
            or _signature(finished) != expected or _signature(after) != expected
            or len(content) != before.st_size):
        _reject("manifest_candidate_changed")
    if _chain(directory) != chain:
        _reject("manifest_directory_changed")
    return content


def read_latest_manifest(
    maintenance_root: str | Path,
    *,
    expected_pc_id: str,
    expected_log_type: str,
    expected_target_period: str,
    current_utc: datetime | None,
    current_utc_reliable: bool,
    require_current_success: bool = True,
    future_tolerance: timedelta = timedelta(minutes=5),
    maximum_candidate_bytes: int | None = None,
    maximum_total_bytes: int | None = None,
    maximum_entries: int | None = None,
) -> ReadManifestSelection:
    """Observe fixed PC directory, select scoped latest, recheck before return.

    Validate all directory entries, including other well-formed periods/log
    types for this PC, before filtering the requested tuple. Unknown names,
    stale temp entries and invalid foreign-scope content block, not disappear.
    This is point-in-time defense, not a namespace snapshot or use permission.
    """
    options = dict(
        expected_pc_id=expected_pc_id, expected_log_type=expected_log_type,
        expected_target_period=expected_target_period, current_utc=current_utc,
        current_utc_reliable=current_utc_reliable, require_current_success=require_current_success,
        future_tolerance=future_tolerance, enumeration_completed=True,
    )
    _validate_context(**options)  # Reject invalid scope/clock/mode before any root IO.
    if any(value is not None and (type(value) is not int or value < 1)
           for value in (maximum_candidate_bytes, maximum_total_bytes, maximum_entries)):
        _reject("manifest_read_limit_invalid")
    try:
        root = Path(maintenance_root)
        if not root.is_absolute() or ".." in root.parts:
            _reject("maintenance_root_invalid")
        directory = root / "_maintenance" / "manifests" / expected_pc_id
        chain = _chain(directory)
        initial = _scan(directory, chain, maximum_entries)
        # Include older/foreign-period entries: resource limits must not become
        # a way to skip unknown candidates and fall back to an older success.
        if (maximum_candidate_bytes is not None
                and any(signature[2] > maximum_candidate_bytes for signature in initial.values())):
            _reject("manifest_candidate_limit_exceeded")
        if maximum_total_bytes is not None and sum(signature[2] for signature in initial.values()) > maximum_total_bytes:
            _reject("manifest_total_limit_exceeded")
        candidates = []
        for name, signature in initial.items():
            identity = parse_manifest_filename(name)
            if identity["pc_id"] != expected_pc_id:
                _reject("manifest_directory_scope_mismatch")
            content = _read_stable(directory / name, signature, directory, chain)
            candidate = ManifestCandidate(name, content)
            # Validate other periods/types too: hiding corrupt JSON behind a
            # plausible foreign basename is not a filter bypass.
            select_latest_manifest(
                [candidate], expected_pc_id=identity["pc_id"],
                expected_log_type=identity["log_type"],
                expected_target_period=identity["target_period"],
                enumeration_completed=True, current_utc=current_utc,
                current_utc_reliable=current_utc_reliable,
                require_current_success=False, future_tolerance=future_tolerance,
            )
            if (identity["log_type"], identity["target_period"]) == (expected_log_type, expected_target_period):
                candidates.append(candidate)
        selected = select_latest_manifest(candidates, **options)
        if _scan(directory, chain, maximum_entries) != initial:
            _reject("manifest_directory_changed")
        chosen = candidates[selected.selected_index]
        return ReadManifestSelection(
            chosen.filename, selected.run_id, selected.status,
            hashlib.sha256(chosen.content).hexdigest(), chosen.content,
        )
    except (LatestManifestSelectionError, ManifestDirectoryReadError):
        raise
    except Exception:
        _reject("manifest_directory_read_failed")


def read_latest_manifest_with_report(
    maintenance_root: str | Path, report_path: str | Path, contracts_path: str | Path, *,
    expected_pc_id: str, expected_log_type: str, expected_target_period: str,
    current_utc: datetime | None, current_utc_reliable: bool,
    require_current_success: bool = True,
    future_tolerance: timedelta = timedelta(minutes=5),
    maximum_candidate_bytes: int | None = None,
    maximum_total_bytes: int | None = None,
    maximum_entries: int | None = None,
    maximum_artifact_bytes: int | None = None,
) -> ReadManifestSelection:
    """Bind scoped latest bytes to a semantically verified report, then reselect.

    A report path is supplied explicitly; no report location or missing report
    is inferred. This remains a read observation, not archive permission or a
    locked/atomic snapshot. Current clock/root/Drive qualification is external.
    """
    if maximum_artifact_bytes is not None and (type(maximum_artifact_bytes) is not int or maximum_artifact_bytes < 1):
        _reject("manifest_read_limit_invalid")
    options = dict(expected_pc_id=expected_pc_id, expected_log_type=expected_log_type,
        expected_target_period=expected_target_period, current_utc=current_utc,
        current_utc_reliable=current_utc_reliable, require_current_success=require_current_success,
        future_tolerance=future_tolerance, maximum_candidate_bytes=maximum_candidate_bytes,
        maximum_total_bytes=maximum_total_bytes, maximum_entries=maximum_entries)
    selected = read_latest_manifest(maintenance_root, **options)
    reference = f"_maintenance/manifests/{expected_pc_id}/{selected.filename}"
    result = validate_referenced_artifacts(maintenance_root, report_path, contracts_path,
        expected_manifest_bytes=selected.content, expected_manifest_path=reference,
        maximum_artifact_bytes=maximum_artifact_bytes)
    if result["status"] != "verified":
        _reject("selected_manifest_report_invalid")
    observed_again = read_latest_manifest(maintenance_root, **options)
    if observed_again != selected:
        _reject("selected_manifest_changed")
    return selected
