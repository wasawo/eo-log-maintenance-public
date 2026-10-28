"""Official SDK media downloads into a hash with synthetic HTTP only."""
import hashlib
import unittest
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

from googleapiclient.discovery import build

from Common.DriveContentReader import DriveContentReadError, read_drive_content_hash
from Common.DriveContentComparison import (
    ComparisonSource, plan_content_downloads, compare_planned_drive_contents,
)
from Common.DriveMetadataReader import read_drive_listing
from test_drive_metadata_reader import FILE, FOLDER, OfflineHttp


DATA=b'abcde'
DIGEST=hashlib.sha256(DATA).hexdigest()
METADATA=dict(FILE,size='5',sha256Checksum=DIGEST,capabilities={'canDownload':True})


class DriveContentReaderTests(unittest.TestCase):
    def service(self,*responses):
        http=OfflineHttp(responses)
        return build('drive','v3',http=http,static_discovery=True,cache_discovery=False),http

    def read(self,service,**options):
        return read_drive_content_hash(service,folder_id='dummy-folder',file_id='dummy-file',chunk_size=options.pop('chunk_size',2),**options)

    def assert_private_failure(self,operation):
        with self.assertRaises(DriveContentReadError) as raised:operation()
        self.assertEqual(str(raised.exception),'drive_content_unconfirmed')

    def test_sdk_chunks_are_hashed_without_retaining_contents_and_metadata_is_reobserved(self):
        service,http=self.service((200,METADATA),(206,b'ab',{'content-range':'bytes 0-1/5'}),
            (206,b'cd',{'content-range':'bytes 2-3/5'}),(206,b'e',{'content-range':'bytes 4-4/5'}),(200,METADATA))
        observed=self.read(service,maximum_download_bytes=5)
        self.assertEqual((observed.file_id,observed.version,observed.size_bytes,observed.sha256),('dummy-file','1',5,DIGEST))
        self.assertEqual(set(vars(observed)),{'file_id','version','size_bytes','sha256'})
        self.assertEqual([h.get('range') for h in http.headers[1:4]],['bytes=0-1','bytes=2-3','bytes=4-5'])
        self.assertEqual(len(http.calls),5)
        for uri,method,body in http.calls:
            self.assertEqual(method,'GET');self.assertIsNone(body)
        self.assertEqual(parse_qs(urlsplit(http.calls[1][0]).query)['alt'],['media'])
        self.assertIn('capabilities(canDownload)',parse_qs(urlsplit(http.calls[0][0]).query)['fields'][0])

    def test_zero_byte_files_require_success_or_exact_zero_range_and_post_metadata(self):
        empty=dict(METADATA,size='0',sha256Checksum=hashlib.sha256(b'').hexdigest())
        for media in ((200,b'',{'content-length':'0'}),(416,b'private synthetic error body',{'content-range':'bytes */0'})):
            service,http=self.service((200,empty),media,(200,empty))
            observed=self.read(service)
            self.assertEqual((observed.size_bytes,observed.sha256),(0,hashlib.sha256(b'').hexdigest()))
            self.assertEqual(len(http.calls),3)

    def test_missing_hash_download_connects_to_plan_and_version_bound_comparison(self):
        metadata=dict(METADATA);del metadata['sha256Checksum']
        service,http=self.service((200,FOLDER),(200,dict(files=[metadata])),(200,metadata),
            (200,DATA,{'content-length':'5'}),(200,metadata),(200,FOLDER),(200,dict(files=[metadata])))
        sources=(ComparisonSource(FILE['name'],5,DIGEST),)
        before=read_drive_listing(service,folder_id='dummy-folder')
        plan=plan_content_downloads(sources,before,source_trusted=True,expected_folder_id='dummy-folder')
        downloaded=self.read(service,chunk_size=5)
        after=read_drive_listing(service,folder_id='dummy-folder')
        options=dict(source_trusted=True,expected_folder_id='dummy-folder')
        result=compare_planned_drive_contents(sources,before,after,plan,downloads=(downloaded,),**options)
        self.assertEqual(result.status,'compared')
        self.assertEqual(result.results[0].candidate_file_id,'dummy-file')
        self.assertFalse(result.may_report_sync_success or result.may_archive or result.may_restore)
        stale=compare_planned_drive_contents(sources,before,after,plan,downloads=(replace(downloaded,version='2'),),**options)
        self.assertEqual((stale.status,stale.reason_code),('held','comparison_download_version_mismatch'))
        self.assertEqual(len(http.calls),7)

    def test_changed_post_metadata_or_unconfirmed_download_permission_returns_no_observation(self):
        for change in (dict(version='2'),dict(name='other.txt'),dict(parents=['other']),dict(size='6'),
                dict(sha256Checksum='f'*64),dict(capabilities={'canDownload':False})):
            with self.subTest(change=change):
                service,http=self.service((200,METADATA),(200,DATA),(200,dict(METADATA,**change)))
                self.assert_private_failure(lambda:self.read(service,chunk_size=5))
                self.assertEqual(len(http.calls),3)
        for capability in (None,{'canDownload':False},{'canDownload':'true'}):
            service,http=self.service((200,dict(METADATA,capabilities=capability)))
            self.assert_private_failure(lambda:self.read(service))
            self.assertEqual(len(http.calls),1)

    def test_download_limits_reject_before_media_and_invalid_options_before_any_request(self):
        service,http=self.service((200,METADATA))
        self.assert_private_failure(lambda:self.read(service,maximum_download_bytes=4))
        self.assertEqual(len(http.calls),1)
        for options in (dict(chunk_size=0),dict(chunk_size=True),dict(maximum_download_bytes=0),dict(maximum_download_bytes=True)):
            service,http=self.service()
            self.assert_private_failure(lambda:self.read(service,**options))
            self.assertEqual(http.calls,[])

    def test_invalid_ranges_lengths_redirects_or_nonprogress_are_not_hashed_as_complete(self):
        for response in (
                (206,b'ab',{'content-range':'bytes 1-2/5'}),(206,b'ab',{'content-range':'bytes 0-1/6'}),
                (206,b'ab',{}),(206,b'',{'content-range':'bytes 0-0/5'}),
                (206,b'abc',{'content-range':'bytes 0-2/5'}),
                (206,b'ab',{'content-range':'bytes 0-1/5','content-length':'9'}),
                (206,b'ab',{'content-range':'bytes 0-1/5','content-location':'https://example.invalid/other'}),
                (200,b'ab'),(200,DATA),(416,b'',{'content-range':'bytes */0'})):
            with self.subTest(response=response):
                service,http=self.service((200,METADATA),response)
                self.assert_private_failure(lambda:self.read(service))
                self.assertEqual(len(http.calls),2)

    def test_mid_download_or_post_observation_failure_never_retries_or_exposes_error_body(self):
        for status in (403,404,429,503):
            service,http=self.service((200,METADATA),(206,b'ab',{'content-range':'bytes 0-1/5'}),
                (status,b'private synthetic response body'))
            with self.assertNoLogs('googleapiclient.http',level='WARNING'):
                self.assert_private_failure(lambda:self.read(service))
            self.assertEqual(len(http.calls),3)
        service,http=self.service((200,METADATA),(200,DATA),(403,b'private synthetic metadata error'))
        self.assert_private_failure(lambda:self.read(service,chunk_size=5))
        self.assertEqual(len(http.calls),3)

    def test_content_must_match_api_hash_even_when_size_and_version_match(self):
        service,http=self.service((200,METADATA),(200,b'xxxxx'),(200,METADATA))
        self.assert_private_failure(lambda:self.read(service,chunk_size=5))
        self.assertEqual(len(http.calls),2)  # A known content mismatch needs no further request.


if __name__=='__main__':unittest.main()
