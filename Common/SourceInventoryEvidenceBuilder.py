"""Read-only source enumeration and deterministic B2 evidence construction.

No network calls, source mutations, or artifact publication occur here. Callers
must treat incomplete enumeration as non-completable and must publish returned
artifacts atomically only after their own lock/publication gates are implemented.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
import uuid

from Common.RunInputEvidenceIntegrity import (
    EVIDENCE_CANONICALIZATION,
    compute_evidence_digest,
    compute_inventory_digest,
    validate_evidence_invariants,
)


class InventoryBuildError(ValueError):
    """Expected fail-closed input rejection with a stable reason code."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


_PATTERNS = {
    "BattleLog": re.compile(r"^(?P<date>[0-9]{8})_[0-9]{8}@.+\.txt$"),
    "ErrorReport": re.compile(r"^(?P<date>[0-9]{8})_[0-9]{8}\.txt$"),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cutoff(log_type: str, reference_date: date) -> date:
    if log_type == "BattleLog":
        return date.fromordinal(date(reference_date.year, reference_date.month, 1).toordinal() - 1)
    if log_type == "ErrorReport":
        return date(reference_date.year - 1, 12, 31)
    raise InventoryBuildError("unsupported_log_type")


def _classify_filename(name: str, log_type: str) -> date | None:
    match = _PATTERNS[log_type].fullmatch(name)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group("date"), "%Y%m%d").date()
    except ValueError:
        return None


def _is_source_reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def _reject_source_reparse(path: Path) -> None:
    # Resolving first would erase junction/symlink evidence.
    absolute = path.absolute()
    for component in (absolute, *absolute.parents):
        if _is_source_reparse(component.lstat()):
            raise InventoryBuildError("source_reparse_component")


def _hash_stable_file(path: Path) -> tuple[int, str]:
    """Hash exact bytes and reject observable metadata changes during the read."""
    try:
        _reject_source_reparse(path)
        before = path.lstat()
        if not path.is_file() or path.is_symlink():
            raise InventoryBuildError("source_entry_not_regular_file")
        digest = hashlib.sha256()
        byte_count = 0
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise InventoryBuildError("source_entry_not_regular_file")
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                byte_count += len(block)
                digest.update(block)
            finished = os.fstat(stream.fileno())
        _reject_source_reparse(path)
        after = path.lstat()
    except InventoryBuildError:
        raise
    except OSError as exc:
        raise InventoryBuildError("source_file_unavailable") from exc
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    identity_opened = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
    identity_finished = (finished.st_dev, finished.st_ino, finished.st_size, finished.st_mtime_ns)
    if not (identity_before == identity_opened == identity_finished == identity_after) or byte_count != finished.st_size:
        raise InventoryBuildError("source_mutation_detected")
    return byte_count, digest.hexdigest()


