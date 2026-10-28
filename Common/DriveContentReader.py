"""Read one Drive blob into a hash, with metadata reobservation; never save/delete."""
import hashlib
import re

from googleapiclient.http import MediaIoBaseDownload

from Common.DriveContentComparison import DownloadHashObservation
from Common.DriveMetadataReader import read_drive_file_metadata


class DriveContentReadError(ValueError):
    pass


def _require(condition):
    if not condition:
        raise DriveContentReadError('drive_content_unconfirmed')


class _HashSink:
    def __init__(self):
        self.size=0
        self.digest=hashlib.sha256()

    def write(self,content):
        self.digest.update(content)
        self.size+=len(content)
        return len(content)


class _DownloadHttp:
    def __init__(self,transport,sink,size,chunk_size,uri):
        self.transport=transport
        self.sink=sink
        self.size=size
        self.chunk_size=chunk_size
        self.uri=uri

    def request(self,uri,method='GET',*,headers,**kwargs):
        start=self.sink.size
        _require(method=='GET' and uri==self.uri and
                 headers.get('range')==f'bytes={start}-{start+self.chunk_size-1}')
        response,content=self.transport.request(uri,method,headers=headers,**kwargs)
        _require(type(content) is bytes)
        _require(response.get('content-location',uri)==uri)
        if response.status==416:
            _require(self.size==0 and start==0 and response.get('content-range')=='bytes */0')
            return response,b''
        # Validate before SDK diagnostics or hash updates consume the response.
        _require(response.status in (200,206) and len(content)<=self.chunk_size and start+len(content)<=self.size)
        if 'content-length' in response:
            _require(response['content-length']==str(len(content)))
        if response.status==200:
            _require(start==0 and len(content)==self.size and 'content-range' not in response)
        else:
            span=re.fullmatch(r'bytes ([0-9]+)-([0-9]+)/([0-9]+)',response.get('content-range',''))
            _require(span is not None and len(content)>0)
            _require(tuple(map(int,span.groups()))==(start,start+len(content)-1,self.size))
        return response,content


def read_drive_content_hash(service, *, folder_id, file_id, chunk_size, maximum_download_bytes=None):
    """Return ID/version/size/SHA only after complete bytes and unchanged metadata.

    The caller owns service/auth/timeout. SDK/HTTP may materialize a whole
    response before our chunk checks; this is not a transport memory bound.
    """
    _require(type(chunk_size) is int and chunk_size>0)
    _require(maximum_download_bytes is None or (type(maximum_download_bytes) is int and maximum_download_bytes>0))
    try:
        before=read_drive_file_metadata(service,folder_id=folder_id,file_id=file_id,require_download=True)
        _require(maximum_download_bytes is None or before.size_bytes<=maximum_download_bytes)
        sink=_HashSink()
        request=service.files().get_media(fileId=file_id,supportsAllDrives=True)
        request.http=_DownloadHttp(request.http,sink,before.size_bytes,chunk_size,request.uri)
        downloader=MediaIoBaseDownload(sink,request,chunksize=chunk_size)
        done=False
        while not done:
            _,done=downloader.next_chunk(num_retries=0)
        _require(sink.size==before.size_bytes)
        after=read_drive_file_metadata(service,folder_id=folder_id,file_id=file_id,require_download=True)
        _require(after==before)
        digest=sink.digest.hexdigest()
        _require(before.sha256 is None or digest==before.sha256)
        return DownloadHashObservation(file_id,sink.size,digest,before.version)
    except Exception:
        raise DriveContentReadError('drive_content_unconfirmed') from None
