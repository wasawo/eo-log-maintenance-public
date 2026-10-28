"""Cold SDK staging inspection without passing producer observations to child."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from googleapiclient.discovery import build

from Common.DriveContentComparison import DownloadRequirement
from sdk_download_staging_fixture import SdkDownloadStagingFixture
from download_staging_fixture import StagingFixtureError
from test_drive_metadata_reader import OfflineHttp
from test_drive_content_reader import DATA, METADATA


@unittest.skipUnless(os.name=='nt','real Windows owned staging required')
class SdkStagingObserverTests(unittest.TestCase):
    def fixture(self):
        value=SdkDownloadStagingFixture();self.addCleanup(value.close)
        return value

    def produce(self,value, *, responses=None,checkpoint=None):
        if responses is None:responses=[(200,METADATA),(200,DATA),(200,METADATA)]
        service=build('drive','v3',http=OfflineHttp(responses),static_discovery=True,cache_discovery=False)
        return value.download_from_sdk(DownloadRequirement('dummy-file',5),service,
            folder_id='dummy-folder',chunk_size=5,at_checkpoint=checkpoint)

    def observe(self,value, *, expected='ready_candidate',**changes):
        before={str(p.relative_to(value.root)):p.read_bytes() for p in value.root.rglob('*') if p.is_file()}
        request=dict(root=str(value.root),nonce=value.nonce.decode('ascii'),
            attempt=value.attempts[0].parent.name,maximum_record_bytes=4096)
        request.update(changes)
        child=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).with_name('sdk_staging_observer.py'))],
            input=json.dumps(request),capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
        result=json.loads(child.stdout)
        self.assertEqual(result['status'],expected)
        self.assertEqual(child.returncode,1 if expected=='unconfirmed' else 0)
        self.assertFalse(result['may_change_state'] or result['cloud_observed'])
        for private in (str(value.root),value.nonce.decode('ascii'),'dummy-file',DATA.decode()):
            self.assertNotIn(private,child.stdout+child.stderr)
        self.assertEqual(before,{str(p.relative_to(value.root)):p.read_bytes() for p in value.root.rglob('*') if p.is_file()})
        return result

    def test_complete_records_are_independently_matched_without_mutation(self):
        value=self.fixture();self.produce(value)
        result=self.observe(value)
        self.assertEqual(result['reason_code'],'local_records_and_payload_match')

    def test_allocation_only_and_partial_payload_remain_incomplete(self):
        value=self.fixture()
        def stop(phase,path):
            if phase=='after_staging_record':raise RuntimeError('synthetic interruption')
        with self.assertRaises(StagingFixtureError):self.produce(value,checkpoint=stop)
        self.observe(value,expected='allocation_only')
        value=self.fixture()
        with self.assertRaises(StagingFixtureError):
            self.produce(value,responses=[(200,METADATA),(206,b'ab',{'content-range':'bytes 0-1/5'}),(503,b'private detail')])
        self.observe(value,expected='incomplete')

    def test_lost_ready_ack_is_only_a_local_candidate_not_past_success(self):
        value=self.fixture()
        def stop(phase,path):
            if phase=='after_ready_record':raise RuntimeError('synthetic response loss')
        with self.assertRaises(StagingFixtureError):self.produce(value,checkpoint=stop)
        result=self.observe(value)
        self.assertEqual(set(result),{'status','reason_code','may_change_state','cloud_observed'})

    def test_corrupt_binding_identity_shape_duplicates_and_payload_are_unconfirmed(self):
        for change in ('digest','identity','field','duplicate','version','payload'):
            with self.subTest(change=change):
                value=self.fixture();self.produce(value);path=value.attempts[0];ready_path=path.parent/'ready.json'
                ready=json.loads(ready_path.read_bytes())
                if change=='payload':path.write_bytes(b'xxxxx')
                elif change=='duplicate':
                    ready_path.write_bytes(ready_path.read_bytes().replace(b'"record_version":1',b'"record_version":1,"record_version":1',1))
                else:
                    if change=='digest':ready['staging_record_sha256']='0'*64
                    if change=='identity':ready['file_identity']=[0,0]
                    if change=='field':ready['unexpected']=True
                    if change=='version':ready['version']='0'
                    ready_path.write_text(json.dumps(ready),encoding='utf-8')
                self.observe(value,expected='unconfirmed')

    def test_same_bytes_replacement_missing_records_and_hardlink_do_not_match(self):
        for change in ('replacement','payload_missing','allocation_missing','hardlink'):
            with self.subTest(change=change):
                value=self.fixture();self.produce(value);path=value.attempts[0]
                value.guard()
                if change=='replacement':
                    path.rename(value.root/'original-payload.bin');path.write_bytes(DATA)
                if change=='payload_missing':path.unlink()
                if change=='allocation_missing':(path.parent/'staging.json').unlink()
                if change=='hardlink':os.link(path.parent/'ready.json',value.root/'ready-alias.json')
                self.observe(value,expected='unconfirmed')

    def test_owner_record_is_preserved_and_does_not_become_no_work(self):
        value=self.fixture();self.produce(value)
        (value.root/'owner.json').write_bytes(b'retained synthetic ownership')
        result=self.observe(value,expected='held')
        self.assertEqual(result['reason_code'],'owner_record_present')

    def test_invalid_locator_budget_and_unexpected_entries_are_refused(self):
        value=self.fixture();self.produce(value)
        for changes in (dict(nonce='0'*32),dict(attempt='../escape'),dict(maximum_record_bytes=1),dict(maximum_record_bytes=True)):
            self.observe(value,expected='unconfirmed',**changes)
        (value.attempts[0].parent/'unexpected.tmp').write_bytes(b'leftover')
        self.observe(value,expected='unconfirmed')


if __name__=='__main__':unittest.main()
