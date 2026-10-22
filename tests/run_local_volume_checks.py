"""Explicit opt-in, partial local-volume evidence; never a production runner."""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crash_publication_harness import (
    HarnessError, disposable_parent, validate_disposable_parent,
)


def local_environment(expected_volume: str, pc_role: str) -> dict:
    if pc_role not in {"PC-A", "PC-B"}:
        raise HarnessError("pc_role_invalid")
    if not isinstance(expected_volume, str) or not re.fullmatch(r"[A-Za-z]:", expected_volume):
        raise HarnessError("expected_volume_invalid")
    if os.name != "nt":
        raise HarnessError("windows_volume_required")
    repository = Path(__file__).resolve().parents[1]
    if repository.anchor.casefold() != (expected_volume + "\\").casefold():
        raise HarnessError("repository_not_on_expected_volume")
    validate_disposable_parent(repository)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetVolumeInformationW.argtypes = [
        ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32), ctypes.c_wchar_p, ctypes.c_uint32,
    ]
    kernel.GetVolumeInformationW.restype = ctypes.c_int
    filesystem = ctypes.create_unicode_buffer(64)
    if not kernel.GetVolumeInformationW(
        repository.anchor, None, 0, None, None, None, filesystem, len(filesystem),
    ):
        raise HarnessError("filesystem_identity_unavailable")
    try:
        commit = subprocess.check_output(
            ["git", "-c", "safe.directory=" + str(repository),
             "-C", str(repository), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise HarnessError("source_commit_unavailable") from exc
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise HarnessError("source_commit_invalid")
    return {
        "pc_role": pc_role,
        "source_commit": commit,
        "os": "Windows",
        "os_version": platform.version(),
        "python_version": platform.python_version(),
        "filesystem": filesystem.value,
        "volume_category": "operator-confirmed-intended-local-fixed-volume",
        "root_category": "new-disposable-repository-child",
    }


def run_local_volume_checks(
    expected_volume: str, pc_role: str, *, acknowledged: bool = False,
) -> dict:
    if acknowledged is not True:
        raise HarnessError("disposable_acknowledgement_required")
    environment = local_environment(expected_volume, pc_role)
    old_mode = os.environ.get("EO_TEST_VOLUME_MODE")
    try:
        os.environ["EO_TEST_VOLUME_MODE"] = "repository-local"
        disposable_parent()
        suite = unittest.TestSuite()
        for module in ("test_crash_publication_harness", "test_owned_publication_integration"):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module))
        # Retain diagnostics in memory; never emit raw traces/paths/hostnames.
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        return {
            "schema_version": 1,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "environment": environment,
            "checks_passed": result.wasSuccessful() and not result.skipped,
            "tests_run": result.testsRun,
            "failure_count": len(result.failures),
            "error_count": len(result.errors),
            "skipped_count": len(result.skipped),
            "failed_test_ids": [test.id() for test, _ in result.failures + result.errors],
            "tier_b_acceptance": "incomplete",
            "remaining": [
                "PC-A intended-volume evidence",
                "complete adversarial reparse/read-failure filesystem matrix",
                "all required integration and source-race acceptance",
            ],
            "evidence_limit": "synthetic-process-crashes-not-power-loss-or-Drive",
        }
    finally:
        if old_mode is None:
            os.environ.pop("EO_TEST_VOLUME_MODE", None)
        else:
            os.environ["EO_TEST_VOLUME_MODE"] = old_mode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pc-role", choices=["PC-A", "PC-B"], required=True)
    parser.add_argument("--expected-volume", required=True)
    parser.add_argument("--acknowledge-disposable", action="store_true")
    args = parser.parse_args()
    try:
        result = run_local_volume_checks(
            args.expected_volume, args.pc_role,
            acknowledged=args.acknowledge_disposable,
        )
    except (HarnessError, OSError):
        print(json.dumps({"error": "local_volume_checks_rejected"}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
