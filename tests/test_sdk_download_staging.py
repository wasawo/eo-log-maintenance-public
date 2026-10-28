"""Real owned file staging fed by the production SDK transfer and fake HTTP."""
import os
import hashlib
import json
from unittest.mock import patch
import unittest

from googleapiclient.discovery import build

from Common.DriveContentComparison import DownloadRequirement, ComparisonSource, plan_content_downloads, compare_planned_drive_contents
from Common.DriveMetadataReader import read_drive_listing
from download_staging_fixture import StagingFixtureError
from sdk_download_staging_fixture import SdkDownloadStagingFixture
import sdk_download_staging_fixture as staging_module
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

    def test_metadata_precedes_payload_and_ready_binds_allocation_and_verified_copy(self):
        value=self.fixture();service,http=self.service(*self.responses());seen=[]
        def inspect(phase,path):
            if phase=='before_create':
                allocated=json.loads((path.parent/'staging.json').read_bytes())
                self.assertEqual(allocated['state'],'staging')
                self.assertTrue(allocated['fixture_only'])
                self.assertEqual((allocated['file_id'],allocated['folder_id'],allocated['expected_size_bytes']),('dummy-file','dummy-folder',5))
                self.assertFalse(path.exists())
                self.assertFalse((path.parent/'ready.json').exists())
                self.assertEqual(http.calls,[])
                seen.append(phase)
            if phase=='before_ready_record':
                self.assertEqual(path.read_bytes(),DATA)
                self.assertEqual(len(http.calls),5)
                self.assertFalse((path.parent/'ready.json').exists())
                seen.append(phase)
        observed=self.download(value,service,at_checkpoint=inspect)
        path=value.attempts[0];allocated_raw=(path.parent/'staging.json').read_bytes()
        ready=json.loads((path.parent/'ready.json').read_bytes())
        self.assertEqual(seen,['before_create','before_ready_record'])
        self.assertEqual(ready['state'],'ready');self.assertTrue(ready['fixture_only'])
        self.assertEqual(ready['staging_record_sha256'],hashlib.sha256(allocated_raw).hexdigest())
        self.assertEqual(ready['file_identity'],[path.stat().st_dev,path.stat().st_ino])
        self.assertEqual((ready['size_bytes'],ready['sha256'],ready['version']),(observed.size_bytes,DIGEST,'1'))

    def test_allocation_publication_failure_prevents_payload_and_sdk_requests(self):
        value=self.fixture();service,http=self.service()
        with patch.object(staging_module,'publish_bytes_no_overwrite',side_effect=OSError('synthetic metadata failure')):
            self.assert_failure(lambda:self.download(value,service))
        self.assertFalse(value.attempts[0].exists())
        self.assertFalse((value.attempts[0].parent/'ready.json').exists())
        self.assertEqual(http.calls,[])

    def test_interruption_after_allocation_preserves_record_and_retry_does_not_adopt_it(self):
        value=self.fixture();service,http=self.service()
        def stop(phase,path):
            if phase=='after_staging_record':raise RuntimeError('synthetic interruption')
        self.assert_failure(lambda:self.download(value,service,at_checkpoint=stop))
        old=value.attempts[0];allocated=(old.parent/'staging.json').read_bytes()
        self.assertFalse(old.exists());self.assertEqual(http.calls,[])
        service,http=self.service(*self.responses())
        self.download(value,service)
        self.assertNotEqual(old.parent,value.attempts[1].parent)
        self.assertEqual((old.parent/'staging.json').read_bytes(),allocated)
        self.assertFalse((old.parent/'ready.json').exists())

    def test_record_corruption_or_lost_ownership_before_ready_cannot_publish_ready(self):
        for change in ('allocation','ownership','payload'):
            value=self.fixture();service,http=self.service(*self.responses())
            def corrupt(phase,path):
                if phase=='before_ready_record':
                    target=path.parent/'staging.json' if change=='allocation' else value.root/'owner.json' if change=='ownership' else path
                    target.write_bytes(b'changed synthetic data')
            self.assert_failure(lambda:self.download(value,service,at_checkpoint=corrupt))
            self.assertTrue((value.attempts[0].parent/'staging.json').exists())
            self.assertFalse((value.attempts[0].parent/'ready.json').exists())

    def test_failed_or_uncertain_ready_publication_keeps_files_without_success_receipt(self):
        original=staging_module.publish_bytes_no_overwrite
        for after_publish in (False,True):
            value=self.fixture();service,http=self.service(*self.responses())
            def fail(path,raw):
                if path.name=='ready.json':
                    if after_publish:original(path,raw)
                    raise OSError('synthetic publication response loss')
                return original(path,raw)
            with patch.object(staging_module,'publish_bytes_no_overwrite',side_effect=fail):
                self.assert_failure(lambda:self.download(value,service))
            path=value.attempts[0]
            self.assertEqual(path.read_bytes(),DATA)
            self.assertTrue((path.parent/'staging.json').exists())
            self.assertEqual((path.parent/'ready.json').exists(),after_publish)
            self.assertFalse((value.root/'owner.json').exists())

    def test_preexisting_metadata_is_not_overwritten(self):
        value=self.fixture();service,http=self.service()
        def occupy(phase,path):
            if phase=='before_staging_record':(path.parent/'staging.json').write_bytes(b'occupied')
        self.assert_failure(lambda:self.download(value,service,at_checkpoint=occupy))
        path=value.attempts[0]
        self.assertEqual((path.parent/'staging.json').read_bytes(),b'occupied')
        self.assertFalse(path.exists());self.assertEqual(http.calls,[])


if __name__=='__main__':unittest.main()
