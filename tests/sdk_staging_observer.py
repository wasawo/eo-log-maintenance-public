"""TEST ONLY: fresh, read-only inspection of an owned SDK staging attempt."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from Common.AtomicArtifactPublication import _chain
from Common.DriveContentComparison import hash_downloaded_content, _hash, _version
from Common.ArtifactSetDirectoryVerification import _reject_duplicate_keys, _reject_json_constant
from download_staging_fixture import regular, signature


BASE_KEYS={'record_version','fixture_only','attempt_id','fixture_ref','file_id','folder_id','staging_file','expected_size_bytes','state'}
READY_KEYS=BASE_KEYS|{'staging_record_sha256','file_identity','size_bytes','sha256','version'}


def _require(condition):
    if not condition:raise ValueError('inspection_unconfirmed')


def _read(path,limit):
    before=path.lstat()
    _require(regular(before) and 0<before.st_size<=limit)
    with path.open('rb') as stream:
        _require(signature(os.fstat(stream.fileno()))==signature(before))
        raw=stream.read(before.st_size+1)
        _require(signature(os.fstat(stream.fileno()))==signature(before))
    _require(len(raw)==before.st_size and signature(path.lstat())==signature(before))
    return raw


def _decode(raw):
    return json.loads(raw.decode('utf-8'),object_pairs_hook=_reject_duplicate_keys,
        parse_float=_reject_json_constant,parse_constant=_reject_json_constant)


def _result(status,reason):
    return dict(status=status,reason_code=reason,may_change_state=False,cloud_observed=False)


def inspect_attempt(request):
    _require(type(request) is dict and set(request)=={'root','nonce','attempt','maximum_record_bytes'})
    _require(type(request['nonce']) is str and re.fullmatch('[0-9a-f]{32}',request['nonce']) is not None)
    _require(type(request['attempt']) is str and re.fullmatch('attempt-[A-Za-z0-9_-]+',request['attempt']) is not None)
    limit=request['maximum_record_bytes']
    _require(type(limit) is int and 0<limit<=16384)
    _require(type(request['root']) is str)
    root=Path(request['root'])
    _require(root.is_absolute() and root.parent==Path(tempfile.gettempdir()).resolve(strict=True) and
        root.name.startswith('eolm-download-staging-') and root.resolve(strict=True)==root)
    root_chain=_chain(root);marker=request['nonce'].encode('ascii')
    def guard():
        _require(_chain(root)==root_chain and _read(root/'.fixture-owner',32)==marker)
    guard()
    try:(root/'owner.json').lstat()
    except FileNotFoundError:pass
    else:return _result('held','owner_record_present')
    attempt=root/request['attempt'];chain=_chain(attempt)
    names={p.name for p in attempt.iterdir()}
    _require('staging.json' in names and names<={'staging.json','ready.json','download.bin'})
    raw=_read(attempt/'staging.json',limit);allocated=_decode(raw)
    _require(type(allocated) is dict and set(allocated)==BASE_KEYS)
    _require(type(allocated['record_version']) is int and allocated['record_version']==1 and allocated['fixture_only'] is True)
    _require(allocated['state']=='staging' and allocated['staging_file']=='download.bin' and
        allocated['attempt_id']==request['attempt'] and allocated['fixture_ref']==hashlib.sha256(marker).hexdigest())
    _require(all(type(allocated[k]) is str and bool(allocated[k].strip()) and
        not any(ord(c)<32 or ord(c)==127 for c in allocated[k]) for k in ('file_id','folder_id')))
    _require(type(allocated['expected_size_bytes']) is int and allocated['expected_size_bytes']>=0)
    ready_raw=None;payload=attempt/'download.bin'
    if 'ready.json' not in names:
        if 'download.bin' in names:_require(regular(payload.lstat()))
        result=_result('incomplete','payload_without_ready') if 'download.bin' in names else _result('allocation_only','payload_not_created')
    else:
        _require('download.bin' in names)
        ready_raw=_read(attempt/'ready.json',limit);ready=_decode(ready_raw)
        _require(type(ready) is dict and set(ready)==READY_KEYS and ready['state']=='ready')
        _require(type(ready['record_version']) is int and type(ready['expected_size_bytes']) is int and ready['fixture_only'] is True)
        _require(all(ready[key]==allocated[key] for key in BASE_KEYS-{'state'}))
        _require(ready['staging_record_sha256']==hashlib.sha256(raw).hexdigest())
        _require(type(ready['file_identity']) is list and len(ready['file_identity'])==2 and
            all(type(value) is int and value>=0 for value in ready['file_identity']))
        _require(type(ready['size_bytes']) is int and ready['size_bytes']==allocated['expected_size_bytes'] and
            _hash(ready['sha256']) and type(ready['version']) is str and _version(ready['version']))
        before=payload.lstat()
        _require(regular(before) and [before.st_dev,before.st_ino]==ready['file_identity'] and before.st_size==ready['size_bytes'])
        with payload.open('rb') as stream:
            _require(signature(os.fstat(stream.fileno()))==signature(before))
            current=hash_downloaded_content(allocated['file_id'],iter(lambda:stream.read(1024*1024),b''),
                expected_size_bytes=ready['size_bytes'],download_completed=True)
            _require(signature(os.fstat(stream.fileno()))==signature(before))
        _require(current.sha256==ready['sha256'] and signature(payload.lstat())==signature(before))
        result=_result('ready_candidate','local_records_and_payload_match')
    # Re-read after payload observation; record existence alone is never sufficient.
    _require(_read(attempt/'staging.json',limit)==raw and _chain(attempt)==chain and
        {p.name for p in attempt.iterdir()}==names)
    if ready_raw is not None:_require(_read(attempt/'ready.json',limit)==ready_raw)
    guard()
    try:(root/'owner.json').lstat()
    except FileNotFoundError:pass
    else:return _result('held','owner_record_present')
    return result


def main():
    try:
        raw=sys.stdin.buffer.read(16385)
        _require(0<len(raw)<=16384)
        result=inspect_attempt(_decode(raw))
    except Exception:
        print(json.dumps(_result('unconfirmed','inspection_unconfirmed')))
        return 1
    print(json.dumps(result))
    return 0


if __name__=='__main__':raise SystemExit(main())
