"""Real Windows ownership around synthetic model runs, never live logs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

from Common.SimulationRunReport import save_report


@unittest.skipUnless(os.name == 'nt', 'Windows named mutex required')
class SimulationRunOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='eolm-run-owner-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.lifecycle=self.root/'journal.lifecycle'; self.lifecycle.mkdir()
        self.journal=self.root/'journal'; self.journal.mkdir()
        self.reports=self.root/'reports'; self.reports.mkdir()

    def start(self, *, run=None, machine='PC-A', route='local_to_cloud', lifecycle=None):
        run=run or str(uuid4())
        command=[sys.executable,'-B','Common/SimulationRunOwner.py','--lifecycle-root',str(lifecycle or self.lifecycle),
            '--journal-root',str(self.journal),'--report-root',str(self.reports),'--run-id',run,'--machine-id',machine,'--route',route]
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def cleanup():
            if process.poll() is None: process.kill()
            process.communicate(timeout=20)
        self.addCleanup(cleanup)
        return process,run

    def ready(self, process, run):
        self.assertEqual(json.loads(process.stdout.readline()),dict(protocol_version=1,phase='ready',run_id=run))

    def finish(self, process, run, report_status='unconfirmed'):
        message=json.dumps(dict(protocol_version=1,run_id=run,operation_status='no_work',report_save_status=report_status))+'\n'
        stdout,stderr=process.communicate(message,timeout=20)
        return stdout,stderr

    def ended(self, run):
        return json.loads((self.lifecycle/(run+'.ended.json')).read_bytes())

    def test_ownership_blocks_second_route_even_with_other_lifecycle_directory(self):
        one,run=self.start(); self.ready(one,run)
        same,_=self.start(route='cloud_to_archive')
        stdout,stderr=same.communicate(timeout=20)
        self.assertEqual(same.returncode,1)
        self.assertNotIn('ready',stdout)
        alternate=self.root/'alternate'; alternate.mkdir()
        two,_=self.start(route='cloud_to_archive',lifecycle=alternate)
        stdout,stderr=two.communicate(timeout=20)
        self.assertEqual(two.returncode,1)
        self.assertNotIn('ready',stdout)
        self.assertEqual(list(alternate.iterdir()),[])
        stdout,stderr=self.finish(one,run)
        self.assertEqual(one.returncode,0)
        self.assertEqual(json.loads(stdout)['phase'],'finished')
        self.assertEqual(self.ended(run)['report_save_status'],'unconfirmed')
        self.assertFalse(list(self.lifecycle.glob('*.lock')))
        self.assertNotIn(str(self.root),stdout+stderr)

    def test_eof_records_interruption_without_operation_success(self):
        process,run=self.start(); self.ready(process,run)
        stdout,stderr=process.communicate('',timeout=20)
        self.assertEqual(process.returncode,1)
        record=self.ended(run)
        self.assertEqual(record['disposition'],'interrupted')
        self.assertIsNone(record['operation_status'])
        self.assertNotIn('finished',stdout)
        self.assertFalse(list(self.lifecycle.glob('*.lock')))

    def test_killed_owner_leaves_lock_and_start_and_refuses_automatic_recovery(self):
        process,run=self.start(); self.ready(process,run)
        process.kill(); process.communicate(timeout=20)
        before={p.name:p.read_bytes() for p in self.lifecycle.iterdir()}
        self.assertFalse((self.lifecycle/(run+'.ended.json')).exists())
        self.assertEqual(len(list(self.lifecycle.glob('*.lock'))),1)
        other,_=self.start()
        stdout,stderr=other.communicate(timeout=20)
        self.assertEqual(other.returncode,1)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.lifecycle.iterdir()})
        self.assertNotIn('ready',stdout)
        alternate=self.root/'alternate'; alternate.mkdir()
        bypass,_=self.start(lifecycle=alternate)
        bypass.communicate(timeout=20)
        self.assertEqual(bypass.returncode,1)
        self.assertEqual(list(alternate.iterdir()),[])

    def test_confirmed_report_is_reloaded_and_bound_to_ending(self):
        process,run=self.start(); self.ready(process,run)
        report=dict(report_version=1,simulation_only=True,run_id=run,machine_id='PC-A',route='local_to_cloud',
            inventory_complete=True,inventory_source_count=0,journal_read_status='confirmed',journal_unresolved_move_refs=[],results=[])
        save_report(self.reports,report)
        self.finish(process,run,'confirmed')
        self.assertEqual(process.returncode,0)
        record=self.ended(run)
        self.assertEqual(record['disposition'],'finished')
        self.assertEqual(record['report_sha256'],hashlib.sha256((self.reports/(run+'.json')).read_bytes()).hexdigest())
        self.assertEqual(record['started_sha256'],hashlib.sha256((self.lifecycle/(run+'.started.json')).read_bytes()).hexdigest())

    def test_missing_or_wrong_scope_report_cannot_finish(self):
        for variant in ('missing','wrong_scope'):
            process,run=self.start(); self.ready(process,run)
            if variant=='wrong_scope':
                save_report(self.reports,dict(report_version=1,simulation_only=True,run_id=run,machine_id='PC-B',route='local_to_cloud',
                    inventory_complete=True,inventory_source_count=0,journal_read_status='confirmed',journal_unresolved_move_refs=[],results=[]))
            stdout,stderr=self.finish(process,run,'confirmed')
            self.assertEqual(process.returncode,1)
            self.assertEqual(self.ended(run)['disposition'],'interrupted')
            self.assertNotIn('finished',stdout)

    def test_scope_and_root_overlap_fail_before_writes(self):
        for kwargs in (dict(machine='PC-B',route='cloud_to_archive'),dict(lifecycle=self.journal),dict(run='D:/synthetic-private')):
            process,_=self.start(**kwargs)
            stdout,stderr=process.communicate(timeout=20)
            self.assertEqual(process.returncode,1)
            self.assertNotIn('synthetic-private',stdout+stderr)
            self.assertEqual(list(self.lifecycle.iterdir()),[])
            self.assertEqual(list(self.journal.iterdir()),[])

    def test_run_uuid_cannot_be_reused(self):
        process,run=self.start(); self.ready(process,run); self.finish(process,run)
        before={p.name:p.read_bytes() for p in self.lifecycle.iterdir()}
        second,_=self.start(run=run)
        second.communicate(timeout=20)
        self.assertEqual(second.returncode,1)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.lifecycle.iterdir()})

    def test_modified_owner_record_is_preserved_and_no_finished_ack_is_sent(self):
        process,run=self.start(); self.ready(process,run)
        lock=next(self.lifecycle.glob('*.lock'))
        lock.write_bytes(b'changed synthetic ownership')
        stdout,stderr=self.finish(process,run)
        self.assertEqual(process.returncode,1)
        self.assertEqual(lock.read_bytes(),b'changed synthetic ownership')
        self.assertNotIn('finished',stdout)

    def test_invalid_request_records_interrupted_and_never_leaks_private_input(self):
        for message in ('{}\n','{"private":"secret-synthetic-value"}\n','x'*4097+'\n'):
            process,run=self.start(); self.ready(process,run)
            stdout,stderr=process.communicate(message,timeout=20)
            self.assertEqual(process.returncode,1)
            self.assertEqual(self.ended(run)['disposition'],'interrupted')
            self.assertNotIn('secret-synthetic-value',stdout+stderr)


if __name__=='__main__': unittest.main()
