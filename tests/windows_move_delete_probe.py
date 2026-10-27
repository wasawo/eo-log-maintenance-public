"""TEST ONLY: verify/copy-record/handle-delete in a fresh synthetic temp root.

No caller-selected path, production provider, or restart recovery is exposed.
"""
from contextlib import contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from uuid import uuid4


class MoveDeleteProbeError(RuntimeError):
    pass


class DisposableMoveDeleteProbe:
    _NAMES = frozenset(("source.bin", "destination.bin", "replacement.bin", "prepared.json", "result.json", "reconciled.json"))

    def __init__(self, content=b"synthetic log"):
        if os.name != "nt":
            raise MoveDeleteProbeError("probe_windows_required")
        if type(content) is not bytes or len(content) > 1024 * 1024:
            raise MoveDeleteProbeError("probe_content_invalid")
        from ctypes import wintypes as w
        self._api = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, args, result in (
            ("CreateFileW", (w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE), w.HANDLE),
            ("CloseHandle", (w.HANDLE,), w.BOOL),
            ("GetFileInformationByHandleEx", (w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD), w.BOOL),
            ("SetFileInformationByHandle", (w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD), w.BOOL),
            ("ReadFile", (w.HANDLE, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID), w.BOOL),
            ("GetFileAttributesW", (w.LPCWSTR,), w.DWORD),
        ):
            function = getattr(self._api, name)
            function.argtypes, function.restype = args, result

        class FileIdInfo(ctypes.Structure):
            _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong), ("FileId", ctypes.c_ubyte * 16)]

        class StandardInfo(ctypes.Structure):
            _fields_ = [("AllocationSize", ctypes.c_longlong), ("EndOfFile", ctypes.c_longlong),
                        ("NumberOfLinks", w.DWORD), ("DeletePending", ctypes.c_ubyte), ("Directory", ctypes.c_ubyte)]

        class AttributeInfo(ctypes.Structure):
            _fields_ = [("FileAttributes", w.DWORD), ("ReparseTag", w.DWORD)]

        self._structures = (FileIdInfo, StandardInfo, AttributeInfo)
        self._parent = Path(tempfile.gettempdir()).resolve(strict=True)
        self._root = Path(tempfile.mkdtemp(prefix="eolm-move-delete-", dir=self._parent))
        self._nonce = uuid4().hex.encode("ascii")
        self._chain = self._directory_chain()
        self._reader = None
        self._prepared_bytes = None
        (self._root / ".probe-owner").write_bytes(self._nonce)
        for name in ("source.bin", "destination.bin"):
            with (self._root / name).open("xb") as stream:
                stream.write(content)
        self._baseline = hashlib.sha256(content).hexdigest()
        self._size = len(content)
        with self._handle("source.bin") as handle:
            self._source_id = self._info(handle)[0]
        with self._handle("destination.bin") as handle:
            self._destination_id = self._info(handle)[0]

    def _directory_chain(self):
        chain = []
        for path in (self._root, *self._root.parents):
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise MoveDeleteProbeError("probe_root_changed")
            chain.append((info.st_dev, info.st_ino))
        return tuple(chain)

    def _verify_root(self):
        if (self._root.parent != self._parent or not self._root.name.startswith("eolm-move-delete-")
                or self._root.resolve(strict=True) != self._root or self._directory_chain() != self._chain):
            raise MoveDeleteProbeError("probe_root_changed")
        marker = self._root / ".probe-owner"
        info = marker.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & 0x400 or marker.read_bytes() != self._nonce):
            raise MoveDeleteProbeError("probe_root_changed")

    def _path(self, name, *, existing=True):
        if name not in self._NAMES:
            raise MoveDeleteProbeError("probe_name_invalid")
        self._verify_root()
        path = self._root / name
        if existing:
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or getattr(info, "st_file_attributes", 0) & 0x400):
                raise MoveDeleteProbeError("probe_file_changed")
        return path

    def _open(self, name, *, access=0x80000000, share=1):
        # OPEN_EXISTING + OPEN_REPARSE_POINT. No path-based delete is used.
        handle = self._api.CreateFileW(str(self._path(name)), access, share, None, 3, 0x00200000, None)
        if handle in (None, ctypes.c_void_p(-1).value):
            raise MoveDeleteProbeError("probe_open_failed")
        return handle

    def _close(self, handle):
        if not self._api.CloseHandle(handle):
            raise MoveDeleteProbeError("probe_close_failed")

    @contextmanager
    def _handle(self, name, **options):
        handle = self._open(name, **options)
        try:
            yield handle
        finally:
            self._close(handle)

    def _info(self, handle):
        identity, standard, attributes = (kind() for kind in self._structures)
        for info_class, value in ((18, identity), (1, standard), (9, attributes)):
            if not self._api.GetFileInformationByHandleEx(handle, info_class, ctypes.byref(value), ctypes.sizeof(value)):
                raise MoveDeleteProbeError("probe_metadata_failed")
        if (standard.Directory or standard.NumberOfLinks != 1 or attributes.FileAttributes & 0x410
                or standard.EndOfFile < 0 or standard.EndOfFile > 1024 * 1024):
            raise MoveDeleteProbeError("probe_file_changed")
        return (identity.VolumeSerialNumber, bytes(identity.FileId).hex()), standard.EndOfFile

    def _content(self, handle):
        before = self._info(handle)
        digest, size = hashlib.sha256(), 0
        buffer, read = ctypes.create_string_buffer(65536), ctypes.c_ulong()
        while True:
            if not self._api.ReadFile(handle, buffer, len(buffer), ctypes.byref(read), None):
                raise MoveDeleteProbeError("probe_read_failed")
            if read.value == 0:
                break
            size += read.value
            if size > 1024 * 1024:
                raise MoveDeleteProbeError("probe_read_failed")
            digest.update(buffer.raw[:read.value])
        if self._info(handle) != before or size != before[1]:
            raise MoveDeleteProbeError("probe_file_changed")
        return before[0], size, digest.hexdigest()

    def _write_record(self, name, value):
        data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        path = self._path(name, existing=False)
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if self._path(name).read_bytes() != data:
            raise MoveDeleteProbeError("probe_record_failed")
        return data

    def _absence(self):
        self._verify_root()
        attributes = self._api.GetFileAttributesW(str(self._root / "source.bin"))
        if attributes != 0xffffffff:
            return False
        # Only in this intact self-created fixture; not a runtime absence permit.
        return ctypes.get_last_error() == 2

    def competing_open(self, access):
        """Attempt a fixed synthetic source write/delete open while guard is held."""
        handle = self._api.CreateFileW(str(self._path("source.bin")), access, 7, None, 3, 0x00200000, None)
        if handle in (None, ctypes.c_void_p(-1).value):
            return False, ctypes.get_last_error()
        self._close(handle)
        return True, 0

    def run(self, *, fault=None, keep_reader=False):
        if fault not in (None, "source_changed", "source_replaced", "destination_changed", "destination_replaced", "record_failed", "result_record_failed"):
            raise MoveDeleteProbeError("probe_fault_invalid")
        if fault == "source_changed":
            self._path("source.bin").write_bytes(b"changed")
        elif fault == "source_replaced":
            self._path("replacement.bin", existing=False).write_bytes(self._path("source.bin").read_bytes())
            os.replace(self._path("replacement.bin"), self._path("source.bin"))
        elif fault == "destination_changed":
            self._path("destination.bin").write_bytes(b"changed")
        elif fault == "destination_replaced":
            self._path("replacement.bin", existing=False).write_bytes(self._path("destination.bin").read_bytes())
            os.replace(self._path("replacement.bin"), self._path("destination.bin"))
        if keep_reader:
            self._reader = self._open("source.bin", share=5)  # READ | DELETE sharing
        with self._handle("destination.bin") as destination:
            with self._handle("source.bin", access=0x80010000) as source:  # READ | DELETE
                current_source = self._content(source)
                current_destination = self._content(destination)
                if current_source != (self._source_id, self._size, self._baseline):
                    return {"status": "retained", "reason": "source_changed"}
                if current_destination != (self._destination_id, self._size, self._baseline):
                    return {"status": "retained", "reason": "destination_changed"}
                if fault == "record_failed":
                    return {"status": "retained", "reason": "record_failed"}
                prepared = {"kind": "probe-prepared-v0", "source_id": self._source_id,
                            "destination_id": self._destination_id, "size": self._size, "sha256": self._baseline}
                try:
                    self._prepared_bytes = self._write_record("prepared.json", prepared)
                except (OSError, MoveDeleteProbeError):
                    return {"status": "retained", "reason": "record_failed"}
                writer, writer_error = self.competing_open(0x40000000)
                deleter, delete_error = self.competing_open(0x10000)
                if writer or deleter or writer_error != 32 or delete_error != 32:
                    return {"status": "retained", "reason": "sharing_guard_unconfirmed"}
                self._verify_root()
                if (self._info(source) != (self._source_id, self._size)
                        or self._info(destination) != (self._destination_id, self._size)):
                    return {"status": "retained", "reason": "identity_changed"}
                # FILE_DISPOSITION_INFO uses BOOLEAN, not Win32 BOOL.
                disposition = ctypes.c_ubyte(1)
                if not self._api.SetFileInformationByHandle(source, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)):
                    return {"status": "retained", "reason": "delete_failed"}
            # Source handle is closed; destination guard is still held.
            absent = self._absence()
            if fault == "result_record_failed":
                return {"status": "unknown", "reason": "result_record_failed"}
            result = {"status": "completed" if absent else "unknown",
                      "reason": "delete_confirmed" if absent else "delete_pending",
                      "write_open_blocked": True, "delete_open_blocked": True}
            try:
                self._write_record("result.json", result)
            except (OSError, MoveDeleteProbeError):
                return {"status": "unknown", "reason": "result_record_failed"}
            return result

    def release_reader(self):
        if self._reader is not None:
            reader, self._reader = self._reader, None
            self._close(reader)

    def reconcile(self):
        self._verify_root()
        try:
            if self._prepared_bytes is None or self._path("prepared.json").read_bytes() != self._prepared_bytes:
                return {"status": "unknown", "reason": "record_invalid"}
            with self._handle("destination.bin") as destination:
                current = self._content(destination)
                if current != (self._destination_id, self._size, self._baseline) or not self._absence():
                    return {"status": "unknown", "reason": "state_unconfirmed"}
                result = {"status": "completed", "reason": "reconciled_completion"}
                record = dict(result, prepared_sha256=hashlib.sha256(self._prepared_bytes).hexdigest())
                path = self._path("reconciled.json", existing=False)
                if path.exists():
                    if json.loads(self._path("reconciled.json").read_bytes()) != record:
                        return {"status": "unknown", "reason": "record_invalid"}
                else:
                    self._write_record("reconciled.json", record)
        except (OSError, MoveDeleteProbeError):
            return {"status": "unknown", "reason": "state_unconfirmed"}
        except ValueError:
            return {"status": "unknown", "reason": "record_failed"}
        return result

    def close(self):
        self.release_reader()
        self._verify_root()
        shutil.rmtree(self._root)
