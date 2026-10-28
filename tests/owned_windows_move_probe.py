"""TEST ONLY: same-process ownership around constructor-owned native deletion.

No caller-selected paths, production provider, or ownership broker is exposed.
"""
from contextlib import contextmanager, ExitStack
import ctypes
import hashlib
from Common.ArtifactSetDirectoryVerification import _chain
from Common.OwnedRunLock import acquire_owned_lock, _record_matches, _strict_record_bytes
from windows_move_delete_probe import DisposableMoveDeleteProbe, MoveDeleteProbeError
from windows_security_observation import NativeSecurityObserver


class OwnedDisposableMoveDeleteProbe(DisposableMoveDeleteProbe):
    def __init__(self, content=b'synthetic log'):
        super().__init__(content,journal=True)
        self._ownership_root=self._root/'ownership'
        self._ownership_root.mkdir()
        self._ownership_chain=_chain(self._ownership_root)
        self._journal_root=self._root/'journal'
        self._journal_chain=_chain(self._journal_root)
        self._lock_path=self._ownership_root/'run.lock'
        self._scope='NativeMoveProbe-'+self._nonce.decode('ascii')

    def run_owned(self, *, at_checkpoint=None, **options):
        self._verify_root()
        if _chain(self._ownership_root) != self._ownership_chain:
            raise MoveDeleteProbeError('probe_ownership_root_changed')
        if _chain(self._journal_root) != self._journal_chain:
            raise MoveDeleteProbeError('probe_journal_root_changed')
        with ExitStack() as directories:
            handles=[directories.enter_context(self._directory_handle(path)) for path in (self._root,self._ownership_root,self._journal_root)]
            observer=NativeSecurityObserver(self)
            baseline=[observer.read(handle) for handle in handles]
            def unchanged_security():
                return [observer.read(handle) for handle in handles]==baseline
            return self._run_with_owner(at_checkpoint,options,unchanged_security)

    def _run_with_owner(self,at_checkpoint,options,unchanged_security):
        with acquire_owned_lock(self._scope,self._lock_path,timeout_seconds=0,maximum_record_bytes=4096) as token:
            with self._owner_record_handle(token):
                def verify(phase):
                    # Test-only fault injection runs BEFORE ownership observation.
                    if at_checkpoint is not None:
                        at_checkpoint(phase)
                    self._verify_root()
                    return (_chain(self._ownership_root) == self._ownership_chain
                            and _chain(self._journal_root) == self._journal_chain
                            and unchanged_security()
                            and _record_matches(self._lock_path,self._scope,token,4096))
                return self.run(ownership_check=verify,**options)

    @contextmanager
    def _directory_handle(self,path):
        # Only three constructor-owned directories can reach this method.
        if path not in (self._root,self._ownership_root,self._journal_root):
            raise MoveDeleteProbeError('probe_directory_guard_invalid')
        self._verify_root()
        # BACKUP_SEMANTICS | OPEN_REPARSE_POINT; allow READ/WRITE, deny DELETE.
        handle=self._api.CreateFileW(str(path),0x80000000,3,None,3,0x02200000,None)
        if handle in (None,ctypes.c_void_p(-1).value):
            raise MoveDeleteProbeError('probe_directory_guard_failed')
        try:
            attributes=self._structures[2]()
            if (not self._api.GetFileInformationByHandleEx(handle,9,ctypes.byref(attributes),ctypes.sizeof(attributes))
                    or not attributes.FileAttributes&0x10 or attributes.FileAttributes&0x400):
                raise MoveDeleteProbeError('probe_directory_guard_invalid')
            self._verify_root()
            if _chain(self._ownership_root) != self._ownership_chain:
                raise MoveDeleteProbeError('probe_ownership_root_changed')
            if _chain(self._journal_root) != self._journal_chain:
                raise MoveDeleteProbeError('probe_journal_root_changed')
            yield handle
        finally:
            self._close(handle)

    @contextmanager
    def _owner_record_handle(self,token):
        self._verify_root()
        handle=self._api.CreateFileW(str(self._lock_path),0x80000000,1,None,3,0x00200000,None)
        if handle in (None,ctypes.c_void_p(-1).value):
            raise MoveDeleteProbeError('probe_ownership_guard_failed')
        try:
            expected=_strict_record_bytes(self._scope,token)
            proof=self._content(handle)
            if proof[1:] != (len(expected),hashlib.sha256(expected).hexdigest()):
                raise MoveDeleteProbeError('probe_ownership_guard_failed')
            yield handle
        finally:
            self._close(handle)
