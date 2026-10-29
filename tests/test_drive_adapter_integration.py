"""Official entry -> real SDK -> isolated fake HTTP; never credentials/network."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import uuid

from googleapiclient.discovery import build
from Common.DriveTransferAdapter import sync_bytes, DriveTransferError
from drive_adapter_fixture_worker import FixtureHttp


REPO = Path(__file__).resolve().parents[1]
NAME = '20240101_12345678@synthetic.txt'


class DriveAdapterIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            if (root.parent.resolve() != Path(tempfile.gettempdir()).resolve() or root.is_symlink()
                    or re.fullmatch(r'eolm-s[12]-(?:sync|archive)-[a-f0-9]{32}', root.name) is None):
                raise AssertionError('unsafe fixture cleanup')
            shutil.rmtree(root)

    def fixture(self, route):
        prefix = 'eolm-s1-sync-' if route == 'Sync' else 'eolm-s2-archive-'
        root = Path(tempfile.gettempdir()) / (prefix + uuid.uuid4().hex)
        root.mkdir()
        self.roots.append(root)
        (root / '.synthetic-fixture').write_text('eolm-s1-synthetic-v1' if route == 'Sync' else 'eolm-s2-synthetic-v1')
        for side in ('source', 'mock-drive') if route == 'Sync' else ('mock-drive', 'archive'):
            for kind in ('BattleLog', 'ErrorReport'):
                (root / side / kind).mkdir(parents=True)
        return root

    def run_entry(self, root, route, fault='none', extra=()):
        python_options = [] if '-PythonExecutable' in extra else ['-PythonExecutable', os.sys.executable]
        command = [shutil.which('pwsh'), '-NoProfile', '-File', str(REPO / 'scripts' / (route + 'Logs.ps1')),
            '-Synthetic', '-SyntheticRoot', str(root), '-DriveApiMock', '-ApiFault', fault,
            '-ReferenceDate', '2026-10-29', *python_options, *extra]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertNotIn('synthetic-secret', result.stdout + result.stderr)
        self.assertNotIn(str(root), result.stdout)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout)
        self.assertEqual(report['AdapterMode'], 'sdk_http_mock')
        self.assertFalse(report['CloudObserved'])
        self.assertEqual(report['CompletedMoveCount'], 0)
        return result.returncode, report

    def test_sync_real_sdk_upload_hash_and_rerun_reuse_from_official_entry(self):
        root = self.fixture('Sync')
        source = root / 'source/BattleLog' / NAME
        source.write_bytes(b'synthetic upload')
        code, result = self.run_entry(root, 'Sync')
        self.assertEqual((code, result['SuccessCount']), (0, 1))
        self.assertEqual((root / 'mock-drive/BattleLog' / NAME).read_bytes(), source.read_bytes())
        self.assertEqual(result['Results'][0]['DestinationSha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        code, result = self.run_entry(root, 'Sync')
        self.assertEqual(code, 0)
        self.assertTrue(result['Results'][0]['Reused'])
        self.assertEqual(len(list((root / 'mock-drive/BattleLog').iterdir())), 1)

    def test_archive_real_sdk_list_download_hash_and_source_retention(self):
        root = self.fixture('Archive')
        source = root / 'mock-drive/BattleLog' / NAME
        source.write_bytes(b'synthetic download')
        (root / 'mock-drive/ErrorReport/20241231_12345678.txt').write_bytes(b'error report')
        (root / 'mock-drive/BattleLog/20260101_12345678@current.txt').write_bytes(b'retain current')
        code, result = self.run_entry(root, 'Archive')
        self.assertEqual((code, result['SuccessCount'], result['ExcludedCount']), (0, 2, 1))
        self.assertEqual((root / 'archive/BattleLog' / NAME).read_bytes(), source.read_bytes())
        self.assertEqual(source.read_bytes(), b'synthetic download')

    def test_auth_api_errors_duplicates_and_content_or_version_change_hold_sources(self):
        for route in ('Sync', 'Archive'):
            for fault in ('auth_denied', 'api_error', 'duplicate_name', 'content_changed', 'version_changed'):
                with self.subTest(route=route, fault=fault):
                    root = self.fixture(route)
                    side = 'source' if route == 'Sync' else 'mock-drive'
                    source = root / side / 'BattleLog' / NAME
                    source.write_bytes(b'keep original')
                    if fault == 'duplicate_name' and route == 'Sync':
                        (root / 'mock-drive/BattleLog' / NAME).write_bytes(b'keep original')
                    code, result = self.run_entry(root, route, fault)
                    self.assertEqual(code, 1)
                    self.assertEqual(result['SuccessCount'], 0)
                    self.assertGreater(result['HeldCount'], 0)
                    self.assertEqual(source.read_bytes(), b'keep original')

    def test_unknown_upload_response_is_not_retried_and_next_run_reuses_current_copy(self):
        root = self.fixture('Sync')
        source = root / 'source/BattleLog' / NAME
        source.write_bytes(b'unknown response synthetic')
        code, result = self.run_entry(root, 'Sync', 'upload_unknown')
        self.assertEqual((code, result['SuccessCount'], result['HeldCount']), (1, 0, 1))
        self.assertEqual(len(list((root / 'mock-drive/BattleLog').iterdir())), 1)
        code, result = self.run_entry(root, 'Sync')
        self.assertEqual(code, 0)
        self.assertTrue(result['Results'][0]['Reused'])
        self.assertEqual(source.read_bytes(), b'unknown response synthetic')

    def test_conflicts_never_overwrite_and_archive_role_denial_still_precedes_api(self):
        for route in ('Sync', 'Archive'):
            root = self.fixture(route)
            source_side, destination_side = ('source', 'mock-drive') if route == 'Sync' else ('mock-drive', 'archive')
            source = root / source_side / 'BattleLog' / NAME
            destination = root / destination_side / 'BattleLog' / NAME
            source.write_bytes(b'source content')
            destination.write_bytes(b'existing conflict')
            code, result = self.run_entry(root, route)
            self.assertEqual((code, result['HeldCount']), (1, 1))
            self.assertEqual(destination.read_bytes(), b'existing conflict')
            self.assertEqual(source.read_bytes(), b'source content')
        code, result = self.run_entry(root, 'Archive', 'auth_denied', ('-MachineId', 'PC-B'))
        self.assertEqual((code, result['Results'][0]['Reason']), (1, 'archive_role_denied'))

    def test_dry_run_does_not_start_python_or_use_authentication(self):
        for route in ('Sync', 'Archive'):
            root = self.fixture(route)
            source_side = 'source' if route == 'Sync' else 'mock-drive'
            (root / source_side / 'BattleLog' / NAME).write_bytes(b'dry run')
            code, result = self.run_entry(root, route, 'auth_denied',
                ('-DryRun', '-PythonExecutable', 'nonexistent-synthetic-python'))
            self.assertEqual((code, result['PlannedCount'], result['SuccessCount']), (0, 1, 0))

    def test_sdk_create_is_single_attempt_no_update_delete_or_raw_error_logging(self):
        root = self.fixture('Sync')
        http = FixtureHttp(root, 'BattleLog')
        service = build('drive', 'v3', http=http, static_discovery=True, cache_discovery=False)
        result = sync_bytes(service, folder_id=http.folder, filename=NAME, content=b'abc')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(http.calls.count('POST'), 1)
        self.assertTrue(set(http.calls) <= {'GET', 'POST'})
        http.fault = 'auth_denied'
        with self.assertNoLogs('googleapiclient.http', level='WARNING'):
            with self.assertRaisesRegex(DriveTransferError, '^drive_transfer_unconfirmed$'):
                sync_bytes(service, folder_id=http.folder, filename=NAME, content=b'abc')


if __name__ == '__main__':
    unittest.main()
