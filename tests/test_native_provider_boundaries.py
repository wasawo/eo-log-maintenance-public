"""Actual mapping/namespace refusal evidence, not runtime qualification."""
import ctypes
import os
import unittest

from Common.MoveJournal import read_move_journal
from Common.ArtifactSetDirectoryVerification import _chain
from owned_windows_move_probe import OwnedDisposableMoveDeleteProbe
from windows_move_delete_probe import MoveDeleteProbeError
from windows_mapping_fixture import mapping_api,writable_view_without_handles


@unittest.skipUnless(os.name=='nt','real Windows mapping and directory handles required')
class NativeProviderBoundaryTests(unittest.TestCase):
    def probe(self):
        probe=OwnedDisposableMoveDeleteProbe()
        self.addCleanup(probe.close)
        return probe

    def test_existing_writable_view_after_both_handles_close_blocks_guard(self):
        for name in ('source.bin','destination.bin'):
            with self.subTest(name=name):
                probe=self.probe()
                with writable_view_without_handles(probe,name):
                    access=0x80010000 if name=='source.bin' else 0x80000000
                    handle=probe._api.CreateFileW(str(probe._path(name)),access,1,None,3,0x00200000,None)
                    if handle not in (None,ctypes.c_void_p(-1).value):
                        probe._close(handle);self.fail('writable_mapping_guard_unexpectedly_acquired')
                    self.assertEqual(ctypes.get_last_error(),32)
                    with self.assertRaisesRegex(MoveDeleteProbeError,'probe_open_failed'):
                        probe.run_owned()
                    self.assertTrue((probe._root/'source.bin').exists())
                    self.assertEqual(read_move_journal(probe._root/'journal'),[])
                self.assertEqual(probe.run_owned()['status'],'completed')

    def test_existing_view_can_change_bytes_but_changed_content_is_never_deleted(self):
        for name in ('source.bin','destination.bin'):
            probe=self.probe()
            with writable_view_without_handles(probe,name) as update:
                update(b'Synthetic log')
                self.assertEqual((probe._root/name).read_bytes(),b'Synthetic log')
                with self.assertRaisesRegex(MoveDeleteProbeError,'probe_open_failed'): probe.run_owned()
            result=probe.run_owned()
            self.assertEqual(result['status'],'retained')
            self.assertEqual(result['reason'],'source_changed' if name=='source.bin' else 'destination_changed')
            self.assertTrue((probe._root/'source.bin').exists())
            self.assertEqual(read_move_journal(probe._root/'journal'),[])

    def test_writable_mapping_from_readonly_guard_compatible_handle_is_denied(self):
        probe=self.probe();api=mapping_api(probe);observed=[]
        def checkpoint(phase):
            if phase=='before_delete':
                for name in ('source.bin','destination.bin'):
                    with probe._handle(name,share=5) as read_handle:
                        mapping=api.CreateFileMappingW(read_handle,None,4,0,0,None)
                        if mapping:
                            probe._close(mapping);self.fail('readonly_handle_created_writable_mapping')
                        observed.append(ctypes.get_last_error())
        self.assertEqual(probe.run_owned(at_checkpoint=checkpoint)['status'],'completed')
        self.assertEqual(observed,[5,5])

    def test_held_fixture_and_ownership_directories_reject_rename(self):
        from ctypes import wintypes as w
        for kind in ('root','ownership','journal'):
            probe=self.probe();api=probe._api
            api.MoveFileExW.argtypes=(w.LPCWSTR,w.LPCWSTR,w.DWORD);api.MoveFileExW.restype=w.BOOL
            original={'root':probe._root,'ownership':probe._ownership_root,'journal':probe._journal_root}[kind]
            renamed=original.with_name(original.name+'-renamed')
            self.assertEqual(original.parent,renamed.parent)
            self.assertEqual(original.parent,probe._parent if kind=='root' else probe._root)
            self.assertFalse(renamed.exists());observed=[]
            def checkpoint(phase):
                if phase=='before_delete':
                    if api.MoveFileExW(str(original),str(renamed),0):
                        observed.append(0)
                        raise RuntimeError('synthetic_namespace_guard_failed')
                    observed.append(ctypes.get_last_error())
            try:
                result=probe.run_owned(at_checkpoint=checkpoint)
            finally:
                # Restore only this self-created sibling if the negative test
                # unexpectedly moved it. Never move a path supplied by callers.
                if renamed.exists():
                    self.assertFalse(original.exists())
                    expected={'root':probe._chain,'ownership':probe._ownership_chain,'journal':probe._journal_chain}[kind]
                    self.assertEqual(_chain(renamed),tuple(expected))
                    self.assertEqual(renamed.resolve(strict=True).parent,original.absolute().parent)
                    renamed.rename(original)
            self.assertEqual(observed,[32])
            self.assertEqual(result['status'],'completed')

    def test_existing_directory_delete_access_prevents_weak_guard_fallback(self):
        for path_kind in ('root','ownership','journal'):
            probe=self.probe();path={'root':probe._root,'ownership':probe._ownership_root,'journal':probe._journal_root}[path_kind]
            handle=probe._api.CreateFileW(str(path),0x10000,7,None,3,0x02200000,None)
            self.assertNotIn(handle,(None,ctypes.c_void_p(-1).value))
            try:
                with self.assertRaisesRegex(MoveDeleteProbeError,'probe_directory_guard_failed'):
                    probe.run_owned()
                self.assertTrue((probe._root/'source.bin').exists())
                self.assertEqual(read_move_journal(probe._root/'journal'),[])
                self.assertFalse(probe._lock_path.exists())
            finally:
                probe._close(handle)


if __name__=='__main__': unittest.main()
