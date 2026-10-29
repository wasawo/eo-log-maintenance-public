"""Explicit S3 setup. Production operations require a separate user approval."""
import argparse
import getpass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import re
import threading
from urllib.parse import urlsplit
import webbrowser
import warnings

from Common.DriveAuthentication import DesktopAuthorization, SingleAttemptHttp, validate_record
from Common.DriveCredentialStore import CredentialStore, WindowsProtection
from Common.IsolatedDriveRunner import configuration, validate_configuration


class SetupError(ValueError):
    def __init__(self): super().__init__('drive_setup_unconfirmed')


class CallbackReceiver:
    """One-shot loopback receiver. Never logs request targets or credentials."""
    def __init__(self, *, timeout=120):
        if type(timeout) not in (int, float) or not 0 < timeout <= 120: raise SetupError()
        self.timeout = timeout
        self.path = '/oauth/' + secrets.token_urlsafe(24)
        self.event, self.lock = threading.Event(), threading.Lock()
        self.callback, self.failed, self.flow = None, False, None
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(2)

            def log_message(self, *args): pass

            def send_error(self, code, message=None, explain=None):
                self.close_connection=True
                self.send_response(400); self.send_header('Content-Length','0'); self.end_headers()

            def do_GET(self):
                with receiver.lock:
                    status = 400
                    if receiver.event.is_set():
                        status = 409
                    else:
                        try:
                            expected_host = '127.0.0.1:' + str(receiver.server.server_port)
                            if (self.client_address[0] != '127.0.0.1' or len(self.path) > 8192
                                    or self.headers.get_all('Host') != [expected_host]
                                    or self.headers.get('Origin') is not None
                                    or urlsplit(self.path).path != receiver.path
                                    or not self.path.startswith(receiver.path + '?') or receiver.flow is None):
                                raise SetupError()
                            callback = 'http://' + expected_host + self.path
                            receiver.flow.validate_callback(callback)
                            receiver.callback = callback
                            status = 200
                        except Exception:
                            receiver.failed = True
                        receiver.event.set()
                content = b'Setup response received. Close this window.'
                self.send_response(status)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Connection', 'close')
                self.end_headers()
                try: self.wfile.write(content)
                except OSError: pass

            def do_POST(self):
                with receiver.lock:
                    if not receiver.event.is_set(): receiver.failed = True; receiver.event.set()
                self.send_response(400); self.send_header('Content-Length','0'); self.end_headers()

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.server.handle_error = lambda *args: None
        self.redirect_uri = 'http://127.0.0.1:' + str(self.server.server_port) + self.path
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval':0.05}, daemon=True)

    def __enter__(self): self.thread.start(); return self

    def wait(self):
        if not self.event.wait(self.timeout) or self.failed or self.callback is None: raise SetupError()
        return self.callback

    def __exit__(self, *args):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3)


def request_for(config):
    root = Path(config['fixture_root'])
    return dict(root=str(root), machine_id=config['machine_id'],
        route='Archive' if root.name.startswith('eolm-s2-archive-') else 'Sync')


def prepare_configuration(config, output_path):
    """Create protected config once. No credential read, token or network."""
    try:
        validate_configuration(config, request_for(config), require_approval=False)
        directory = Path(config['store_directory'])
        target = Path(output_path)
        repo = Path(__file__).resolve().parents[1]
        if (not directory.is_absolute() or '..' in directory.parts or str(directory).startswith('\\\\')
                or ':' in str(directory)[2:] or directory == repo or repo in directory.parents
                or target.parent != directory or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}\.json',target.name) is None
                or target.name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
                or target.exists() or target.is_symlink()): raise SetupError()
        for parent in directory.parents:
            if parent.lstat().st_file_attributes & 0x400 or not parent.is_dir(): raise SetupError()
        store = CredentialStore(directory)
        if not directory.exists(): store.protection.create_directory(directory)
        store.validate()
        content = json.dumps(config, ensure_ascii=True, separators=(',',':')).encode()
        if len(content) > 16384: raise SetupError()
        with store.transaction():
            with store.protection.open_private(target, 1) as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            store.protection.validate_acl(target)
            with store.protection.open_private(target, 3) as stream:
                if stream.read(16385) != content: raise SetupError()
        configuration(target, request_for(config), require_approval=False)
        return dict(status='prepared', ready=all(config[k] for k in ('principal_verified','environment_verified','execution_approved')))
    except Exception: raise SetupError() from None


