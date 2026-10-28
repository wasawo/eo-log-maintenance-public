"""TEST ONLY: narrow explicit DACL on one constructor-owned directory.

Never used by the observer or product; cannot accept a caller path or SDDL.
"""
import ctypes
from windows_security_observation import NativeSecurityObserver
from windows_move_delete_probe import MoveDeleteProbeError


def protect_fixture_directory(probe,kind):
    from ctypes import wintypes as w
    paths={'root':probe._root,'ownership':probe._ownership_root,'journal':probe._journal_root}
    if kind not in paths:
        raise MoveDeleteProbeError('probe_fixture_acl_scope_invalid')
    probe._verify_root()
    observer=NativeSecurityObserver(probe);sid=observer.process_user_sid();security=observer.security
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes=(w.LPCWSTR,w.DWORD,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(w.DWORD))
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype=w.BOOL
    security.SetSecurityInfo.argtypes=(w.HANDLE,ctypes.c_int,w.DWORD,w.LPVOID,w.LPVOID,w.LPVOID,w.LPVOID)
    security.SetSecurityInfo.restype=w.DWORD
    security.GetSecurityDescriptorDacl.argtypes=(w.LPVOID,ctypes.POINTER(w.BOOL),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(w.BOOL))
    security.GetSecurityDescriptorDacl.restype=w.BOOL
    descriptor=ctypes.c_void_p();handle=None
    try:
        sddl='D:P(A;OICI;FA;;;'+sid+')(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'
        observer._require(security.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,ctypes.byref(descriptor),None))
        present=w.BOOL();defaulted=w.BOOL();dacl=ctypes.c_void_p()
        observer._require(security.GetSecurityDescriptorDacl(descriptor,ctypes.byref(present),ctypes.byref(dacl),ctypes.byref(defaulted)) and present and dacl)
        # READ_CONTROL | WRITE_DAC, self-created directory only.
        handle=probe._api.CreateFileW(str(paths[kind]),0x60000,7,None,3,0x02200000,None)
        observer._require(handle not in (None,ctypes.c_void_p(-1).value))
        observer._require(security.SetSecurityInfo(handle,1,0x80000004,None,None,dacl,None)==0)
    finally:
        if handle not in (None,ctypes.c_void_p(-1).value):probe._close(handle)
        observer._free(descriptor)
