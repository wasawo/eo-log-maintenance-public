"""TEST ONLY: same-process ownership around constructor-owned native deletion.

No caller-selected paths, production provider, or ownership broker is exposed.
"""
from contextlib import contextmanager
import ctypes
import hashlib
from Common.ArtifactSetDirectoryVerification import _chain
from Common.OwnedRunLock import acquire_owned_lock, _record_matches, _strict_record_bytes
from windows_move_delete_probe import DisposableMoveDeleteProbe, MoveDeleteProbeError


class OwnedDisposableMoveDeleteProbe(DisposableMoveDeleteProbe):
    def __init__(self, content=b'synthetic log'):
        super().__init__(content,journal=True)
        self._ownership_root=self._root/'ownership'
        self._ownership_root.mkdir()
        self._ownership_chain=_chain(self._ownership_root)
        self._lock_path=self._ownership_root/'run.lock'
        self._scope='NativeMoveProbe-'+self._nonce.decode('ascii')

    def run_owned(self, *, at_checkpoint=None, **options):
        self._verify_root()
        if _chain(self._ownership_root) != self._ownership_chain:
            raise MoveDeleteProbeError('probe_ownership_root_changed')
        with acquire_owned_lock(self._scope,self._lock_path,timeout_seconds=0,maximum_record_bytes=4096) as token:
            with self._owner_record_handle(token):
                def verify(phase):
                    # Test-only fault injection runs BEFORE ownership observation.
                    if at_checkpoint is not None:
                        at_checkpoint(phase)
                    self._verify_root()
                    return (_chain(self._ownership_root) == self._ownership_chain
                            and _record_matches(self._lock_path,self._scope,token,4096))
                return self.run(ownership_check=verify,**options)

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
