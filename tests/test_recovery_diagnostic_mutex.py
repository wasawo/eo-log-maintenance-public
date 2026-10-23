"""Record-free mutex lifetime, including actual Windows abandonment."""
from dataclasses import FrozenInstanceError
import multiprocessing
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common.OwnedRunLock import _NamedMutex, _mutex_name
from Common.RecoveryDiagnosticMutex import acquire_diagnostic_mutex, DiagnosticMutexError
from crash_publication_harness import create_disposable_root, disposable_parent, _receive, _stop


class FakeMutex:
    def __init__(self, *, result=True, abandoned=False, wait_error=False, release_error=False, close_error=False):
        self.result, self.abandoned = result, abandoned
        self.wait_error, self.release_error, self.close_error = wait_error, release_error, close_error
        self.calls = []

    def acquire(self, timeout):
        self.calls.append(("acquire", timeout))
        if self.wait_error:
            raise OSError("synthetic_private_detail")
        return self.result

    def release(self):
        self.calls.append("release")
        if self.release_error:
            raise OSError("synthetic_private_detail")

    def close(self):
        self.calls.append("close")
        if self.close_error:
            raise OSError("synthetic_private_detail")


class DiagnosticMutexTests(unittest.TestCase):
    def lease(self, mutex, **kwargs):
        return acquire_diagnostic_mutex("synthetic-scope", mutex_factory=lambda name: mutex, **kwargs)

    def test_lease_no_file_io_token_or_change_permission(self):
        mutex = FakeMutex()
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")):
            with self.lease(mutex) as observation:
                self.assertFalse(observation.abandoned)
                self.assertFalse(observation.may_change_state)
                with self.assertRaises(FrozenInstanceError):
                    observation.abandoned = True
        self.assertEqual(mutex.calls, [("acquire", 0.0), "release", "close"])

    def test_abandonment_is_reported_without_adoption(self):
        mutex = FakeMutex(abandoned=True)
        with self.lease(mutex) as observation:
            self.assertTrue(observation.abandoned)
            self.assertFalse(observation.may_change_state)
        self.assertEqual(mutex.calls[-2:], ["release", "close"])

    def test_timeout_does_not_enter_or_release_nonowned_mutex(self):
        mutex = FakeMutex(result=False)
        with self.assertRaisesRegex(DiagnosticMutexError, "diagnostic_mutex_timeout"):
            with self.lease(mutex):
                self.fail("must_not_enter")
        self.assertEqual(mutex.calls, [("acquire", 0.0), "close"])

    def test_wait_error_attempts_safe_release_and_close(self):
        mutex = FakeMutex(wait_error=True)
        with self.assertRaisesRegex(DiagnosticMutexError, "diagnostic_mutex_wait_failed"):
            with self.lease(mutex):
                self.fail("must_not_enter")
        self.assertEqual(mutex.calls[-2:], ["release", "close"])

    def test_body_failure_still_releases_and_closes(self):
        mutex = FakeMutex()
        with self.assertRaisesRegex(ValueError, "synthetic_body_failure"):
            with self.lease(mutex):
                raise ValueError("synthetic_body_failure")
        self.assertEqual(mutex.calls[-2:], ["release", "close"])

    def test_release_or_close_error_is_fixed_failure(self):
        for changes in ({"release_error": True}, {"close_error": True}):
            mutex = FakeMutex(**changes)
            with self.assertRaisesRegex(DiagnosticMutexError, "diagnostic_mutex_cleanup_failed"):
                with self.lease(mutex):
                    pass
            self.assertEqual(mutex.calls[-1], "close")

    def test_invalid_timeout_rejected_before_creation(self):
        for timeout in (-1, 61, True, float("nan"), float("inf"), "60", 10 ** 1000):
            with patch("Common.RecoveryDiagnosticMutex._NamedMutex") as factory:
                with self.assertRaisesRegex(DiagnosticMutexError, "diagnostic_timeout_invalid"):
                    with acquire_diagnostic_mutex("synthetic-scope", timeout_seconds=timeout):
                        self.fail("must_not_enter")
                factory.assert_not_called()

    def test_invalid_scope_rejected_before_creation(self):
        with patch("Common.RecoveryDiagnosticMutex._NamedMutex") as factory:
            with self.assertRaisesRegex(DiagnosticMutexError, "diagnostic_scope_invalid"):
                with acquire_diagnostic_mutex("synthetic/private"):
                    self.fail("must_not_enter")
            factory.assert_not_called()

    def test_interrupted_acquire_still_attempts_release_and_close(self):
        mutex = FakeMutex()
        with patch.object(mutex, "acquire", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                with self.lease(mutex):
                    self.fail("must_not_enter")
        self.assertEqual(mutex.calls, ["release", "close"])

    def test_same_global_namespace_as_normal_ownership(self):
        names = []
        def factory(name):
            names.append(name)
            return FakeMutex()
        with acquire_diagnostic_mutex("synthetic-scope", timeout_seconds=60, mutex_factory=factory):
            pass
        self.assertEqual(names, [_mutex_name("synthetic-scope")])

    def test_factory_failure_sanitized(self):
        def fail(name):
            raise OSError("synthetic_private_detail")
        with self.assertRaisesRegex(DiagnosticMutexError, "diagnostic_mutex_create_failed"):
            with acquire_diagnostic_mutex("synthetic-scope", mutex_factory=fail):
                self.fail("must_not_enter")


def _probe(scope, connection):
    try:
        with acquire_diagnostic_mutex(scope):
            connection.send(("acquired",))
    except Exception:
        connection.send(("blocked",))
    finally:
        connection.close()


def _owner(scope, connection):
    try:
        mutex = _NamedMutex(_mutex_name(scope))
        if not mutex.acquire(0):
            connection.send(("error",))
            return
        connection.send(("owned",))
        connection.recv()
    finally:
        connection.close()


@unittest.skipUnless(os.name == "nt", "real Windows named mutex required")
class ActualDiagnosticMutexTests(unittest.TestCase):
    def setUp(self):
        self.root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
        create_disposable_root(self.root, acknowledged=True)
        self.addCleanup(self.cleanup)
        self.scope = "synthetic-" + uuid4().hex
        self.record = self.root / "synthetic.lock"
        self.record.write_bytes(b"synthetic_prior_record_unchanged")
        keeper = _NamedMutex(_mutex_name(self.scope))
        self.addCleanup(keeper.close)
        context = multiprocessing.get_context("spawn")
        self.channel, child = context.Pipe()
        self.process = context.Process(target=_owner, args=(self.scope, child))
        self.process.start()
        child.close()
        self.addCleanup(self.channel.close)
        self.addCleanup(_stop, self.process)
        self.assertEqual(_receive(self.channel), ("owned",))

    def cleanup(self):
        assert self.root.parent == disposable_parent()
        assert not self.root.is_symlink()
        shutil.rmtree(self.root)

    def test_live_contender_never_enters_and_preserves_record(self):
        before = self.record.read_bytes()
        with self.assertRaisesRegex(DiagnosticMutexError, "diagnostic_mutex_timeout"):
            with acquire_diagnostic_mutex(self.scope):
                self.fail("must_not_enter")
        self.assertEqual(self.record.read_bytes(), before)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_abandonment_consumption_second_diagnosis_and_body_failure(self):
        before = self.record.read_bytes()
        _stop(self.process)
        self.assertNotEqual(self.process.exitcode, 0)
        with acquire_diagnostic_mutex(self.scope) as first:
            self.assertTrue(first.abandoned)
            self.assertFalse(first.may_change_state)
        with self.assertRaisesRegex(ValueError, "synthetic_body_failure"):
            with acquire_diagnostic_mutex(self.scope) as second:
                self.assertFalse(second.abandoned)
                self.assertFalse(second.may_change_state)
                raise ValueError("synthetic_body_failure")
        # Prove release using a different process; same-thread recursive
        # reacquisition alone would not prove that Win32 mutex was released.
        parent, child = multiprocessing.get_context("spawn").Pipe()
        probe = multiprocessing.get_context("spawn").Process(target=_probe, args=(self.scope, child))
        probe.start()
        child.close()
        self.addCleanup(parent.close)
        self.addCleanup(_stop, probe)
        self.assertEqual(_receive(parent), ("acquired",))
        probe.join(timeout=5)
        self.assertEqual(probe.exitcode, 0)
        # Separate process termination or body failure must not strand ownership.
        with acquire_diagnostic_mutex(self.scope) as third:
            self.assertFalse(third.abandoned)
        self.assertEqual(self.record.read_bytes(), before)
        self.assertEqual(len(list(self.root.iterdir())), 1)
