"""Own a synthetic move run while its PowerShell caller processes the model.

This broker neither reads source logs nor grants production root qualification.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Common.AtomicArtifactPublication import _chain, _same_bytes, publish_bytes_no_overwrite
from Common.MoveJournal import _unique, _number
from Common.MoveRunReport import _scope
from Common.OwnedRunLock import acquire_owned_lock, _record_matches
from Common.SimulationRunReport import read_report, summarize

MAX_REQUEST_BYTES = 4096


def _require(condition):
    if not condition:
        raise ValueError('simulation_owner_unconfirmed')


def _root(value):
    root = Path(value).absolute()
    _chain(root)
    return root


def _scope_ref(journal):
    # The model journal is a single-writer resource, regardless of route/PC.
    return hashlib.sha256(str(journal).replace('\\', '/').casefold().encode('utf-8')).hexdigest()


def _publish(root, name, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')
    path = root / name
    publish_bytes_no_overwrite(path, raw)
    _require(_same_bytes(path, raw))
    return hashlib.sha256(raw).hexdigest()


def _emit(phase, run_id, **extra):
    print(json.dumps(dict(protocol_version=1, phase=phase, run_id=run_id, **extra)), flush=True)


def serve(args, input_stream):
    _scope(args.run_id, args.machine_id, args.route)
    lifecycle, journal, reports = map(_root, (args.lifecycle_root, args.journal_root, args.report_root))
    roots = (lifecycle, journal, reports)
    # Fixed placement prevents a new caller selecting another directory to
    # bypass a preserved lock record after the original owner was killed.
    _require(lifecycle == journal.with_name(journal.name+'.lifecycle'))
    _require(all(a != b and a not in b.parents and b not in a.parents for index,a in enumerate(roots) for b in roots[index+1:]))
    chains = [_chain(root) for root in roots]
    scope = _scope_ref(journal)
    base = dict(lifecycle_version=1, simulation_only=True, run_id=args.run_id,
                machine_id=args.machine_id, route=args.route, scope_ref=scope)
    lock_path = lifecycle / (scope+'.lock')
    lock_scope='MoveSimulation-'+scope[:48]
    with acquire_owned_lock(lock_scope, lock_path, timeout_seconds=0, maximum_record_bytes=4096) as token:
        _require([_chain(root) for root in roots] == chains)
        # A run UUID is single-use, even if the previous model never moved data.
        _require(not (lifecycle/(args.run_id+'.started.json')).exists() and not (lifecycle/(args.run_id+'.ended.json')).exists())
        started = dict(base, event_kind='started', recorded_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))
        digest = _publish(lifecycle, args.run_id+'.started.json', started)
        ending = dict(base, event_kind='ended', started_sha256=digest, disposition='interrupted',
                      operation_status=None, report_save_status=None, report_sha256=None)
        try:
            _emit('ready', args.run_id)
            sequence=0
            while True:
                raw = input_stream.readline(MAX_REQUEST_BYTES+1)
                _require(0 < len(raw) <= MAX_REQUEST_BYTES and raw.endswith(b'\n'))
                request = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_float=_number, parse_constant=_number)
                _require(type(request) is dict)
                _require([_chain(root) for root in roots] == chains and _record_matches(lock_path,lock_scope,token,4096))
                if request.get('kind') != 'check':
                    break
                _require(set(request) == {'protocol_version','run_id','kind','sequence'})
                _require(type(request['protocol_version']) is int and request['protocol_version'] == 1 and request['run_id'] == args.run_id)
                _require(type(request['sequence']) is int and request['sequence'] == sequence+1)
                sequence=request['sequence']
                _emit('owned',args.run_id,sequence=sequence)
            _require(type(request) is dict and set(request) == {'protocol_version','run_id','operation_status','report_save_status'})
            _require(type(request['protocol_version']) is int and request['protocol_version'] == 1 and request['run_id'] == args.run_id)
            _require(request['operation_status'] in ('success','no_work','partial_failure','failure'))
            _require(request['report_save_status'] in ('confirmed','unconfirmed'))
            _require([_chain(root) for root in roots] == chains)
            if request['report_save_status'] == 'confirmed':
                report_raw, report = read_report(reports, args.run_id)
                summary = summarize(report)
                _require(all(report[key] == base[key] for key in ('run_id','machine_id','route')))
                _require(summary['status'] == request['operation_status'])
                ending['report_sha256'] = hashlib.sha256(report_raw).hexdigest()
            ending.update(disposition='finished', operation_status=request['operation_status'], report_save_status=request['report_save_status'])
        finally:
            ending['recorded_at_utc'] = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            _publish(lifecycle, args.run_id+'.ended.json', ending)
    # ACK only after the mutex/ownership cleanup has also returned.
    try:
        lock_path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ValueError('simulation_owner_unconfirmed')
    _emit('finished', args.run_id)


def main():
    parser=argparse.ArgumentParser()
    for name in ('lifecycle-root','journal-root','report-root','run-id','machine-id','route'):
        parser.add_argument('--'+name, required=True)
    args=parser.parse_args()
    try:
        serve(args, sys.stdin.buffer)
        return 0
    except Exception:
        print(json.dumps(dict(protocol_version=1, phase='unconfirmed')), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
