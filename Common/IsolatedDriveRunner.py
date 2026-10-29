"""Explicit S3 test connection only. No consent, credential search or cleanup."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import uuid

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Common.DriveAuthentication import create_service, SCOPE
from Common.DriveCredentialStore import CredentialStore, WindowsProtection
from Common.DriveMetadataReader import read_drive_listing
from Common.DriveTransferAdapter import sync_bytes, download_bytes


def configuration(path, request):
    path = Path(path)
    protection = WindowsProtection()
    repo = Path(__file__).resolve().parents[1]
    if not path.is_absolute() or repo in path.parents or '..' in path.parts: raise ValueError('connection_unconfirmed')
    for p in (path, *path.parents):
        if p.lstat().st_file_attributes & 0x400: raise ValueError('connection_unconfirmed')
    protection.validate_acl(path)
    with path.open('rb') as stream: raw = stream.read(16385)
    if len(raw) > 16384: raise ValueError('connection_unconfirmed')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('connection_unconfirmed')
            result[key] = value
        return result
    config = json.loads(raw, object_pairs_hook=unique)
    keys = {'version','mode','machine_id','principal','client_id','scope','folders','store_directory',
        'fixture_root','upload_names','required_visible','principal_verified','environment_verified','allow_refresh','execution_approved'}
    if (type(config) is not dict or set(config) != keys or type(config['version']) is not int or config['version'] != 1
            or config['mode'] != 'isolated_drive' or config['scope'] != SCOPE
            or config['machine_id'] not in ('PC-A','PC-B') or config['machine_id'] != request['machine_id']
            or any(type(config[k]) is not bool for k in ('principal_verified','environment_verified','allow_refresh','execution_approved'))
            or not all(config[k] for k in ('principal_verified','environment_verified','execution_approved'))
            or any(type(config[k]) is not str or not config[k] for k in ('principal','client_id','store_directory','fixture_root'))):
        raise ValueError('connection_unconfirmed')
    if request['route'] not in ('Sync','Archive') or (request['route'] == 'Archive' and config['machine_id'] != 'PC-A'):
        raise ValueError('connection_unconfirmed')
    root = Path(config['fixture_root'])
    supplied_root = Path(request['root'])
    # Windows Temp can use an 8.3 alias in Python and a long name in .NET.
    # Reject reparse paths first, then compare the same canonical directory.
    for candidate in (root, supplied_root):
        if not candidate.is_absolute() or '..' in candidate.parts: raise ValueError('connection_unconfirmed')
        for p in (candidate, *candidate.parents):
            if p.lstat().st_file_attributes & 0x400: raise ValueError('connection_unconfirmed')
    root = root.resolve(strict=True)
    if root != supplied_root.resolve(strict=True) or root.parent != Path(tempfile.gettempdir()).resolve(strict=True):
        raise ValueError('connection_unconfirmed')
    prefix = 'eolm-s1-sync-' if request['route'] == 'Sync' else 'eolm-s2-archive-'
    if re.fullmatch(prefix + '[a-f0-9]{32}', root.name) is None or root.lstat().st_file_attributes & 0x400:
        raise ValueError('connection_unconfirmed')
    if set(config['folders']) != {'BattleLog','ErrorReport'} or len(set(config['folders'].values())) != 2:
        raise ValueError('connection_unconfirmed')
    for value in config['folders'].values():
        if type(value) is not str or re.fullmatch('[A-Za-z0-9_-]{1,200}', value) is None: raise ValueError('connection_unconfirmed')
    for key in ('upload_names','required_visible'):
        if type(config[key]) is not dict or set(config[key]) != set(config['folders']): raise ValueError('connection_unconfirmed')
        for names in config[key].values():
            if (type(names) is not list or len(names) > (1 if key == 'upload_names' else 6)
                    or len(names) != len(set(names)) or any(type(n) is not str or not n or '/' in n or '\\' in n for n in names)):
                raise ValueError('connection_unconfirmed')
    return config


def execute(request, *, service_factory=create_service, store_factory=CredentialStore):
    config = configuration(request['connection_config'], request)
    kind = request['kind']
    if kind not in config['folders'] or request['operation'] not in ('list','sync','download'): raise ValueError('connection_unconfirmed')
    if ((request['operation'] == 'sync' and request['route'] != 'Sync')
            or (request['operation'] == 'download' and request['route'] != 'Archive')):
        raise ValueError('connection_unconfirmed')
    # Pending upload intent is durable; do not silently retry after worker death/unknown response.
    journal = Path(config['store_directory']) / 'transfer-intents.jsonl'
    store = store_factory(config['store_directory'])
    with store.transaction():
        events = []
        if journal.exists():
            if journal.lstat().st_file_attributes & 0x400: raise ValueError('connection_unconfirmed')
            store.protection.validate_acl(journal)
            with store.protection.open_private(journal, 3) as stream:
                raw = stream.read(65537)
            if len(raw) > 65536: raise ValueError('connection_unconfirmed')
            events = [json.loads(line) for line in raw.splitlines()]
        pending = set()
        for event in events:
            if event['state'] == 'intent': pending.add(event['key'])
            elif event['state'] == 'confirmed': pending.discard(event['key'])
            else: raise ValueError('connection_unconfirmed')
        if pending: raise ValueError('connection_unconfirmed')
    service = service_factory(config, store)
    try:
        folder = config['folders'][kind]
        listing = read_drive_listing(service, folder_id=folder, maximum_pages=100, maximum_files=4096)
        names = [f.filename for f in listing.files]
        allowed = set(config['upload_names'][kind] + config['required_visible'][kind])
        if (len(names) != len(set(names)) or set(names) - allowed
                or set(config['required_visible'][kind]) - set(names)):
            raise ValueError('connection_unconfirmed')
        if request['operation'] == 'list':
            return dict(items=[dict(name=f.filename,id=f.file_id) for f in listing.files])
        if request['operation'] == 'download':
            if request['file_id'] not in {f.file_id for f in listing.files}: raise ValueError('connection_unconfirmed')
            content, observed = download_bytes(service, folder_id=folder, file_id=request['file_id'], maximum_bytes=4096)
            return dict(content=base64.b64encode(content).decode(), sha256=observed.sha256)
        if request['name'] not in config['upload_names'][kind]: raise ValueError('connection_unconfirmed')
        content = base64.b64decode(request['content'], validate=True)
        if len(content) > 4096: raise ValueError('connection_unconfirmed')
        key = hashlib.sha256((kind + '/' + request['name']).encode()).hexdigest()
        with store.transaction():
            # Keep lease across POST, so another runner cannot race/create a second copy.
            if journal.exists():
                with store.protection.open_private(journal, 3) as stream:
                    latest = [json.loads(line) for line in stream.read(65537).splitlines()]
                unresolved = set()
                for event in latest:
                    if event['state'] == 'intent': unresolved.add(event['key'])
                    elif event['state'] == 'confirmed': unresolved.discard(event['key'])
                    else: raise ValueError('connection_unconfirmed')
                if unresolved: raise ValueError('connection_unconfirmed')
            def append(state):
                with store.protection.open_private(journal, 4) as stream:
                    stream.seek(0, 2)
                    stream.write((json.dumps(dict(key=key,state=state))+'\n').encode())
                    stream.flush()
                    import os
                    os.fsync(stream.fileno())
            append('intent')
            result = sync_bytes(service, folder_id=folder, filename=request['name'], content=content)
            append('confirmed')
            return result
    finally:
        service.close()


def main():
    request_id = None
    try:
        request = json.loads(sys.stdin.read(8 * 1024 * 1024))
        request_id = str(uuid.UUID(request['request_id']))
        result = execute(request)
        print(json.dumps(dict(protocol_version=1, request_id=request_id, ok=True, result=result)))
        return 0
    except Exception:
        print(json.dumps(dict(protocol_version=1, request_id=request_id, ok=False, result={})))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
