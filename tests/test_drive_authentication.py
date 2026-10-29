"""Synthetic credentials only, Windows DPAPI and real SDK with offline HTTP."""
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid
from urllib.parse import parse_qs, urlsplit, urlencode

import httplib2
from Common.DriveCredentialStore import CredentialStore, CredentialStoreError, WindowsProtection
from Common.DriveAuthentication import create_service, DesktopAuthorization, SCOPE, DriveAuthenticationError, SingleAttemptHttp
from Common.IsolatedDriveRunner import execute, configuration
from Common.DriveTransferAdapter import sync_bytes
from drive_adapter_fixture_worker import FixtureHttp

NAME = '20240101_12345678@synthetic.txt'
REPO = Path(__file__).resolve().parents[1]


class Http(FixtureHttp):
    def __init__(self, root, kind, fault='none', token_error=False, scope=SCOPE):
        super().__init__(root, kind, fault)
        self.observed = []; self.token_error = token_error; self.scope = scope

    def request(self, uri, method='GET', body=None, headers=None, **kwargs):
        self.observed.append((uri,method))
        if urlsplit(uri).hostname == 'oauth2.googleapis.com':
            value = {'access_token':'synthetic-refreshed-token','refresh_token':'synthetic-refresh',
                'token_type':'Bearer','expires_in':3600,'scope':self.scope}
            if self.token_error: value = {'error':'synthetic-secret-never-log'}
            return httplib2.Response({'status':'400' if self.token_error else '200'}), json.dumps(value).encode()
        if not (headers or {}).get('authorization','').startswith('Bearer synthetic-'):
            raise AssertionError('missing synthetic bearer')
        return super().request(uri,method,body,headers,**kwargs)

    def close(self): pass


