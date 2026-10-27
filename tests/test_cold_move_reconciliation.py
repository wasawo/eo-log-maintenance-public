"""Cold native observations of self-created synthetic source/destination only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from Common.MoveJournal import load_move_record, read_move_journal
from windows_move_delete_probe import DisposableMoveDeleteProbe


@unittest.skipUnless(os.name == 'nt', 'real Windows file APIs required')
class ColdMoveReconciliationTests(unittest.TestCase):
    def probe(self):
        probe = DisposableMoveDeleteProbe(journal=True)
        self.addCleanup(probe.close)
        return probe

    def observe(self, probe, *, successful=True):
        worker = Path(__file__).with_name('cold_move_reconciliation_worker.py')
        child = subprocess.run([sys.executable, '-B', str(worker), str(probe._root), probe._nonce.decode('ascii')],
                               capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        output = json.loads(child.stdout)
        self.assertEqual(successful, child.returncode == 0, output)
        return output

    def test_result_lost_then_new_process_observes_actual_absence_and_destination(self):
        probe = self.probe()
        self.assertEqual('unknown', probe.run(fault='result_record_failed')['status'])
        before = {p.name: p.read_bytes() for p in (probe._root/'journal').iterdir()}
        self.assertEqual(1, len(before))
        result = self.observe(probe)
        self.assertEqual('completed', result['decision'])
        self.assertEqual('absent', result['source_current'])
        value = load_move_record(probe._root/'journal', result['record_id'])
        self.assertEqual('reconciled', value['event_data']['completion_basis'])
        for name, raw in before.items():
            self.assertEqual(raw, (probe._root/'journal'/name).read_bytes())
        self.assertEqual(b'synthetic log', probe._path('destination.bin').read_bytes())
        self.assertFalse((probe._root/'source.bin').exists())

    def test_pending_other_handle_is_not_absence_and_old_result_is_unchanged(self):
        probe = self.probe()
        self.assertEqual('unknown', probe.run(keep_reader=True)['status'])
        records = read_move_journal(probe._root/'journal')
        prior = next(r for r in records if r['event_kind'] == 'deletion_result')
        path = probe._root/'journal'/(prior['record_id']+'.json')
        old = path.read_bytes()
        first = self.observe(probe)
        self.assertEqual('unknown', first['decision'])
        probe.release_reader()
        second = self.observe(probe)
        self.assertEqual('completed', second['decision'])
        self.assertEqual(old, path.read_bytes())

    def test_current_damage_missing_destination_and_recreated_source_cannot_complete(self):
        for issue in ('destination_changed', 'destination_missing', 'destination_replaced', 'source_recreated'):
            with self.subTest(issue=issue):
                probe = self.probe()
                probe.run(fault='result_record_failed')
                if issue == 'destination_changed':
                    probe._path('destination.bin').write_bytes(b'changed')
                elif issue == 'destination_missing':
                    probe._path('destination.bin').unlink()
                elif issue == 'destination_replaced':
                    probe._path('replacement.bin', existing=False).write_bytes(b'synthetic log')
                    os.replace(probe._path('replacement.bin'), probe._path('destination.bin'))
                else:
                    probe._path('source.bin', existing=False).write_bytes(b'synthetic log')
                result = self.observe(probe)
                self.assertNotEqual('completed', result['decision'])
                if issue == 'source_recreated':
                    self.assertEqual(b'synthetic log', probe._path('source.bin').read_bytes())

    def test_tampered_binding_partial_record_and_wrong_nonce_stop_recovery(self):
        for issue in ('record_changed', 'descriptor_changed', 'partial_record', 'wrong_nonce'):
            with self.subTest(issue=issue):
                probe = self.probe()
                probe.run(fault='result_record_failed')
                if issue == 'record_changed':
                    path = next((probe._root/'journal').iterdir())
                    path.write_bytes(path.read_bytes()+b' ')
                elif issue == 'descriptor_changed':
                    descriptor = json.loads(probe._path('fixture.json').read_bytes())
                    descriptor['root_chain'][0][1] += 1
                    probe._path('fixture.json').write_text(json.dumps(descriptor), encoding='utf-8')
                elif issue == 'partial_record':
                    (probe._root/'journal'/'partial.tmp').write_bytes(b'partial')
                original_nonce = probe._nonce
                if issue == 'wrong_nonce': probe._nonce = b'0'*32
                try:
                    result = self.observe(probe, successful=False)
                    self.assertIn('error', result)
                finally:
                    probe._nonce = original_nonce

    def test_original_source_still_present_is_not_deleted_by_recovery(self):
        probe = self.probe()
        self.assertEqual('interrupted_before_delete', probe.run(fault='after_prepare')['reason'])
        before = probe._path('source.bin').read_bytes()
        result = self.observe(probe)
        self.assertEqual('incomplete', result['decision'])
        self.assertEqual('present', result['source_current'])
        self.assertEqual(before, probe._path('source.bin').read_bytes())
        self.assertFalse((probe._root/'result.json').exists())

    def test_source_access_failure_is_unknown_not_absence(self):
        probe = self.probe()
        probe.run(fault='after_prepare')
        with probe._handle('source.bin', share=0):
            result = self.observe(probe)
        self.assertEqual('unknown', result['decision'])
        self.assertEqual('unknown', result['source_current'])
        self.assertEqual(b'synthetic log', probe._path('source.bin').read_bytes())


if __name__ == '__main__':
    unittest.main()
