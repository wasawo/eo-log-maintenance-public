"""Immutable move-record storage/validation; never authorizes file operations.

Caller must qualify the private journal root, ownership, ACL and live providers.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re

from jsonschema import Draft202012Validator
from referencing import Registry

from Common.AtomicArtifactPublication import (
    ArtifactPublicationError, publish_bytes_no_overwrite, _chain, _regular, _signature,
)
from Common.LatestManifestSelection import _require_local_schema_refs, _no_schema_retrieval


class MoveJournalError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


MAX_RECORD_BYTES = 1024 * 1024
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"


def _reject(reason="move_record_invalid"):
    raise MoveJournalError(reason) from None


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _reject()
        value[key] = item
    return value


def _number(_):
    _reject()


def _relative(value):
    if type(value) is not str or not value or re.search(r'[<>:"\\|?*\x00-\x1f\x7f]', value):
        _reject()
    if any(0xd800 <= ord(c) <= 0xdfff for c in value):
        _reject()
    for segment in value.split('/'):
        if not segment or segment in ('.', '..') or segment.endswith((' ', '.')):
            _reject()
        if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', segment, re.IGNORECASE):
            _reject()


def _stamp(value):
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]+))?Z", value)
    if match is None:
        _reject()
    try:
        datetime.fromisoformat(match[1] + '+00:00')
    except ValueError:
        _reject()
    # Validate whole seconds, preserving the exact arbitrary-precision string.


def decode_move_record(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RECORD_BYTES:
        _reject()
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                           parse_float=_number, parse_constant=_number)
        schema_path = Path(__file__).resolve().parent.parent / 'contracts' / 'move-record-v1.schema.json'
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        _require_local_schema_refs(schema)
        Draft202012Validator(schema, registry=Registry(retrieve=_no_schema_retrieval)).validate(value)
        for field in ('observed_at_utc', 'recorded_at_utc'):
            _stamp(value[field])
        for ref in value['prior_record_refs']:
            if ref['path'] != ref['record_id'] + '.json':
                _reject()
        if len({ref['record_id'] for ref in value['prior_record_refs']}) != len(value['prior_record_refs']):
            _reject()
        if any(ref['record_id'] == value['record_id'] for ref in value['prior_record_refs']):
            _reject()
        data = value['event_data']
        if value['event_kind'] == 'prepared':
            source, destination = data['source'], data['destination']
            for endpoint in (source, destination):
                if endpoint['kind'] == 'local':
                    _relative(endpoint['relative_path'])
                else:
                    _relative(endpoint['name'])
                    if '/' in endpoint['name']:
                        _reject()
            suffix = 'battleLog' if value['log_type'] == 'BattleLog' else 'errorLog'
            if value['route'] == 'local_to_cloud':
                if (source['kind'] != 'local' or destination['kind'] != 'cloud'
                        or source['machine_id'] != value['machine_id']
                        or source['root_key'] != suffix + 'Local' or destination['root_key'] != suffix + 'Drive'):
                    _reject()
                name, target_name = source['relative_path'].rsplit('/', 1)[-1], destination['name']
            else:
                if (source['kind'] != 'cloud' or destination['kind'] != 'local'
                        or destination['machine_id'] != 'PC-A'
                        or source['root_key'] != suffix + 'Drive' or destination['root_key'] != suffix + 'Archive'):
                    _reject()
                name, target_name = source['name'], destination['relative_path']
            if name != target_name or data['copy_content'] != data['destination_content']:
                _reject()
            if data['destination_method'] == 'unavailable':
                _reject()
            allowed = ('windows_handle',) if destination['kind'] == 'local' else ('drive_metadata', 'drive_download')
            if data['destination_method'] not in allowed:
                _reject()
        else:
            if data['destination_current'] is not None and data['destination_method'] == 'unavailable':
                _reject()
            if value['event_kind'] == 'deletion_result':
                if data['source_before_delete'] is not None and data['source_method'] == 'unavailable':
                    _reject()
            elif data['source_current'] != 'unknown' and data['source_method'] == 'unavailable':
                _reject()
            allowed = ('windows_handle',) if data['destination']['kind'] == 'local' else ('drive_metadata', 'drive_download')
            if data['destination_current'] is not None and data['destination_method'] not in allowed:
                _reject()
            if value['event_kind'] == 'deletion_result' and data['source_before_delete'] is not None:
                allowed = ('windows_handle',) if data['source']['kind'] == 'local' else ('drive_metadata', 'drive_download')
                if data['source_method'] not in allowed:
                    _reject()
            if value['event_kind'] == 'deletion_result' and data['source_after_delete'] != 'unknown':
                expected = 'windows_lookup' if data['source']['kind'] == 'local' else 'provider_observation'
                if data['source_after_method'] != expected:
                    _reject()
            if value['event_kind'] == 'reconciliation' and data['source_current'] != 'unknown':
                expected = 'windows_lookup' if data['source']['kind'] == 'local' else 'provider_observation'
                if data['source_method'] != expected:
                    _reject()
    except MoveJournalError:
        raise
    except Exception:
        _reject()
    return value


def encode_move_record(value):
    try:
        raw = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    except Exception:
        _reject()
    decode_move_record(raw)
    return raw


def _read(root, record_id):
    if type(record_id) is not str or re.fullmatch(_UUID, record_id) is None:
        _reject('move_record_id_invalid')
    path = root / (record_id + '.json')
    try:
        chain = _chain(root)
        before = path.lstat()
        if not _regular(before) or before.st_nlink != 1 or not 0 < before.st_size <= MAX_RECORD_BYTES:
            _reject('move_record_file_invalid')
        signature = _signature(before)
        with path.open('rb') as stream:
            if _signature(os.fstat(stream.fileno())) != signature:
                _reject('move_record_changed')
            raw = stream.read(before.st_size + 1)
            finished = os.fstat(stream.fileno())
        if (len(raw) != before.st_size or _signature(finished) != signature
                or _signature(path.lstat()) != signature or _chain(root) != chain):
            _reject('move_record_changed')
    except MoveJournalError:
        raise
    except (OSError, ArtifactPublicationError):
        _reject('move_record_unavailable')
    value = decode_move_record(raw)
    if value['record_id'] != record_id:
        _reject('move_record_id_mismatch')
    return raw, value


def _binding(value, parents):
    if value['event_kind'] == 'prepared':
        return
    prepared = parents[0]
    if prepared['event_kind'] != 'prepared':
        _reject('move_record_reference_invalid')
    for parent in parents:
        if any(value[key] != parent[key] for key in ('move_id', 'machine_id', 'route', 'log_type')):
            _reject('move_record_reference_mismatch')
    data, baseline = value['event_data'], prepared['event_data']['copy_content']
    if value['event_kind'] == 'deletion_result':
        if (value['run_id'] != prepared['run_id'] or value['attempt_id'] != prepared['attempt_id']):
            _reject('move_record_reference_mismatch')
        confirmed_q5 = data['source_before_delete'] == baseline and data['destination_current'] == baseline
        if data['request_outcome'] == 'succeeded' and not confirmed_q5:
            _reject('move_record_q5_missing')
        complete = confirmed_q5 and data['request_outcome'] == 'succeeded' and data['source_after_delete'] == 'absent'
        decision = 'completed' if complete else ('incomplete' if data['source_after_delete'] == 'present' else 'unknown')
        basis = 'delete_confirmed' if complete else 'none'
    else:
        if len(parents) == 2:
            if (parents[1]['event_kind'] != 'deletion_result'
                    or parents[1]['prior_record_refs'][0]['record_id'] != prepared['record_id']):
                _reject('move_record_reference_invalid')
        complete = data['source_current'] == 'absent' and data['destination_current'] == baseline
        decision = 'completed' if complete else ('incomplete' if data['source_current'] == 'present' else 'unknown')
        basis = 'reconciled' if complete else 'none'
    if data['decision'] != decision or data['completion_basis'] != basis:
        _reject('move_record_decision_invalid')
    expected_reason = 'delete_confirmed' if basis == 'delete_confirmed' else 'reconciled_completion'
    if ((decision == 'completed' and data['reason_code'] != expected_reason)
            or (decision != 'completed' and data['reason_code'] in ('delete_confirmed', 'reconciled_completion'))):
        _reject('move_record_decision_invalid')
    if data['source'] != prepared['event_data']['source'] or data['destination'] != prepared['event_data']['destination']:
        _reject('move_record_target_mismatch')


def load_move_record(root, record_id):
    """Validate exact-byte references; observations remain untrusted provider claims."""
    root, visiting, cache = Path(root), set(), {}

    def load(identity, allowed=None):
        if identity in visiting:
            _reject('move_record_reference_cycle')
        if identity in cache:
            if allowed is not None and cache[identity][1]['event_kind'] not in allowed:
                _reject('move_record_reference_invalid')
            return cache[identity]
        visiting.add(identity)
        raw, value = _read(root, identity)
        if allowed is not None and value['event_kind'] not in allowed:
            _reject('move_record_reference_invalid')
        parents = []
        # Schema permits only prepared -> result -> reconciliation (no long chain).
        for index, ref in enumerate(value['prior_record_refs']):
            prior_raw, prior = load(ref['record_id'], {'prepared'} if index == 0 else {'deletion_result'})
            if hashlib.sha256(prior_raw).hexdigest() != ref['sha256']:
                _reject('move_record_reference_digest_mismatch')
            parents.append(prior)
        _binding(value, parents)
        visiting.remove(identity)
        cache[identity] = raw, value
        return raw, value

    try:
        return load(record_id)[1]
    except RecursionError:
        _reject('move_record_reference_cycle')


def save_move_record(root, raw):
    """No-overwrite publication with reference checks before and after saving."""
    value, root = decode_move_record(raw), Path(root)
    existing = read_move_journal(root)
    for record in existing:
        if record['record_id'] == value['record_id']:
            continue  # The byte publisher checks idempotence versus conflict.
        if value['event_kind'] == record['event_kind'] == 'prepared':
            if all(value[field] == record[field] for field in ('run_id', 'move_id', 'attempt_id')):
                _reject('move_journal_attempt_conflict')
        if value['event_kind'] == record['event_kind'] == 'deletion_result':
            if value['prior_record_refs'][0]['record_id'] == record['prior_record_refs'][0]['record_id']:
                _reject('move_journal_attempt_conflict')
    parents = []
    for ref in value['prior_record_refs']:
        parent_raw, _ = _read(root, ref['record_id'])
        if hashlib.sha256(parent_raw).hexdigest() != ref['sha256']:
            _reject('move_record_reference_digest_mismatch')
        parents.append(load_move_record(root, ref['record_id']))
    _binding(value, parents)
    try:
        status = publish_bytes_no_overwrite(root / (value['record_id'] + '.json'), raw)
    except ArtifactPublicationError as exc:
        _reject('move_record_publish_' + exc.reason_code)
    if _read(root, value['record_id'])[0] != raw:
        _reject('move_record_changed')
    load_move_record(root, value['record_id'])
    return status


def read_move_journal(root):
    """Read a complete dedicated record directory or fail, never silently no-work."""
    root = Path(root)
    try:
        chain = _chain(root)
        entries = sorted(root.iterdir(), key=lambda path: path.name)
        names = [path.name for path in entries]
        if any(re.fullmatch(_UUID + r'\.json', name) is None for name in names):
            _reject('move_journal_unexpected_entry')
        snapshots = {name: _read(root, name[:-5])[0] for name in names}
        records = [load_move_record(root, name[:-5]) for name in names]
        attempts, results = set(), set()
        for record in records:
            if record['event_kind'] == 'prepared':
                key = tuple(record[field] for field in ('run_id', 'move_id', 'attempt_id'))
                if key in attempts:
                    _reject('move_journal_attempt_conflict')
                attempts.add(key)
            elif record['event_kind'] == 'deletion_result':
                key = record['prior_record_refs'][0]['record_id']
                if key in results:
                    _reject('move_journal_attempt_conflict')
                results.add(key)
        if sorted(path.name for path in root.iterdir()) != names or _chain(root) != chain:
            _reject('move_journal_changed')
        # Re-read content after graph validation; never combine two record versions.
        for record in records:
            if _read(root, record['record_id'])[0] != snapshots[record['record_id'] + '.json']:
                _reject('move_journal_changed')
        return records
    except MoveJournalError:
        raise
    except (OSError, ArtifactPublicationError):
        _reject('move_journal_unavailable')
