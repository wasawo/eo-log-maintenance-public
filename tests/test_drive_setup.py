"""S3 setup uses synthetic credentials, offline token responses and loopback only."""
from contextlib import redirect_stdout, redirect_stderr
import http.client
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlencode, parse_qs, urlsplit
import uuid
import warnings
import getpass

import httplib2
from Common.DriveAuthentication import DesktopAuthorization, SCOPE, TOKEN_URI
from Common.DriveCredentialStore import CredentialStore, WindowsProtection
from Common.DriveSetup import CallbackReceiver, SetupError, prepare_configuration, validate_configuration_file, enroll, main


FOLDERS=['synthetic-battle-folder','synthetic-error-folder']


class TokenHttp:
    def __init__(self,fail=False): self.calls=[]; self.fail=fail; self.closed=False
    def request(self,uri,method='GET',body=None,headers=None):
        if uri != TOKEN_URI or method != 'POST': raise AssertionError('unexpected network target')
        self.calls.append(parse_qs(body))
        value=dict(access_token='synthetic-access-token',refresh_token='synthetic-refresh-token',
            token_type='Bearer',scope=SCOPE,expires_in=3600)
        if self.fail: value={'error':'synthetic-secret-error-body'}
        return httplib2.Response({'status':'400' if self.fail else '200'}),json.dumps(value).encode()
    def close(self): self.closed=True


def submit(receiver,fields,*,target=None,host=None,method='GET'):
    connection=http.client.HTTPConnection('127.0.0.1',receiver.server.server_port,timeout=3)
    path=target if target is not None else receiver.path+'?'+urlencode(fields)
    headers={} if host is None else {'Host':host}
    try:
        connection.request(method,path,headers=headers)
        response=connection.getresponse(); data=response.read()
        if b'synthetic-code' in data or b'synthetic-secret' in data: raise AssertionError('callback reflected secret')
        return response.status,response.getheader('Cache-Control')
    finally: connection.close()


class CallbackTests(unittest.TestCase):
    def flow(self,receiver):
        flow=DesktopAuthorization('synthetic-client','synthetic-secret','synthetic-principal',
            receiver.redirect_uri,picker_folder_ids=FOLDERS)
        receiver.flow=flow
        return flow

    def fields(self,flow):
        return dict(state=flow.state,code='synthetic-code',scope=SCOPE,picked_file_ids=','.join(FOLDERS))

    def test_picker_url_preserves_pkce_scope_and_exact_folder_filter(self):
        with CallbackReceiver(timeout=1) as receiver:
            flow=self.flow(receiver); q=parse_qs(urlsplit(flow.authorization_url()).query)
            self.assertEqual(q['scope'],[SCOPE]); self.assertEqual(q['code_challenge_method'],['S256'])
            for name in ('trigger_onepick','allow_multiple','allow_folder_selection'): self.assertEqual(q[name],['true'])
            self.assertEqual(q['prompt'],['consent']); self.assertEqual(q['file_ids'],[','.join(FOLDERS)])
            self.assertEqual(q['mimetypes'],['application/vnd.google-apps.folder'])

    def test_callback_once_duplicate_rejected_no_reflection_or_access_log(self):
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err),CallbackReceiver(timeout=1) as receiver:
            flow=self.flow(receiver); fields=self.fields(flow)
            self.assertEqual(submit(receiver,fields),(200,'no-store'))
            original=receiver.wait()
            self.assertEqual(submit(receiver,fields)[0],409)
            self.assertEqual(receiver.wait(),original)
        self.assertEqual(out.getvalue()+err.getvalue(),'')

    def test_state_cancel_selection_duplicate_query_and_malformed_callbacks_fail(self):
        changes=[{'state':'wrong'},{'picked_file_ids':'wrong,ids'},{'picked_file_ids':FOLDERS[0]},
            {'picked_file_ids':FOLDERS[0]+','+FOLDERS[0]},{'picked_file_ids':''},
            {'scope':'unapproved-scope'},{'code':''},{'error':'access_denied'}]
        for change in changes:
            with self.subTest(change=tuple(change)),CallbackReceiver(timeout=1) as receiver:
                flow=self.flow(receiver); fields=dict(self.fields(flow),**change)
                self.assertEqual(submit(receiver,fields)[0],400)
                with self.assertRaises(SetupError): receiver.wait()
        for bad in ('duplicate','path','host','post'):
            with self.subTest(bad=bad),CallbackReceiver(timeout=1) as receiver:
                flow=self.flow(receiver); fields=self.fields(flow)
                kwargs={}
                if bad=='duplicate': kwargs['target']=receiver.path+'?'+urlencode(fields)+'&state='+flow.state
                if bad=='path': kwargs['target']='/unapproved?'+urlencode(fields)
                if bad=='host': kwargs['host']='unapproved.invalid'
                if bad=='post': kwargs['method']='POST'
                self.assertEqual(submit(receiver,fields,**kwargs)[0],400)
                with self.assertRaises(SetupError): receiver.wait()

    def test_timeout_does_not_return_a_callback(self):
        with CallbackReceiver(timeout=0.05) as receiver:
            self.flow(receiver)
            with self.assertRaises(SetupError): receiver.wait()


