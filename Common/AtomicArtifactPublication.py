"""Atomic, no-overwrite publication of already validated artifact bytes.

This helper publishes one file only. It does not provide run locking, multi-file
transactions, stale-lock recovery, or integration with official entry points.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile


class ArtifactPublicationError(RuntimeError):
    """Stable, sanitized failure from the publication primitive."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _same_bytes(path: Path, expected: bytes) -> bool:
    try:
        with path.open("rb") as stream:
            digest = hashlib.sha256()
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
        return digest.hexdigest() == _sha256(expected) and path.stat().st_size == len(expected)
    except OSError as exc:
        raise ArtifactPublicationError("existing_artifact_unavailable") from exc


def publish_bytes_no_overwrite(destination: str | os.PathLike[str], data: bytes) -> str:
    """Publish bytes atomically without replacing an existing destination.

    Returns published or already_exists_identical. If the destination exists
    with different bytes, or the filesystem cannot provide the required atomic
    hard-link create, the operation fails closed. A same-directory temp is
    flushed and fsynced before os.link makes the complete bytes visible.
    """
    if not isinstance(data, bytes):
        raise ArtifactPublicationError("artifact_bytes_required")
    try:
        requested = Path(destination)
        parent = requested.parent.resolve(strict=True)
        if not parent.is_dir():
            raise ArtifactPublicationError("destination_parent_invalid")
        if requested.name in ("", ".", "..") or requested.name.endswith((" ", ".")):
            raise ArtifactPublicationError("destination_name_invalid")
        final_path = parent / requested.name
        if final_path.exists() or final_path.is_symlink():
            if final_path.is_symlink() or not final_path.is_file():
                raise ArtifactPublicationError("destination_not_regular_file")
            if _same_bytes(final_path, data):
                return "already_exists_identical"
            raise ArtifactPublicationError("destination_conflict")
    except ArtifactPublicationError:
        raise
    except OSError as exc:
        raise ArtifactPublicationError("destination_unavailable") from exc

    temp_path: Path | None = None
    fd: int | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{requested.name}.tmp-", dir=str(parent))
        temp_path = Path(temp_name)
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        try:
            os.link(temp_path, final_path)
        except FileExistsError:
            if final_path.is_symlink() or not final_path.is_file():
                raise ArtifactPublicationError("destination_not_regular_file")
            if _same_bytes(final_path, data):
                return "already_exists_identical"
            raise ArtifactPublicationError("destination_conflict")
        except OSError as exc:
            raise ArtifactPublicationError("atomic_publish_unavailable") from exc
        return "published"
    except ArtifactPublicationError:
        raise
    except OSError as exc:
        raise ArtifactPublicationError("artifact_publish_failed") from exc
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                # Do not mask the primary result; orphan cleanup requires ownership proof.
                pass
