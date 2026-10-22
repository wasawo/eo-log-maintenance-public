"""Read-only verification of a published artifact set on disk.

This module hashes observed file bytes and validates the marker before delegating
classification. It never publishes, overwrites, deletes, or repairs artifacts.
"""
from __future__ import annotations

import hashlib
import json
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


def _is_link_or_reparse(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def verify_published_artifact_set(
    directory: str | Path,
    expected_sha256: Mapping[str, str],
    *,
    commit_marker_name: str = "commit-marker.json",
) -> ArtifactSetDecision:
    """Inspect one directory and classify only bytes actually observed on disk.

    The directory is expected to contain exactly the expected artifact files and
    optionally the marker. Symlinks, subdirectories, temporary/unexpected files,
    malformed marker JSON, and unreadable files fail closed. No filesystem state
    is changed.
    """
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

    root = Path(directory).absolute()
    try:
        if root.is_symlink() or not root.is_dir():
            raise ArtifactSetDirectoryVerificationError("directory_unavailable")
        if any(_is_link_or_reparse(component) for component in (root, *root.parents)):
            raise ArtifactSetDirectoryVerificationError("directory_unavailable")
        if not isinstance(expected_sha256, Mapping):
            raise ArtifactSetDirectoryVerificationError("expected_artifact_set_invalid")
        expected_names = set(expected_sha256)
        if not expected_names or commit_marker_name in expected_names:
            raise ArtifactSetDirectoryVerificationError("expected_artifact_set_invalid")

        published: dict[str, str] = {}
        marker: object = None
        allowed_names = expected_names | {commit_marker_name}
        for entry in root.iterdir():
            if entry.name not in allowed_names:
                raise ArtifactSetDirectoryVerificationError("unexpected_directory_entry")
            if _is_link_or_reparse(entry) or not entry.is_file():
                raise ArtifactSetDirectoryVerificationError("non_regular_artifact")
            try:
                content = entry.read_bytes()
            except OSError as exc:
                raise ArtifactSetDirectoryVerificationError("artifact_read_failed") from exc

            if entry.name == commit_marker_name:
                try:
                    marker = json.loads(
                        content.decode("utf-8"),
                        object_pairs_hook=_reject_duplicate_keys,
                    )
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    raise ArtifactSetDirectoryVerificationError("commit_marker_json_invalid") from exc
            else:
                published[entry.name] = hashlib.sha256(content).hexdigest()

        return classify_artifact_set(
            expected_sha256=expected_sha256,
            published_sha256=published,
            staged_sha256={},
            commit_marker=marker,
        )
    except ArtifactSetDirectoryVerificationError:
        raise
    except OSError as exc:
        raise ArtifactSetDirectoryVerificationError("directory_read_failed") from exc
