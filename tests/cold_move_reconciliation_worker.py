"""TEST ONLY: cold, read-only native observation of a constructor-owned fixture.

Only journal appends are allowed; never delete a source or invoke Drive APIs.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from uuid import uuid4

# The script's directory is tests/, not the repository import root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Common.MoveJournal import (MoveJournalError, encode_move_record, load_move_record,
                                read_move_journal, save_move_record)
from windows_move_delete_probe import DisposableMoveDeleteProbe, MoveDeleteProbeError


class _ReadOnlyObserver:
    _NAMES = DisposableMoveDeleteProbe._NAMES
    _initialize_api = DisposableMoveDeleteProbe._initialize_api
    _directory_chain = DisposableMoveDeleteProbe._directory_chain
    _verify_root = DisposableMoveDeleteProbe._verify_root
    _path = DisposableMoveDeleteProbe._path
    _info = DisposableMoveDeleteProbe._info
    _content = DisposableMoveDeleteProbe._content
    _open = DisposableMoveDeleteProbe._open
    _close = DisposableMoveDeleteProbe._close
    _handle = DisposableMoveDeleteProbe._handle
    _absence = DisposableMoveDeleteProbe._absence

    def __init__(self, root, nonce):
        if os.name != 'nt' or re.fullmatch('[0-9a-f]{32}', nonce) is None:
            raise MoveDeleteProbeError('fixture_invalid')
        self._parent = Path(tempfile.gettempdir()).resolve(strict=True)
        self._root = Path(root)
        if (not self._root.is_absolute() or self._root.parent != self._parent
                or not self._root.name.startswith('eolm-move-delete-')
                or self._root.resolve(strict=True) != self._root):
            raise MoveDeleteProbeError('fixture_invalid')
        self._nonce = nonce.encode('ascii')
        self._chain = self._directory_chain()
        self._verify_root()
        self._initialize_api()
        create = self._api.CreateFileW

        def readonly_open(path, access, *args):
            if access & (0x40000000 | 0x10000):  # GENERIC_WRITE | DELETE
                raise MoveDeleteProbeError('fixture_mutation_denied')
            return create(path, access, *args)

        def deny_disposition(*_):
            raise MoveDeleteProbeError('fixture_mutation_denied')

        self._api.CreateFileW = readonly_open
        self._api.SetFileInformationByHandle = deny_disposition


def _source_state(observer, prepared):
    source = prepared['event_data']['source']
    expected = (int(source['identity']['volume_serial'], 16), source['identity']['file_id'])
    try:
        with observer._handle('source.bin') as handle:
            identity, _ = observer._info(handle)
            return 'present' if identity == expected else 'unknown'
    except FileNotFoundError:
        return 'absent' if observer._absence() else 'unknown'
    except (OSError, MoveDeleteProbeError):
        return 'unknown'


def reconcile_fixture(root, nonce):
    observer = _ReadOnlyObserver(root, nonce)
    path = observer._path('fixture.json')
    if path.stat().st_size > 16384:
        raise MoveDeleteProbeError('fixture_invalid')
    descriptor = json.loads(path.read_bytes())
    if (set(descriptor) != {'kind', 'prepared_id', 'prepared_sha256', 'destination_id', 'root_chain'}
            or descriptor['kind'] != 'cold-move-fixture-v1'
            or tuple(map(tuple, descriptor['root_chain'])) != observer._chain):
        raise MoveDeleteProbeError('fixture_invalid')
    journal = observer._root / 'journal'
    records = read_move_journal(journal)
    prepared = load_move_record(journal, descriptor['prepared_id'])
    raw = (journal / (prepared['record_id']+'.json')).read_bytes()
    if (hashlib.sha256(raw).hexdigest() != descriptor['prepared_sha256']
            or prepared['event_kind'] != 'prepared' or prepared['route'] != 'local_to_cloud'
            or prepared['machine_id'] != 'PC-A' or prepared['log_type'] != 'BattleLog'
            or prepared['event_data']['source']['relative_path'] != 'source.bin'
            or prepared['event_data']['destination']['file_id'] != 'synthetic-cloud-object'):
        raise MoveDeleteProbeError('fixture_binding_invalid')
    results = [r for r in records if r['event_kind'] == 'deletion_result'
               and r['prior_record_refs'][0]['record_id'] == prepared['record_id']]
    refs = [dict(record_id=prepared['record_id'], path=prepared['record_id']+'.json',
                 sha256=hashlib.sha256(raw).hexdigest())]
    if results:
        prior = results[0]
        refs.append(dict(record_id=prior['record_id'], path=prior['record_id']+'.json',
                         sha256=hashlib.sha256((journal/(prior['record_id']+'.json')).read_bytes()).hexdigest()))
    with ExitStack() as stack:
        current = None
        try:
            destination = stack.enter_context(observer._handle('destination.bin'))
            identity, size, digest = observer._content(destination)
            if identity == tuple(descriptor['destination_id']):
                current = dict(size=size, sha256=digest)
        except (OSError, MoveDeleteProbeError):
            pass
        presence = _source_state(observer, prepared)
        observer._verify_root()
        complete = presence == 'absent' and current == prepared['event_data']['copy_content']
        decision = 'completed' if complete else ('incomplete' if presence == 'present' else 'unknown')
        value = dict(prepared, record_id=str(uuid4()), run_id=str(uuid4()), attempt_id=str(uuid4()),
                     event_kind='reconciliation', prior_record_refs=refs,
                     observed_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                     recorded_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
        value['event_data'] = dict(source=prepared['event_data']['source'], destination=prepared['event_data']['destination'],
            source_current=presence, destination_current=current,
            source_method='windows_lookup' if presence != 'unknown' else 'unavailable',
            destination_method='drive_download' if current is not None else 'unavailable',
            decision=decision, completion_basis='reconciled' if complete else 'none',
            reason_code='reconciled_completion' if complete else 'state_unconfirmed')
        save_move_record(journal, encode_move_record(value))
    return dict(record_id=value['record_id'], decision=decision, source_current=presence)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise MoveDeleteProbeError('fixture_arguments_invalid')
        print(json.dumps(reconcile_fixture(sys.argv[1], sys.argv[2])))
    except (MoveDeleteProbeError, MoveJournalError) as exc:
        print(json.dumps(dict(error=str(exc))))
        raise SystemExit(1)
    except Exception:
        print(json.dumps(dict(error='fixture_observation_failed')))
        raise SystemExit(1)
