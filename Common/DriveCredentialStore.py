"""Explicit Windows current-user DPAPI store; never discovers credentials."""
import ctypes as c
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import uuid
from contextlib import contextmanager

from Common.PrivateEvidenceAclProfile import assess_private_file_acl


class CredentialStoreError(ValueError):
    def __init__(self):
        super().__init__('credential_store_unconfirmed')


class Blob(c.Structure):
    _fields_ = [('size', w.DWORD), ('data', c.c_void_p)]


class SecurityAttributes(c.Structure):
    _fields_ = [('size', w.DWORD), ('descriptor', c.c_void_p), ('inherit', w.BOOL)]


class WindowsProtection:
    def __init__(self):
        if os.name != 'nt': raise CredentialStoreError()
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        self.advapi = c.WinDLL('advapi32', use_last_error=True)
        self.crypt = c.WinDLL('crypt32', use_last_error=True)
        self.kernel.GetCurrentProcess.restype = w.HANDLE
        self.kernel.LocalFree.argtypes = [c.c_void_p]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
        self.kernel.CreateFileW.restype = w.HANDLE
        self.kernel.CreateDirectoryW.argtypes = [w.LPCWSTR, c.c_void_p]
        self.advapi.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
        self.advapi.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
        self.advapi.ConvertSidToStringSidW.argtypes = [c.c_void_p, c.POINTER(w.LPWSTR)]
        self.advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p]
        self.advapi.GetNamedSecurityInfoW.argtypes = [w.LPWSTR, c.c_int, w.DWORD] + [c.POINTER(c.c_void_p)] * 5
        self.advapi.GetSecurityDescriptorControl.argtypes = [c.c_void_p, c.POINTER(w.WORD), c.POINTER(w.DWORD)]
        self.advapi.GetAce.argtypes = [c.c_void_p, w.DWORD, c.POINTER(c.c_void_p)]
        token = w.HANDLE()
        if not self.advapi.OpenProcessToken(self.kernel.GetCurrentProcess(), 8, c.byref(token)): raise CredentialStoreError()
        try:
            size = w.DWORD()
            self.advapi.GetTokenInformation(token, 1, None, 0, c.byref(size))
            buf = c.create_string_buffer(size.value)
            if not self.advapi.GetTokenInformation(token, 1, buf, size, c.byref(size)): raise CredentialStoreError()
            self.sid = self.sid_string(c.c_void_p.from_buffer(buf).value)
        finally:
            self.kernel.CloseHandle(token)

    def sid_string(self, sid):
        result = w.LPWSTR()
        if not self.advapi.ConvertSidToStringSidW(sid, c.byref(result)): raise CredentialStoreError()
        try: return result.value
        finally: self.kernel.LocalFree(c.cast(result, c.c_void_p))

    def descriptor(self):
        result = c.c_void_p()
        if not self.advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                f'O:{self.sid}D:P(A;;FA;;;{self.sid})', 1, c.byref(result), None): raise CredentialStoreError()
        return result

    def create_directory(self, path):
        """Explicit provisioning only; never called by load/service generation."""
        sd = self.descriptor()
        try:
            sa = SecurityAttributes(c.sizeof(SecurityAttributes), sd, False)
            if not self.kernel.CreateDirectoryW(str(path), c.byref(sa)): raise CredentialStoreError()
        finally: self.kernel.LocalFree(sd)

    def validate_acl(self, path):
        owner, group, dacl, sacl, sd = (c.c_void_p() for _ in range(5))
        if self.advapi.GetNamedSecurityInfoW(str(path), 1, 5, c.byref(owner), c.byref(group),
                c.byref(dacl), c.byref(sacl), c.byref(sd)): raise CredentialStoreError()
        try:
            control, revision = w.WORD(), w.DWORD()
            if not self.advapi.GetSecurityDescriptorControl(sd, c.byref(control), c.byref(revision)) or not dacl.value:
                raise CredentialStoreError()
            count = c.c_ushort.from_address(dacl.value + 4).value
            aces = []
            for index in range(count):
                ace = c.c_void_p()
                if not self.advapi.GetAce(dacl, index, c.byref(ace)): raise CredentialStoreError()
                kind, flags = c.string_at(ace, 2)
                if kind != 0: raise CredentialStoreError()
                aces.append(dict(sid=self.sid_string(ace.value + 8), type='allow' if kind == 0 else 'unsupported',
                    flags=flags, mask=c.c_uint32.from_address(ace.value + 4).value))
            snapshot = dict(object_kind='file', owner_sid=self.sid_string(owner), dacl_present=bool(control.value & 4),
                dacl_null=False, dacl_protected=bool(control.value & 0x1000), aces=aces)
            if not assess_private_file_acl(snapshot, execution_sid=self.sid).profile_matches: raise CredentialStoreError()
        finally: self.kernel.LocalFree(sd)

    def open_private(self, path, disposition):
        import msvcrt
        sd = self.descriptor()
        try:
            sa = SecurityAttributes(c.sizeof(SecurityAttributes), sd, False)
            handle = self.kernel.CreateFileW(str(path), 0xC0000000, 0, c.byref(sa), disposition, 0x00200000, None)
            if handle == c.c_void_p(-1).value: raise CredentialStoreError()
            try: fd = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
            except Exception:
                self.kernel.CloseHandle(handle)
                raise
            return os.fdopen(fd, 'r+b')
        finally: self.kernel.LocalFree(sd)

    def transform(self, content, decrypt=False):
        source = c.create_string_buffer(content)
        incoming, outgoing = Blob(len(content), c.cast(source, c.c_void_p)), Blob()
        fn = self.crypt.CryptUnprotectData if decrypt else self.crypt.CryptProtectData
        fn.argtypes = [c.POINTER(Blob), c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p, w.DWORD, c.POINTER(Blob)]
        if not fn(c.byref(incoming), None, None, None, None, 1, c.byref(outgoing)): raise CredentialStoreError()
        try: return c.string_at(outgoing.data, outgoing.size)
        finally:
            c.memset(outgoing.data, 0, outgoing.size)
            self.kernel.LocalFree(outgoing.data)
            c.memset(source, 0, len(content))


class CredentialStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.protection = WindowsProtection()

    def validate(self):
        p = self.directory
        if not p.is_absolute() or '..' in p.parts or str(p).startswith('\\\\') or ':' in str(p)[2:]: raise CredentialStoreError()
        repo = Path(__file__).resolve().parents[1]
        if p == repo or repo in p.parents: raise CredentialStoreError()
        for ancestor in (p, *p.parents):
            if ancestor.lstat().st_file_attributes & 0x400: raise CredentialStoreError()
        if not p.is_dir(): raise CredentialStoreError()
        self.protection.validate_acl(p)

    @contextmanager
    def transaction(self):
        self.validate()
        lock = self.directory / 'credential.lock'
        if lock.exists():
            if lock.lstat().st_file_attributes & 0x400: raise CredentialStoreError()
            self.protection.validate_acl(lock)
        handle = self.protection.open_private(lock, 4)  # OPEN_ALWAYS, no sharing; retained after release.
        try:
            self.protection.validate_acl(lock)
            yield self
        finally: handle.close()

    def load(self):
        try:
            self.validate()
            path = self.directory / 'credential.bin'
            if path.lstat().st_file_attributes & 0x400: raise CredentialStoreError()
            self.protection.validate_acl(path)
            with self.protection.open_private(path, 3) as stream: encrypted = stream.read(131073)
            if len(encrypted) > 131072: raise CredentialStoreError()
            return json.loads(self.protection.transform(encrypted, decrypt=True))
        except Exception: raise CredentialStoreError() from None

    def save(self, record, *, initial=False):
        try:
            self.validate()
            target = self.directory / 'credential.bin'
            if target.exists():
                if initial or target.lstat().st_file_attributes & 0x400: raise CredentialStoreError()
                self.protection.validate_acl(target)
            elif not initial: raise CredentialStoreError()
            raw = json.dumps(record, separators=(',', ':')).encode()
            if len(raw) > 65536: raise CredentialStoreError()
            encrypted = self.protection.transform(raw)
            temporary = self.directory / (uuid.uuid4().hex + '.pending')
            with self.protection.open_private(temporary, 1) as stream:
                stream.write(encrypted); stream.flush(); os.fsync(stream.fileno())
            self.protection.validate_acl(temporary)
            with self.protection.open_private(temporary, 3) as stream:
                if self.protection.transform(stream.read(), decrypt=True) != raw: raise CredentialStoreError()
            if initial:
                os.link(temporary, target)  # Atomic no-replace publication; encrypted pending retained.
            else: os.replace(temporary, target)
        except Exception: raise CredentialStoreError() from None
