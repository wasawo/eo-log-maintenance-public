"""Simulation bridge identity selection and immutable journal binding."""
import copy
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from Common.MoveJournal import MoveJournalError, encode_move_record, save_move_record
from Common.MoveJournalCommand import publish_simulation_record
from test_move_journal import prepared


def request(value):
    return dict(protocol_version=1,request_id=value['record_id'],simulation_only=True,record=value)


class SimulationJournalCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='eolm-journal-command-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_same_source_and_copy_reuse_move_but_keep_distinct_run_and_attempt(self):
        one=prepared()
        first=publish_simulation_record(self.root,request(one))
        two=prepared()
        second=publish_simulation_record(self.root,request(two))
        self.assertEqual(first['record']['move_id'],second['record']['move_id'])
        self.assertNotEqual(first['record']['run_id'],second['record']['run_id'])
        self.assertNotEqual(first['record']['attempt_id'],second['record']['attempt_id'])
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(second,publish_simulation_record(self.root,request(two)))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_distinct_physical_source_or_changed_copy_gets_a_new_move(self):
        one=prepared()
        first=publish_simulation_record(self.root,request(one))
        for variant in ('identity','content'):
            other=prepared()
            if variant=='identity': other['event_data']['source']['identity']['file_id']='2'*32
            else:
                other['event_data']['copy_content']['sha256']='3'*64
                other['event_data']['destination_content']['sha256']='3'*64
            result=publish_simulation_record(self.root,request(other))
            self.assertNotEqual(first['record']['move_id'],result['record']['move_id'])

    def test_conflicting_existing_move_ids_or_bad_request_add_no_record(self):
        one=prepared()
        save_move_record(self.root,encode_move_record(one))
        two=prepared()
        save_move_record(self.root,encode_move_record(two))
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        with self.assertRaisesRegex(MoveJournalError,'identity_conflict'):
            publish_simulation_record(self.root,request(prepared()))
        bad=request(copy.deepcopy(one)); bad['simulation_only']=False
        with self.assertRaises(MoveJournalError): publish_simulation_record(self.root,bad)
        bad=request(copy.deepcopy(one)); bad['request_id']=str(uuid4())
        with self.assertRaises(MoveJournalError): publish_simulation_record(self.root,bad)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})


if __name__=='__main__': unittest.main()
