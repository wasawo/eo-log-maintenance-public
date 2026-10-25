"""TEST ONLY: native replacement counterexamples in a self-created temp root.

No caller-selected destination, real checkpoint store or runtime provider is
offered. The deliberately stale replacement is a controlled negative experiment.
"""
from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import shutil
import stat
import tempfile
from uuid import uuid4

from Common.CompletionWaitAttempt import inspect_completion_wait_attempt_usepoint
from Common.OwnedRunLock import acquire_owned_lock


class ReplaceProbeError(RuntimeError):
    pass


class DisposableReplaceProbe:
    _NAMES = frozenset(("checkpoint.json", "candidate.json", "competitor.json"))

    def __init__(self, prior, candidate, competitor):
        if os.name != "nt": raise ReplaceProbeError("probe_windows_required")
        if any(type(value) is not bytes for value in (prior, candidate, competitor)):
            raise ReplaceProbeError("probe_bytes_required")
        from ctypes import wintypes
        self._api = ctypes.WinDLL("kernel32", use_last_error=True)
        self._api.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                          wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        self._api.CreateFileW.restype = wintypes.HANDLE
        self._api.ReplaceFileW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                           wintypes.DWORD, wintypes.LPVOID, wintypes.LPVOID)
        self._api.ReplaceFileW.restype = wintypes.BOOL
        self._api.CloseHandle.argtypes = (wintypes.HANDLE,)
        self._api.CloseHandle.restype = wintypes.BOOL
        self._parent = Path(tempfile.gettempdir()).resolve(strict=True)
        self._root = Path(tempfile.mkdtemp(prefix="eolm-cp-replace-", dir=self._parent))
        self._nonce = uuid4().hex.encode("ascii")
        self._scope = "synthetic-" + uuid4().hex
        (self._root / ".probe-owner").write_bytes(self._nonce)
        for name, data in zip(("checkpoint.json", "candidate.json", "competitor.json"), (prior, candidate, competitor)):
            with (self._root / name).open("xb") as stream: stream.write(data)

    def _verify_root(self):
        info = self._root.lstat()
        if (self._root.parent != self._parent or not self._root.name.startswith("eolm-cp-replace-")
                or self._root.resolve(strict=True) != self._root or not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise ReplaceProbeError("probe_root_changed")
        marker = self._root / ".probe-owner"
        info = marker.lstat()
        if (not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
                or info.st_nlink != 1 or marker.read_bytes() != self._nonce):
            raise ReplaceProbeError("probe_root_changed")

    def _path(self, name):
        if name not in self._NAMES: raise ReplaceProbeError("probe_name_invalid")
        self._verify_root()
        path = self._root / name
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400 or info.st_nlink != 1):
            raise ReplaceProbeError("probe_file_changed")
        return path

    def replace(self, source_name):
        if source_name not in ("candidate.json", "competitor.json"):
            raise ReplaceProbeError("probe_name_invalid")
        target, source = self._path("checkpoint.json"), self._path(source_name)
        # No expected-value parameter exists here: this is NOT compare-and-swap.
        ok = bool(self._api.ReplaceFileW(str(target), str(source), None, 0, None, None))
        error = 0 if ok else ctypes.get_last_error()
        return ok, error

    @contextmanager
    def deny_write_delete_guard(self):
        target = self._path("checkpoint.json")
        # GENERIC_READ, FILE_SHARE_READ only, OPEN_EXISTING, OPEN_REPARSE_POINT.
        handle = self._api.CreateFileW(str(target), 0x80000000, 1, None, 3, 0x00200000, None)
        if handle in (None, ctypes.c_void_p(-1).value): raise ReplaceProbeError("probe_guard_open_failed")
        try:
            yield
        finally:
            if not self._api.CloseHandle(handle): raise ReplaceProbeError("probe_guard_close_failed")

    def stale_replacement_counterexample(self, plan, context):
        # A named mutex only excludes callers that participate in its protocol.
        with acquire_owned_lock(self._scope, self._root / "synthetic-owner.json", timeout_seconds=0):
            observed = self._path("checkpoint.json").read_bytes()
            inspection = inspect_completion_wait_attempt_usepoint(plan, observed, phase="before_commit",
                                                                  ac_connected=True, **context)
            competing = self._path("competitor.json").read_bytes()
            first, _ = self.replace("competitor.json")
            if not first: raise ReplaceProbeError("probe_competitor_replace_failed")
            intermediate = self._path("checkpoint.json").read_bytes()
            changed = intermediate == competing and intermediate not in (plan.expected_bytes, plan.proposed_bytes)
            second, _ = self.replace("candidate.json")
            if not second: raise ReplaceProbeError("probe_stale_replace_failed")
            return dict(inspection_non_authorizing=not inspection["may_check"],
                        changed_after_inspection=changed,
                        stale_replace_overwrote_competitor=self._path("checkpoint.json").read_bytes() == plan.proposed_bytes)

    def close(self):
        # Verify the resolved, self-created target immediately before deletion.
        self._verify_root()
        shutil.rmtree(self._root)
