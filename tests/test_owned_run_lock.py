"""Synthetic acceptance tests for the isolated owned-run lock primitive."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from Common.OwnedRunLock import LockAcquisitionError, acquire_owned_lock


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


class OwnedRunLockTests(unittest.TestCase):
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
