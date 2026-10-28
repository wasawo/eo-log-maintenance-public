"""Real SDK requests with offline HTTP responses; no credentials or network."""
import copy
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from googleapiclient.discovery import build
from httplib2 import Response

from Common.DriveContentComparison import ComparisonSource, compare_reobserved_drive_contents
from Common.DriveMetadataReader import (
    DriveMetadataReadError, read_drive_file_metadata, read_drive_listing,
)


FOLDER = dict(id='dummy-folder',mimeType='application/vnd.google-apps.folder',trashed=False)
FILE = dict(id='dummy-file',name='20240101_12345678@a.txt',mimeType='text/plain',
    parents=['dummy-folder'],trashed=False,size='3',version='1',sha256Checksum='a'*64)


class OfflineHttp:
    def __init__(self,responses):
        self.responses=list(responses)
        self.calls=[]
        self.headers=[]

    def request(self,uri,method='GET',body=None,headers=None,**kwargs):
        self.calls.append((uri,method,body))
        self.headers.append(dict(headers or {}))
        if not self.responses:
            raise AssertionError('Unexpected SDK HTTP request')
        entry=self.responses.pop(0);status,value=entry[:2]
        response_headers={'status':str(status),'content-type':'application/json'}
        if len(entry)==3:response_headers.update(entry[2])
        return Response(response_headers),value if type(value) is bytes else json.dumps(value).encode('utf-8')


