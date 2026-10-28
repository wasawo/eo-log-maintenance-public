"""Synthetic immutable records, disk failures and a cold-process reload."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

from jsonschema import Draft202012Validator

from Common.MoveJournal import (MoveJournalError, decode_move_record, encode_move_record,
                                load_move_record, read_move_journal, save_move_record)


def identifier():
    return str(uuid4())


def content(data=b'synthetic'):
    return dict(size=len(data), sha256=hashlib.sha256(data).hexdigest())


def prepared(machine='PC-A', route='local_to_cloud'):
    local = dict(kind='local', machine_id=machine, root_key='battleLogLocal',
                 relative_path='nested/20240101_12345678@a.txt',
                 identity=dict(volume_serial='0' * 16, file_id='1' * 32))
    cloud = dict(kind='cloud', root_key='battleLogDrive', file_id='synthetic-file',
                 parent_id='synthetic-parent', name='20240101_12345678@a.txt', version='7')
    if route == 'cloud_to_archive':
        local.update(machine_id='PC-A', root_key='battleLogArchive', relative_path=cloud['name'])
        source, destination = cloud, local
    else:
        source, destination = local, cloud
    return dict(record_version=1, record_id=identifier(), run_id=identifier(), move_id=identifier(),
                attempt_id=identifier(), event_kind='prepared', route=route, machine_id=machine,
                log_type='BattleLog', observed_at_utc='2026-10-28T01:00:00.123456789123Z',
                recorded_at_utc='2026-10-28T01:00:01Z', prior_record_refs=[],
                event_data=dict(source=source, destination=destination, copy_content=content(),
                                destination_content=content(), reused=False,
                                destination_method='drive_download' if route == 'local_to_cloud' else 'windows_handle'))


def reference(value, raw=None):
    raw = encode_move_record(value) if raw is None else raw
    return dict(path=value['record_id'] + '.json', record_id=value['record_id'], sha256=hashlib.sha256(raw).hexdigest())


def followup(prior, kind='deletion_result', *, absent=False):
    value = copy.deepcopy(prior)
    value.update(record_id=identifier(), event_kind=kind, prior_record_refs=[reference(prior)])
    if kind == 'deletion_result':
        value['event_data'] = dict(source=prior['event_data']['source'], destination=prior['event_data']['destination'],
            source_before_delete=content(), destination_current=content(),
            source_method='windows_handle' if prior['event_data']['source']['kind'] == 'local' else 'drive_download',
            destination_method='windows_handle' if prior['event_data']['destination']['kind'] == 'local' else 'drive_download', request_outcome='unknown', source_after_delete='unknown', source_after_method='unavailable',
            decision='unknown', completion_basis='none', reason_code='verification_unknown')
    else:
        value.update(run_id=identifier(), attempt_id=identifier())
        value['event_data'] = dict(source=prior['event_data']['source'], destination=prior['event_data']['destination'],
            source_current='absent' if absent else 'unknown', destination_current=content(),
            source_method=('windows_lookup' if prior['event_data']['source']['kind'] == 'local' else 'provider_observation') if absent else 'unavailable',
            destination_method='windows_handle' if prior['event_data']['destination']['kind'] == 'local' else 'drive_download',
            decision='completed' if absent else 'unknown', completion_basis='reconciled' if absent else 'none',
            reason_code='reconciled_completion' if absent else 'state_unconfirmed')
    return value


class MoveJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='eolm-journal-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, value):
        return save_move_record(self.root, encode_move_record(value))

    def test_schema_valid_and_both_routes_roundtrip(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / 'contracts/move-record-v1.schema.json').read_bytes())
        Draft202012Validator.check_schema(schema)
        for machine, route in [('PC-A','local_to_cloud'), ('PC-B','local_to_cloud'), ('PC-A','cloud_to_archive')]:
            value = prepared(machine, route)
            self.assertEqual('published', self.save(value))
            self.assertEqual(value, load_move_record(self.root, value['record_id']))
            self.assertEqual('already_exists_identical', self.save(value))
            self.save(followup(value))
            reconciliation = followup(value, 'reconciliation', absent=True)
            self.save(reconciliation)
            self.assertEqual('completed', load_move_record(self.root, reconciliation['record_id'])['event_data']['decision'])
        self.assertEqual(9, len(read_move_journal(self.root)))

    def test_shape_duplicate_keys_numbers_dates_and_role_rejected(self):
        base = prepared()
        changes = [('record_version', True), ('record_version', 1.0), ('machine_id', 'PC-B'),
                   ('observed_at_utc', '2026-02-30T00:00:00Z'), ('unexpected', 'private detail')]
        for field, value in changes:
            bad = copy.deepcopy(base)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(MoveJournalError):
                encode_move_record(bad)
        bad = prepared('PC-B', 'cloud_to_archive')
        with self.assertRaises(MoveJournalError): encode_move_record(bad)
        raw = encode_move_record(base).replace(b'"record_version":1', b'"record_version":1,"record_version":1')
        with self.assertRaises(MoveJournalError): decode_move_record(raw)
        for raw in (b'{}', b'\xef\xbb\xbf' + encode_move_record(base), b'\xff', b'NaN', b'x' * (1024*1024+1)):
            with self.assertRaises(MoveJournalError): decode_move_record(raw)
        self.assertEqual([], list(self.root.iterdir()))

    def test_flattening_and_canonical_paths(self):
        for path in ('../file', '/root/file', 'C:/file', 'a\\file', 'a//file', 'a/./file', 'CON.txt', 'a. /file'):
            bad = prepared()
            bad['event_data']['source']['relative_path'] = path
            with self.subTest(path=path), self.assertRaises(MoveJournalError): encode_move_record(bad)
        bad = prepared()
        bad['event_data']['destination']['name'] = 'nested/20240101_12345678@a.txt'
        with self.assertRaises(MoveJournalError): encode_move_record(bad)

    def test_precision_preserved_and_record_id_conflict_is_not_overwritten(self):
        value = prepared()
        self.save(value)
        path = self.root / (value['record_id'] + '.json')
        original = path.read_bytes()
        value['recorded_at_utc'] = '2026-10-28T01:00:02Z'
        with self.assertRaisesRegex(MoveJournalError, 'destination_conflict'):
            self.save(value)
        self.assertEqual(original, path.read_bytes())
        self.assertIn(b'.123456789123Z', original)

    def test_exact_reference_missing_and_tampered_bytes(self):
        first = prepared()
        result = followup(first)
        with self.assertRaises(MoveJournalError): self.save(result)
        self.save(first)
        path = self.root / (first['record_id'] + '.json')
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(MoveJournalError, 'digest_mismatch'): self.save(result)
        self.assertFalse((self.root / (result['record_id'] + '.json')).exists())

    def test_different_scope_or_observation_target_cannot_complete(self):
        first = prepared()
        self.save(first)
        for changed in ('move_id', 'attempt_id', 'source'):
            bad = followup(first)
            if changed == 'source': bad['event_data']['source']['identity']['file_id'] = '2' * 32
            else: bad[changed] = identifier()
            with self.subTest(changed=changed), self.assertRaises(MoveJournalError): self.save(bad)

    def test_delete_success_does_not_imply_removal_and_q5_is_required(self):
        first = prepared()
        self.save(first)
        result = followup(first)
        result['event_data']['request_outcome'] = 'succeeded'
        self.save(result)
        self.assertEqual('unknown', load_move_record(self.root, result['record_id'])['event_data']['decision'])
        for field in ('source_before_delete', 'destination_current'):
            separate = prepared()
            self.save(separate)
            bad = followup(separate)
            bad['event_data']['request_outcome'] = 'succeeded'
            bad['event_data'][field] = None
            with self.assertRaisesRegex(MoveJournalError, 'q5_missing'): self.save(bad)
        separate = prepared()
        self.save(separate)
        bad = followup(separate)
        bad['event_data'].update(request_outcome='succeeded', decision='completed', completion_basis='delete_confirmed')
        with self.assertRaisesRegex(MoveJournalError, 'decision_invalid'): self.save(bad)

    def test_completed_delete_and_reconciliation_have_distinct_bases(self):
        first = prepared()
        self.save(first)
        result = followup(first)
        result['event_data'].update(request_outcome='succeeded', source_after_delete='absent',
                                    source_after_method='windows_lookup', decision='completed', completion_basis='delete_confirmed', reason_code='delete_confirmed')
        self.save(result)
        reconciled = followup(first, 'reconciliation', absent=True)
        reconciled['prior_record_refs'].append(reference(result))
        self.save(reconciled)
        self.assertEqual('reconciled', load_move_record(self.root, reconciled['record_id'])['event_data']['completion_basis'])
        self.assertEqual('delete_confirmed', load_move_record(self.root, result['record_id'])['event_data']['completion_basis'])

    def test_unconfirmed_reconciliation_cannot_become_completed(self):
        first = prepared()
        self.save(first)
        for issue in ('source_unknown', 'destination_missing', 'destination_mismatch'):
            bad = followup(first, 'reconciliation', absent=True)
            if issue == 'source_unknown': bad['event_data']['source_current'] = 'unknown'
            else: bad['event_data']['destination_current'] = None if issue == 'destination_missing' else content(b'changed')
            with self.subTest(issue=issue), self.assertRaisesRegex(MoveJournalError, 'decision_invalid'): self.save(bad)

    def test_unexpected_or_corrupt_entries_never_disappear_as_no_work(self):
        self.assertEqual([], read_move_journal(self.root))
        for name in ('unfinished.tmp', identifier()+'.json'):
            path = self.root / name
            path.write_bytes(b'partial')
            with self.assertRaises(MoveJournalError): read_move_journal(self.root)
            path.unlink()

    def test_conflicting_results_for_one_attempt_stop_journal_read(self):
        first = prepared()
        self.save(first)
        self.save(followup(first))
        second = followup(first)
        with self.assertRaisesRegex(MoveJournalError, 'attempt_conflict'): self.save(second)
        # Simulate an out-of-protocol writer; the reader must also detect it.
        (self.root / (second['record_id']+'.json')).write_bytes(encode_move_record(second))
        with self.assertRaisesRegex(MoveJournalError, 'attempt_conflict'): read_move_journal(self.root)

    def test_reference_path_cannot_escape_or_follow_a_long_record_chain(self):
        first = prepared()
        self.save(first)
        result = followup(first)
        result['prior_record_refs'][0]['path'] = '../outside.json'
        with self.assertRaises(MoveJournalError): self.save(result)
        result = followup(first)
        self.save(result)
        bad = followup(result)
        bad['event_data'] = followup(first)['event_data']
        with self.assertRaisesRegex(MoveJournalError, 'reference_invalid'): self.save(bad)

    def test_missing_observations_remain_unknown_and_incompatible_methods_are_rejected(self):
        first = prepared()
        self.save(first)
        unknown = followup(first)
        unknown['event_data'].update(source_before_delete=None, destination_current=None,
                                     source_method='unavailable', destination_method='unavailable')
        self.save(unknown)
        self.assertEqual('unknown', load_move_record(self.root, unknown['record_id'])['event_data']['decision'])
        bad = followup(first)
        bad['event_data']['source_method'] = 'drive_metadata'
        with self.assertRaises(MoveJournalError): self.save(bad)
        for identity in ('../outside', 'C:/outside', '', identifier().upper()):
            with self.assertRaisesRegex(MoveJournalError, 'id_invalid'): load_move_record(self.root, identity)

    def test_incomplete_prepare_is_preserved_but_corrupt_filename_binding_is_rejected(self):
        first = prepared()
        self.save(first)
        self.assertEqual(['prepared'], [r['event_kind'] for r in read_move_journal(self.root)])
        wrong_name = self.root / (identifier() + '.json')
        wrong_name.write_bytes(encode_move_record(first))
        with self.assertRaisesRegex(MoveJournalError, 'id_mismatch'): read_move_journal(self.root)

    def test_cold_process_loads_pending_result_and_publishes_separate_reconciliation(self):
        first = prepared()
        self.save(first)
        unknown = followup(first)
        self.save(unknown)
        original = (self.root / (unknown['record_id'] + '.json')).read_bytes()
        # All observations in this child are synthetic adapter outputs, not live I/O.
        code = """
