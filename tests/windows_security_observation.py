"""TEST ONLY: private security facts bound to already-held fixture handles.

No path lookup, ACL mutation, effective-access decision or runtime permission.
"""
import ctypes
from dataclasses import dataclass,field

from windows_move_delete_probe import MoveDeleteProbeError


@dataclass(frozen=True,repr=False)
class HandleSecurityObservation:
    object_kind: str
    identity: tuple
    descriptor_bytes: bytes
    owner_sid: str
    process_user_sid: str
    dacl_present: bool
    dacl_null: bool
    dacl_protected: bool
    may_change_state: bool=field(default=False,init=False)


class NativeSecurityObserver:
    def __init__(self,probe):
        from ctypes import wintypes as w
        self.probe=probe
        self.kernel=probe._api
        self.security=ctypes.WinDLL('advapi32',use_last_error=True)
        pointer=ctypes.POINTER(ctypes.c_void_p)
        for name,args,result in (
            ('GetSecurityInfo',(w.HANDLE,ctypes.c_int,w.DWORD,pointer,pointer,pointer,pointer,pointer),w.DWORD),
            ('IsValidSecurityDescriptor',(w.LPVOID,),w.BOOL),
            ('GetSecurityDescriptorControl',(w.LPVOID,ctypes.POINTER(w.WORD),ctypes.POINTER(w.DWORD)),w.BOOL),
            ('GetSecurityDescriptorLength',(w.LPVOID,),w.DWORD),
            ('ConvertSidToStringSidW',(w.LPVOID,pointer),w.BOOL),
            ('OpenProcessToken',(w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)),w.BOOL),
            ('OpenThreadToken',(w.HANDLE,w.DWORD,w.BOOL,ctypes.POINTER(w.HANDLE)),w.BOOL),
            ('GetTokenInformation',(w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD,ctypes.POINTER(w.DWORD)),w.BOOL),
            ('IsValidSid',(w.LPVOID,),w.BOOL),
            ('GetLengthSid',(w.LPVOID,),w.DWORD),
        ):
            function=getattr(self.security,name);function.argtypes=args;function.restype=result
        self.kernel.GetCurrentProcess.argtypes=();self.kernel.GetCurrentProcess.restype=w.HANDLE
        self.kernel.GetCurrentThread.argtypes=();self.kernel.GetCurrentThread.restype=w.HANDLE
        self.kernel.LocalFree.argtypes=(w.HLOCAL,);self.kernel.LocalFree.restype=w.HLOCAL

    def _require(self,condition):
        if not condition:
            raise MoveDeleteProbeError('probe_security_observation_failed')

    def _free(self,pointer):
        if pointer:
            self._require(not self.kernel.LocalFree(pointer))

    def _sid(self,pointer):
        self._require(pointer and self.security.IsValidSid(pointer))
        text=ctypes.c_void_p()
        try:
            self._require(self.security.ConvertSidToStringSidW(pointer,ctypes.byref(text)))
            value=ctypes.wstring_at(text.value)
            self._require(value.startswith('S-1-') and len(value)<=184)
            return value
        finally:
            self._free(text)

    def process_user_sid(self):
        from ctypes import wintypes as w
        token=w.HANDLE();needed=w.DWORD()
        self._require(self.security.OpenProcessToken(self.kernel.GetCurrentProcess(),8,ctypes.byref(token)))
        try:
            self._require(not self.security.GetTokenInformation(token,1,None,0,ctypes.byref(needed))
                          and ctypes.get_last_error()==122 and ctypes.sizeof(ctypes.c_void_p)<=needed.value<=65536)
            buffer=ctypes.create_string_buffer(needed.value);capacity=len(buffer)
            self._require(self.security.GetTokenInformation(token,1,buffer,capacity,ctypes.byref(needed)) and needed.value<=capacity)
            sid=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_void_p)).contents.value
            start=ctypes.addressof(buffer)
            self._require(sid and start<=sid and sid+8<=start+needed.value)
            self._require(self.security.IsValidSid(sid))
            self._require(sid+self.security.GetLengthSid(sid)<=start+needed.value)
            return self._sid(sid)
        finally:
            self.probe._close(token)

    def _require_primary_context(self):
        from ctypes import wintypes as w
        token=w.HANDLE()
        if self.security.OpenThreadToken(self.kernel.GetCurrentThread(),8,True,ctypes.byref(token)):
            self.probe._close(token)
            raise MoveDeleteProbeError('probe_security_context_unconfirmed')
        if ctypes.get_last_error()!=1008:  # ERROR_NO_TOKEN alone confirms absence.
            raise MoveDeleteProbeError('probe_security_context_unconfirmed')

    def _identity(self,handle):
        identity=self.probe._structures[0]();attributes=self.probe._structures[2]()
        for kind,value in ((18,identity),(9,attributes)):
            self._require(self.kernel.GetFileInformationByHandleEx(handle,kind,ctypes.byref(value),ctypes.sizeof(value)))
        self._require(not attributes.FileAttributes&0x400)
        return ('directory' if attributes.FileAttributes&0x10 else 'file',
                (identity.VolumeSerialNumber,bytes(identity.FileId).hex()))

    def read(self,handle):
        from ctypes import wintypes as w
        self._require_primary_context()
        before=self._identity(handle)
        descriptor=ctypes.c_void_p();owner=ctypes.c_void_p();dacl=ctypes.c_void_p()
        try:
            result=self.security.GetSecurityInfo(handle,1,5,ctypes.byref(owner),None,ctypes.byref(dacl),None,ctypes.byref(descriptor))
            self._require(result==0 and descriptor and self.security.IsValidSecurityDescriptor(descriptor))
            control=w.WORD();revision=w.DWORD()
            self._require(self.security.GetSecurityDescriptorControl(descriptor,ctypes.byref(control),ctypes.byref(revision))
                          and revision.value==1 and control.value&0x8000)
            size=self.security.GetSecurityDescriptorLength(descriptor)
            self._require(20<=size<=65536)
            self._require(owner.value and descriptor.value<=owner.value and owner.value+8<=descriptor.value+size)
            owner_sid=self._sid(owner)
            raw=ctypes.string_at(descriptor,size)
            process_sid=self.process_user_sid()
            self._require(self._identity(handle)==before)
            self._require_primary_context()
            return HandleSecurityObservation(before[0],before[1],raw,owner_sid,process_sid,
                bool(control.value&4),not bool(dacl),bool(control.value&0x1000))
        finally:
            self._free(descriptor)