class DriveMetadataReaderTests(unittest.TestCase):
    def service(self,*responses):
        http=OfflineHttp(responses)
        service=build('drive','v3',http=http,static_discovery=True,cache_discovery=False)
        return service,http

    def assert_private_failure(self,operation):
        with self.assertRaises(DriveMetadataReadError) as raised:
            operation()
        self.assertEqual(str(raised.exception),'drive_metadata_unconfirmed')
        self.assertTrue(raised.exception.__suppress_context__ or raised.exception.__context__ is None)

    def test_all_pages_including_empty_intermediate_page_use_exact_query(self):
        other=dict(FILE,id='dummy-second',name='20240101_12345678@b.txt')
        service,http=self.service((200,FOLDER),(200,dict(files=[],nextPageToken='next-1')),
            (200,dict(files=[FILE],nextPageToken='next-2')),(200,dict(files=[other])))
        observed=read_drive_listing(service,folder_id='dummy-folder')
        self.assertEqual([file.file_id for file in observed.files],['dummy-file','dummy-second'])
        self.assertEqual(observed.files[0].version,'1')
        self.assertTrue(observed.enumeration_completed)
        self.assertFalse(observed.may_report_sync_success or observed.may_archive or observed.may_restore)
        self.assertEqual(len(http.calls),4)
        for uri,method,body in http.calls:
            self.assertEqual(method,'GET'); self.assertIsNone(body)
            self.assertEqual(urlsplit(uri).netloc,'www.googleapis.com')
        queries=[parse_qs(urlsplit(uri).query) for uri,_,_ in http.calls[1:]]
        self.assertNotIn('pageToken',queries[0])
        self.assertEqual(queries[1]['pageToken'],['next-1'])
        self.assertEqual(queries[2]['pageToken'],['next-2'])
        for query in queries:
            self.assertEqual(query['q'],["'dummy-folder' in parents and trashed = false"])
            self.assertIn('incompleteSearch',query['fields'][0])
            self.assertIn('sha256Checksum',query['fields'][0])
            self.assertIn('version',query['fields'][0])

    def test_empty_terminal_list_is_valid_but_incomplete_search_is_not(self):
        for response in ({},{'files':[]}):
            service,http=self.service((200,FOLDER),(200,response))
            self.assertEqual(read_drive_listing(service,folder_id='dummy-folder').files,())
            self.assertEqual(len(http.calls),2)
        for response in (dict(files=[FILE],incompleteSearch=True),dict(files=[],incompleteSearch='false'),dict(files=None)):
            service,http=self.service((200,FOLDER),(200,response))
            self.assert_private_failure(lambda:read_drive_listing(service,folder_id='dummy-folder'))
            self.assertEqual(len(http.calls),2)

    def test_wrong_or_trashed_root_fails_before_listing(self):
        for change in (dict(id='other'),dict(mimeType='text/plain'),dict(trashed=True)):
            service,http=self.service((200,dict(FOLDER,**change)))
            self.assert_private_failure(lambda:read_drive_listing(service,folder_id='dummy-folder'))
            self.assertEqual(len(http.calls),1)

    def test_parent_content_kind_and_metadata_must_be_confirmed(self):
        for change in (dict(parents=['other']),dict(trashed=True),dict(mimeType='application/vnd.google-apps.folder'),
                dict(mimeType='application/vnd.google-apps.shortcut'),dict(mimeType='application/vnd.google-apps.document'),
                dict(size=3),dict(size='-1'),dict(size=str(2**63)),dict(version='0'),dict(version=True),
                dict(version=str(2**63)),dict(sha256Checksum='bad'),dict(id=''),dict(name='')):
            with self.subTest(change=change):
                service,http=self.service((200,FOLDER),(200,dict(files=[dict(FILE,**change)])))
                self.assert_private_failure(lambda:read_drive_listing(service,folder_id='dummy-folder'))
                self.assertEqual(len(http.calls),2)

    def test_duplicate_identity_cycle_and_page_limits_never_return_partial_data(self):
        for responses in (
                [(200,dict(files=[FILE],nextPageToken='next')),(200,dict(files=[FILE]))],
                [(200,dict(files=[],nextPageToken='next')),(200,dict(files=[],nextPageToken='next'))]):
            service,http=self.service((200,FOLDER),*responses)
            self.assert_private_failure(lambda:read_drive_listing(service,folder_id='dummy-folder'))
            self.assertEqual(len(http.calls),3)
        service,http=self.service((200,FOLDER),(200,dict(files=[FILE],nextPageToken='next')))
        self.assert_private_failure(lambda:read_drive_listing(service,folder_id='dummy-folder',maximum_pages=1))
        self.assertEqual(len(http.calls),2)

    def test_request_failure_is_sanitized_without_implicit_sdk_retry(self):
        for code in (403,404,429,503):
            service,http=self.service((200,FOLDER),(200,dict(files=[FILE],nextPageToken='next')),
                (code,dict(error=dict(code=code,message='private synthetic server detail'))))
            self.assert_private_failure(lambda:read_drive_listing(service,folder_id='dummy-folder'))
            self.assertEqual(len(http.calls),3)

    def test_exact_metadata_id_and_parent_are_required_and_missing_hash_stays_unknown(self):
        value=copy.deepcopy(FILE);del value['sha256Checksum']
        service,http=self.service((200,value))
        observed=read_drive_file_metadata(service,folder_id='dummy-folder',file_id='dummy-file')
        self.assertIsNone(observed.sha256);self.assertFalse(observed.sha256_trusted)
        self.assertEqual(urlsplit(http.calls[0][0]).path,'/drive/v3/files/dummy-file')
        service,http=self.service((200,dict(FILE,id='another-file')))
        self.assert_private_failure(lambda:read_drive_file_metadata(service,folder_id='dummy-folder',file_id='dummy-file'))
        self.assertEqual(len(http.calls),1)

    def test_sdk_error_diagnostics_cannot_log_raw_server_messages(self):
        for body in (b'private synthetic malformed error body',dict(error=dict(message='private synthetic message'))):
            service,http=self.service((403,body))
            with self.assertNoLogs('googleapiclient.http',level='WARNING'):
                self.assert_private_failure(lambda:read_drive_file_metadata(service,folder_id='dummy-folder',file_id='dummy-file'))
            self.assertEqual(len(http.calls),1)

    def test_sdk_listing_connects_to_existing_comparison_and_version_change_is_held(self):
        sources=(ComparisonSource(FILE['name'],3,'a'*64),)
        for version,expected_status in (('1','compared'),('2','held')):
            service,http=self.service((200,FOLDER),(200,dict(files=[FILE])),
                (200,FOLDER),(200,dict(files=[dict(FILE,version=version)])))
            before=read_drive_listing(service,folder_id='dummy-folder')
            after=read_drive_listing(service,folder_id='dummy-folder')
            result=compare_reobserved_drive_contents(sources,before,after,source_trusted=True,expected_folder_id='dummy-folder')
            self.assertEqual(result.status,expected_status)
            if version=='2':self.assertEqual(result.reason_code,'comparison_listing_changed')
            else:self.assertEqual(result.results[0].candidate_file_id,'dummy-file')
            self.assertFalse(result.may_report_sync_success or result.may_archive or result.may_restore)
            self.assertEqual(len(http.calls),4)

    def test_query_literals_are_escaped_and_invalid_inputs_make_no_request(self):
        folder="dummy'folder\\part"
        service,http=self.service((200,dict(FOLDER,id=folder)),(200,dict(files=[])))
        read_drive_listing(service,folder_id=folder)
        self.assertEqual(parse_qs(urlsplit(http.calls[1][0]).query)['q'],["'dummy\\'folder\\\\part' in parents and trashed = false"])
        for folder,limit in (('',None),('dummy-folder',True),('dummy-folder',0),('bad\nfolder',None)):
            service,http=self.service()
            self.assert_private_failure(lambda:read_drive_listing(service,folder_id=folder,maximum_pages=limit))
            self.assertEqual(http.calls,[])


if __name__=='__main__':unittest.main()
