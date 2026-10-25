"""Atomic, no-overwrite publication of already validated artifact bytes.

This helper publishes one file only. It does not provide run locking, multi-file
transactions, stale-lock recovery, or integration with official entry points.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile


class ArtifactPublicationError(RuntimeError):
    """Stable, sanitized failure from the publication primitive."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _regular(info):
    return stat.S_ISREG(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400)


def _identity(info):
    return info.st_dev, info.st_ino


def _signature(info):
    return _identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink


def _chain(parent):
    result = []
    for component in (parent, *parent.parents):
        info = component.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ArtifactPublicationError("destination_parent_invalid")
        result.append(_identity(info))
    return tuple(result)


def _owned_temp(path, identity, parent, chain):
    info = path.lstat()
    return _regular(info) and _identity(info) == identity and _chain(parent) == chain


def _same_bytes(path: Path, expected: bytes) -> bool:
    try:
        chain = _chain(path.parent)
        before = path.lstat()
        if not _regular(before):
            raise ArtifactPublicationError("destination_not_regular_file")
        signature = _signature(before)
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _regular(opened) or _signature(opened) != signature:
                raise ArtifactPublicationError("artifact_changed_during_read")
            offset, matches = 0, True
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                matches = matches and block == expected[offset:offset + len(block)]
                offset += len(block)
            finished = os.fstat(stream.fileno())
        after = path.lstat()
        if (not _regular(after) or _signature(after) != signature or _signature(finished) != signature
                or offset != before.st_size or _chain(path.parent) != chain):
            raise ArtifactPublicationError("artifact_changed_during_read")
        return matches and offset == len(expected)
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
        parent = requested.parent.absolute()
        chain = _chain(parent)
        if not parent.is_dir():
            raise ArtifactPublicationError("destination_parent_invalid")
        if requested.name in ("", ".", "..") or requested.name.endswith((" ", ".")):
            raise ArtifactPublicationError("destination_name_invalid")
        final_path = parent / requested.name
        if final_path.exists() or final_path.is_symlink():
            if not _regular(final_path.lstat()):
                raise ArtifactPublicationError("destination_not_regular_file")
            if _same_bytes(final_path, data) and _chain(parent) == chain:
                return "already_exists_identical"
            raise ArtifactPublicationError("destination_conflict")
    except ArtifactPublicationError:
        raise
    except OSError as exc:
        raise ArtifactPublicationError("destination_unavailable") from exc

    temp_path: Path | None = None
    fd: int | None = None
    temp_identity = None
    try:
        if _chain(parent) != chain:
            raise ArtifactPublicationError("destination_parent_changed")
        fd, temp_name = tempfile.mkstemp(prefix=f".{requested.name}.tmp-", dir=str(parent))
        temp_path = Path(temp_name)
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            temp_identity = _identity(os.fstat(stream.fileno()))

        if (not _owned_temp(temp_path, temp_identity, parent, chain) or not _same_bytes(temp_path, data)
                or not _owned_temp(temp_path, temp_identity, parent, chain)):
            raise ArtifactPublicationError("staging_readback_unverified")

        try:
            os.link(temp_path, final_path)
        except FileExistsError:
            if not _regular(final_path.lstat()):
                raise ArtifactPublicationError("destination_not_regular_file")
            if _same_bytes(final_path, data) and _chain(parent) == chain:
                return "already_exists_identical"
            raise ArtifactPublicationError("destination_conflict")
        except OSError as exc:
            raise ArtifactPublicationError("atomic_publish_unavailable") from exc
        if (not _owned_temp(final_path, temp_identity, parent, chain) or not _same_bytes(final_path, data)
                or not _owned_temp(final_path, temp_identity, parent, chain)):
            raise ArtifactPublicationError("published_artifact_unverified")
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
        if temp_path is not None and temp_identity is not None:
            try:
                if (_owned_temp(temp_path, temp_identity, parent, chain) and _same_bytes(temp_path, data)
                        and _owned_temp(temp_path, temp_identity, parent, chain)):
                    temp_path.unlink()
            except (OSError, ArtifactPublicationError):
                # Do not mask the primary result; orphan cleanup requires ownership proof.
                pass
