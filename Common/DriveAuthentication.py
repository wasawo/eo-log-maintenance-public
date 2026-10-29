"""Explicit Desktop-user credential binding; single refresh, no consent/discovery."""
import json
import time
import math
import secrets
import hashlib
import base64
from email.parser import BytesParser
import email.policy
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler, Request
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, parse_qs

import httplib2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPE = 'https://www.googleapis.com/auth/drive.file'
TOKEN_URI = 'https://oauth2.googleapis.com/token'


class DriveAuthenticationError(ValueError):
    def __init__(self): super().__init__('drive_authentication_unconfirmed')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None


class SingleAttemptHttp:
    """SDK HTTP interface with no retry/redirect or environment proxy discovery."""
    def request(self, uri, method='GET', body=None, headers=None, **kwargs):
        try:
            data = body.encode() if type(body) is str else body
            request = Request(uri, data=data, headers=headers or {}, method=method)
            opener = build_opener(ProxyHandler({}), NoRedirect())
            try: response = opener.open(request, timeout=30)
            except HTTPError as error: response = error
            with response:
                raw = response.read(65537)
                if len(raw) > 65536: raise DriveAuthenticationError()
                metadata = dict(response.headers); metadata['status'] = str(response.code)
                return httplib2.Response(metadata), raw
        except Exception: raise DriveAuthenticationError() from None

    def close(self): pass


def validate_record(record, config):
    fields = {'version', 'principal', 'client_id', 'client_secret', 'scopes', 'access_token', 'refresh_token', 'expires_at'}
    if (type(record) is not dict or set(record) != fields or type(record['version']) is not int or record['version'] != 1
            or any(type(record[k]) is not str or not record[k] for k in fields - {'version', 'scopes', 'expires_at'})
            or record['scopes'] != [SCOPE] or type(record['expires_at']) not in (int, float)
            or not math.isfinite(record['expires_at'])
            or any(any(ord(c) < 32 for c in record[k]) for k in fields - {'version','scopes','expires_at'})
            or record['principal'] != config['principal'] or record['client_id'] != config['client_id']):
        raise DriveAuthenticationError()


def refresh_record(record, http, *, now=None):
    """One token request. Caller holds store lease and must persist before use."""
    try:
        body = urlencode(dict(grant_type='refresh_token', refresh_token=record['refresh_token'],
            client_id=record['client_id'], client_secret=record['client_secret']))
        response, content = http.request(TOKEN_URI, method='POST', body=body,
            headers={'content-type': 'application/x-www-form-urlencoded'})
        if response.status != 200 or len(content) > 65536: raise DriveAuthenticationError()
        result = json.loads(content)
        if (type(result) is not dict or type(result.get('access_token')) is not str or not result['access_token']
                or result.get('token_type', '').lower() != 'bearer'
                or type(result.get('expires_in')) is not int or not 300 < result['expires_in'] <= 86400
                or result.get('scope', SCOPE).split() != [SCOPE]): raise DriveAuthenticationError()
        updated = dict(record, access_token=result['access_token'],
            expires_at=(time.time() if now is None else now) + result['expires_in'])
        if 'refresh_token' in result:
            if type(result['refresh_token']) is not str or not result['refresh_token']: raise DriveAuthenticationError()
            updated['refresh_token'] = result['refresh_token']
        return updated
    except Exception: raise DriveAuthenticationError() from None


class BoundedBearerHttp:
    """No auto-refresh, retry, redirection, default credentials or extra APIs."""
    def __init__(self, http, credential, folders, *, now=time.time):
        self.http, self.credential, self.folders, self.now = http, credential, set(folders), now
        self.ids = set(folders)

    def request(self, uri, method='GET', body=None, headers=None, **kwargs):
        try:
            url = urlsplit(uri); query = parse_qs(url.query)
            if url.scheme != 'https' or url.hostname != 'www.googleapis.com' or url.port is not None:
                raise DriveAuthenticationError()
            if method == 'GET' and url.path == '/drive/v3/files':
                q = query.get('q', [''])[0]
                if not any(q == f"'{folder}' in parents and trashed = false" for folder in self.folders):
                    raise DriveAuthenticationError()
            elif method == 'GET' and url.path.startswith('/drive/v3/files/'):
                if url.path.rsplit('/', 1)[1] not in self.ids: raise DriveAuthenticationError()
            elif method == 'POST' and url.path == '/upload/drive/v3/files' and query.get('uploadType') == ['multipart']:
                content_type = {k.lower():v for k,v in (headers or {}).items()}['content-type']
                raw = body if type(body) is bytes else body.encode()
                message = BytesParser(policy=email.policy.default).parsebytes(
                    b'Content-Type: '+content_type.encode()+b'\r\n\r\n'+raw)
                parts = list(message.iter_parts())
                metadata = json.loads(parts[0].get_payload(decode=True))
                if (len(parts) != 2 or set(metadata) != {'name','parents'}
                        or metadata['parents'] not in [[folder] for folder in self.folders]
                        or len(parts[1].get_payload(decode=True)) > 4096): raise DriveAuthenticationError()
            else: raise DriveAuthenticationError()
            # No implicit refresh on expiry or 401, particularly after POST.
            if self.credential.expiry is None or self.credential.expired: raise DriveAuthenticationError()
            safe_headers = dict(headers or {})
            self.credential.apply(safe_headers)
            response, content = self.http.request(uri, method=method, body=body, headers=safe_headers, **kwargs)
            if 200 <= response.status < 300 and query.get('alt') != ['media']:
                data = json.loads(content)
                if type(data) is dict:
                    values = data.get('files', [data])
                    for item in values:
                        if type(item) is dict and type(item.get('id')) is str: self.ids.add(item['id'])
            return response, content
        except Exception: raise DriveAuthenticationError() from None

    def close(self):
        self.http.close()


