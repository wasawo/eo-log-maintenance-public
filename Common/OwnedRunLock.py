"""Fail-closed, per-scope OS mutex and ownership-token lock primitive.

This module is intentionally isolated: it does not recover abandoned records,
write manifests, enumerate sources, call Drive, archive, delete, or integrate
with operational entry points.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import json
import math
import os
from pathlib import Path
import secrets
import socket
from typing import Callable, Iterator

from Common.ArtifactSetDirectoryVerification import (
    ArtifactSetDirectoryVerificationError, _chain, _read_stable, _signature,
)


class LockAcquisitionError(RuntimeError):
    """Stable, sanitized lock failure."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


class _NamedMutex:
    """Small Win32 named-mutex adapter; tests replace this adapter."""

    WAIT_OBJECT_0 = 0x00000000
    WAIT_ABANDONED = 0x00000080
    WAIT_TIMEOUT = 0x00000102
    WAIT_FAILED = 0xFFFFFFFF
    INFINITE = 0xFFFFFFFF

    def __init__(self, name: str):
        if os.name != "nt":
            raise LockAcquisitionError("named_mutex_unsupported")
        from ctypes import wintypes

        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        self._kernel32.CreateMutexW.restype = wintypes.HANDLE
        self._kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        self._kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self._kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
        self._kernel32.ReleaseMutex.restype = wintypes.BOOL
        self._kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._handle = self._kernel32.CreateMutexW(None, False, name)
        if not self._handle:
            raise LockAcquisitionError("named_mutex_create_failed")
        self._owned = False
        self._abandoned = False

    @property
    def abandoned(self) -> bool:
        return self._abandoned

    def acquire(self, timeout_seconds: float) -> bool:
        milliseconds = max(0, min(int(timeout_seconds * 1000), 0xFFFFFFFE))
        result = self._kernel32.WaitForSingleObject(self._handle, milliseconds)
        if result == self.WAIT_OBJECT_0:
            self._owned = True
            return True
        if result == self.WAIT_ABANDONED:
            self._owned = True
            self._abandoned = True
            return True
        if result == self.WAIT_TIMEOUT:
            return False
        raise LockAcquisitionError("named_mutex_wait_failed")

    def release(self) -> None:
        if self._owned:
            try:
                if not self._kernel32.ReleaseMutex(self._handle):
                    raise LockAcquisitionError("named_mutex_release_failed")
            finally:
                self._owned = False

    def close(self) -> None:
        if self._handle:
            if not self._kernel32.CloseHandle(self._handle):
                raise LockAcquisitionError("named_mutex_close_failed")
            self._handle = None


def _validate_scope(scope_id: str) -> str:
    if not isinstance(scope_id, str) or not scope_id or len(scope_id) > 64:
        raise LockAcquisitionError("scope_id_invalid")
    if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in scope_id):
        raise LockAcquisitionError("scope_id_invalid")
    return scope_id


def _mutex_name(scope_id: str) -> str:
    # Global namespace keeps the mutex machine-wide rather than session-local.
    return "Global\\EOLogMaintenance-" + _validate_scope(scope_id)


def _strict_record_bytes(scope_id: str, token: str) -> bytes:
    record = {
        "schema_version": 1,
        "scope_id": scope_id,
        "owner_token": token,
        "pid": os.getpid(),
        "host": socket.gethostname(),
    }
    return (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _record_matches(path: Path, scope_id: str, token: str, maximum_bytes: int | None = None) -> bool:
    try:
        chain = _chain(path.parent)
        before = path.lstat()
        if maximum_bytes is not None and before.st_size > maximum_bytes:
            return False
        raw = _read_stable(path, _signature(before), path.parent, chain)
        record = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, ValueError, RecursionError, ArtifactSetDirectoryVerificationError):
        return False
    if not isinstance(record, dict):
        return False
    if set(record) != {"schema_version", "scope_id", "owner_token", "pid", "host"}:
        return False
    return (
        type(record.get("schema_version")) is int
        and record["schema_version"] == 1
        and record.get("scope_id") == scope_id
        and isinstance(record.get("owner_token"), str)
        and record["owner_token"].isascii()
        and secrets.compare_digest(record["owner_token"], token)
        and type(record.get("pid")) is int
        and record["pid"] > 0
        and isinstance(record.get("host"), str)
        and bool(record["host"])
    )


