"""Single-attempt SDK transfer binding; caller supplies an authorized service.

No credential discovery/storage, workflow selection, overwrite or deletion.
This library alone does not qualify service identity, roots or live operation.
"""
import hashlib
import io
from urllib.parse import parse_qs, urlsplit

from googleapiclient.http import MediaIoBaseUpload

from Common.DriveContentReader import _HashSink, _read_drive_content
from Common.DriveMetadataReader import read_drive_listing


class DriveTransferError(ValueError):
    pass


class _MemorySink(_HashSink):
    def __init__(self):
        super().__init__()
        self.buffer = io.BytesIO()

    def write(self, content):
        self.buffer.write(content)
        return super().write(content)


class _CreateHttp:
    def __init__(self, transport):
        self.transport = transport

    def request(self, uri, method='GET', *args, **kwargs):
        url = urlsplit(uri)
        if (method != 'POST' or url.scheme != 'https' or url.hostname != 'www.googleapis.com'
                or url.path != '/upload/drive/v3/files'
                or parse_qs(url.query).get('uploadType') != ['multipart']):
            raise DriveTransferError('drive_transfer_unconfirmed')
        response, body = self.transport.request(uri, method, *args, **kwargs)
        # Reject raw errors before SDK retry diagnostics can log them.
        if not 200 <= response.status < 300:
            raise DriveTransferError('drive_transfer_unconfirmed')
        return response, body


def download_bytes(service, *, folder_id, file_id, maximum_bytes=4194304):
    """Bounded fixture-sized content plus version-bound observation, not a writer."""
    sink = _MemorySink()
    try:
        observed = _read_drive_content(service, folder_id=folder_id, file_id=file_id,
            chunk_size=65536, maximum_download_bytes=maximum_bytes, sink=sink)
        return sink.buffer.getvalue(), observed
    except Exception:
        raise DriveTransferError('drive_transfer_unconfirmed') from None


def sync_bytes(service, *, folder_id, filename, content):
    """Create a missing copy once, then verify current unique candidate and bytes.

    Concurrent creates or unknown responses never authorize replacement/retry.
    Existing metadata success alone is not content-copy verification.
    """
    if (type(content) is not bytes or len(content) > 4194304 or type(filename) is not str
            or not filename or any(c in filename for c in '/\\\x00')):
        raise DriveTransferError('drive_transfer_unconfirmed')
    try:
        before = read_drive_listing(service, folder_id=folder_id, maximum_pages=100, maximum_files=4096)
        candidates = [item for item in before.files if item.filename == filename]
        if len(candidates) > 1:
            return dict(status='held', reason='drive_candidates_ambiguous', sha256=None, reused=False)
        reused = bool(candidates)
        if reused:
            candidate = candidates[0]
            data, observed = download_bytes(service, folder_id=folder_id, file_id=candidate.file_id)
            if (observed.version != candidate.version or observed.size_bytes != candidate.size_bytes
                    or (candidate.sha256 is not None and observed.sha256 != candidate.sha256)):
                raise DriveTransferError('drive_transfer_unconfirmed')
            if data != content:
                return dict(status='held', reason='content_conflict', sha256=observed.sha256, reused=False)
            file_id = candidate.file_id
        else:
            media = MediaIoBaseUpload(io.BytesIO(content), mimetype='application/octet-stream', resumable=False)
            request = service.files().create(body=dict(name=filename, parents=[folder_id]),
                media_body=media, fields='id', supportsAllDrives=True)
            created = request.execute(http=_CreateHttp(request.http), num_retries=0)
            if type(created) is not dict or type(created.get('id')) is not str or not created['id']:
                raise DriveTransferError('drive_transfer_unconfirmed')
            file_id = created['id']
            data, observed = download_bytes(service, folder_id=folder_id, file_id=file_id)
            if data != content:
                raise DriveTransferError('drive_transfer_unconfirmed')
        after = read_drive_listing(service, folder_id=folder_id, maximum_pages=100, maximum_files=4096)
        current = [item for item in after.files if item.filename == filename]
        if (len(current) != 1 or current[0].file_id != file_id
                or current[0].version != observed.version
                or current[0].size_bytes != observed.size_bytes
                or (current[0].sha256 is not None and current[0].sha256 != observed.sha256)
                or observed.sha256 != hashlib.sha256(content).hexdigest()):
            raise DriveTransferError('drive_transfer_unconfirmed')
        return dict(status='success', reason='existing_content_verified' if reused else 'copied_content_verified',
            sha256=observed.sha256, reused=reused)
    except Exception:
        raise DriveTransferError('drive_transfer_unconfirmed') from None
