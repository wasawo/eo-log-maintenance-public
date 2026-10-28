"""Read-only filesystem input for the model, never a real move adapter."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import stat
import sys

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Common.ArtifactSetDirectoryVerification import _chain, _read_stable, _signature
from Common.MoveJournal import _unique, _number, _relative
from Common.MoveRunReport import _scope
from Common.SourceInventoryEvidenceBuilder import _EntryBudget, _enumeration_snapshot, _source_entry_signature

# Model transport limits, not production log-size policy.
MAX_ENTRIES = 4096
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024
MAX_REQUEST_BYTES = 65536


class SimulationSnapshotError(ValueError):
    pass


def _require(condition):
    if not condition:
        raise SimulationSnapshotError('simulation_snapshot_unconfirmed')


def _keys(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()))


def collect_snapshot(request):
    try:
        return _collect(request)
    except Exception:
        raise SimulationSnapshotError('simulation_snapshot_unconfirmed') from None


def _collect(request):
    _keys(request, 'protocol_version simulation_only request_id machine_id route roots excluded_roots')
    _require(type(request['protocol_version']) is int and request['protocol_version'] == 1 and request['simulation_only'] is True)
    _scope(request['request_id'], request['machine_id'], request['route'])
    _require(type(request['roots']) is list and len(request['roots']) == 4)
    _require(type(request['excluded_roots']) is list and len(request['excluded_roots']) == 3)
    excluded=[]
    for value in request['excluded_roots']:
        _require(type(value) is str and bool(value) and Path(value).is_absolute())
        excluded.append(Path(value).absolute())
    roots=[]; scopes=set()
    for item in request['roots']:
        _keys(item, 'side log_type path')
        _require(item['side'] in ('source','destination') and item['log_type'] in ('BattleLog','ErrorReport'))
        scope=(item['side'],item['log_type'])
        _require(scope not in scopes); scopes.add(scope)
        _require(type(item['path']) is str and bool(item['path']) and Path(item['path']).is_absolute())
        root=Path(item['path']).absolute()
        _chain(root)
        roots.append((item,root))
    all_paths=[root for _,root in roots]
    for index,a in enumerate(all_paths):
        for b in all_paths[index+1:]+excluded:
            _require(a != b and a not in b.parents and b not in a.parents)
    snapshots={}; files=[]; total=0
    budget=_EntryBudget(MAX_ENTRIES)
    for item,root in roots:
        location=(request['machine_id'] if request['route']=='local_to_cloud' else 'Cloud') if item['side']=='source' else ('Cloud' if request['route']=='local_to_cloud' else 'Archive')
        pending=[root]
        while pending:
            directory=pending.pop()
            entries,initial=_enumeration_snapshot(directory,_budget=budget)
            snapshots[directory]=initial
            for entry in entries:
                path=Path(entry.path); info=path.lstat()
                _require(_source_entry_signature(info) == initial[1][entry.name])
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path); continue
                _require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE_BYTES and total+info.st_size <= MAX_TOTAL_BYTES)
                relative=path.relative_to(root).as_posix(); _relative(relative)
                raw=_read_stable(path,_signature(info),path.parent,_chain(path.parent))
                total+=len(raw)
                identity=[location,item['log_type'],_chain(root)[0],info.st_dev,info.st_ino,relative]
                reference=hashlib.sha256(json.dumps(identity,separators=(',',':')).encode('utf-8')).hexdigest()
                files.append(dict(id='snapshot-'+reference,location=location,log_type=item['log_type'],relative_path=relative,
                    size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),content_base64=base64.b64encode(raw).decode('ascii')))
    # One final shared pass catches changes even in an earlier root while a
    # later root was being read. No partial result is returned on any failure.
    final_budget=_EntryBudget(MAX_ENTRIES)
    for directory,initial in snapshots.items():
        _,final=_enumeration_snapshot(directory,_budget=final_budget)
        _require(final == initial)
    files.sort(key=lambda value:(value['location'],value['log_type'],value['relative_path'].encode('utf-8')))
    return dict(protocol_version=1,simulation_only=True,request_id=request['request_id'],machine_id=request['machine_id'],
        route=request['route'],enumeration_complete=True,file_count=len(files),total_bytes=total,files=files)


def main():
    argparse.ArgumentParser(description='Read-only file snapshots for synthetic model inputs.').parse_args()
    try:
        raw=sys.stdin.buffer.read(MAX_REQUEST_BYTES+1)
        _require(0 < len(raw) <= MAX_REQUEST_BYTES)
        request=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique,parse_float=_number,parse_constant=_number)
        print(json.dumps(dict(ok=True,snapshot=collect_snapshot(request)),separators=(',',':')))
        return 0
    except Exception:
        print(json.dumps(dict(ok=False,reason_code='simulation_snapshot_unconfirmed')))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
