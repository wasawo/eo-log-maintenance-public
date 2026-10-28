"""TEST ONLY: verify/copy-record/handle-delete in a fresh synthetic temp root.

No caller-selected path or production provider is exposed. Optional v1 records
support a separate test-only cold observer, not production restart recovery.
"""
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
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
    _NAMES = frozenset(("source.bin", "destination.bin", "replacement.bin", "prepared.json", "result.json", "reconciled.json", "fixture.json"))

    def __init__(self, content=b"synthetic log", *, journal=False):
        if os.name != "nt":
            raise MoveDeleteProbeError("probe_windows_required")
        if type(content) is not bytes or len(content) > 1024 * 1024:
            raise MoveDeleteProbeError("probe_content_invalid")
        self._initialize_api()
        self._parent = Path(tempfile.gettempdir()).resolve(strict=True)
        self._root = Path(tempfile.mkdtemp(prefix="eolm-move-delete-", dir=self._parent))
        self._nonce = uuid4().hex.encode("ascii")
        self._chain = self._directory_chain()
        self._reader = None
        self._prepared_bytes = None
        self._journal_enabled = journal
        self._journal_prepared = None
        self._journal_prepared_bytes = None
        (self._root / ".probe-owner").write_bytes(self._nonce)
        if journal:
            (self._root / "journal").mkdir()
        for name in ("source.bin", "destination.bin"):
            with (self._root / name).open("xb") as stream:
                stream.write(content)
        self._baseline = hashlib.sha256(content).hexdigest()
        self._size = len(content)
        with self._handle("source.bin") as handle:
            self._source_id = self._info(handle)[0]
        with self._handle("destination.bin") as handle:
            self._destination_id = self._info(handle)[0]

    def _initialize_api(self):
        """Native declarations only; reused by the read-only cold observer."""
        from ctypes import wintypes as w
        self._api = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, args, result in (
            ("CreateFileW", (w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE), w.HANDLE),
            ("CloseHandle", (w.HANDLE,), w.BOOL),
            ("GetFileInformationByHandleEx", (w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD), w.BOOL),
            ("SetFileInformationByHandle", (w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD), w.BOOL),
            ("ReadFile", (w.HANDLE, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID), w.BOOL),
            ("SetFilePointerEx", (w.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), w.DWORD), w.BOOL),
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
        # These are private synchronous handles, never shared between readers.
        if not self._api.SetFilePointerEx(handle, 0, None, 0):  # FILE_BEGIN
            raise MoveDeleteProbeError("probe_seek_failed")
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

    def _save_journal_prepared(self):
        from Common.MoveJournal import encode_move_record, save_move_record
        baseline = dict(size=self._size, sha256=self._baseline)
        source = dict(kind='local', machine_id='PC-A', root_key='battleLogLocal', relative_path='source.bin',
                      identity=dict(volume_serial=f'{self._source_id[0]:016x}', file_id=self._source_id[1]))
        destination = dict(kind='cloud', root_key='battleLogDrive', file_id='synthetic-cloud-object',
                           parent_id='synthetic-parent', name='source.bin', version='1')
        value = dict(record_version=1, record_id=str(uuid4()), run_id=str(uuid4()), move_id=str(uuid4()),
                     attempt_id=str(uuid4()), event_kind='prepared', route='local_to_cloud', machine_id='PC-A',
                     log_type='BattleLog', observed_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                     recorded_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                     prior_record_refs=[], event_data=dict(source=source, destination=destination, copy_content=baseline,
                     destination_content=baseline, reused=False, destination_method='drive_download'))
        raw = encode_move_record(value)
        save_move_record(self._root / 'journal', raw)
        self._write_record('fixture.json', dict(kind='cold-move-fixture-v1', prepared_id=value['record_id'],
            prepared_sha256=hashlib.sha256(raw).hexdigest(), destination_id=self._destination_id,
            root_chain=self._chain))
        self._journal_prepared = value
        self._journal_prepared_bytes = raw

    @contextmanager
    def _journal_prepared_handle(self):
        # Fixed constructor-owned journal record only, never a caller path.
        self._verify_root()
        directory=self._root/'journal'
        info=directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
            raise MoveDeleteProbeError('probe_record_failed')
        path=directory/(self._journal_prepared['record_id']+'.json')
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or getattr(info,'st_file_attributes',0)&0x400:
            raise MoveDeleteProbeError('probe_record_failed')
        handle=self._api.CreateFileW(str(path),0x80000000,1,None,3,0x00200000,None)
        if handle in (None,ctypes.c_void_p(-1).value):
            raise MoveDeleteProbeError('probe_record_failed')
        try:
            yield handle
        finally:
            self._close(handle)

    def _save_journal_result(self, result):
        from Common.MoveJournal import encode_move_record, save_move_record
        p = self._journal_prepared
        raw = (self._root / 'journal' / (p['record_id'] + '.json')).read_bytes()
        value = dict(p, record_id=str(uuid4()), event_kind='deletion_result',
                     observed_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                     recorded_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), prior_record_refs=[
            dict(record_id=p['record_id'], path=p['record_id']+'.json', sha256=hashlib.sha256(raw).hexdigest())])
        complete = result['status'] == 'completed'
        value['event_data'] = dict(source=p['event_data']['source'], destination=p['event_data']['destination'],
            source_before_delete=p['event_data']['copy_content'], destination_current=p['event_data']['copy_content'],
            source_method='windows_handle', destination_method='drive_download', request_outcome='succeeded',
            source_after_delete='absent' if complete else 'unknown', source_after_method='windows_lookup' if complete else 'unavailable',
            decision='completed' if complete else 'unknown', completion_basis='delete_confirmed' if complete else 'none',
            reason_code='delete_confirmed' if complete else 'delete_pending')
        save_move_record(self._root / 'journal', encode_move_record(value))

    def run(self, *, fault=None, keep_reader=False, ownership_check=None):
        ownership_lost = False
        def owned(phase):
            nonlocal ownership_lost
            if ownership_check is None:
                return True
            if ownership_lost:
                return False
            try:
                result = ownership_check(phase)
                if type(result) is not bool or not result:
                    raise MoveDeleteProbeError('probe_ownership_unconfirmed')
                return True
            except Exception:
                ownership_lost = True
                return False
        if not owned('before_open'):
            return dict(status='retained',reason='ownership_unconfirmed')
        if fault not in (None, "source_changed", "source_replaced", "destination_changed", "destination_replaced", "record_failed", "result_record_failed", "after_prepare"):
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
        with ExitStack() as record_guards, self._handle("destination.bin") as destination:
            with self._handle("source.bin", access=0x80010000) as source:  # READ | DELETE
                current_source = self._content(source)
                current_destination = self._content(destination)
                if current_source != (self._source_id, self._size, self._baseline):
                    return {"status": "retained", "reason": "source_changed"}
                if current_destination != (self._destination_id, self._size, self._baseline):
                    return {"status": "retained", "reason": "destination_changed"}
                if fault == "record_failed":
                    return {"status": "retained", "reason": "record_failed"}
                if not owned('before_prepared'):
                    return dict(status='retained',reason='ownership_unconfirmed')
                prepared = {"kind": "probe-prepared-v0", "source_id": self._source_id,
                            "destination_id": self._destination_id, "size": self._size, "sha256": self._baseline}
                try:
                    self._prepared_bytes = self._write_record("prepared.json", prepared)
                    if self._journal_enabled:
                        self._save_journal_prepared()
                except (OSError, ValueError, MoveDeleteProbeError):
                    return {"status": "retained", "reason": "record_failed"}
                if fault == 'after_prepare':
                    return {"status": "retained", "reason": "interrupted_before_delete"}
                if not owned('after_prepared'):
                    return dict(status='retained',reason='ownership_unconfirmed')
                try:
                    prepared_guard=record_guards.enter_context(self._handle('prepared.json'))
                    proof=self._content(prepared_guard)
                    if proof[1:] != (len(self._prepared_bytes),hashlib.sha256(self._prepared_bytes).hexdigest()):
                        return dict(status='retained',reason='record_invalid')
                    if self._journal_enabled:
                        journal_guard=record_guards.enter_context(self._journal_prepared_handle())
                        proof=self._content(journal_guard)
                        if proof[1:] != (len(self._journal_prepared_bytes),hashlib.sha256(self._journal_prepared_bytes).hexdigest()):
                            return dict(status='retained',reason='record_invalid')
                except (OSError,MoveDeleteProbeError):
                    return dict(status='retained',reason='record_invalid')
                writer, writer_error = self.competing_open(0x40000000)
                deleter, delete_error = self.competing_open(0x10000)
                if writer or deleter or writer_error != 32 or delete_error != 32:
                    return {"status": "retained", "reason": "sharing_guard_unconfirmed"}
                self._verify_root()
                if (self._info(source) != (self._source_id, self._size)
                        or self._info(destination) != (self._destination_id, self._size)):
                    return {"status": "retained", "reason": "identity_changed"}
                if not owned('before_delete'):
                    return dict(status='retained',reason='ownership_unconfirmed')
                # Record publication and ownership verification can take time.
                # Re-read Q5 on the SAME source/destination handles afterwards.
                if self._content(source) != (self._source_id,self._size,self._baseline):
                    return dict(status='retained',reason='source_changed')
                if self._content(destination) != (self._destination_id,self._size,self._baseline):
                    return dict(status='retained',reason='destination_changed')
                if self._path('prepared.json').read_bytes() != self._prepared_bytes:
                    return dict(status='retained',reason='record_invalid')
                # FILE_DISPOSITION_INFO uses BOOLEAN, not Win32 BOOL.
                disposition = ctypes.c_ubyte(1)
                if not self._api.SetFileInformationByHandle(source, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)):
                    return {"status": "retained", "reason": "delete_failed"}
            # Source handle is closed; destination guard is still held.
            if not owned('after_delete'):
                return dict(status='unknown',reason='ownership_unconfirmed_after_delete')
            absent = self._absence()
            if fault == "result_record_failed":
                return {"status": "unknown", "reason": "result_record_failed"}
            result = {"status": "completed" if absent else "unknown",
                      "reason": "delete_confirmed" if absent else "delete_pending",
                      "write_open_blocked": True, "delete_open_blocked": True}
            try:
                self._write_record("result.json", result)
                if self._journal_enabled:
                    self._save_journal_result(result)
            except (OSError, ValueError, MoveDeleteProbeError):
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
