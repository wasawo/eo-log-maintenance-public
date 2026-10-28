"""Private final reports for the in-memory model, never deletion evidence."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Common.AtomicArtifactPublication import publish_bytes_no_overwrite, _chain, _regular, _signature
from Common.MoveJournal import _unique, _number, _relative, _UUID
from Common.MoveRunReport import _scope

MAX_REPORT_BYTES = 8 * 1024 * 1024
REASONS = {
    'retention_period': ('not_eligible', 'none'),
    'filename_invalid': ('retained', 'inspect_source'),
    'destination_ambiguous': ('retained', 'resolve_conflict'),
    'content_conflict': ('retained', 'resolve_conflict'),
    'copy_failed': ('retained', 'retry_move'),
    'destination_mismatch': ('retained', 'inspect_destination'),
    'record_failed': ('retained', 'inspect_records'),
    'source_changed': ('retained', 'retry_move'),
    'verification_unknown': ('retained', 'reobserve'),
    'delete_failed': ('retained', 'retry_move'),
    'delete_unknown': ('unknown', 'reobserve'),
    'result_record_failed': ('unknown', 'inspect_records'),
    'record_missing': ('unknown', 'inspect_records'),
    'reconciliation_unconfirmed': ('unknown', 'reobserve'),
    'delete_confirmed': ('completed', 'none'),
    'reconciled_completion': ('completed', 'none'),
}


def _require(condition):
    if not condition:
        raise ValueError('simulation_report_invalid')


def _keys(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()))


def _hex(value):
    _require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None)


def summarize(report):
    _keys(report, 'report_version simulation_only run_id machine_id route inventory_complete inventory_source_count journal_read_status journal_unresolved_move_refs results')
    _require(type(report['report_version']) is int and report['report_version'] == 1 and report['simulation_only'] is True)
    _scope(report['run_id'], report['machine_id'], report['route'])
    _require(report['inventory_complete'] is True and type(report['inventory_source_count']) is int and report['inventory_source_count'] >= 0)
    _require(report['journal_read_status'] in ('disabled', 'confirmed', 'unconfirmed'))
    refs = report['journal_unresolved_move_refs']
    _require(type(refs) is list and all(type(ref) is str and re.fullmatch(_UUID, ref) for ref in refs) and len(refs) == len(set(refs)))
    _require(report['journal_read_status'] == 'confirmed' or not refs)
    _require(type(report['results']) is list)
    seen = set()
    for item in report['results']:
        _keys(item, 'source_ref source_relative_path log_type outcome reason_code next_action destination_candidates')
        _hex(item['source_ref'])
        _require(item['source_ref'] not in seen)
        seen.add(item['source_ref'])
        _relative(item['source_relative_path'])
        _require(item['log_type'] in ('BattleLog', 'ErrorReport') and type(item['reason_code']) is str and item['reason_code'] in REASONS)
        _require(item['outcome'] == REASONS[item['reason_code']][0])
        _require(item['next_action'] == REASONS[item['reason_code']][1])
        _require(type(item['destination_candidates']) is list)
        targets = set()
        for target in item['destination_candidates']:
            _keys(target, 'target_ref relative_path')
            _hex(target['target_ref'])
            _relative(target['relative_path'])
            _require(target['target_ref'] not in targets)
            targets.add(target['target_ref'])
    _require(len(seen) >= report['inventory_source_count'])
    results = report['results']
    deleted = sum(r['reason_code'] == 'delete_confirmed' for r in results)
    reconciled = sum(r['reason_code'] == 'reconciled_completion' for r in results)
    unresolved = sum(r['outcome'] in ('retained', 'unknown') for r in results)
    pending = unresolved or refs or report['journal_read_status'] == 'unconfirmed'
    status = ('partial_failure' if deleted + reconciled else 'failure') if pending else ('success' if deleted + reconciled else 'no_work')
    return dict(report_version=1, run_id=report['run_id'], machine_id=report['machine_id'], route=report['route'],
                simulation_only=True, status=status, inventory_source_count=report['inventory_source_count'],
                result_source_count=len(results), deleted_source_count=deleted, reconciled_source_count=reconciled,
                unresolved_source_count=unresolved, journal_unresolved_source_count=len(refs),
                journal_read_status=report['journal_read_status'])


def encode(report):
    summarize(report)
    raw = (json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')
    _require(len(raw) <= MAX_REPORT_BYTES)
    return raw


def decode(raw):
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_REPORT_BYTES)
    report = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_float=_number, parse_constant=_number)
    summarize(report)
    return report


def read_report(root, run_id):
    _require(type(run_id) is str and re.fullmatch(_UUID, run_id) is not None)
    parent = Path(root).absolute()
    path = parent / (run_id+'.json')
    chain = _chain(parent)
    before = path.lstat()
    _require(_regular(before) and before.st_nlink == 1 and 0 < before.st_size <= MAX_REPORT_BYTES)
    signature = _signature(before)
    with path.open('rb') as stream:
        _require(_signature(os.fstat(stream.fileno())) == signature)
        raw = stream.read(before.st_size+1)
        _require(_signature(os.fstat(stream.fileno())) == signature)
    _require(len(raw) == before.st_size and _signature(path.lstat()) == signature and _chain(parent) == chain)
    report = decode(raw)
    _require(report['run_id'] == run_id)
    return raw, report


def save_report(root, report):
    raw = encode(report)
    publish_bytes_no_overwrite(Path(root) / (report['run_id']+'.json'), raw)
    saved, loaded = read_report(root, report['run_id'])
    _require(saved == raw)
    return summarize(loaded)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report-root', required=True)
    parser.add_argument('--read-run-id')
    args = parser.parse_args()
    try:
        if args.read_run_id:
            summary = summarize(read_report(args.report_root, args.read_run_id)[1])
        else:
            summary = save_report(args.report_root, decode(sys.stdin.buffer.read(MAX_REPORT_BYTES+1)))
        print(json.dumps(dict(ok=True, summary=summary), separators=(',', ':')))
        return 0
    except Exception:
        print(json.dumps(dict(ok=False, reason_code='simulation_report_unconfirmed')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
