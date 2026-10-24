"""Executable fixture evidence only: no production dispatcher or Drive adapter."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


WORKER = Path(__file__).with_name("dry_run_boundary_harness.py")


def snapshot(root):
    return {
        str(path.relative_to(root)): (
            path.stat().st_mode,
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        )
        for path in root.rglob("*")
    }


class DryRunBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eo-dryrun-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".synthetic-fixture").write_bytes(b"dry-run-boundary-v1")
        (self.root / "sentinel").write_bytes(b"preserve")
        for name in ("manifest", "lock", "private", "budget", "scheduler", "config"):
            (self.root / name).write_bytes(b"synthetic-preserved")
        self.before = snapshot(self.root)

    def probe(self, scenario):
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(WORKER), "--synthetic-fixture",
             str(self.root), scenario], capture_output=True, timeout=20, check=True,
        )
        self.assertEqual(b"", completed.stderr)
        self.assertTrue(completed.stdout.endswith(b"\n"))
        result = json.loads(completed.stdout.decode("utf-8"))
        self.assertFalse(result["may_start_run"])
        self.assertFalse(result["may_archive"])
        self.assertNotIn(str(self.root), completed.stdout.decode())
        self.assertNotIn("synthetic_private_detail", completed.stdout.decode())
        self.assertEqual(self.before, snapshot(self.root))
        return result

    def test_readonly_observation_is_not_run_authority(self):
        result = self.probe("read")
        self.assertEqual("observed", result["status"])
        self.assertEqual([], result["denied_events"])
        self.assertEqual([], result["normal_calls"])

    def test_unqualified_root_never_observes_or_initializes(self):
        result = self.probe("unqualified")
        self.assertEqual("qualification_pending", result["status"])
        self.assertEqual([], result["normal_calls"])
        self.assertEqual([], result["denied_events"])

    def test_mode_role_and_failed_gates_never_reach_normal_initialization(self):
        for scenario, expected in (
            ("normal", "mode_rejected"), ("pc_b_archive", "role_rejected"),
            ("invalid_config", "gate_rejected"), ("invalid_root", "gate_rejected"),
            ("writer_busy", "gate_rejected"), ("abandoned", "gate_rejected"),
        ):
            with self.subTest(scenario=scenario):
                result = self.probe(scenario)
                self.assertEqual(expected, result["status"])
                self.assertEqual([], result["normal_calls"])
                self.assertEqual([], result["denied_events"])

    def test_dependency_effects_are_seen_and_blocked_before_mutation(self):
        for scenario, event in (
            ("write", "open"), ("create", "open"), ("os_open", "open"),
            ("delete", "os.remove"), ("rename", "os.rename"),
            ("mkdir", "os.mkdir"), ("chmod", "os.chmod"), ("temp", "open"),
            ("network", "socket.__new__"), ("subprocess", "subprocess.Popen"),
        ):
            with self.subTest(scenario=scenario):
                result = self.probe(scenario)
                self.assertEqual("effect_rejected", result["status"])
                self.assertEqual([event], result["denied_events"])
                self.assertEqual([], result["normal_calls"])

    def test_real_helper_refuses_unqualified_or_failed_mutex_paths(self):
        acquired = ["create", "acquire", "abandoned", "lease_body", "release", "close"]
        for scenario, status, calls in (
            ("mutex_acquired", "qualification_pending", acquired),
            ("mutex_abandoned", "mutex_abandoned_rejected", acquired),
            ("mutex_timeout", "diagnostic_mutex_timeout", ["create", "acquire", "close"]),
            ("mutex_create_error", "diagnostic_mutex_create_failed", ["create"]),
            ("mutex_acquire_error", "diagnostic_mutex_wait_failed",
             ["create", "acquire", "release", "close"]),
            ("mutex_observation_error", "diagnostic_mutex_observation_invalid",
             ["create", "acquire", "abandoned", "release", "close"]),
            ("mutex_release_error", "diagnostic_mutex_cleanup_failed", acquired),
            ("mutex_close_error", "diagnostic_mutex_cleanup_failed", acquired),
        ):
            with self.subTest(scenario=scenario):
                result = self.probe(scenario)
                self.assertEqual(status, result["status"])
                self.assertEqual(calls, result["mutex_calls"])
                self.assertEqual([], result["denied_events"])
                self.assert_mutex_boundary(result)

    def assert_mutex_boundary(self, result):
        self.assertEqual([], result["normal_calls"])
        self.assertEqual([], result["observation_calls"])
        self.assertEqual(["Common.RecoveryDiagnosticMutex", "Common.OwnedRunLock"],
                         result["helper_imports"])

    def test_real_helper_dependency_writes_are_audited_across_lifetime(self):
        acquired = ["create", "acquire", "abandoned", "lease_body", "release", "close"]
        for scenario, status, calls in (
            ("mutex_acquire_write", "diagnostic_mutex_wait_failed",
             ["create", "acquire", "release", "close"]),
            ("mutex_body_write", "effect_rejected", acquired),
            ("mutex_release_write", "diagnostic_mutex_cleanup_failed", acquired),
            ("mutex_close_write", "diagnostic_mutex_cleanup_failed", acquired),
        ):
            with self.subTest(scenario=scenario):
                result = self.probe(scenario)
                self.assertEqual(status, result["status"])
                self.assertEqual(calls, result["mutex_calls"])
                self.assertEqual(["open"], result["denied_events"])
                self.assert_mutex_boundary(result)

    def test_unknown_scenario_is_sanitized_and_preserves_state(self):
        result = self.probe("unknown-synthetic-token")
        self.assertEqual("probe_failed", result["status"])
        self.assertEqual([], result["normal_calls"])

    def test_control_reaches_normal_spy_and_is_still_denied(self):
        result = self.probe("normal_control")
        self.assertEqual("effect_rejected", result["status"])
        self.assertEqual(["normal_initialization"], result["normal_calls"])
        self.assertEqual(["open"], result["denied_events"])

    def test_unmarked_root_is_rejected(self):
        (self.root / ".synthetic-fixture").unlink()
        self.before = snapshot(self.root)
        result = self.probe("read")
        self.assertEqual("invalid_fixture", result["status"])
