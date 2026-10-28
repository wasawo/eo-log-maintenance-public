"""Read-only Drive v3 SDK binding; no credential discovery, writes or CLI.

The caller owns the authorized service and its timeout. Observations do not
qualify roots, grant deletion, or establish a conditional-delete capability.
"""
import re

from Common.DriveContentComparison import (
    DriveFileObservation, DriveListingPage, collect_drive_listing,
)

FILE_FIELDS = 'id,name,mimeType,parents,trashed,size,sha256Checksum,version'
FOLDER_MIME = 'application/vnd.google-apps.folder'


class DriveMetadataReadError(ValueError):
    pass


class _ReadHttp:
    def __init__(self,transport):
        self.transport=transport

    def request(self,uri,method='GET',*args,**kwargs):
        _require(method=='GET')
        response,body=self.transport.request(uri,method,*args,**kwargs)
        # Reject before SDK retry diagnostics can log the raw error body.
        _require(200<=response.status<300)
        return response,body


def _execute_read(request):
    return request.execute(http=_ReadHttp(request.http),num_retries=0)


def _require(condition):
    if not condition:
        raise DriveMetadataReadError('drive_metadata_unconfirmed')


def _identifier(value):
    _require(type(value) is str and bool(value.strip()) and
             not any(ord(c)<32 or ord(c)==127 for c in value))


def _file_observation(value, folder_id, expected_id=None):
    _require(type(value) is dict)
    _identifier(value.get('id')); _identifier(value.get('name'))
    _require(expected_id is None or value['id']==expected_id)
    _require(value.get('parents')==[folder_id] and value.get('trashed') is False)
    mime=value.get('mimeType')
    _require(type(mime) is str and bool(mime) and not mime.startswith('application/vnd.google-apps.'))
    size=value.get('size'); version=value.get('version')
    _require(type(size) is str and re.fullmatch('0|[1-9][0-9]*',size) is not None)
    _require(type(version) is str and re.fullmatch('[1-9][0-9]*',version) is not None)
    _require(int(size)<=2**63-1 and int(version)<=2**63-1)
    sha=value.get('sha256Checksum')
    _require(sha is None or (type(sha) is str and re.fullmatch('[a-f0-9]{64}',sha) is not None))
    return DriveFileObservation(value['id'],value['name'],int(size),sha,sha is not None,version)


def read_drive_file_metadata(service, *, folder_id, file_id):
    """Observe one exact file ID in one expected parent, never a name substitute."""
    _identifier(folder_id); _identifier(file_id)
    try:
        value=_execute_read(service.files().get(fileId=file_id,fields=FILE_FIELDS,supportsAllDrives=True))
        return _file_observation(value,folder_id,file_id)
    except Exception:
        raise DriveMetadataReadError('drive_metadata_unconfirmed') from None


def read_drive_listing(service, *, folder_id, maximum_pages=None, maximum_files=None):
    """Collect direct children completely or fail; no recursive/source selection.

    Folders, shortcuts and native Workspace documents are unsupported rather
    than silently omitted. Missing hashes remain unknown for download fallback.
    """
    _identifier(folder_id)
    for limit in (maximum_pages,maximum_files):
        _require(limit is None or (type(limit) is int and limit>0))
    try:
        files=service.files()
        root=_execute_read(files.get(fileId=folder_id,fields='id,mimeType,trashed',supportsAllDrives=True))
        _require(type(root) is dict and root.get('id')==folder_id and
                 root.get('mimeType')==FOLDER_MIME and root.get('trashed') is False)
        escaped=folder_id.replace('\\','\\\\').replace("'","\\'")
        def pages():
            token=None
            while True:
                query=dict(q=f"'{escaped}' in parents and trashed = false",spaces='drive',
                    fields=f'nextPageToken,incompleteSearch,files({FILE_FIELDS})',
                    supportsAllDrives=True,includeItemsFromAllDrives=True)
                if token is not None: query['pageToken']=token
                value=_execute_read(files.list(**query))
                _require(type(value) is dict and value.get('incompleteSearch',False) is False)
                items=value.get('files',[])
                _require(type(items) is list)
                next_token=value.get('nextPageToken')
                if next_token is not None: _identifier(next_token)
                yield DriveListingPage(folder_id,token,next_token,
                    tuple(_file_observation(item,folder_id) for item in items),True)
                if next_token is None: return
                token=next_token
        return collect_drive_listing(pages(),expected_folder_id=folder_id,
            maximum_pages=maximum_pages,maximum_files=maximum_files)
    except Exception:
        raise DriveMetadataReadError('drive_metadata_unconfirmed') from None
