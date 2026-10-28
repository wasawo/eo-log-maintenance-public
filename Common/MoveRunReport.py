"""Read-only, identifier-only summaries of persisted move records.

This reports record facts, never run completeness or operation authority.
"""
import argparse
import json
from pathlib import Path
import re
import sys

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Common.MoveJournal import MoveJournalError, read_move_journal


class MoveRunReportError(ValueError):
    pass


def _scope(run_id, machine_id, route):
    if (type(run_id) is not str or re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', run_id) is None
            or machine_id not in ('PC-A', 'PC-B') or route not in ('local_to_cloud', 'cloud_to_archive')
            or (machine_id == 'PC-B' and route == 'cloud_to_archive')):
        raise MoveRunReportError('move_report_scope_invalid')


def summarize_move_run(records, *, run_id, machine_id, route):
    _scope(run_id, machine_id, route)
    # Input must come from read_move_journal, which validates references/decisions.
    scoped = [r for r in records if r['machine_id'] == machine_id and r['route'] == route]
    current = [r for r in scoped if r['run_id'] == run_id]
    source_moves = {}
    for record in scoped:
        if record['event_kind'] != 'prepared': continue
        data = record['event_data']
        key = json.dumps([record['log_type'], data['source'], data['copy_content']], sort_keys=True)
        previous = source_moves.setdefault(key, record['move_id'])
        if previous != record['move_id']:
            raise MoveRunReportError('move_report_source_identity_conflict')
    grouped = {}
    for record in scoped:
        grouped.setdefault(record['move_id'], []).append(record)
    details = []
    prepared_count = len({r['move_id'] for r in current if r['event_kind'] == 'prepared'})
    newly_completed = deleted = reconciled = already_completed = carried = 0
    for move_id, history in sorted(grouped.items()):
        present = [r for r in history if r['run_id'] == run_id]
        prior = [r for r in history if r['run_id'] != run_id]
        superseded = {ref['record_id'] for r in present for ref in r['prior_record_refs']}
        terminals = [r for r in present if r['event_kind'] != 'prepared' and r['record_id'] not in superseded]
        preparations = [r for r in history if r['event_kind'] == 'prepared']
        source_keys = {json.dumps([r['event_data']['source'],r['event_data']['copy_content']], sort_keys=True) for r in preparations}
        log_types = {r['log_type'] for r in history}
        state, reason, basis, action = 'unknown', 'result_not_recorded', 'none', 'reobserve'
        if len(source_keys) != 1 or len(log_types) != 1:
            reason, action = 'move_identity_conflict', 'inspect_records'
        elif len(terminals) > 1:
            reason, action = 'current_results_ambiguous', 'inspect_records'
        elif len(terminals) == 1:
            data = terminals[0]['event_data']
            state, reason, basis = data['decision'], data['reason_code'], data['completion_basis']
            if state == 'completed':
                action = 'none'
                prior_complete = any(r['event_kind'] != 'prepared' and r['event_data']['decision'] == 'completed' for r in prior)
                if prior_complete:
                    already_completed += 1
                else:
                    newly_completed += 1
                    if basis == 'delete_confirmed': deleted += 1
                    if basis == 'reconciled': reconciled += 1
        elif not present:
            # A result superseded by an explicit reference is not a pending leaf.
            referenced = {ref['record_id'] for r in history for ref in r['prior_record_refs']}
            leaves = [r for r in history if r['record_id'] not in referenced]
            attempts = {}
            for record in leaves:
                key = record['record_id'] if record['event_kind']=='prepared' else record['prior_record_refs'][0]['record_id']
                attempts.setdefault(key,[]).append(record)
            # One unambiguous completed attempt closes this exact source/content
            # movement; older failed attempts do not create another source task.
            if any(all(r['event_kind'] != 'prepared' and r['event_data']['decision']=='completed' for r in attempt)
                   for attempt in attempts.values()):
                continue
            if leaves and all(r['event_kind'] != 'prepared' and r['event_data']['decision'] == 'incomplete' for r in leaves):
                state = 'incomplete'
            reason = 'prior_unresolved_records'
        if not present:
            carried += 1
        if state == 'incomplete' and action != 'inspect_records':
            action = 'retry_move'
        details.append(dict(move_ref=move_id, log_type=next(iter(log_types)) if len(log_types) == 1 else 'unknown',
            state=state, completion_basis=basis, reason_code=reason, next_action=action,
            from_prior_run=not bool(present)))
    unresolved = sum(item['state'] != 'completed' for item in details)
    return dict(report_version=1, run_id=run_id, machine_id=machine_id, route=route,
        run_records_present=bool(current), prepared_source_count=prepared_count,
        newly_completed_source_count=newly_completed, deleted_source_count=deleted,
        reconciled_source_count=reconciled, already_completed_source_count=already_completed,
        unresolved_source_count=unresolved, carried_unresolved_source_count=carried, details=details)


def read_move_run_report(root, *, run_id, machine_id, route):
    _scope(run_id, machine_id, route)
    return summarize_move_run(read_move_journal(root), run_id=run_id, machine_id=machine_id, route=route)


def main():
    parser = argparse.ArgumentParser(description='Read private move records; no source/cloud operations.')
    parser.add_argument('--journal-root', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--machine-id', required=True)
    parser.add_argument('--route', required=True)
    args = parser.parse_args()
    try:
        report = read_move_run_report(args.journal_root, run_id=args.run_id, machine_id=args.machine_id, route=args.route)
        print(json.dumps(dict(ok=True, report=report), ensure_ascii=True, separators=(',', ':')))
        return 0
    except (MoveJournalError, MoveRunReportError) as exc:
        print(json.dumps(dict(ok=False, reason_code=str(exc))))
        return 1
    except Exception:
        print(json.dumps(dict(ok=False, reason_code='move_report_read_failed')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
