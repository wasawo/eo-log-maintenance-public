"""Synthetic acceptance tests for the isolated owned-run lock primitive."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from Common.OwnedRunLock import LockAcquisitionError, _NamedMutex, acquire_owned_lock
from Common import OwnedRunLock as owned


class FakeMutex:
    def __init__(self, name, *, acquired=True, abandoned=False):
        self.name = name
        self._acquired = acquired
        self.abandoned = abandoned
        self.released = False
        self.closed = False
        self.timeout = None

    def acquire(self, timeout_seconds):
        self.timeout = timeout_seconds
        return self._acquired

    def release(self):
        self.released = True

    def close(self):
        self.closed = True


class NamedMutexCloseTests(unittest.TestCase):
    def test_success_clears_handle_and_second_close_is_noop(self):
        for result in (1, 7):  # Win32 BOOL accepts any nonzero success value.
            with self.subTest(result=result):
                mutex = _NamedMutex.__new__(_NamedMutex)
                mutex._handle = 123
                mutex._kernel32 = Mock()
                mutex._kernel32.CloseHandle.return_value = result
                mutex.close()
                self.assertIsNone(mutex._handle)
                mutex.close()
                mutex._kernel32.CloseHandle.assert_called_once_with(123)

    def test_failure_preserves_handle_and_does_not_retry(self):
        mutex = _NamedMutex.__new__(_NamedMutex)
        mutex._handle = 123
        mutex._kernel32 = Mock()
        mutex._kernel32.CloseHandle.return_value = 0
        with self.assertRaises(LockAcquisitionError) as caught:
            mutex.close()
        self.assertEqual("named_mutex_close_failed", caught.exception.reason_code)
        self.assertEqual("named_mutex_close_failed", str(caught.exception))
        self.assertEqual(123, mutex._handle)
        mutex._kernel32.CloseHandle.assert_called_once_with(123)
        self.assertEqual(1, len(mutex._kernel32.method_calls))


class OwnedRunLockTests(unittest.TestCase):
    def test_nonbool_wait_results_cannot_create_records_or_enter_body(self):
        class UnexpectedTruth:
            def __bool__(self): raise AssertionError("must not coerce adapter result")
        for result in (None, 0, 1, "true", [], UnexpectedTruth()):
            with self.subTest(result_type=type(result).__name__), patch.object(owned, "_strict_record_bytes") as payload:
                with self.assertRaisesRegex(LockAcquisitionError, "^named_mutex_wait_failed$"):
                    with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(acquired=result),
                            token_factory=lambda: "a"*64):
                        self.fail("must not enter")
                payload.assert_not_called()
            self.assertFalse(self.path.exists())
            self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_wait_exceptions_are_sanitized_and_uncertain_ownership_is_released(self):
        for error in (OSError("synthetic private detail"), RuntimeError("synthetic private detail")):
            mutex = FakeMutex("synthetic")
            with self.subTest(error_type=type(error).__name__), patch.object(mutex, "acquire", side_effect=error):
                with self.assertRaises(LockAcquisitionError) as caught:
                    with acquire_owned_lock("PC-A", self.path, mutex_factory=lambda name: mutex,
                            token_factory=lambda: "a"*64):
                        self.fail("must not enter")
            self.assertEqual("named_mutex_wait_failed", str(caught.exception))
            self.assertIsNone(caught.exception.__cause__)
            self.assertFalse(self.path.exists())
            self.assertTrue(mutex.released and mutex.closed)

    def test_interrupted_wait_still_releases_and_closes_without_record_io(self):
        mutex = FakeMutex("synthetic")
        with patch.object(mutex, "acquire", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            with acquire_owned_lock("PC-A", self.path, mutex_factory=lambda name: mutex,
                    token_factory=lambda: "a"*64):
                self.fail("must not enter")
        self.assertFalse(self.path.exists())
        self.assertTrue(mutex.released and mutex.closed)

    def test_abandoned_observation_requires_exact_bool_before_record_creation(self):
        for value in (None, 0, 1, "false", []):
            with self.subTest(value_type=type(value).__name__), patch.object(owned, "_strict_record_bytes") as payload:
                with self.assertRaisesRegex(LockAcquisitionError, "^named_mutex_observation_invalid$"):
                    with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(abandoned=value),
                            token_factory=lambda: "a"*64):
                        self.fail("must not enter")
                payload.assert_not_called()
            self.assertFalse(self.path.exists())
            self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_missing_or_failed_abandoned_observation_is_not_defaulted_to_false(self):
        class FailedObservation(FakeMutex):
            def __getattribute__(self, name):
                if name == "abandoned": raise OSError("synthetic private detail")
                return super().__getattribute__(name)
        missing = FakeMutex("synthetic")
        del missing.abandoned
        for mutex in (missing, FailedObservation("synthetic")):
            with self.subTest(adapter_type=type(mutex).__name__), self.assertRaisesRegex(
                    LockAcquisitionError, "^named_mutex_observation_invalid$"):
                with acquire_owned_lock("PC-A", self.path, mutex_factory=lambda name: mutex,
                        token_factory=lambda: "a"*64):
                    self.fail("must not enter")
            self.assertFalse(self.path.exists())
            self.assertTrue(mutex.released and mutex.closed)

    def test_invalid_write_counts_preserve_even_parseable_records_and_primary_reason(self):
        real_open = Path.open
        for index, count in enumerate((None, False, True, -1, 0, "short", "long")):
            for close_failure in (False, True, "exists"):
                path = self.root / f"count-{index}-{close_failure}.lock"
                contents = []
                class Stream:
                    def __init__(self, stream): self.stream = stream
                    def __enter__(self): return self
                    def __exit__(self, *args):
                        self.stream.close()
                        if close_failure == "exists": raise FileExistsError("synthetic close failure")
                        if close_failure: raise OSError("synthetic close failure")
                    def write(self, payload):
                        raw = payload[:-1] if count == "short" else payload
                        contents.append(raw)
                        self.stream.write(raw)
                        return len(payload)-1 if count == "short" else len(payload)+1 if count == "long" else count
                    def flush(self): raise AssertionError("must stop before flush")
                    def fileno(self): raise AssertionError("must stop before fsync")
                def opened(target, mode="r", *args, **kwargs):
                    stream = real_open(target, mode, *args, **kwargs)
                    return Stream(stream) if target == path and mode == "xb" else stream
                with self.subTest(count=count, close_failure=close_failure), patch.object(Path, "open", opened), \
                        patch.object(owned, "_record_matches") as verify:
                    with self.assertRaisesRegex(LockAcquisitionError, "^lock_record_write_incomplete$"):
                        with acquire_owned_lock("PC-A", path, mutex_factory=self.factory(), token_factory=lambda: "a"*64):
                            self.fail("must not enter")
                    verify.assert_not_called()
                self.assertEqual(contents[0], path.read_bytes())
                self.assertIsInstance(json.loads(path.read_bytes()), dict)
                self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_creation_io_failures_preserve_written_record_and_never_attempt_cleanup(self):
        real_open, real_fsync = Path.open, owned.os.fsync
        for stage in ("write", "flush", "fsync", "close"):
            path = self.root / (stage + ".lock")
            contents = []
            class Stream:
                def __init__(self, stream): self.stream = stream
                def __enter__(self): return self
                def __exit__(self, *args):
                    self.stream.close()
                    if stage == "close": raise OSError("synthetic close failure")
                def write(self, payload):
                    contents.append(payload)
                    count = self.stream.write(payload)
                    if stage == "write": raise OSError("synthetic write failure")
                    return count
                def flush(self):
                    if stage == "flush": raise OSError("synthetic flush failure")
                    self.stream.flush()
                def fileno(self): return self.stream.fileno()
            def opened(target, mode="r", *args, **kwargs):
                stream = real_open(target, mode, *args, **kwargs)
                return Stream(stream) if target == path and mode == "xb" else stream
            def sync(fd):
                if stage == "fsync": raise OSError("synthetic fsync failure")
                return real_fsync(fd)
            with self.subTest(stage=stage), patch.object(Path, "open", opened), \
                    patch.object(owned.os, "fsync", sync), patch.object(owned, "_record_matches") as verify:
                with self.assertRaisesRegex(LockAcquisitionError, "^lock_record_create_failed$"):
                    with acquire_owned_lock("PC-A", path, mutex_factory=self.factory(), token_factory=lambda: "a"*64):
                        self.fail("must not enter")
                verify.assert_not_called()
            self.assertEqual(contents[0], path.read_bytes())
            self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_failed_initial_ownership_verification_is_not_retried_for_cleanup(self):
        with patch.object(owned, "_record_matches", side_effect=(False, True)) as verify:
            with self.assertRaisesRegex(LockAcquisitionError, "^lock_record_ownership_unverified$"):
                with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(), token_factory=lambda: "a"*64):
                    self.fail("must not enter")
            self.assertEqual(1, verify.call_count)
        self.assertEqual(owned._strict_record_bytes("PC-A", "a"*64), self.path.read_bytes())
        self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_record_byte_limit_exact_boundary_preserves_normal_ownership_cleanup(self):
        token = "a" * 64
        limit = len(owned._strict_record_bytes("PC-A", token))
        with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(),
                token_factory=lambda: token, maximum_record_bytes=limit):
            self.assertEqual(limit, self.path.stat().st_size)
        self.assertFalse(self.path.exists())
        self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_invalid_record_limits_reject_before_token_path_or_mutex(self):
        class UnpreparedPath:
            def __fspath__(self): raise AssertionError("must not prepare path")
        for value in (True, False, 0, -1, 1.0, "1"):
            factory, token = Mock(), Mock()
            with self.subTest(value=value), self.assertRaisesRegex(LockAcquisitionError, "^lock_record_limit_invalid$"):
                with acquire_owned_lock("PC-A", UnpreparedPath(), mutex_factory=factory,
                        token_factory=token, maximum_record_bytes=value):
                    self.fail("must not enter")
            factory.assert_not_called()
            token.assert_not_called()

    def test_creation_budget_excess_creates_no_record_and_releases_mutex(self):
        with patch.object(Path, "open") as opened:
            with self.assertRaisesRegex(LockAcquisitionError, "^lock_record_limit_exceeded$"):
                with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(),
                        token_factory=lambda: "a" * 64, maximum_record_bytes=1):
                    self.fail("must not enter")
            opened.assert_not_called()
        self.assertFalse(self.path.exists())
        self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_oversized_replacement_is_preserved_without_payload_read_on_release(self):
        token = "a" * 64
        limit = len(owned._strict_record_bytes("PC-A", token))
        changed = b"synthetic-untrusted" * limit
        with patch.object(owned, "_read_stable", wraps=owned._read_stable) as read:
            with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(),
                    token_factory=lambda: token, maximum_record_bytes=limit):
                self.assertEqual(1, read.call_count)
                self.path.write_bytes(changed)
            self.assertEqual(1, read.call_count)
        self.assertEqual(changed, self.path.read_bytes())
        self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_growth_between_path_and_handle_observations_never_yields_ownership(self):
        token = "a" * 64
        limit = len(owned._strict_record_bytes("PC-A", token))
        real_open = Path.open
        grown = False
        def grow(path, mode="r", *args, **kwargs):
            nonlocal grown
            if path == self.path and mode == "rb" and not grown:
                with open(path, "ab") as stream: stream.write(b"x" * 4096)
                grown = True
            return real_open(path, mode, *args, **kwargs)
        with patch.object(Path, "open", grow), self.assertRaisesRegex(LockAcquisitionError,
                "^lock_record_ownership_unverified$"):
            with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(),
                    token_factory=lambda: token, maximum_record_bytes=limit):
                self.fail("must not enter")
        self.assertEqual(limit + 4096, self.path.stat().st_size)
        self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_deep_json_on_release_is_preserved_and_cannot_skip_mutex_release(self):
        changed = b"[" * 2000 + b"0" + b"]" * 2000
        with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(), token_factory=lambda: "a" * 64):
            self.path.write_bytes(changed)
        self.assertEqual(changed, self.path.read_bytes())
        self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_unavailable_stable_observation_preserves_record_and_releases_mutex(self):
        with patch.object(owned, "_read_stable", side_effect=owned.ArtifactSetDirectoryVerificationError("artifact_changed")):
            with self.assertRaisesRegex(LockAcquisitionError, "^lock_record_ownership_unverified$"):
                with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(), token_factory=lambda: "a" * 64):
                    self.fail("must not enter")
        self.assertTrue(self.path.exists())
        self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def test_bounded_read_does_not_impose_canonical_json_spelling(self):
        with acquire_owned_lock("PC-A", self.path, mutex_factory=self.factory(),
                token_factory=lambda: "a" * 64, maximum_record_bytes=4096):
            record = json.loads(self.path.read_bytes())
            self.path.write_bytes(json.dumps(record, indent=2).encode("utf-8"))
        self.assertFalse(self.path.exists())
        self.assertTrue(self.mutexes[-1].released and self.mutexes[-1].closed)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "run.lock"
        self.mutexes = []

    def factory(self, **kwargs):
        def create(name):
            mutex = FakeMutex(name, **kwargs)
            self.mutexes.append(mutex)
            return mutex
        return create

    def test_acquires_exclusive_record_and_cleans_own_record(self):
        with acquire_owned_lock(
            "PC-A", self.path, mutex_factory=self.factory(),
            token_factory=lambda: "a" * 64,
        ) as token:
            self.assertEqual(token, "a" * 64)
            record = json.loads(self.path.read_text(encoding="utf-8"))
            self.assertEqual(record["scope_id"], "PC-A")
            self.assertEqual(record["owner_token"], token)
            self.assertEqual(record["schema_version"], 1)
        self.assertFalse(self.path.exists())
        self.assertTrue(self.mutexes[0].released)
        self.assertTrue(self.mutexes[0].closed)

    def test_concurrent_or_unavailable_mutex_times_out_before_record_write(self):
        with self.assertRaisesRegex(LockAcquisitionError, "lock_timeout"):
            with acquire_owned_lock(
                "PC-A", self.path, mutex_factory=self.factory(acquired=False),
                token_factory=lambda: "b" * 64,
            ):
                self.fail("must not enter critical section")
        self.assertFalse(self.path.exists())
        self.assertTrue(self.mutexes[0].closed)
        self.assertFalse(self.mutexes[0].released)

    def test_existing_record_is_never_overwritten_or_removed(self):
        original = b'{"owner_token":"other","schema_version":1}\n'
        self.path.write_bytes(original)
        with self.assertRaisesRegex(LockAcquisitionError, "lock_record_already_exists"):
            with acquire_owned_lock(
                "PC-A", self.path, mutex_factory=self.factory(),
                token_factory=lambda: "c" * 64,
            ):
                self.fail("must not enter critical section")
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(self.mutexes[0].released)

    def test_abandoned_mutex_fails_closed_and_preserves_record(self):
        original = b'not-json'
        self.path.write_bytes(original)
        with self.assertRaisesRegex(LockAcquisitionError, "abandoned_mutex_requires_recovery"):
            with acquire_owned_lock(
                "PC-A", self.path, mutex_factory=self.factory(abandoned=True),
                token_factory=lambda: "d" * 64,
            ):
                self.fail("must not enter critical section")
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(self.mutexes[0].released)

    def test_token_record_is_removed_only_if_still_owned(self):
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with acquire_owned_lock(
                "PC-A", self.path, mutex_factory=self.factory(),
                token_factory=lambda: "e" * 64,
            ):
                self.path.write_text(
                    json.dumps({
                        "schema_version": 1, "scope_id": "PC-A",
                        "owner_token": "f" * 64, "pid": 1, "host": "fixture",
                    }),
                    encoding="utf-8",
                )
                raise RuntimeError("synthetic")
        self.assertTrue(self.path.exists())
        self.assertEqual(json.loads(self.path.read_text())["owner_token"], "f" * 64)
        self.assertTrue(self.mutexes[0].released)

    def test_invalid_scope_rejected_before_mutex_creation(self):
        with self.assertRaisesRegex(LockAcquisitionError, "scope_id_invalid"):
            with acquire_owned_lock("../PC-A", self.path, mutex_factory=self.factory()):
                self.fail("must not enter critical section")
        self.assertEqual(self.mutexes, [])

    def test_timeout_above_sixty_seconds_rejected(self):
        with self.assertRaisesRegex(LockAcquisitionError, "timeout_out_of_range"):
            with acquire_owned_lock("PC-A", self.path, 60.1, mutex_factory=self.factory()):
                self.fail("must not enter critical section")
        self.assertEqual(self.mutexes, [])

    def test_invalid_timeout_never_prepares_path_token_or_mutex(self):
        for timeout, reason in (
            (float("nan"), "timeout_invalid"),
            (float("inf"), "timeout_out_of_range"),
            (float("-inf"), "timeout_out_of_range"),
            (10 ** 1000, "timeout_out_of_range"),
            (-1, "timeout_out_of_range"),
            (True, "timeout_invalid"),
            ("60", "timeout_invalid"),
        ):
            with self.subTest(reason=reason, timeout_type=type(timeout).__name__):
                path_calls = []

                class UnpreparedPath:
                    def __fspath__(self):
                        path_calls.append("path_conversion")
                        raise AssertionError("path_must_not_be_prepared")

                factory = Mock(side_effect=AssertionError("mutex_must_not_be_created"))
                token_factory = Mock(side_effect=AssertionError("token_must_not_be_created"))
                with self.assertRaises(LockAcquisitionError) as caught:
                    with acquire_owned_lock(
                        "PC-A", UnpreparedPath(), timeout, mutex_factory=factory,
                        token_factory=token_factory,
                    ):
                        self.fail("must not enter critical section")
                self.assertEqual(reason, caught.exception.reason_code)
                self.assertEqual(reason, str(caught.exception))
                self.assertEqual([], path_calls)
                factory.assert_not_called()
                token_factory.assert_not_called()

    def test_finite_timeout_boundaries_reach_mutex_and_release_owned_record(self):
        for timeout in (0, 0.25, 60):
            with self.subTest(timeout=timeout):
                with acquire_owned_lock(
                    "PC-A", self.path, timeout, mutex_factory=self.factory(),
                    token_factory=lambda: "a" * 64,
                ):
                    self.assertTrue(self.path.is_file())
                    self.assertEqual(timeout, self.mutexes[-1].timeout)
                self.assertFalse(self.path.exists())
                self.assertTrue(self.mutexes[-1].released)
                self.assertTrue(self.mutexes[-1].closed)

    def test_token_factory_output_must_be_unpredictable_length(self):
        with self.assertRaisesRegex(LockAcquisitionError, "owner_token_invalid"):
            with acquire_owned_lock(
                "PC-A", self.path, mutex_factory=self.factory(),
                token_factory=lambda: "short",
            ):
                self.fail("must not enter critical section")
        self.assertEqual(self.mutexes, [])

    def test_scope_is_part_of_mutex_name(self):
        first = self.factory()
        with acquire_owned_lock("PC-A", self.path, mutex_factory=first,
                                token_factory=lambda: "1" * 64):
            pass
        other_path = self.root / "other.lock"
        second = self.factory()
        with acquire_owned_lock("PC-B", other_path, mutex_factory=second,
                                token_factory=lambda: "2" * 64):
            pass
        self.assertNotEqual(self.mutexes[0].name, self.mutexes[1].name)

    def test_lock_record_write_failure_leaves_unverified_partial_record(self):
        # A pre-existing directory at the record path causes exclusive create to fail.
        self.path.mkdir()
        with self.assertRaisesRegex(LockAcquisitionError, "lock_record_already_exists"):
            with acquire_owned_lock(
                "PC-A", self.path, mutex_factory=self.factory(),
                token_factory=lambda: "3" * 64,
            ):
                self.fail("must not enter critical section")
        self.assertTrue(self.path.is_dir())
        self.assertTrue(self.mutexes[0].released)


    def test_duplicate_record_keys_preserved_on_release(self):
        with acquire_owned_lock(
            "PC-A", self.path, mutex_factory=self.factory(),
            token_factory=lambda: "a" * 64,
        ):
            raw = self.path.read_bytes()
            altered = raw.replace(b'{', b'{"owner_token":"other",', 1)
            self.path.write_bytes(altered)
        self.assertTrue(self.path.exists(), "ambiguous_record_must_be_preserved")
        self.assertEqual(self.path.read_bytes(), altered)
        self.assertTrue(self.mutexes[0].released)
        self.assertTrue(self.mutexes[0].closed)

    def test_invalid_record_types_preserved_on_release(self):
        for field, value in (("schema_version", True), ("pid", True), ("pid", 0), ("pid", -1),
                             ("host", ""), ("owner_token", "\u975eASCII")):
            with self.subTest(field=field, value=value):
                path = self.root / (field + str(value) + ".lock")
                with acquire_owned_lock(
                    "PC-A", path, mutex_factory=self.factory(),
                    token_factory=lambda: "a" * 64,
                ):
                    record = json.loads(path.read_text(encoding="utf-8"))
                    record[field] = value
                    altered = json.dumps(record).encode("utf-8")
                    path.write_bytes(altered)
                self.assertTrue(path.exists(), "malformed_record_must_be_preserved")
                self.assertEqual(path.read_bytes(), altered)
                self.assertTrue(self.mutexes[-1].released)
                self.assertTrue(self.mutexes[-1].closed)


if __name__ == "__main__":
    unittest.main()
