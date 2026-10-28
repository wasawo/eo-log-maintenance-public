"""Read-only complete filesystem snapshots for both model routes."""
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common import SimulationFileSnapshot as snapshot
import test_artifact_directory_reparse as reparse


class SimulationFileSnapshotTests(unittest.TestCase):
    make_junction=reparse.ArtifactDirectoryReparseTests.make_junction

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='eolm-file-snapshot-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        roots=[]
        for side in ('source','destination'):
            for kind in ('BattleLog','ErrorReport'):
                path=self.root/(side+'-'+kind); path.mkdir()
                roots.append(dict(side=side,log_type=kind,path=str(path)))
        self.request=dict(protocol_version=1,simulation_only=True,request_id=str(uuid4()),machine_id='PC-A',route='local_to_cloud',
            roots=roots,excluded_roots=[str(self.root/name) for name in ('journal','journal.lifecycle','reports')])
        self.source=Path(roots[0]['path'])
        self.file=self.source/'nested'/'20240101_12345678@synthetic.txt'
        self.file.parent.mkdir(); self.file.write_bytes(b'synthetic contents')

    def test_both_routes_preserve_bytes_and_unchanged_file_identity(self):
        for route in ('local_to_cloud','cloud_to_archive'):
            self.request['route']=route
            first=snapshot.collect_snapshot(self.request)
            second=snapshot.collect_snapshot(self.request)
            self.assertEqual(first,second)
            self.assertEqual(first['file_count'],1)
            item=first['files'][0]
            self.assertEqual(item['location'],'PC-A' if route=='local_to_cloud' else 'Cloud')
            self.assertEqual(base64.b64decode(item['content_base64']),self.file.read_bytes())
            self.assertEqual(item['relative_path'],'nested/'+self.file.name)
        before=snapshot.collect_snapshot(self.request)['files'][0]['id']
        self.file.write_bytes(b'changed synthetic content')
        self.assertEqual(snapshot.collect_snapshot(self.request)['files'][0]['id'],before)
        replacement=self.file.parent/'replacement.txt'; replacement.write_bytes(self.file.read_bytes()); replacement.replace(self.file)
        self.assertNotEqual(snapshot.collect_snapshot(self.request)['files'][0]['id'],before)

    def test_empty_roots_are_complete_but_missing_root_is_not_empty_success(self):
        self.file.unlink(); self.file.parent.rmdir()
        self.assertEqual(snapshot.collect_snapshot(self.request)['files'],[])
        self.source.rmdir()
        with self.assertRaises(snapshot.SimulationSnapshotError): snapshot.collect_snapshot(self.request)

    def test_scan_or_read_failure_cannot_return_partial_files(self):
        real=snapshot._enumeration_snapshot
        def fail_later(directory,**kwargs):
            if directory==Path(self.request['roots'][1]['path']): raise PermissionError('private synthetic path')
            return real(directory,**kwargs)
        for target,behavior in (('_enumeration_snapshot',fail_later),('_read_stable',PermissionError('private synthetic path'))):
            with patch.object(snapshot,target,side_effect=behavior):
                with self.assertRaisesRegex(snapshot.SimulationSnapshotError,'^simulation_snapshot_unconfirmed$'):
                    snapshot.collect_snapshot(self.request)

    def test_mutation_in_earlier_root_during_later_read_is_rejected(self):
        later=Path(self.request['roots'][-1]['path'])/'20240101_12345678.txt'; later.write_bytes(b'later')
        real=snapshot._read_stable
        def read(path,*args):
            raw=real(path,*args)
            if path==later: self.file.write_bytes(b'new changed data')
            return raw
        with patch.object(snapshot,'_read_stable',side_effect=read):
            with self.assertRaises(snapshot.SimulationSnapshotError): snapshot.collect_snapshot(self.request)

    def test_limits_and_invalid_scope_roots_are_rejected(self):
        for constant,value in (('MAX_ENTRIES',1),('MAX_FILE_BYTES',1),('MAX_TOTAL_BYTES',1)):
            with patch.object(snapshot,constant,value):
                with self.assertRaises(snapshot.SimulationSnapshotError): snapshot.collect_snapshot(self.request)
        variants=[]
        for key,bad in (('protocol_version',True),('simulation_only',False),('request_id','private-invalid-run')):
            item=copy.deepcopy(self.request); item[key]=bad; variants.append(item)
        for side in ('duplicate','overlap','metadata','relative'):
            item=copy.deepcopy(self.request)
            if side=='duplicate': item['roots'][1]['log_type']='BattleLog'
            if side=='overlap': item['roots'][1]['path']=item['roots'][0]['path']
            if side=='metadata': item['excluded_roots'][0]=str(self.source)
            if side=='relative': item['roots'][0]['path']='relative'
            variants.append(item)
        item=copy.deepcopy(self.request); item['machine_id']='PC-B'; item['route']='cloud_to_archive'; variants.append(item)
        for item in variants:
            with self.assertRaises(snapshot.SimulationSnapshotError): snapshot.collect_snapshot(item)

    @unittest.skipUnless(os.name=='nt','Windows junction required')
    def test_junction_is_rejected_without_following_target(self):
        external=self.root/'external'; external.mkdir(); marker=external/'secret.txt'; marker.write_bytes(b'preserve')
        self.make_junction('source-BattleLog/alias',external)
        with self.assertRaises(snapshot.SimulationSnapshotError): snapshot.collect_snapshot(self.request)
        self.assertEqual(marker.read_bytes(),b'preserve')

    def test_cli_failure_is_sanitized_without_partial_payload(self):
        self.request['roots'][1]['path']=str(self.root/'missing-private-folder')
        process=subprocess.run([sys.executable,'-B','Common/SimulationFileSnapshot.py'],input=json.dumps(self.request),text=True,capture_output=True,timeout=20)
        self.assertEqual(process.returncode,1)
        self.assertEqual(json.loads(process.stdout),dict(ok=False,reason_code='simulation_snapshot_unconfirmed'))
        self.assertNotIn(str(self.root),process.stdout+process.stderr)
        self.assertNotIn('content_base64',process.stdout)


if __name__=='__main__': unittest.main()