import hashlib,json,sys,uuid
from pathlib import Path
from Common.MoveJournal import read_move_journal,load_move_record,save_move_record,encode_move_record
root=Path(sys.argv[1]); records=read_move_journal(root)
p=next(r for r in records if r['event_kind']=='prepared')
u=next(r for r in records if r['event_kind']=='deletion_result')
r=dict(p,record_id=str(uuid.uuid4()),run_id=str(uuid.uuid4()),attempt_id=str(uuid.uuid4()),event_kind='reconciliation')
r['prior_record_refs']=[dict(path=v['record_id']+'.json',record_id=v['record_id'],sha256=hashlib.sha256((root/(v['record_id']+'.json')).read_bytes()).hexdigest()) for v in (p,u)]
r['event_data']=dict(source=p['event_data']['source'],destination=p['event_data']['destination'],source_current='absent',destination_current=p['event_data']['copy_content'],source_method='windows_lookup',destination_method='drive_download',decision='completed',completion_basis='reconciled',reason_code='reconciled_completion')
save_move_record(root,encode_move_record(r))
print(json.dumps(dict(record_id=r['record_id'],decision=load_move_record(root,r['record_id'])['event_data']['decision'],pending=u['event_data']['request_outcome'])))
"""
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        child = subprocess.run([sys.executable, '-B', '-c', code, str(self.root)],
                               cwd=Path(__file__).resolve().parents[1], env=env,
                               capture_output=True, text=True, check=True)
        output = json.loads(child.stdout)
        self.assertEqual('completed', output['decision'])
        self.assertEqual('unknown', output['pending'])
        self.assertEqual(original, (self.root / (unknown['record_id'] + '.json')).read_bytes())
        self.assertEqual('reconciliation', load_move_record(self.root, output['record_id'])['event_kind'])
        self.assertEqual(3, len(read_move_journal(self.root)))


if __name__ == '__main__':
    unittest.main()
