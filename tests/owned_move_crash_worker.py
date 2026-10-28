"""TEST ONLY: create own fixture and exit at a fixed native operation boundary."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from owned_windows_move_probe import OwnedDisposableMoveDeleteProbe


def main():
    if len(sys.argv)!=2 or sys.argv[1] not in ('before_delete','after_delete'):
        return 1
    probe=OwnedDisposableMoveDeleteProbe()
    try:
        def checkpoint(phase):
            if phase==sys.argv[1]:
                # Private pipe to the parent test; never a public artifact.
                print(json.dumps(dict(root=str(probe._root),nonce=probe._nonce.decode('ascii'))),flush=True)
                if sys.stdin.readline(32)!='exit\n':
                    raise RuntimeError('synthetic_request_invalid')
                os._exit(91)
        probe.run_owned(at_checkpoint=checkpoint)
        return 1
    finally:
        probe.close()


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps(dict(error='synthetic_worker_failed')),flush=True)
        raise SystemExit(1)