@unittest.skipUnless(os.name == 'nt', 'Windows current-user DPAPI required')
class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.paths=[]
        self.private=Path(tempfile.gettempdir())/('eolm-s3-auth-'+uuid.uuid4().hex)
        WindowsProtection().create_directory(self.private); self.paths.append(self.private)
        self.store=CredentialStore(self.private)
        self.record=dict(version=1,principal='synthetic-principal',client_id='synthetic-client',
            client_secret='synthetic-client-secret',scopes=[SCOPE],access_token='synthetic-access-token',
            refresh_token='synthetic-refresh',expires_at=time.time()+3600)
        with self.store.transaction(): self.store.save(self.record,initial=True)
        self.root=Path(tempfile.gettempdir())/('eolm-s1-sync-'+uuid.uuid4().hex)
        self.root.mkdir(); self.paths.append(self.root)
        for kind in ('BattleLog','ErrorReport'): (self.root/'mock-drive'/kind).mkdir(parents=True)
        self.http=Http(self.root,'BattleLog')
        self.config=dict(version=1,mode='isolated_drive',machine_id='PC-B',principal='synthetic-principal',
            client_id='synthetic-client',scope=SCOPE,folders=dict(BattleLog=self.http.folder,ErrorReport='dummy-ErrorReport'),
            store_directory=str(self.private),fixture_root=str(self.root),upload_names=dict(BattleLog=[NAME],ErrorReport=[]),
            required_visible=dict(BattleLog=[],ErrorReport=[]),principal_verified=True,environment_verified=True,
            allow_refresh=True,execution_approved=True)
        self.configpath=self.private/'connection.json'
        self.write_config()

    def write_config(self):
        if not self.configpath.exists():
            with self.store.protection.open_private(self.configpath,1) as stream: stream.write(json.dumps(self.config).encode())
        else:
            with self.store.protection.open_private(self.configpath,3) as stream:
                stream.truncate(0); stream.write(json.dumps(self.config).encode())

    def tearDown(self):
        for p in self.paths:
            assert p.parent == Path(tempfile.gettempdir()) and p.name.startswith(('eolm-s3-auth-','eolm-s1-sync-','eolm-s2-archive-'))
            assert not p.is_symlink()
            shutil.rmtree(p)

    def test_dpapi_encrypted_roundtrip_acl_lease_tamper_and_failed_publication(self):
        encrypted=(self.private/'credential.bin').read_bytes()
        self.assertNotIn(b'synthetic-access-token',encrypted)
        with self.store.transaction():
            with self.assertRaises(CredentialStoreError):
                with self.store.transaction(): pass
            with patch('Common.DriveCredentialStore.os.replace',side_effect=OSError('synthetic-secret')):
                with self.assertRaisesRegex(CredentialStoreError,'^credential_store_unconfirmed$'):
                    self.store.save(dict(self.record,access_token='synthetic-other'))
        self.assertEqual(self.store.load(),self.record)
        (self.private/'credential.bin').write_bytes(encrypted[:-1]+bytes([encrypted[-1]^1]))
        with self.assertRaises(CredentialStoreError): self.store.load()

    def test_unprotected_store_rejected_without_credential_read(self):
        p=Path(tempfile.gettempdir())/('eolm-s3-auth-'+uuid.uuid4().hex); p.mkdir(); self.paths.append(p)
        with self.assertRaises(CredentialStoreError): CredentialStore(p).validate()

    def test_service_no_refresh_and_single_refresh_persist_before_use(self):
        service=create_service(self.config,self.store,http=self.http)
        self.assertEqual(self.http.observed,[]); service.close()
        with self.store.transaction(): self.store.save(dict(self.record,expires_at=0))
        service=create_service(self.config,self.store,http=self.http)
        self.assertEqual(len(self.http.observed),1)
        self.assertEqual(self.store.load()['access_token'],'synthetic-refreshed-token')
        result=sync_bytes(service,folder_id=self.http.folder,filename=NAME,content=b'synthetic-data')
        self.assertEqual(result['status'],'success')
        self.assertEqual(sum(m=='POST' and 'upload/' in u for u,m in self.http.observed),1)
        service.close()

    def test_refresh_errors_scope_mismatch_and_save_failure_preserve_old(self):
        old=dict(self.record,expires_at=0)
        with self.store.transaction(): self.store.save(old)
        for http in (Http(self.root,'BattleLog',token_error=True),Http(self.root,'BattleLog',scope='broad-synthetic-scope')):
            with self.assertRaisesRegex(DriveAuthenticationError,'^drive_authentication_unconfirmed$'):
                create_service(self.config,self.store,http=http)
            self.assertEqual(len(http.observed),1); self.assertEqual(self.store.load(),old)
        with patch.object(self.store,'save',side_effect=OSError('synthetic-secret')):
            with self.assertRaises(DriveAuthenticationError): create_service(self.config,self.store,http=self.http)
        self.assertEqual(self.store.load(),old)

    def test_identity_scope_and_refresh_opt_in_fail_closed(self):
        for config in (dict(self.config,principal='other'),dict(self.config,scope='other'),dict(self.config,principal_verified=False)):
            with self.assertRaises(DriveAuthenticationError): create_service(config,self.store,http=self.http)
        with self.store.transaction(): self.store.save(dict(self.record,expires_at=0))
        with self.assertRaises(DriveAuthenticationError): create_service(dict(self.config,allow_refresh=False),self.store,http=self.http)
        self.assertEqual(self.http.observed,[])

    def test_desktop_pkce_state_one_exchange_without_browser_or_real_tokens(self):
        flow=DesktopAuthorization('synthetic-client','synthetic-secret','synthetic-principal','http://127.0.0.1:8765/callback')
        query=parse_qs(urlsplit(flow.authorization_url()).query)
        self.assertEqual(query['scope'],[SCOPE]); self.assertEqual(query['code_challenge_method'],['S256'])
        with self.assertRaises(DriveAuthenticationError): flow.exchange('http://127.0.0.1:8765/callback?state=wrong&code=fake',self.http,principal_verified=True)
        callback='http://127.0.0.1:8765/callback?'+urlencode(dict(state=flow.state,code='synthetic-code'))
        record=flow.exchange(callback,self.http,principal_verified=True)
        self.assertEqual(record['principal'],'synthetic-principal')
        with self.assertRaises(DriveAuthenticationError): flow.exchange(callback,self.http,principal_verified=True)
        self.assertEqual(len(self.http.observed),1)

    def request(self,operation='sync',**changes):
        return dict(connection_config=str(self.configpath),root=str(self.root),route='Sync',machine_id='PC-B',kind='BattleLog',
            operation=operation,name=NAME,content=base64.b64encode(b'synthetic-data').decode(),**changes)

    def factory(self,config,store): return create_service(config,store,http=self.http)

    def test_runner_upload_reuse_conflict_and_unknown_response_blocks_reentry(self):
        request=self.request()
        request['root']=str(self.root.resolve())
        result=execute(request,service_factory=self.factory)
        self.assertEqual(result['status'],'success')
        self.assertTrue(execute(self.request(),service_factory=self.factory)['reused'])
        req=self.request(); req['content']=base64.b64encode(b'conflict').decode()
        self.assertEqual(execute(req,service_factory=self.factory)['status'],'held')
        self.assertEqual(sum(m=='POST' for u,m in self.http.observed),1)

    def test_unknown_upload_persists_intent_and_does_not_retry(self):
        self.http=Http(self.root,'BattleLog',fault='upload_unknown')
        with self.assertRaises(Exception): execute(self.request(),service_factory=self.factory)
        calls=len(self.http.observed)
        with self.assertRaises(Exception): execute(self.request(),service_factory=self.factory)
        self.assertEqual(len(self.http.observed),calls)
        self.assertEqual(len(list((self.root/'mock-drive/BattleLog').iterdir())),1)

    def test_runner_rejects_role_unknown_config_and_unapproved_before_service(self):
        wrong_root=self.request(); wrong_root['root']=str(self.private)
        with self.assertRaises(Exception): execute(wrong_root,service_factory=lambda *_:self.fail('service called'))
        original_lstat=Path.lstat
        def reparse_root(path, *args, **kwargs):
            if path == self.root:
                from types import SimpleNamespace
                return SimpleNamespace(st_file_attributes=0x400)
            return original_lstat(path,*args,**kwargs)
        with patch.object(Path,'lstat',reparse_root):
            with self.assertRaises(Exception): execute(self.request(),service_factory=lambda *_:self.fail('service called'))
        req=self.request(); req['route']='Archive'
        with self.assertRaises(Exception): execute(req,service_factory=lambda *_:self.fail('service called'))
        for field,value in (('execution_approved',False),('extra',True),('scope','other')):
            original=dict(self.config); self.config[field]=value; self.write_config()
            with self.assertRaises(Exception): execute(self.request(),service_factory=lambda *_:self.fail('service called'))
            self.config=original
        self.write_config()

    def test_official_dry_run_does_not_read_config_or_spawn_python(self):
        (self.root/'.synthetic-fixture').write_text('eolm-s1-synthetic-v1')
        for kind in ('BattleLog','ErrorReport'): (self.root/'source'/kind).mkdir(parents=True)
        (self.root/'source/BattleLog'/NAME).write_bytes(b'synthetic-data')
        command=[shutil.which('pwsh'),'-NoProfile','-File',str(REPO/'scripts/SyncLogs.ps1'),'-Synthetic',
            '-SyntheticRoot',str(self.root),'-IsolatedDrive','-ConnectionConfig','does-not-exist',
            '-PythonExecutable','does-not-exist','-DryRun','-ReferenceDate','2026-10-29']
        result=subprocess.run(command,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['PlannedCount'],1)
        self.assertNotIn(str(self.root),result.stdout+result.stderr)

    def shared_entry(self, route):
        # Injection only in test scope; production bridge exposes no HTTP-factory override.
        quote=lambda p: "'"+str(p).replace("'","''")+"'"
        script=". "+quote(REPO/'Common/SyntheticLogTransfer.ps1')+"\n"+r'''
function Invoke-EoDriveApiFixture {
 param($PythonExecutable,$Request,$ConnectionConfig)
 $Request.connection_config=$ConnectionConfig
 $Request.request_id='synthetic-request'
 $requestJson=$Request|ConvertTo-Json -Depth 8 -Compress
 $raw=$requestJson | & $PythonExecutable -B WORKER
 if ($LASTEXITCODE -ne 0) { [Console]::Error.WriteLine($raw); throw 'synthetic-bridge-failed' }
 $response=$raw|ConvertFrom-Json -AsHashtable
 if (-not $response.ok) { throw 'synthetic-bridge-failed' }
 return $response.result
}
'''.replace('WORKER',quote(REPO/'tests/authenticated_drive_fixture_worker.py'))
        script+='$report=Invoke-EoSyntheticLogTransfer -Route '+route+' -Operation '+route+' -MachineId '+self.config['machine_id']+' -Synthetic -SyntheticRoot '+quote(self.root)+' -IsolatedDrive -ConnectionConfig '+quote(self.configpath)+' -PythonExecutable '+quote(sys.executable)+" -ReferenceDate '2026-10-29'\n$report | ConvertTo-Json -Depth 8\n"
        proc=subprocess.run([shutil.which('pwsh'),'-NoProfile','-Command',script],capture_output=True,text=True,timeout=60)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(proc.stderr,'')
        self.assertNotIn(str(self.private),proc.stdout+proc.stderr)
        return json.loads(proc.stdout)

    def test_shared_sync_authenticated_store_service_sdk_offline_e2e(self):
        (self.root/'.synthetic-fixture').write_text('eolm-s1-synthetic-v1')
        for kind in ('BattleLog','ErrorReport'): (self.root/'source'/kind).mkdir(parents=True)
        source=self.root/'source/BattleLog'/NAME; source.write_bytes(b'synthetic-data')
        report=self.shared_entry('Sync')
        self.assertEqual(report['SuccessCount'],1,report)
        self.assertEqual(report['AdapterMode'],'isolated_drive')
        self.assertEqual(source.read_bytes(),(self.root/'mock-drive/BattleLog'/NAME).read_bytes())
        self.assertEqual(report['CompletedMoveCount'],0)

    def test_shared_archive_authenticated_store_service_sdk_offline_e2e(self):
        self.root=Path(tempfile.gettempdir())/('eolm-s2-archive-'+uuid.uuid4().hex)
        self.root.mkdir(); self.paths.append(self.root)
        (self.root/'.synthetic-fixture').write_text('eolm-s2-synthetic-v1')
        for side in ('mock-drive','archive'):
            for kind in ('BattleLog','ErrorReport'): (self.root/side/kind).mkdir(parents=True)
        source=self.root/'mock-drive/BattleLog'/NAME; source.write_bytes(b'synthetic-data')
        self.config.update(machine_id='PC-A',fixture_root=str(self.root))
        self.config['folders']['ErrorReport']='dummy-ErrorReport'
        self.write_config()
        report=self.shared_entry('Archive')
        self.assertEqual(report['SuccessCount'],1,report)
        self.assertEqual(source.read_bytes(),(self.root/'archive/BattleLog'/NAME).read_bytes())
        self.assertEqual(report['CompletedMoveCount'],0)

    def test_single_attempt_transport_has_fixed_timeout_no_proxy_and_no_retry(self):
        from unittest.mock import MagicMock
        response=MagicMock(); response.__enter__.return_value=response
        response.read.return_value=b'{}'; response.headers={}; response.code=200
        opener=MagicMock(); opener.open.return_value=response
        with patch('Common.DriveAuthentication.build_opener',return_value=opener):
            result=SingleAttemptHttp().request('https://www.googleapis.com/drive/v3/files')
        self.assertEqual(result[0].status,200); opener.open.assert_called_once()
        self.assertEqual(opener.open.call_args.kwargs['timeout'],30)
        with patch('Common.DriveAuthentication.build_opener',return_value=opener):
            opener.open.side_effect=OSError('synthetic-secret')
            with self.assertRaisesRegex(DriveAuthenticationError,'^drive_authentication_unconfirmed$'):
                SingleAttemptHttp().request('https://www.googleapis.com/drive/v3/files')
        self.assertEqual(opener.open.call_count,2)
