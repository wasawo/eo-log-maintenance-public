"""Synthetic child-process boundary probe; NOT an official Dry Run entry point.

The dispatcher below is fixture code. Audit hooks observe the selected Python
operations, not arbitrary native code or a production security sandbox.
"""
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile


class EffectDenied(Exception):
    pass


def fixture_root(value):
    root = Path(value)
    if not root.is_absolute() or not root.name.startswith("eo-dryrun-fixture-"):
        raise ValueError("invalid_fixture")
    for path in (root, *root.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("invalid_fixture")
    if (root / ".synthetic-fixture").read_bytes() != b"dry-run-boundary-v1":
        raise ValueError("invalid_fixture")
    return root


def run_probe(root, scenario):
    events = []
    normal_calls = []

    def audit(event, args):
        denied = event in {
            "os.remove", "os.rmdir", "os.rename", "os.mkdir", "os.chmod",
            "os.chown", "os.link", "os.symlink", "os.truncate", "os.utime",
            "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn",
        } or event.startswith("socket.")
        if event == "open":
            mode, flags = args[1], args[2]
            denied = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and bool(flags & (
                    os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
                ))
            )
        if denied:
            events.append(event)  # Names only: never paths, payloads or exception text.
            raise EffectDenied()

    sys.addaudithook(audit)
    target = root / "sentinel"

    def normal():
        normal_calls.append("normal_initialization")
        target.write_bytes(b"must not execute")

    def dependency():
        actions = {
            "write": lambda: target.write_bytes(b"changed"),
            "create": lambda: (root / "new").write_bytes(b"new"),
            "os_open": lambda: os.close(os.open(target, os.O_WRONLY)),
            "delete": lambda: target.unlink(),
            "rename": lambda: target.rename(root / "renamed"),
            "mkdir": lambda: (root / "newdir").mkdir(),
            "chmod": lambda: target.chmod(0o600),
            "temp": lambda: tempfile.mkstemp(dir=root),
            "network": lambda: socket.socket(),
            "subprocess": lambda: subprocess.run([sys.executable, "-V"], check=True),
        }
        if scenario == "read":
            if target.read_bytes() != b"preserve":
                raise ValueError("invalid_fixture")
        else:
            actions[scenario]()

    def dispatch():
        # Synthetic injections; these are NOT trusted host/root qualifications.
        if scenario == "normal_control":
            normal()  # Instrumentation control, deliberately not the Dry Run path.
            return "invalid_control"
        if scenario == "normal":
            return "mode_rejected"
        if scenario == "pc_b_archive":
            return "role_rejected"
        if scenario in ("invalid_config", "invalid_root", "writer_busy", "abandoned"):
            return "gate_rejected"
        if scenario == "unqualified":
            return "qualification_pending"
        # Only this explicitly synthetic callback may execute. No normal fallback.
        dependency()
        return "observed"

    try:
        status = dispatch()
    except EffectDenied:
        status = "effect_rejected"
    except Exception:
        status = "probe_failed"
    return dict(status=status, denied_events=events, normal_calls=normal_calls,
                may_start_run=False, may_archive=False)


if __name__ == "__main__":
    try:
        if len(sys.argv) != 4 or sys.argv[1] != "--synthetic-fixture":
            raise ValueError("invalid_fixture")
        root = fixture_root(sys.argv[2])
        result = run_probe(root, sys.argv[3])
    except Exception:
        result = dict(status="invalid_fixture", may_start_run=False, may_archive=False)
    print(json.dumps(result, separators=(",", ":")))