def build_run_input_evidence(
    source_root: str | os.PathLike[str],
    *,
    root_id: str,
    relative_scope: str,
    pc_id: str,
    log_type: str,
    run_id: str,
    evidence_id: str | None = None,
    reference_date: date | None = None,
    started_at: datetime | None = None,
) -> dict[str, Any]:
    """Enumerate a source tree, freeze eligible targets, and build validated B2 evidence.

    Any traversal/read/hash failure produces an evidence object with
    enumeration.status='incomplete' and a positive enumeration_errors count.
    It never emits completed enumeration after a failure. Invalid filenames
    are recorded as validation errors rather than silently ignored.
    """
    if pc_id not in ("PC-A", "PC-B"):
        raise InventoryBuildError("unsupported_pc_id")
    if log_type not in _PATTERNS:
        raise InventoryBuildError("unsupported_log_type")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,256}", root_id or ""):
        raise InventoryBuildError("invalid_root_id")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", run_id or ""):
        raise InventoryBuildError("invalid_run_id")
    if not isinstance(relative_scope, str) or not relative_scope or relative_scope.startswith("/") or "\\" in relative_scope or any(p in ("", ".", "..") for p in relative_scope.split("/")):
        raise InventoryBuildError("invalid_relative_scope")

    root = Path(source_root).absolute()
    try:
        _reject_source_reparse(root)
        root_stat = root.lstat()
        if not stat.S_ISDIR(root_stat.st_mode):
            raise InventoryBuildError("source_root_invalid")
    except InventoryBuildError as exc:
        raise InventoryBuildError("source_root_invalid") from exc
    except OSError as exc:
        raise InventoryBuildError("source_root_unavailable") from exc

    started = started_at or datetime.now(timezone.utc)
    ref_date = reference_date or started.astimezone(timezone.utc).date()
    cutoff = _cutoff(log_type, ref_date)
    observed = 0
    enumeration_errors = 0
    eligible = 0
    ineligible = 0
    ignored = 0
    validation_errors: list[dict[str, str]] = []
    targets: list[dict[str, Any]] = []
    pending = [root]

    while pending:
        directory = pending.pop()
        try:
            _reject_source_reparse(directory)
            entries = sorted(os.scandir(directory), key=lambda item: item.name.encode("utf-8", errors="strict"))
        except (OSError, UnicodeError, InventoryBuildError):
            enumeration_errors += 1
            continue
        for entry in entries:
            try:
                entry_info = Path(entry.path).lstat()
                if _is_source_reparse(entry_info):
                    enumeration_errors += 1
                    continue
                if stat.S_ISDIR(entry_info.st_mode):
                    pending.append(Path(entry.path))
                    continue
                observed += 1
                if not stat.S_ISREG(entry_info.st_mode):
                    ignored += 1
                    continue
                name = entry.name
                relative_path = Path(entry.path).relative_to(root).as_posix()
                file_date = _classify_filename(name, log_type)
                if file_date is None:
                    validation_errors.append({
                        "error_id": "",
                        "code": "unclassifiable_relevant_filename",
                        "filename": name,
                        "relative_path": relative_path,
                    })
                    continue
                if file_date > cutoff:
                    ineligible += 1
                    continue
                try:
                    size, digest = _hash_stable_file(Path(entry.path))
                except InventoryBuildError:
                    enumeration_errors += 1
                    continue
                targets.append({
                    "filename": name,
                    "relative_path": relative_path,
                    "size_bytes": size,
                    "expected_sha256": digest,
                })
                eligible += 1
            except (OSError, UnicodeError, ValueError):
                enumeration_errors += 1

    targets.sort(key=lambda item: item["relative_path"].encode("utf-8"))
    validation_errors.sort(key=lambda item: item["relative_path"].encode("utf-8"))
    for index, error in enumerate(validation_errors, start=1):
        error["error_id"] = f"VAL-{index:06d}"

    finished = datetime.now(timezone.utc)
    evidence: dict[str, Any] = {
        "evidence_schema_version": 1,
        "evidence_id": evidence_id or f"evidence-{uuid.uuid4()}",
        "run_id": run_id,
        "pc_id": pc_id,
        "log_type": log_type,
        "source_scope": {"root_id": root_id, "relative_scope": relative_scope},
        "enumeration": {
            "status": "completed" if enumeration_errors == 0 else "incomplete",
            "started_at_utc": _utc(started),
            "finished_at_utc": _utc(finished),
            "entries_observed": observed,
            "eligible_target_count": len(targets),
            "inventory_sha256": compute_inventory_digest(targets),
            "enumeration_errors": enumeration_errors,
        },
        "validation": {
            # V1 completion records classification coverage, not absence of
            # invalid inputs. Unobserved/uncertain entries still block coverage.
            "status": "completed" if enumeration_errors == 0 else "incomplete",
            "valid_eligible_count": len(targets),
            "valid_ineligible_count": ineligible,
            "invalid_relevant_count": len(validation_errors),
            "ignored_entries_count": ignored,
            "errors": validation_errors,
        },
        "inventory": {"kind": "embedded", "targets": targets},
        "integrity": {
            "algorithm": "sha256",
            "canonicalization": EVIDENCE_CANONICALIZATION,
            "digest": "0" * 64,
        },
    }
    evidence["integrity"]["digest"] = compute_evidence_digest(evidence)
    return evidence


def serialize_evidence(evidence: dict[str, Any], schema: dict[str, Any]) -> bytes:
    """Validate and serialize B2 evidence deterministically; performs no file I/O."""
    validate_evidence_invariants(evidence, schema)
    return (json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
