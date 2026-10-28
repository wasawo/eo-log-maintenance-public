"""Read-only reporting across runs and the actual PowerShell display command."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

from Common.MoveJournal import encode_move_record, save_move_record
from Common.MoveRunReport import read_move_run_report
from test_move_journal import prepared as fixture_prepared, followup, reference


def prepared(*args):
    value = fixture_prepared(*args)
    source = value['event_data']['source']
    if source['kind'] == 'local': source['identity']['file_id'] = uuid4().hex
    else: source['file_id'] = 'synthetic-source-' + uuid4().hex
    return value


class MoveRunReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='eolm-report-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, record):
        save_move_record(self.root, encode_move_record(record))

    def report(self, run_id, machine='PC-A', route='local_to_cloud'):
        return read_move_run_report(self.root, run_id=run_id, machine_id=machine, route=route)

    def complete(self, first):
        result = followup(first)
        result['event_data'].update(request_outcome='succeeded', source_after_delete='absent',
            source_after_method='windows_lookup' if first['route']=='local_to_cloud' else 'provider_observation',
            decision='completed', completion_basis='delete_confirmed', reason_code='delete_confirmed')
        self.save(result)
        return result

    def shell(self, run_id, *, as_json=True, machine='PC-A', operation='Sync', extra_env=None, timeout=30):
        script = Path(__file__).resolve().parents[1]/'scripts/Show-MoveRun.ps1'
        command = ['pwsh','-NoProfile','-File',str(script),'-JournalRoot',str(self.root),'-RunId',run_id,
                   '-MachineId',machine,'-Operation',operation,'-PythonExecutable',sys.executable,'-TimeoutSeconds',str(timeout)]
        if as_json: command.append('-AsJson')
        return subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **(extra_env or {})))

    def test_first_completion_reconfirmation_and_pending_are_source_counts(self):
        first = prepared()
        self.save(first)
        done = self.complete(first)
        one = self.report(first['run_id'])
        self.assertEqual(1, one['newly_completed_source_count'])
        self.assertEqual(1, one['deleted_source_count'])
        again = followup(first, 'reconciliation', absent=True)
        again['prior_record_refs'].append(reference(done))
        self.save(again)
        two = self.report(again['run_id'])
        self.assertEqual(0, two['newly_completed_source_count'])
        self.assertEqual(1, two['already_completed_source_count'])
        pending = prepared()
        self.save(pending)
        three = self.report(again['run_id'])
        self.assertEqual(1, three['carried_unresolved_source_count'])
        self.assertEqual(1, three['unresolved_source_count'])

    def test_old_unknown_is_superseded_by_reconciliation_and_not_recounted(self):
        first = prepared()
        self.save(first)
        unknown = followup(first)
        self.save(unknown)
        reconciled = followup(first,'reconciliation',absent=True)
        reconciled['prior_record_refs'].append(reference(unknown))
        self.save(reconciled)
        report = self.report(reconciled['run_id'])
        self.assertEqual(1, report['newly_completed_source_count'])
        self.assertEqual(1, report['reconciled_source_count'])
        self.assertEqual(0, report['unresolved_source_count'])
        later = self.report(str(uuid4()))
        self.assertFalse(later['run_records_present'])
        self.assertEqual([], later['details'])

    def test_successful_retry_closes_old_failed_attempt_of_same_source_content(self):
        first=prepared()
        self.save(first)
        failed=followup(first)
        failed['event_data'].update(request_outcome='failed',source_after_delete='present',source_after_method='windows_lookup',
                                    decision='incomplete',reason_code='delete_failed')
        self.save(failed)
        retry=copy.deepcopy(first)
        for field in ('record_id','run_id','attempt_id'): retry[field]=str(uuid4())
        self.save(retry)
        self.complete(retry)
        report=self.report(str(uuid4()))
        self.assertEqual(0,report['unresolved_source_count'])
        self.assertEqual(0,report['newly_completed_source_count'])

    def test_no_run_record_is_not_no_work_and_old_prepared_is_not_lost(self):
        run = str(uuid4())
        report = self.report(run)
        self.assertFalse(report['run_records_present'])
        self.assertNotIn('success', report.values())
        first = prepared()
        self.save(first)
        report = self.report(run)
        self.assertFalse(report['run_records_present'])
        self.assertEqual(1, report['carried_unresolved_source_count'])
        self.assertEqual('prior_unresolved_records', report['details'][0]['reason_code'])

    def test_same_run_linked_result_is_resolved_but_unlinked_siblings_are_ambiguous(self):
        first = prepared()
        self.save(first)
        result = followup(first)
        self.save(result)
        reconciled = followup(first,'reconciliation',absent=True)
        reconciled['run_id'] = first['run_id']
        reconciled['prior_record_refs'].append(reference(result))
        self.save(reconciled)
        self.assertEqual(1,self.report(first['run_id'])['newly_completed_source_count'])
        sibling = copy.deepcopy(reconciled)
        sibling['record_id'], sibling['attempt_id'] = str(uuid4()),str(uuid4())
        self.save(sibling)
        report = self.report(first['run_id'])
        self.assertEqual(0,report['newly_completed_source_count'])
        self.assertEqual('current_results_ambiguous',report['details'][0]['reason_code'])

    def test_move_identity_conflict_does_not_merge_distinct_sources(self):
        first = prepared()
        self.save(first)
        other = prepared()
        other['move_id'] = first['move_id']
        other['event_data']['source']['identity']['file_id'] = '2'*32
        self.save(other)
        report = self.report(other['run_id'])
        self.assertEqual('move_identity_conflict',report['details'][0]['reason_code'])
        self.assertEqual(1,report['unresolved_source_count'])

    def test_new_move_id_cannot_double_count_same_source_and_copy_content(self):
        first = prepared()
        self.save(first)
        self.complete(first)
        alias = copy.deepcopy(first)
        for field in ('record_id','run_id','move_id','attempt_id'): alias[field] = str(uuid4())
        self.save(alias)
        self.complete(alias)
        with self.assertRaisesRegex(ValueError,'source_identity_conflict'): self.report(alias['run_id'])

    def test_machine_and_route_scopes_are_separate(self):
        first = prepared('PC-B')
        self.save(first)
        self.complete(first)
        archive = prepared('PC-A','cloud_to_archive')
        self.save(archive)
        self.complete(archive)
        self.assertEqual(0,self.report(first['run_id'])['newly_completed_source_count'])
        self.assertEqual(1,self.report(first['run_id'],'PC-B')['newly_completed_source_count'])
        self.assertEqual(1,self.report(archive['run_id'],'PC-A','cloud_to_archive')['newly_completed_source_count'])

    def test_shell_outputs_japanese_summary_and_identifier_only_json_without_writes(self):
        first = prepared()
        first['event_data']['source']['relative_path'] = 'SYNTHETIC-PRIVATE-DIRECTORY/20240101_12345678@a.txt'
        first['event_data']['destination']['file_id'] = 'SYNTHETIC-PRIVATE-DRIVE-ID'
        self.save(first)
        self.complete(first)
        before = {p.name:p.read_bytes() for p in self.root.iterdir()}
        result = self.shell(first['run_id'])
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(1,json.loads(result.stdout)['newly_completed_source_count'])
        text = self.shell(first['run_id'],as_json=False)
        self.assertEqual(0,text.returncode,text.stderr)
        self.assertIn('今回初めて完了: 1',text.stdout)
        self.assertNotIn('SYNTHETIC-PRIVATE',text.stdout+result.stdout)
        self.assertNotIn(str(self.root),text.stdout+result.stdout)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_shell_corrupt_journal_and_pc_b_archive_fail_without_raw_details(self):
        (self.root/'private.tmp').write_bytes(b'SYNTHETIC-PRIVATE-CONTENT')
        result = self.shell(str(uuid4()))
        self.assertNotEqual(0,result.returncode)
        self.assertNotIn(str(self.root),result.stdout+result.stderr)
        self.assertNotIn('SYNTHETIC-PRIVATE',result.stdout+result.stderr)
        denied = self.shell(str(uuid4()),machine='PC-B',operation='Archive')
        self.assertNotEqual(0,denied.returncode)
        self.assertIn('move_report_scope_invalid',denied.stderr)

    def test_unexpected_python_output_is_not_forwarded_and_timeout_is_bounded(self):
        run_id = str(uuid4())
        with tempfile.TemporaryDirectory(prefix='eolm-python-reply-') as fake:
            startup = Path(fake)/'sitecustomize.py'
            payload = json.dumps(dict(ok=True,report=dict(private='SYNTHETIC-PRIVATE-RESPONSE')))
            startup.write_text('import os,sys\nsys.stdout.write('+repr(payload)+')\nsys.stdout.flush()\nos._exit(0)\n',encoding='utf-8')
            invalid = self.shell(run_id,extra_env={'PYTHONPATH':fake})
            self.assertNotEqual(0,invalid.returncode)
            self.assertIn('move_report_response_invalid',invalid.stderr)
            self.assertNotIn('SYNTHETIC-PRIVATE-RESPONSE',invalid.stdout+invalid.stderr)
            startup.write_text('import time\ntime.sleep(60)\n',encoding='utf-8')
            timed = self.shell(run_id,extra_env={'PYTHONPATH':fake},timeout=1)
            self.assertNotEqual(0,timed.returncode)
            self.assertIn('move_report_process_timeout',timed.stderr)


if __name__ == '__main__': unittest.main()
