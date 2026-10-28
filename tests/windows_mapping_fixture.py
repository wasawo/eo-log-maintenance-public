"""TEST ONLY: map a constructor-owned synthetic file, closing BOTH handles."""
from contextlib import contextmanager
import ctypes

from windows_move_delete_probe import MoveDeleteProbeError


def mapping_api(probe):
    from ctypes import wintypes as w
    for name,args,result in (
        ('CreateFileMappingW',(w.HANDLE,w.LPVOID,w.DWORD,w.DWORD,w.DWORD,w.LPCWSTR),w.HANDLE),
        ('MapViewOfFile',(w.HANDLE,w.DWORD,w.DWORD,w.DWORD,ctypes.c_size_t),w.LPVOID),
        ('UnmapViewOfFile',(w.LPCVOID,),w.BOOL),
        ('FlushViewOfFile',(w.LPCVOID,ctypes.c_size_t),w.BOOL),
    ):
        function=getattr(probe._api,name);function.argtypes=args;function.restype=result
    return probe._api


@contextmanager
def writable_view_without_handles(probe,name):
    if name not in ('source.bin','destination.bin'):
        raise MoveDeleteProbeError('probe_mapping_name_invalid')
    api=mapping_api(probe)
    view=None
    try:
        with probe._handle(name,access=0xc0000000,share=7) as file_handle:
            mapping=api.CreateFileMappingW(file_handle,None,4,0,0,None)  # PAGE_READWRITE
            if not mapping:
                raise MoveDeleteProbeError('probe_mapping_create_failed')
            try:
                view=api.MapViewOfFile(mapping,2,0,0,0)  # FILE_MAP_WRITE
                if not view:
                    raise MoveDeleteProbeError('probe_mapping_view_failed')
            finally:
                probe._close(mapping)
        # File and mapping-object handles are closed; only the view remains.
        def update(data):
            if type(data) is not bytes or len(data)!=probe._size:
                raise MoveDeleteProbeError('probe_mapping_content_invalid')
            ctypes.memmove(view,data,len(data))
            if not api.FlushViewOfFile(view,len(data)):
                raise MoveDeleteProbeError('probe_mapping_flush_failed')
        yield update
    finally:
        if view and not api.UnmapViewOfFile(view):
            raise MoveDeleteProbeError('probe_mapping_unmap_failed')
