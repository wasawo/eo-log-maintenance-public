"""Read-only verification of a published artifact set on disk.

This module hashes observed file bytes and validates the marker before delegating
classification. It never publishes, overwrites, deletes, or repairs artifacts.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Mapping

from Common.ArtifactSetRecovery import ArtifactSetDecision, classify_artifact_set


class ArtifactSetDirectoryVerificationError(RuntimeError):
    """Sanitized, stable failure from directory inspection."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_json_constant(_value):
    raise ValueError("nonstandard_json_constant")


def _is_link_or_reparse(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def _signature(info):
    # Windows 3.12 stat/fstat ctime can differ; compare explicit birthtime.
    stamp = getattr(info, "st_birthtime_ns", info.st_ctime_ns) if os.name == "nt" else info.st_ctime_ns
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, stamp, info.st_nlink


def _chain(root):
    identities = []
    for path in (root, *root.parents):
        info = path.lstat()
        if _is_link_or_reparse(path) or not stat.S_ISDIR(info.st_mode):
            raise ArtifactSetDirectoryVerificationError("directory_unavailable")
        identities.append((info.st_dev, info.st_ino))
    return tuple(identities)


def _scan(root, allowed, chain):
    if _chain(root) != chain:
        raise ArtifactSetDirectoryVerificationError("directory_changed")
    result = {}
    for entry in root.iterdir():
        if entry.name not in allowed:
            raise ArtifactSetDirectoryVerificationError("unexpected_directory_entry")
        if entry.name in result:
            raise ArtifactSetDirectoryVerificationError("directory_changed")
        info = entry.lstat()
        if _is_link_or_reparse(entry) or not stat.S_ISREG(info.st_mode):
            raise ArtifactSetDirectoryVerificationError("non_regular_artifact")
        result[entry.name] = _signature(info)
    return result


def _read_stable(path, expected, root, chain):
    if _chain(root) != chain:
        raise ArtifactSetDirectoryVerificationError("directory_changed")
    before = path.lstat()
    if _is_link_or_reparse(path) or not stat.S_ISREG(before.st_mode) or _signature(before) != expected:
        raise ArtifactSetDirectoryVerificationError("artifact_changed")
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or _signature(opened) != expected:
                raise ArtifactSetDirectoryVerificationError("artifact_changed")
            blocks, count = [], 0
            while True:
                block = stream.read(min(65536, before.st_size-count+1))
                if not block:
                    break
                count += len(block)
                if count > before.st_size:
                    raise ArtifactSetDirectoryVerificationError("artifact_changed")
                blocks.append(block)
            content = b"".join(blocks)
            finished = os.fstat(stream.fileno())
    except OSError as exc:
        raise ArtifactSetDirectoryVerificationError("artifact_read_failed") from exc
    after = path.lstat()
    if (_is_link_or_reparse(path) or not stat.S_ISREG(after.st_mode)
            or _signature(after) != expected or _signature(finished) != expected
            or len(content) != before.st_size or _chain(root) != chain):
        raise ArtifactSetDirectoryVerificationError("artifact_changed")
    return content


def verify_published_artifact_set(
    directory: str | Path,
    expected_sha256: Mapping[str, str],
    *,
    commit_marker_name: str = "commit-marker.json",
    expected_transaction_id: str | None = None,
    maximum_artifact_bytes: int | None = None,
    maximum_total_bytes: int | None = None,
) -> ArtifactSetDecision:
    """Inspect one directory and classify only bytes actually observed on disk.

    The directory is expected to contain exactly the expected artifact files and
    optionally the marker. Symlinks, subdirectories, temporary/unexpected files,
    malformed marker JSON, and unreadable files fail closed. No filesystem state
    is changed. Path/handle, directory and exact bytes are rechecked before
    returning; these observations do not prove an atomic snapshot or block ABA.
    Optional expected_transaction_id binds the marker to a supplied identity,
    not to a qualified owner or one-use receipt.
    """
    if any(value is not None and (type(value) is not int or value < 1)
           for value in (maximum_artifact_bytes, maximum_total_bytes)):
        raise ArtifactSetDirectoryVerificationError("artifact_read_limit_invalid")
    if (
        not isinstance(commit_marker_name, str)
        or not commit_marker_name
        or commit_marker_name.startswith(".")
        or commit_marker_name in {".", ".."}
        or "/" in commit_marker_name
        or "\\" in commit_marker_name
        or "\x00" in commit_marker_name
    ):
        raise ArtifactSetDirectoryVerificationError("commit_marker_name_invalid")

    if not isinstance(expected_sha256, Mapping):
        raise ArtifactSetDirectoryVerificationError("expected_artifact_set_invalid")
    try:
        expected = dict(expected_sha256)
    except Exception:
        raise ArtifactSetDirectoryVerificationError("expected_artifact_set_invalid") from None
    expected_names = set(expected)
    if not expected_names or commit_marker_name in expected_names:
        raise ArtifactSetDirectoryVerificationError("expected_artifact_set_invalid")
    # Reuse the classifier's input grammar before any directory I/O. The
    # resulting empty-publication decision is only preflight, never authority.
    preflight = classify_artifact_set(expected_sha256=expected,
        published_sha256={}, staged_sha256={}, expected_transaction_id=expected_transaction_id)
    if preflight.state == "blocked":
        return preflight

    root = Path(directory).absolute()
    try:
        if root.is_symlink() or not root.is_dir():
            raise ArtifactSetDirectoryVerificationError("directory_unavailable")
        chain = _chain(root)
        published: dict[str, str] = {}
        marker: object = None
        allowed_names = expected_names | {commit_marker_name}
        initial = _scan(root, allowed_names, chain)
        # Include the marker and incomplete sets. Never truncate/fall back to
        # a subset when caller-selected resource bounds cannot be met.
        if (maximum_artifact_bytes is not None
                and any(signature[2] > maximum_artifact_bytes for signature in initial.values())):
            raise ArtifactSetDirectoryVerificationError("artifact_read_limit_exceeded")
        if maximum_total_bytes is not None and sum(signature[2] for signature in initial.values()) > maximum_total_bytes:
            raise ArtifactSetDirectoryVerificationError("artifact_total_limit_exceeded")
        contents = {}
        for name, signature in initial.items():
            entry = root / name
            content = _read_stable(entry, signature, root, chain)
            contents[name] = content

            if entry.name == commit_marker_name:
                try:
                    marker = json.loads(
                        content.decode("utf-8"),
                        object_pairs_hook=_reject_duplicate_keys,
                        parse_constant=_reject_json_constant,
                    )
                    if type(marker) is not dict:
                        raise ValueError("commit_marker_root_not_object")
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
                    raise ArtifactSetDirectoryVerificationError("commit_marker_json_invalid") from exc
            else:
                published[entry.name] = hashlib.sha256(content).hexdigest()

        decision = classify_artifact_set(
            expected_sha256=expected,
            published_sha256=published,
            staged_sha256={},
            commit_marker=marker,
            expected_transaction_id=expected_transaction_id,
        )
        if _scan(root, allowed_names, chain) != initial:
            raise ArtifactSetDirectoryVerificationError("directory_changed")
        for name, content in contents.items():
            if _read_stable(root / name, initial[name], root, chain) != content:
                raise ArtifactSetDirectoryVerificationError("artifact_changed")
        if _scan(root, allowed_names, chain) != initial:
            raise ArtifactSetDirectoryVerificationError("directory_changed")
        return decision
    except ArtifactSetDirectoryVerificationError:
        raise
    except OSError as exc:
        raise ArtifactSetDirectoryVerificationError("directory_read_failed") from exc
