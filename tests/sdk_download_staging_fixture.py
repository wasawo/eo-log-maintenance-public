"""TEST ONLY: shared SDK transfer into constructor-owned staging attempts."""
import os
import hashlib
import json
from pathlib import Path
import tempfile

from Common.AtomicArtifactPublication import _chain, _same_bytes, publish_bytes_no_overwrite
from Common.DriveContentComparison import DownloadRequirement, hash_downloaded_content
from Common.DriveContentReader import _HashSink, _read_drive_content
from Common.OwnedRunLock import acquire_owned_lock, _record_matches
from download_staging_fixture import DownloadStagingFixture, StagingFixtureError, regular, signature


class _FileSink(_HashSink):
    def __init__(self,stream,path,guard,expected_size,checkpoint):
        super().__init__()
        self.stream=stream
        self.path=path
        self.guard=guard
        self.expected_size=expected_size
        self.checkpoint=checkpoint
        self.written=None

    def write(self,content):
        self.guard()
        if self.size+len(content)>self.expected_size:
            raise StagingFixtureError('fixture_size_exceeded')
        count=self.stream.write(content)
        if type(count) is not int or count!=len(content):
            raise StagingFixtureError('fixture_short_write')
        return super().write(content)

    def finish(self,observed):
        self.guard()
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.written=os.fstat(self.stream.fileno())
        self.stream.close()
        self.checkpoint('after_close',self.path)
        self.verify(observed)

    def verify(self,observed):
        self.guard()
        before=self.path.lstat()
        if not regular(before) or signature(before)!=signature(self.written):
            raise StagingFixtureError('fixture_staging_changed')
        with self.path.open('rb') as stream:
            if signature(os.fstat(stream.fileno()))!=signature(before):
                raise StagingFixtureError('fixture_staging_changed')
            readback=hash_downloaded_content(observed.file_id,iter(lambda:stream.read(1024*1024),b''),
                expected_size_bytes=self.expected_size,download_completed=True)
            if signature(os.fstat(stream.fileno()))!=signature(before):
                raise StagingFixtureError('fixture_staging_changed')
        self.guard()
        if (signature(self.path.lstat())!=signature(before) or
                (readback.size_bytes,readback.sha256)!=(observed.size_bytes,observed.sha256)):
            raise StagingFixtureError('fixture_staging_changed')


class SdkDownloadStagingFixture(DownloadStagingFixture):
    def download_from_sdk(self,requirement,service, *, folder_id,chunk_size,maximum_download_bytes=None,
                          at_checkpoint=None,stream_factory=None):
        if (type(requirement) is not DownloadRequirement or type(requirement.file_id) is not str or not requirement.file_id
                or type(requirement.expected_size_bytes) is not int or requirement.expected_size_bytes<0):
            raise StagingFixtureError('fixture_requirement_invalid')
        self.guard()
        checkpoint=at_checkpoint if at_checkpoint is not None else lambda phase,path:None
        try:
            with acquire_owned_lock(self.scope,self.root/'owner.json',timeout_seconds=0) as token:
                directory=Path(tempfile.mkdtemp(prefix='attempt-',dir=self.root))
                chain=_chain(directory)
                path=directory/'download.bin'
                self.attempts.append(path)
                records={}
                def guard():
                    self.guard()
                    if _chain(directory)!=chain or not _record_matches(self.root/'owner.json',self.scope,token,4096):
                        raise StagingFixtureError('fixture_ownership_unconfirmed')
                    for record_path,raw in records.items():
                        if not regular(record_path.lstat()) or not _same_bytes(record_path,raw):
                            raise StagingFixtureError('fixture_staging_record_changed')
                def publish_record(name,value):
                    guard()
                    record_path=directory/name
                    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
                    if record_path.exists() or record_path.is_symlink():
                        raise StagingFixtureError('fixture_staging_record_exists')
                    if publish_bytes_no_overwrite(record_path,raw)!='published' or not _same_bytes(record_path,raw):
                        raise StagingFixtureError('fixture_staging_record_unconfirmed')
                    if json.loads(record_path.read_bytes())!=value:
                        raise StagingFixtureError('fixture_staging_record_unconfirmed')
                    records[record_path]=raw
                    guard()
                    return hashlib.sha256(raw).hexdigest()
                allocation=dict(record_version=1,fixture_only=True,attempt_id=directory.name,
                    fixture_ref=hashlib.sha256(self.nonce).hexdigest(),file_id=requirement.file_id,
                    folder_id=folder_id,staging_file='download.bin',expected_size_bytes=requirement.expected_size_bytes)
                checkpoint('before_staging_record',path)
                allocated_sha=publish_record('staging.json',dict(allocation,state='staging'))
                checkpoint('after_staging_record',path)
                checkpoint('before_create',path)
                guard()
                with (path.open('xb') if stream_factory is None else stream_factory(path)) as stream:
                    sink=_FileSink(stream,path,guard,requirement.expected_size_bytes,checkpoint)
                    observed=_read_drive_content(service,folder_id=folder_id,file_id=requirement.file_id,
                        chunk_size=chunk_size,maximum_download_bytes=maximum_download_bytes,sink=sink,verify_copy=sink.finish)
                    checkpoint('before_ready_record',path)
                    sink.verify(observed)
                    publish_record('ready.json',dict(allocation,state='ready',staging_record_sha256=allocated_sha,
                        file_identity=[sink.written.st_dev,sink.written.st_ino],size_bytes=observed.size_bytes,
                        sha256=observed.sha256,version=observed.version))
                    checkpoint('after_ready_record',path)
                    checkpoint('before_return',path)
                    sink.verify(observed)
                    return observed
        except Exception:
            # Failed/partial attempts remain for inspection; never silently reuse or delete.
            raise StagingFixtureError('fixture_sdk_download_unconfirmed') from None
