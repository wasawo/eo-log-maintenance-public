"""Private model reports: strict results, readback, conflict and sanitization."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

from Common.SimulationRunReport import decode, encode, read_report, save_report, summarize, REASONS


def report():
    return dict(report_version=1, simulation_only=True, run_id=str(uuid4()), machine_id='PC-A',
                route='local_to_cloud', inventory_complete=True, inventory_source_count=0,
                journal_read_status='confirmed', journal_unresolved_move_refs=[], results=[])


def result(reason, index=1):
    return dict(source_ref=f'{index:064x}', source_relative_path=f'nested/20240101_12345678@{index}.txt',
                log_type='BattleLog', outcome=REASONS[reason][0], reason_code=reason,
                next_action=REASONS[reason][1], destination_candidates=[])


class SimulationRunReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='eolm-run-report-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_every_result_class_is_preserved_without_fabricating_move_records(self):
        value=report()
        value['results']=[result(reason,index) for index,reason in enumerate(REASONS,1)]
        value['inventory_source_count']=len(value['results'])
        summary=save_report(self.root,value)
        self.assertEqual(summary['status'],'partial_failure')
        self.assertEqual(summary['deleted_source_count'],1)
        self.assertEqual(summary['reconciled_source_count'],1)
        self.assertEqual(read_report(self.root,value['run_id'])[1],value)
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(save_report(self.root,value),summary)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})
        other=copy.deepcopy(value); other['results'][0]['source_relative_path']='different.txt'
        with self.assertRaises(Exception): save_report(self.root,other)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_empty_inventory_does_not_hide_prior_or_unknown_journal(self):
        value=report()
        self.assertEqual(summarize(value)['status'],'no_work')
        value['journal_unresolved_move_refs']=[str(uuid4())]
        self.assertEqual(summarize(value)['status'],'failure')
        value['journal_unresolved_move_refs']=[]; value['journal_read_status']='unconfirmed'
        self.assertEqual(summarize(value)['status'],'failure')

    def test_rejects_malformed_results_paths_duplicates_scope_and_incomplete_inventory(self):
        value=report(); value['results']=[result('copy_failed')]; value['inventory_source_count']=1
        variants=[]
        for key,bad in [('report_version',True),('inventory_source_count',2),('inventory_complete',False),('machine_id','PC-B')]:
            candidate=copy.deepcopy(value); candidate[key]=bad
            if key=='machine_id': candidate['route']='cloud_to_archive'
            variants.append(candidate)
        for key,bad in [('source_relative_path','../secret'),('source_relative_path','D:/secret'),('outcome','completed'),('next_action','none'),('source_ref','private-id')]:
            candidate=copy.deepcopy(value); candidate['results'][0][key]=bad; variants.append(candidate)
        candidate=copy.deepcopy(value); candidate['results']*=2; variants.append(candidate)
        for candidate in variants:
            with self.subTest(candidate=candidate):
                with self.assertRaises(Exception): save_report(self.root,candidate)
        self.assertEqual(list(self.root.iterdir()),[])
        with self.assertRaises(Exception): decode(b'{"report_version":1,"report_version":1}')

    def test_cold_reader_summary_omits_private_details_and_fails_safely(self):
        value=report(); value['results']=[result('content_conflict')]; value['inventory_source_count']=1
        value['results'][0]['source_relative_path']='private-subfolder/20240101_12345678@private.txt'
        save_report(self.root,value)
        command=[sys.executable,'-B','Common/SimulationRunReport.py','--report-root',str(self.root),'--read-run-id',value['run_id']]
        proc=subprocess.run(command,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(proc.stdout)['summary']['status'],'failure')
        self.assertNotIn('private',proc.stdout+proc.stderr)
        self.assertNotIn(str(self.root),proc.stdout+proc.stderr)
        (self.root/(value['run_id']+'.json')).write_bytes(encode(value)[:-4])
        failed=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(failed.returncode,1)
        self.assertEqual(json.loads(failed.stdout),dict(ok=False,reason_code='simulation_report_unconfirmed'))
        self.assertNotIn(str(self.root),failed.stdout+failed.stderr)


if __name__=='__main__': unittest.main()
