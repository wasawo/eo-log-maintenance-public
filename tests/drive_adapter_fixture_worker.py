"""TEST ONLY: real SDK against a filesystem-backed HTTP fake. No network/auth.

The parent owns the synthetic marker lease. Only fixed S1/S2 fixture paths and
dummy folder/file identifiers are accepted; no live service factory exists.
"""
import base64
import email.policy
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from googleapiclient.discovery import build
from httplib2 import Response
from Common.DriveMetadataReader import FOLDER_MIME, read_drive_listing
from Common.DriveTransferAdapter import download_bytes, sync_bytes


class FixtureHttp:
    def __init__(self, root, kind, fault='none'):
        self.folder = 'dummy-' + kind
        self.directory = Path(root) / 'mock-drive' / kind
        self.fault = fault
        self.metadata_reads = 0
        self.calls = []

    def _files(self):
        values = {}
        for path in self.directory.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError('fixture_file_invalid')
            key = 'dummy-' + hashlib.sha256(path.name.encode()).hexdigest()[:24]
            values[key] = path
        return values

    def metadata(self, key, path):
        data = path.read_bytes()
        return dict(id=key, name=path.name, parents=[self.folder], mimeType='application/octet-stream',
            trashed=False, size=str(len(data)), version='1', sha256Checksum=hashlib.sha256(data).hexdigest(),
            capabilities=dict(canDownload=True))

    def request(self, uri, method='GET', body=None, headers=None, **kwargs):
        self.calls.append(method)
        if method not in ('GET', 'POST'):
            raise ValueError('fixture_method_denied')
        def reply(status, value, **extra):
            return Response({'status': str(status), 'content-type': 'application/json', **extra}), (
                value if type(value) is bytes else json.dumps(value).encode())
        if self.fault in ('auth_denied', 'api_error'):
            return reply(401 if self.fault == 'auth_denied' else 503, {'private': 'synthetic-secret'})
        url = urlsplit(uri)
        if url.scheme != 'https' or url.hostname != 'www.googleapis.com':
            raise ValueError('fixture_uri_denied')
        query = parse_qs(url.query)
        files = self._files()
        if method == 'POST':
            if url.path != '/upload/drive/v3/files' or query.get('uploadType') != ['multipart']:
                raise ValueError('fixture_write_denied')
            content_type = {k.lower(): v for k, v in headers.items()}['content-type']
            raw = body if type(body) is bytes else body.encode()
            message = BytesParser(policy=email.policy.default).parsebytes(
                b'Content-Type: ' + content_type.encode() + b'\r\n\r\n' + raw)
            parts = list(message.iter_parts())
            metadata = json.loads(parts[0].get_payload(decode=True))
            name = metadata['name']
            if (metadata['parents'] != [self.folder] or Path(name).name != name
                    or '/' in name or '\\' in name or name in ('.', '..')):
                raise ValueError('fixture_name_denied')
            with (self.directory / name).open('xb') as stream:
                stream.write(parts[1].get_payload(decode=True))
            if self.fault == 'upload_unknown':
                return reply(503, {'private': 'synthetic-secret'})
            return reply(200, {'id': next(k for k, p in self._files().items() if p.name == name)})
        if url.path == '/drive/v3/files':
            if query.get('q') != [f"'{self.folder}' in parents and trashed = false"]:
                raise ValueError('fixture_parent_denied')
            values = [self.metadata(k, p) for k, p in files.items()]
            if self.fault == 'duplicate_name' and values:
                values.append(dict(values[0], id='dummy-duplicate'))
            return reply(200, dict(files=values))
        key = unquote(url.path.rsplit('/', 1)[-1])
        if key == self.folder:
            return reply(200, dict(id=self.folder, mimeType=FOLDER_MIME, trashed=False))
        path = files[key]
        if query.get('alt') == ['media']:
            data = path.read_bytes()
            if self.fault == 'content_changed': data += b'!'
            return reply(200, data, **{'content-length': str(len(data))})
        self.metadata_reads += 1
        value = self.metadata(key, path)
        if self.fault == 'version_changed' and self.metadata_reads > 1: value['version'] = '2'
        return reply(200, value)


def execute(request):
    root = Path(request['root'])
    if (root.parent.resolve() != Path(tempfile.gettempdir()).resolve() or root.is_symlink()
            or re.fullmatch(r'eolm-s[12]-(?:sync|archive)-[a-f0-9]{32}', root.name) is None
            or request['kind'] not in ('BattleLog', 'ErrorReport')):
        raise ValueError('fixture_root_invalid')
    for path in (root / 'mock-drive', root / 'mock-drive' / request['kind']):
        if path.is_symlink() or not path.is_dir(): raise ValueError('fixture_root_invalid')
    http = FixtureHttp(root, request['kind'], request['fault'])
    service = build('drive', 'v3', http=http, static_discovery=True, cache_discovery=False)
    if request['operation'] == 'list':
        listing = read_drive_listing(service, folder_id=http.folder, maximum_pages=100, maximum_files=4096)
        names = [f.filename for f in listing.files]
        if len(names) != len(set(names)): raise ValueError('fixture_candidates_ambiguous')
        result = dict(items=[dict(name=f.filename, id=f.file_id) for f in listing.files])
    elif request['operation'] == 'sync':
        result = sync_bytes(service, folder_id=http.folder, filename=request['name'],
            content=base64.b64decode(request['content'], validate=True))
    elif request['operation'] == 'download':
        data, observed = download_bytes(service, folder_id=http.folder, file_id=request['file_id'])
        result = dict(content=base64.b64encode(data).decode(), sha256=observed.sha256)
    else:
        raise ValueError('fixture_operation_invalid')
    return result


if __name__ == '__main__':
    request_id = None
    try:
        raw = sys.stdin.read(8388609)
        if len(raw) > 8388608: raise ValueError('fixture_request_too_large')
        request = json.loads(raw)
        request_id = request['request_id']
        result = execute(request)
        print(json.dumps(dict(protocol_version=1, request_id=request_id, ok=True, result=result)))
    except Exception:
        print(json.dumps(dict(protocol_version=1, request_id=request_id, ok=False,
            error='drive_api_unconfirmed')))
        sys.exit(1)
