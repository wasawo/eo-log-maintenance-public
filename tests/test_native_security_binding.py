"""Private held-handle observations, not authorization or real-root ACL edits."""
import ctypes
import os
import subprocess
import unittest
from unittest.mock import patch

from Common.MoveJournal import read_move_journal
from owned_windows_move_probe import OwnedDisposableMoveDeleteProbe
from windows_security_observation import NativeSecurityObserver
from windows_fixture_acl import protect_fixture_directory
from windows_move_delete_probe import MoveDeleteProbeError


@unittest.skipUnless(os.name=='nt','real Windows handle security required')
class NativeSecurityBindingTests(unittest.TestCase):
    def probe(self):
        probe=OwnedDisposableMoveDeleteProbe()
        self.addCleanup(probe.close)
        return probe

    def test_held_directory_observation_and_process_user_are_actual_private_facts(self):
        probe=self.probe();observer=NativeSecurityObserver(probe)
        child=subprocess.run(['pwsh','-NoLogo','-NoProfile','-NonInteractive','-Command',
            '[Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],capture_output=True,text=True,timeout=20,check=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        for path in (probe._root,probe._ownership_root,probe._journal_root):
            with probe._directory_handle(path) as handle:
                observed=observer.read(handle)
                self.assertTrue(observed==observer.read(handle),'stable security observation differs')
                self.assertEqual(observed.object_kind,'directory')
                self.assertTrue(observed.process_user_sid==child.stdout.strip(),'process-user binding mismatch')
                self.assertTrue(observed.owner_sid.startswith('S-1-'))
                self.assertTrue(observed.dacl_present and not observed.dacl_null)
                self.assertTrue(20<=len(observed.descriptor_bytes)<=65536)
                self.assertFalse(observed.may_change_state)
                self.assertNotIn('S-1-',repr(observed))

    def test_handle_without_read_control_is_not_promoted_from_owner_claim(self):
        probe=self.probe();observer=NativeSecurityObserver(probe)
        handle=probe._api.CreateFileW(str(probe._root),0x80,7,None,3,0x02200000,None)
        self.assertNotIn(handle,(None,ctypes.c_void_p(-1).value))
        try:
            with self.assertRaisesRegex(MoveDeleteProbeError,'^probe_security_observation_failed$'):
                observer.read(handle)
        finally:
            probe._close(handle)
        self.assertTrue((probe._root/'source.bin').exists())

    def test_initial_observation_failure_stops_before_owned_record_and_prepared(self):
        probe=self.probe()
        with patch.object(NativeSecurityObserver,'read',side_effect=MoveDeleteProbeError('probe_security_observation_failed')):
            with self.assertRaisesRegex(MoveDeleteProbeError,'^probe_security_observation_failed$'):
                probe.run_owned()
        self.assertTrue((probe._root/'source.bin').exists())
        self.assertFalse(probe._lock_path.exists())
        self.assertEqual(read_move_journal(probe._root/'journal'),[])

    def test_acl_change_is_possible_despite_share_guard_but_blocks_source_delete(self):
        for kind in ('root','ownership','journal'):
            with self.subTest(kind=kind):
                probe=self.probe();changed=[]
                def change(phase):
                    if phase=='before_delete':
                        protect_fixture_directory(probe,kind);changed.append(True)
                result=probe.run_owned(at_checkpoint=change)
                self.assertEqual(changed,[True])
                self.assertEqual(result,dict(status='retained',reason='ownership_unconfirmed'))
                self.assertEqual((probe._root/'source.bin').read_bytes(),b'synthetic log')
                self.assertEqual(len(read_move_journal(probe._root/'journal')),1)
                self.assertFalse((probe._root/'result.json').exists())

    def test_acl_change_after_delete_cannot_create_success_result(self):
        probe=self.probe()
        def change(phase):
            if phase=='after_delete':protect_fixture_directory(probe,'root')
        result=probe.run_owned(at_checkpoint=change)
        self.assertEqual(result,dict(status='unknown',reason='ownership_unconfirmed_after_delete'))
        self.assertFalse((probe._root/'source.bin').exists())
        self.assertEqual(len(read_move_journal(probe._root/'journal')),1)
        self.assertFalse((probe._root/'result.json').exists())

    def test_protected_fixture_acl_is_observable_but_not_runtime_qualification(self):
        probe=self.probe();protect_fixture_directory(probe,'root');observer=NativeSecurityObserver(probe)
        with probe._directory_handle(probe._root) as handle:
            value=observer.read(handle)
            self.assertTrue(value.dacl_protected)
            self.assertFalse(value.may_change_state)
        self.assertEqual(probe.run_owned()['status'],'completed')


if __name__=='__main__':unittest.main()