@contextmanager
def acquire_owned_lock(
    scope_id: str,
    lock_record_path: str | os.PathLike[str],
    timeout_seconds: float = 60.0,
    *,
    mutex_factory: Callable[[str], object] = _NamedMutex,
    token_factory: Callable[[], str] = lambda: secrets.token_hex(32),
    maximum_record_bytes: int | None = None,
) -> Iterator[str]:
    """Acquire mutex + exclusive token record, yielding the private owner token.

    A pre-existing lock record is never removed or adopted, including after an
    abandoned mutex. Recovery requires a separate validated recovery slice.
    Optional maximum_record_bytes bounds the newly generated record and each
    ownership read. Unreadable, changed or oversized records are preserved.
    """
    scope = _validate_scope(scope_id)
    if maximum_record_bytes is not None and (type(maximum_record_bytes) is not int or maximum_record_bytes < 1):
        raise LockAcquisitionError("lock_record_limit_invalid")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise LockAcquisitionError("timeout_invalid")
    if timeout_seconds < 0 or timeout_seconds > 60:
        raise LockAcquisitionError("timeout_out_of_range")
    if not math.isfinite(timeout_seconds):
        raise LockAcquisitionError("timeout_invalid")

    token = token_factory()
    if not isinstance(token, str) or len(token) < 32:
        raise LockAcquisitionError("owner_token_invalid")
    try:
        token_bytes = token.encode("ascii")
    except UnicodeEncodeError as exc:
        raise LockAcquisitionError("owner_token_invalid") from exc
    if len(token_bytes) > 256:
        raise LockAcquisitionError("owner_token_invalid")

    try:
        path = Path(lock_record_path)
        parent = path.parent.resolve(strict=True)
        if not parent.is_dir() or path.name in ("", ".", ".."):
            raise LockAcquisitionError("lock_record_path_invalid")
        path = parent / path.name
    except LockAcquisitionError:
        raise
    except OSError as exc:
        raise LockAcquisitionError("lock_record_path_unavailable") from exc

    mutex = mutex_factory(_mutex_name(scope))
    acquired = False
    record_created = False
    record_verified = False
    write_error = None
    try:
        # The existing adapter returns exact bool and release is safe when not
        # owned. On interrupted/uncertain waits, still attempt release + close.
        acquired = True
        try:
            result = mutex.acquire(float(timeout_seconds))
        except Exception:
            raise LockAcquisitionError("named_mutex_wait_failed") from None
        if type(result) is not bool:
            raise LockAcquisitionError("named_mutex_wait_failed")
        acquired = result
        if not acquired:
            raise LockAcquisitionError("lock_timeout")
        # Abandonment is evidence only. This slice deliberately does not recover.
        try:
            abandoned = getattr(mutex, "abandoned", None)
            if type(abandoned) is not bool:
                raise LockAcquisitionError("named_mutex_observation_invalid")
        except Exception:
            raise LockAcquisitionError("named_mutex_observation_invalid") from None
        if abandoned:
            raise LockAcquisitionError("abandoned_mutex_requires_recovery")
        payload = _strict_record_bytes(scope, token)
        if maximum_record_bytes is not None and len(payload) > maximum_record_bytes:
            raise LockAcquisitionError("lock_record_limit_exceeded")
        if path.exists() or path.is_symlink():
            raise LockAcquisitionError("lock_record_already_exists")
        try:
            with path.open("xb") as stream:
                record_created = True
                written = stream.write(payload)
                if type(written) is not int or written != len(payload):
                    write_error = LockAcquisitionError("lock_record_write_incomplete")
                    raise write_error
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            if write_error is not None:
                raise write_error from None
            raise LockAcquisitionError("lock_record_already_exists") from exc
        except OSError as exc:
            if write_error is not None:
                raise write_error from None
            raise LockAcquisitionError("lock_record_create_failed") from exc

        if not _record_matches(path, scope, token, maximum_record_bytes):
            raise LockAcquisitionError("lock_record_ownership_unverified")
        record_verified = True
        yield token
    finally:
        try:
            if record_created and record_verified:
                try:
                    if _record_matches(path, scope, token, maximum_record_bytes):
                        path.unlink()
                except OSError:
                    # Preserve mismatched or unverifiable state for explicit recovery.
                    pass
        finally:
            # Record observation/cleanup can itself be interrupted. It must
            # never bypass release/close of the already-created OS mutex.
            if acquired:
                try:
                    mutex.release()
                finally:
                    close = getattr(mutex, "close", None)
                    if callable(close):
                        close()
            else:
                close = getattr(mutex, "close", None)
                if callable(close):
                    close()