@unittest.skipUnless(os.name=='nt','Windows DPAPI required')
class SetupTests(unittest.TestCase):
    def setUp(self):
        self.parent=Path(tempfile.gettempdir())/('eolm-s3-setup-'+uuid.uuid4().hex)
        WindowsProtection().create_directory(self.parent)
        self.root=Path(tempfile.gettempdir())/('eolm-s1-sync-'+uuid.uuid4().hex)
        self.root.mkdir()
        self.directory=self.parent/'store'
        self.path=self.directory/'pc-b.json'
        self.config=dict(version=1,mode='isolated_drive',machine_id='PC-B',principal='synthetic-principal',
            client_id='synthetic-client',scope=SCOPE,folders=dict(zip(('BattleLog','ErrorReport'),FOLDERS)),
            store_directory=str(self.directory),fixture_root=str(self.root),
            upload_names=dict(BattleLog=[],ErrorReport=[]),required_visible=dict(BattleLog=[],ErrorReport=[]),
            principal_verified=False,environment_verified=False,allow_refresh=False,execution_approved=False)

    def tearDown(self):
        for path in (self.parent,self.root):
            assert path.parent==Path(tempfile.gettempdir()) and path.name.startswith(('eolm-s3-setup-','eolm-s1-sync-'))
            assert not path.is_symlink()
            shutil.rmtree(path)

    def prepare(self):
        self.assertEqual(prepare_configuration(self.config,self.path),dict(status='prepared',ready=False))

    def browser(self,url):
        q=parse_qs(urlsplit(url).query); redirect=urlsplit(q['redirect_uri'][0])
        connection=http.client.HTTPConnection('127.0.0.1',redirect.port,timeout=3)
        fields=dict(state=q['state'][0],code='synthetic-code',scope=SCOPE,picked_file_ids=q['file_ids'][0])
        try:
            connection.request('GET',redirect.path+'?'+urlencode(fields))
            response=connection.getresponse(); response.read(); self.assertEqual(response.status,200)
        finally: connection.close()
        return True

    def test_prepare_and_validate_both_roles_without_credentials_or_network(self):
        self.prepare()
        self.assertEqual(validate_configuration_file(self.path),self.config)
        self.assertFalse((self.directory/'credential.bin').exists())
        with self.assertRaises(SetupError): validate_configuration_file(self.path,ready=True)
        ready=dict(self.config,machine_id='PC-A',principal_verified=True,environment_verified=True,execution_approved=True)
        target=self.directory/'pc-a-ready.json'
        prepare_configuration(ready,target)
        self.assertEqual(validate_configuration_file(target,ready=True),ready)

    def test_unknown_settings_role_scope_bad_acl_and_existing_target_stop(self):
        for changes in ({'machine_id':'unknown'},{'scope':'wrong'},{'extra':True},{'allow_refresh':1}):
            with self.assertRaises(SetupError): prepare_configuration(dict(self.config,**changes),self.path)
        self.assertFalse(self.directory.exists())
        bad=dict(self.config,store_directory=str(self.root))
        with self.assertRaises(SetupError): prepare_configuration(bad,self.root/'bad-acl.json')
        self.prepare(); before=self.path.read_bytes()
        with self.assertRaises(SetupError): prepare_configuration(self.config,self.path)
        self.assertEqual(self.path.read_bytes(),before)
        for name in ('CON.json','plan:stream.json'):
            with self.assertRaises(SetupError): prepare_configuration(self.config,self.directory/name)

    def test_enrollment_callback_exchange_and_dpapi_initial_save(self):
        self.prepare(); http=TokenHttp(); out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            result=enroll(self.path,'synthetic-client-secret',execute=True,principal_verified=True,
                http=http,browser_open=self.browser)
        self.assertEqual(result,dict(status='enrolled',google_identity_verified=False,drive_visibility_verified=False))
        self.assertEqual(len(http.calls),1); self.assertEqual(http.calls[0]['code'],['synthetic-code'])
        self.assertTrue(http.closed)
        encrypted=(self.directory/'credential.bin').read_bytes()
        self.assertNotIn(b'synthetic-access-token',encrypted)
        self.assertEqual(CredentialStore(self.directory).load()['access_token'],'synthetic-access-token')
        self.assertEqual(out.getvalue()+err.getvalue(),'')

    def test_existing_credential_never_read_or_overwritten_and_no_browser(self):
        self.prepare(); store=CredentialStore(self.directory)
        with store.transaction(): store.save({'synthetic-old':'preserve'},initial=True)
        before=(self.directory/'credential.bin').read_bytes(); http=TokenHttp()
        with patch.object(CredentialStore,'load',side_effect=AssertionError('must not read old')):
            with self.assertRaises(SetupError): enroll(self.path,'synthetic-secret',execute=True,principal_verified=True,
                http=http,browser_open=lambda *_:self.fail('must not launch'))
        self.assertEqual((self.directory/'credential.bin').read_bytes(),before); self.assertEqual(http.calls,[])

    def test_token_failure_or_save_failure_keeps_configuration_and_no_credential(self):
        self.prepare(); before=self.path.read_bytes()
        with self.assertRaises(SetupError): enroll(self.path,'synthetic-secret',execute=True,principal_verified=True,
            http=TokenHttp(fail=True),browser_open=self.browser)
        with patch.object(CredentialStore,'save',side_effect=OSError('synthetic-secret')):
            with self.assertRaises(SetupError): enroll(self.path,'synthetic-secret',execute=True,principal_verified=True,
                http=TokenHttp(),browser_open=self.browser)
        self.assertFalse((self.directory/'credential.bin').exists()); self.assertEqual(self.path.read_bytes(),before)

    def test_declined_post_callback_principal_confirmation_never_exchanges(self):
        self.prepare(); http=TokenHttp()
        with self.assertRaises(SetupError): enroll(self.path,'synthetic-secret',execute=True,principal_verified=True,
            http=http,browser_open=self.browser,confirm_principal=lambda:False)
        self.assertEqual(http.calls,[]); self.assertFalse((self.directory/'credential.bin').exists())

    def test_bad_selection_or_timeout_never_exchanges_code(self):
        self.prepare(); http=TokenHttp()
        def bad_browser(url):
            q=parse_qs(urlsplit(url).query); address=urlsplit(q['redirect_uri'][0])
            conn=http.client.HTTPConnection('127.0.0.1',address.port,timeout=3)
            try:
                conn.request('GET',address.path+'?'+urlencode(dict(state=q['state'][0],code='synthetic-code',picked_file_ids='wrong')))
                response=conn.getresponse(); response.read(); self.assertEqual(response.status,400)
            finally: conn.close()
            return True
        with self.assertRaises(SetupError): enroll(self.path,'synthetic-secret',execute=True,principal_verified=True,
            http=http,browser_open=bad_browser)
        with self.assertRaises(SetupError): enroll(self.path,'synthetic-secret',execute=True,principal_verified=True,
            http=http,browser_open=lambda *_:True,receiver_factory=lambda:CallbackReceiver(timeout=0.05))
        self.assertEqual(http.calls,[]); self.assertFalse((self.directory/'credential.bin').exists())

    def test_cli_masked_prepare_and_enroll_requires_explicit_switches(self):
        out=io.StringIO()
        with patch('Common.DriveSetup.getpass.getpass',side_effect=[str(self.path),json.dumps(self.config)]),redirect_stdout(out):
            self.assertEqual(main(['prepare']),0)
        self.assertEqual(json.loads(out.getvalue()),dict(status='prepared',ready=False))
        out=io.StringIO()
        with patch('Common.DriveSetup.getpass.getpass',side_effect=AssertionError('must not prompt')),redirect_stdout(out):
            self.assertEqual(main(['enroll']),1)
        self.assertEqual(json.loads(out.getvalue()),dict(status='held',reason='drive_setup_unconfirmed'))

    def test_cli_rejects_echo_fallback_and_unknown_arguments_without_secret_output(self):
        def no_echo(prompt):
            warnings.warn('no echo available',getpass.GetPassWarning)
            self.fail('must not read echoed input')
        for args in (['prepare'],['enroll','--token','synthetic-secret']):
            out,err=io.StringIO(),io.StringIO()
            with patch('Common.DriveSetup.getpass.getpass',side_effect=no_echo),redirect_stdout(out),redirect_stderr(err):
                self.assertEqual(main(args),1)
            self.assertNotIn('synthetic-secret',out.getvalue()+err.getvalue())
            self.assertEqual(err.getvalue(),'')