def validate_configuration_file(path, *, ready=False):
    """Protected supplied config only; never read credential.bin."""
    try:
        # Discover role/root only after ACL validation; then reuse full runner validation.
        path = Path(path)
        if not path.is_absolute() or '..' in path.parts: raise SetupError()
        repo = Path(__file__).resolve().parents[1]
        if path == repo or repo in path.parents: raise SetupError()
        for item in (path,*path.parents):
            if item.lstat().st_file_attributes & 0x400: raise SetupError()
        WindowsProtection().validate_acl(path)
        with path.open('rb') as stream: data=stream.read(16385)
        if len(data)>16384: raise SetupError()
        config=json.loads(data)
        confirmed=configuration(path, request_for(config), require_approval=ready)
        if confirmed != config: raise SetupError()
        CredentialStore(config['store_directory']).validate()
        return config
    except Exception: raise SetupError() from None


def enroll(path, client_secret, *, execute=False, principal_verified=False, http=None,
        browser_open=webbrowser.open, receiver_factory=CallbackReceiver, confirm_principal=None):
    """Single enrollment. Picker callback validates selection; no Drive API calls."""
    try:
        if execute is not True or principal_verified is not True or type(client_secret) is not str or not client_secret:
            raise SetupError()
        config=validate_configuration_file(path)
        store=CredentialStore(config['store_directory'])
        transport=http if http is not None else SingleAttemptHttp()
        try:
            with store.transaction():
                existing=store.directory/'credential.bin'
                if existing.exists() or existing.is_symlink(): raise SetupError()
                with receiver_factory() as receiver:
                    flow=DesktopAuthorization(config['client_id'],client_secret,config['principal'],receiver.redirect_uri,
                        picker_folder_ids=list(config['folders'].values()))
                    receiver.flow=flow
                    if not browser_open(flow.authorization_url()): raise SetupError()
                    callback=receiver.wait()
                    if confirm_principal is not None and confirm_principal() is not True: raise SetupError()
                    record=flow.exchange(callback,transport,principal_verified=True)
                    validate_record(record,config)
                    store.save(record,initial=True)
            return dict(status='enrolled', google_identity_verified=False, drive_visibility_verified=False)
        finally: transport.close()
    except Exception: raise SetupError() from None


def private_input(prompt):
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        return getpass.getpass(prompt)


def main(argv=None):
    class Parser(argparse.ArgumentParser):
        def error(self,message): raise SetupError()
    parser=Parser(description='Explicit isolated Drive setup; no default credential discovery.')
    parser.add_argument('action',choices=('prepare','validate','enroll'))
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--principal-verified',action='store_true')
    parser.add_argument('--ready',action='store_true')
    try:
        args=parser.parse_args(argv)
        if args.action=='enroll' and not (args.execute and args.principal_verified): raise SetupError()
        path=private_input('Private connection config path: ')
        if args.action=='prepare':
            raw=private_input('Connection plan JSON (no credentials): ')
            def unique(pairs):
                result={}
                for k,v in pairs:
                    if k in result: raise SetupError()
                    result[k]=v
                return result
            result=prepare_configuration(json.loads(raw,object_pairs_hook=unique),path)
        elif args.action=='validate':
            validate_configuration_file(path,ready=args.ready)
            result=dict(status='validated')
        else:
            secret=private_input('Approved Desktop client secret: ')
            result=enroll(path,secret,execute=args.execute,principal_verified=args.principal_verified,
                confirm_principal=lambda:private_input('Confirm the actual selected Google account; type CONFIRM: ')=='CONFIRM')
        print(json.dumps(result))
        return 0
    except (Exception,KeyboardInterrupt):
        print(json.dumps(dict(status='held',reason='drive_setup_unconfirmed')))
        return 1


if __name__=='__main__': raise SystemExit(main())