class DesktopAuthorization:
    """PKCE/state-bound enrollment primitive. Does not open browser/listener."""
    def __init__(self, client_id, client_secret, principal, redirect_uri):
        url = urlsplit(redirect_uri)
        if (url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port
                or url.username or url.password or url.query or url.fragment): raise DriveAuthenticationError()
        self.client_id, self.client_secret, self.principal = client_id, client_secret, principal
        self.redirect_uri = redirect_uri
        self.state, self.verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        self.used = False

    def authorization_url(self):
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b'=').decode()
        return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(dict(client_id=self.client_id,
            redirect_uri=self.redirect_uri, response_type='code', scope=SCOPE, access_type='offline',
            state=self.state, code_challenge=challenge, code_challenge_method='S256', login_hint=self.principal))

    def exchange(self, callback, http, *, principal_verified=False):
        try:
            url = urlsplit(callback); expected = urlsplit(self.redirect_uri); query = parse_qs(url.query)
            if (self.used or principal_verified is not True or url._replace(query='') != expected
                    or not {'state','code'} <= set(query) or set(query) - {'state','code','scope','authuser','prompt'}
                    or ('scope' in query and query['scope'] != [SCOPE]) or query['state'] != [self.state]
                    or len(query['code']) != 1 or not query['code'][0]): raise DriveAuthenticationError()
            self.used = True  # Unknown response must not trigger a second code exchange.
            response, raw = http.request(TOKEN_URI, method='POST', headers={'content-type':'application/x-www-form-urlencoded'},
                body=urlencode(dict(grant_type='authorization_code',code=query['code'][0],code_verifier=self.verifier,
                    redirect_uri=self.redirect_uri,client_id=self.client_id,client_secret=self.client_secret)))
            if response.status != 200 or len(raw) > 65536: raise DriveAuthenticationError()
            value = json.loads(raw)
            if (value.get('scope','').split() != [SCOPE] or value.get('token_type','').lower() != 'bearer'
                    or type(value.get('expires_in')) is not int or not 300 < value['expires_in'] <= 86400):
                raise DriveAuthenticationError()
            record = dict(version=1,principal=self.principal,client_id=self.client_id,client_secret=self.client_secret,
                scopes=[SCOPE],access_token=value['access_token'],refresh_token=value['refresh_token'],
                expires_at=time.time()+value['expires_in'])
            validate_record(record, dict(principal=self.principal,client_id=self.client_id))
            return record
        except Exception: raise DriveAuthenticationError() from None


def create_service(config, store, *, http=None):
    from datetime import datetime, timezone
    try:
        if config['scope'] != SCOPE or not config['principal_verified']: raise DriveAuthenticationError()
        with store.transaction():
            record = store.load()
            validate_record(record, config)
            transport = http if http is not None else SingleAttemptHttp()
            transport.follow_redirects = False
            if record['expires_at'] <= time.time() + 300:
                if not config['allow_refresh']: raise DriveAuthenticationError()
                record = refresh_record(record, transport)
                validate_record(record, config)
                store.save(record)
            credential = Credentials(record['access_token'], scopes=[SCOPE],
                expiry=datetime.fromtimestamp(record['expires_at'], timezone.utc).replace(tzinfo=None))
            bounded = BoundedBearerHttp(transport, credential, config['folders'].values())
            return build('drive', 'v3', http=bounded, static_discovery=True, cache_discovery=False)
    except Exception: raise DriveAuthenticationError() from None
