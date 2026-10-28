"""Real owned file staging fed by the production SDK transfer and fake HTTP."""
import os
import hashlib
import unittest

from googleapiclient.discovery import build

from Common.DriveContentComparison import DownloadRequirement, ComparisonSource, plan_content_downloads, compare_planned_drive_contents
from Common.DriveMetadataReader import read_drive_listing
from download_staging_fixture import StagingFixtureError
from sdk_download_staging_fixture import SdkDownloadStagingFixture
from test_drive_content_reader import DATA, DIGEST, METADATA
from test_drive_metadata_reader import FOLDER, FILE, OfflineHttp


class FaultStream:
    def __init__(self,path,fault):
        self.stream=path.open('xb')
        self.fault=fault
        self.calls=0

    def __enter__(self):return self
    def __exit__(self,*args):return self.stream.__exit__(*args)
    def __getattr__(self,name):return getattr(self.stream,name)
    def write(self,content):
        self.calls+=1
        if self.fault=='short':return self.stream.write(content[:-1])
        if self.fault=='full' and self.calls==2:raise OSError('synthetic disk full detail')
        return self.stream.write(content)
    def flush(self):
        if self.fault=='flush':raise OSError('synthetic flush detail')
        return self.stream.flush()


@unittest.skipUnless(os.name=='nt','real Windows owned mutex staging required')
class SdkDownloadStagingTests(unittest.TestCase):
    def fixture(self):
        value=SdkDownloadStagingFixture();self.addCleanup(value.close)
        return value

    def service(self,*responses):
        http=OfflineHttp(responses)
        return build('drive','v3',http=http,static_discovery=True,cache_discovery=False),http

    def download(self,value,service,**options):
        return value.download_from_sdk(DownloadRequirement('dummy-file',options.pop('size',5)),service,
            folder_id='dummy-folder',chunk_size=options.pop('chunk_size',2),**options)

    def responses(self,after=METADATA):
        return [(200,METADATA),(206,b'ab',{'content-range':'bytes 0-1/5'}),
            (206,b'cd',{'content-range':'bytes 2-3/5'}),(206,b'e',{'content-range':'bytes 4-4/5'}),(200,after)]

    def assert_failure(self,operation):
        with self.assertRaisesRegex(StagingFixtureError,'^fixture_sdk_download_unconfirmed$'):operation()

    def test_sdk_bytes_are_exclusively_saved_synced_reobserved_and_version_bound(self):
        value=self.fixture();service,http=self.service(*self.responses())
        observed=self.download(value,service)
        self.assertEqual(value.attempts[0].read_bytes(),DATA)
        self.assertEqual((observed.size_bytes,observed.sha256,observed.version),(5,DIGEST,'1'))
        self.assertFalse((value.root/'owner.json').exists())
        self.assertEqual(len(http.calls),5)

    def test_missing_hash_staging_connects_to_actual_sdk_listing_plan_and_comparison(self):
        value=self.fixture();metadata=dict(METADATA);del metadata['sha256Checksum']
        service,http=self.service((200,FOLDER),(200,dict(files=[metadata])),(200,metadata),
            (200,DATA),(200,metadata),(200,FOLDER),(200,dict(files=[metadata])))
        sources=(ComparisonSource(FILE['name'],5,DIGEST),)
        before=read_drive_listing(service,folder_id='dummy-folder')
        plan=plan_content_downloads(sources,before,source_trusted=True,expected_folder_id='dummy-folder')
        observed=self.download(value,service,chunk_size=5)
        after=read_drive_listing(service,folder_id='dummy-folder')
        result=compare_planned_drive_contents(sources,before,after,plan,source_trusted=True,
            expected_folder_id='dummy-folder',downloads=(observed,))
        self.assertEqual(result.results[0].candidate_file_id,'dummy-file')
        self.assertFalse(result.may_report_sync_success or result.may_archive or result.may_restore)
        self.assertEqual(value.attempts[0].read_bytes(),DATA)
        self.assertEqual(len(http.calls),7)

    def test_interrupted_or_changed_source_attempt_is_preserved_and_retry_is_fresh(self):
        for responses,expected in (
                ([(200,METADATA),(206,b'ab',{'content-range':'bytes 0-1/5'}),(503,b'private synthetic error')],b'ab'),
                (self.responses(dict(METADATA,version='2')),DATA)):
            with self.subTest(expected=expected):
                value=self.fixture();service,http=self.service(*responses)
                self.assert_failure(lambda:self.download(value,service))
                old=value.attempts[0]
                self.assertEqual(old.read_bytes(),expected)
                self.assertFalse((value.root/'owner.json').exists())
                service,http=self.service(*self.responses())
                self.download(value,service)
                self.assertNotEqual(value.attempts[1],old)
                self.assertEqual(old.read_bytes(),expected)
                self.assertEqual(value.attempts[1].read_bytes(),DATA)

    def test_occupied_name_is_not_overwritten_or_sent_to_sdk(self):
        value=self.fixture();service,http=self.service()
        def occupy(phase,path):
            if phase=='before_create':path.write_bytes(b'occupied')
        self.assert_failure(lambda:self.download(value,service,at_checkpoint=occupy))
        self.assertEqual(value.attempts[0].read_bytes(),b'occupied')
        self.assertEqual(http.calls,[])

    def test_short_write_disk_full_and_flush_failure_leave_no_observation(self):
        for fault,expected in (('short',b'a'),('full',b'ab'),('flush',DATA)):
            with self.subTest(fault=fault):
                value=self.fixture();service,http=self.service(*self.responses())
                self.assert_failure(lambda:self.download(value,service,stream_factory=lambda path:FaultStream(path,fault)))
                self.assertEqual(value.attempts[0].read_bytes(),expected)
                self.assertFalse((value.root/'owner.json').exists())

    def test_file_changes_after_close_or_during_final_metadata_wait_are_rejected(self):
        value=self.fixture();service,http=self.service(*self.responses())
        def change(phase,path):
            if phase=='after_close':path.write_bytes(b'changed')
        self.assert_failure(lambda:self.download(value,service,at_checkpoint=change))
        self.assertEqual(value.attempts[0].read_bytes(),b'changed')
        self.assertEqual(len(http.calls),4)
        value=self.fixture();service,http=self.service(*self.responses())
        original=http.request
        def mutate_during_metadata(uri,*args,**kwargs):
            if len(http.calls)==4:value.attempts[0].write_bytes(b'changed')
            return original(uri,*args,**kwargs)
        http.request=mutate_during_metadata
        self.assert_failure(lambda:self.download(value,service))
        self.assertEqual(value.attempts[0].read_bytes(),b'changed')
        self.assertEqual(len(http.calls),5)

    def test_lost_token_before_write_or_return_preserves_attempt_and_foreign_record(self):
        for phase in ('before_create','after_close','before_return'):
            with self.subTest(phase=phase):
                value=self.fixture();service,http=self.service(*self.responses())
                def change(point,path):
                    if point==phase:(value.root/'owner.json').write_bytes(b'changed synthetic ownership')
                self.assert_failure(lambda:self.download(value,service,at_checkpoint=change))
                self.assertEqual((value.root/'owner.json').read_bytes(),b'changed synthetic ownership')
                if phase=='before_create':self.assertFalse(value.attempts[0].exists())
                else:self.assertEqual(value.attempts[0].read_bytes(),DATA)

    def test_zero_bytes_and_plan_size_mismatch_are_distinct(self):
        empty=dict(METADATA,size='0',sha256Checksum=hashlib.sha256(b'').hexdigest())
        value=self.fixture();service,http=self.service((200,empty),(200,b''),(200,empty))
        observed=self.download(value,service,size=0)
        self.assertEqual(observed.size_bytes,0)
        self.assertEqual(value.attempts[0].read_bytes(),b'')
        value=self.fixture();service,http=self.service(*self.responses())
        self.assert_failure(lambda:self.download(value,service,size=6))
        self.assertEqual(value.attempts[0].read_bytes(),DATA)
        self.assertEqual(len(http.calls),4)


if __name__=='__main__':unittest.main()
