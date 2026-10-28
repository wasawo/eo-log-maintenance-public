"""Real mutex + guarded file handles + journal, restricted to synthetic temp."""
import os
import ctypes
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

from Common.MoveJournal import read_move_journal
from Common.OwnedRunLock import acquire_owned_lock, LockAcquisitionError
from owned_windows_move_probe import OwnedDisposableMoveDeleteProbe
from cold_move_reconciliation_worker import _ReadOnlyObserver


@unittest.skipUnless(os.name=='nt','Windows native handles/mutex required')
class OwnedWindowsMoveProbeTests(unittest.TestCase):
    def probe(self, content=b'synthetic log'):
        value=OwnedDisposableMoveDeleteProbe(content)
        self.addCleanup(value.close)
        return value

    def test_same_process_owns_mutex_and_handles_through_verified_deletion(self):
        for content in (b'',b'synthetic log',b'x'*131073):
            with self.subTest(size=len(content)):
                probe=self.probe(content)
                observations=[]
                def observe(phase):
                    self.assertTrue(probe._lock_path.exists())
                    if phase=='before_delete':
                        observations.append(probe.competing_open(0x40000000))
                        observations.append(probe.competing_open(0x10000))
                        outcomes=[]
                        def competitor():
                            try:
                                with acquire_owned_lock(probe._scope,probe._lock_path,timeout_seconds=0):
                                    outcomes.append('unexpected_acquisition')
                            except LockAcquisitionError as error:
                                outcomes.append(error.reason_code)
                        thread=threading.Thread(target=competitor)
                        thread.start(); thread.join(timeout=10)
                        self.assertFalse(thread.is_alive())
                        self.assertEqual(outcomes,['lock_timeout'])
                result=probe.run_owned(at_checkpoint=observe)
                self.assertEqual(result['status'],'completed')
                self.assertEqual(observations,[(False,32),(False,32)])
                self.assertFalse((probe._root/'source.bin').exists())
                records=read_move_journal(probe._root/'journal')
                self.assertEqual([r['event_kind'] for r in records].count('deletion_result'),1)
                self.assertFalse(probe._lock_path.exists())

    def test_unknown_ownership_before_delete_retains_source_and_pending_record(self):
        for phase in ('before_open','before_prepared','after_prepared','before_delete'):
            with self.subTest(phase=phase):
                probe=self.probe()
                def change(point):
                    if point==phase: raise RuntimeError('synthetic unavailable ownership')
                result=probe.run_owned(at_checkpoint=change)
                self.assertEqual(result,dict(status='retained',reason='ownership_unconfirmed'))
                self.assertEqual((probe._root/'source.bin').read_bytes(),b'synthetic log')
                records=read_move_journal(probe._root/'journal')
                self.assertEqual(len(records),1 if phase in ('after_prepared','before_delete') else 0)
                self.assertFalse(probe._lock_path.exists())

    def test_unknown_ownership_after_delete_is_unknown_without_false_result(self):
        probe=self.probe()
        def change(phase):
            if phase=='after_delete': raise RuntimeError('synthetic unavailable ownership')
        result=probe.run_owned(at_checkpoint=change)
        self.assertEqual(result,dict(status='unknown',reason='ownership_unconfirmed_after_delete'))
        self.assertFalse((probe._root/'source.bin').exists())
        records=read_move_journal(probe._root/'journal')
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['event_kind'],'prepared')
        self.assertFalse((probe._root/'result.json').exists())
        self.assertFalse(probe._lock_path.exists())

    def test_prepared_tamper_during_ownership_check_cannot_delete(self):
        for kind in ('local','journal'):
            probe=self.probe()
            def change(phase):
                if phase=='after_prepared':
                    path=probe._root/'prepared.json' if kind=='local' else probe._root/'journal'/(probe._journal_prepared['record_id']+'.json')
                    path.write_bytes(b'changed synthetic record')
            result=probe.run_owned(at_checkpoint=change)
            self.assertEqual(result,dict(status='retained',reason='record_invalid'))
            self.assertTrue((probe._root/'source.bin').exists())
            self.assertEqual(len(list((probe._root/'journal').iterdir())),1)

    def test_owner_and_prepared_records_reject_competing_writes_while_held(self):
        probe=self.probe()
        observed=[]
        def compete(phase):
            if phase=='before_delete':
                paths=[probe._lock_path,probe._root/'prepared.json',probe._root/'journal'/(probe._journal_prepared['record_id']+'.json')]
                for path in paths:
                    handle=probe._api.CreateFileW(str(path),0x40000000,7,None,3,0x00200000,None)
                    if handle not in (None,ctypes.c_void_p(-1).value):
                        probe._close(handle)
                        self.fail('competing_record_writer_acquired')
                    observed.append(ctypes.get_last_error())
        self.assertEqual(probe.run_owned(at_checkpoint=compete)['status'],'completed')
        self.assertEqual(observed,[32,32,32])

    def test_repeated_reads_rewind_same_source_and_destination_handles(self):
        probe=self.probe(b'x'*131073)
        with probe._handle('source.bin') as source:
            first=probe._content(source)
            self.assertEqual(first,probe._content(source))
            self.assertEqual(first,probe._content(source))

    def test_seek_failure_after_preparation_retains_source(self):
        probe=self.probe()
        real=probe._api.SetFilePointerEx
        def change(phase):
            if phase=='before_delete': probe._api.SetFilePointerEx=lambda *_:0
        with self.assertRaisesRegex(RuntimeError,'probe_seek_failed'):
            probe.run_owned(at_checkpoint=change)
        probe._api.SetFilePointerEx=real
        self.assertTrue((probe._root/'source.bin').exists())
        self.assertEqual(len(read_move_journal(probe._root/'journal')),1)
        self.assertFalse(probe._lock_path.exists())

    def test_pending_delete_remains_unknown_with_destination_guard_and_mutex(self):
        probe=self.probe()
        result=probe.run_owned(keep_reader=True)
        self.assertEqual(result['status'],'unknown')
        self.assertEqual(result['reason'],'delete_pending')
        self.assertEqual(len(read_move_journal(probe._root/'journal')),2)
        self.assertFalse(probe._lock_path.exists())
        probe.release_reader()

    def test_owner_process_exit_before_or_after_delete_is_cold_reobserved_without_unlock(self):
        for phase in ('before_delete','after_delete'):
            with self.subTest(phase=phase):
                command=[sys.executable,'-B',str(Path(__file__).with_name('owned_move_crash_worker.py')),phase]
                process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                descriptor={}
                def cleanup():
                    if process.poll() is None: process.kill()
                    process.communicate(timeout=20)
                    if descriptor:
                        root=Path(descriptor['root'])
                        self.assertEqual(root.parent,Path(tempfile.gettempdir()).resolve(strict=True))
                        observer=_ReadOnlyObserver(root,descriptor['nonce'])
                        observer._verify_root()
                        shutil.rmtree(root)
                try:
                    descriptor.update(json.loads(process.stdout.readline()))
                    root=Path(descriptor['root']); observer=_ReadOnlyObserver(root,descriptor['nonce']); observer._verify_root()
                    stdout,stderr=process.communicate('exit\n',timeout=20)
                    self.assertEqual(process.returncode,91)
                    self.assertEqual(stdout+stderr,'')
                    lock=root/'ownership'/'run.lock'; prior_lock=lock.read_bytes()
                    prepared={p.name:p.read_bytes() for p in (root/'journal').iterdir()}
                    self.assertEqual(len(prepared),1)
                    result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('cold_move_reconciliation_worker.py')),
                        str(root),descriptor['nonce']],capture_output=True,text=True,timeout=20,check=True)
                    observed=json.loads(result.stdout)
                    self.assertEqual(observed['decision'],'incomplete' if phase=='before_delete' else 'completed')
                    self.assertEqual(observed['source_current'],'present' if phase=='before_delete' else 'absent')
                    self.assertEqual(lock.read_bytes(),prior_lock)
                    for name,raw in prepared.items(): self.assertEqual((root/'journal'/name).read_bytes(),raw)
                    self.assertFalse((root/'result.json').exists())
                    records=read_move_journal(root/'journal')
                    self.assertFalse(any(r['event_kind']=='deletion_result' for r in records))
                finally:
                    cleanup()


if __name__=='__main__': unittest.main()
