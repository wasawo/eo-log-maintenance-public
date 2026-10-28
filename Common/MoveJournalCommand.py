"""Internal simulation journal bridge, not a Drive or source-file adapter."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Common.MoveJournal import (MAX_RECORD_BYTES, MoveJournalError, _unique, _number,
                               _read, decode_move_record, encode_move_record, read_move_journal, save_move_record)


def publish_simulation_record(root, request):
    if (type(request) is not dict or set(request) != {'protocol_version','request_id','simulation_only','record'}
            or type(request['protocol_version']) is not int or request['protocol_version'] != 1
            or request['simulation_only'] is not True):
        raise MoveJournalError('move_journal_command_invalid')
    candidate = decode_move_record(encode_move_record(request['record']))
    if request['request_id'] != candidate['record_id']:
        raise MoveJournalError('move_journal_command_invalid')
    if candidate['event_kind'] == 'prepared':
        records = read_move_journal(root)
        matching = set()
        for prior in records:
            if prior['event_kind'] != 'prepared': continue
            same = all(candidate[key] == prior[key] for key in ('machine_id','route','log_type'))
            same = same and all(candidate['event_data'][key] == prior['event_data'][key] for key in ('source','copy_content'))
            if prior['move_id'] == candidate['move_id'] and not same:
                raise MoveJournalError('move_journal_identity_conflict')
            if same: matching.add(prior['move_id'])
        if len(matching) > 1:
            raise MoveJournalError('move_journal_identity_conflict')
        if matching: candidate['move_id'] = next(iter(matching))
    elif candidate['event_kind'] == 'reconciliation' and len(candidate['prior_record_refs']) == 1:
        prepared_id = candidate['prior_record_refs'][0]['record_id']
        records = read_move_journal(root)
        results = [r for r in records if r['event_kind'] == 'deletion_result'
                   and r['prior_record_refs'][0]['record_id'] == prepared_id]
        if len(results) == 1:
            prior_raw, prior = _read(Path(root), results[0]['record_id'])
            candidate['prior_record_refs'].append(dict(record_id=prior['record_id'], path=prior['record_id']+'.json',
                sha256=hashlib.sha256(prior_raw).hexdigest()))
    raw = encode_move_record(candidate)
    save_move_record(root, raw)
    return dict(protocol_version=1, request_id=request['request_id'], ok=True,
                record=candidate, record_sha256=hashlib.sha256(raw).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--journal-root', required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_RECORD_BYTES+1)
        if len(raw) > MAX_RECORD_BYTES: raise MoveJournalError('move_journal_command_invalid')
        request = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_float=_number, parse_constant=_number)
        print(json.dumps(publish_simulation_record(args.journal_root, request), separators=(',',':')))
        return 0
    except Exception:
        print(json.dumps(dict(protocol_version=1, ok=False, reason_code='move_journal_command_failed')))
        return 1


if __name__ == '__main__': raise SystemExit(main())
