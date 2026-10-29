"""Test-only runner composition: synthetic DPAPI store -> SDK -> offline HTTP."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Common.DriveAuthentication import create_service
from Common.IsolatedDriveRunner import execute
from test_drive_authentication import Http

try:
    request = json.loads(sys.stdin.read(8 * 1024 * 1024))
    def factory(config, store):
        return create_service(config, store, http=Http(request['root'],request['kind']))
    result = execute(request, service_factory=factory)
    print(json.dumps(dict(ok=True,result=result)))
except Exception:
    print(json.dumps(dict(ok=False,result={})))
    raise SystemExit(1)
