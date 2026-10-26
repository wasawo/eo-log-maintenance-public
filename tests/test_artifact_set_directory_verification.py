"""Synthetic filesystem tests for read-only artifact-set directory verification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from Common import ArtifactSetDirectoryVerification as verification

from Common.ArtifactSetDirectoryVerification import (
    ArtifactSetDirectoryVerificationError,
    verify_published_artifact_set,
)


class ArtifactSetDirectoryVerificationTests(unittest.TestCase):
    def test_present_marker_with_nonobject_json_never_becomes_missing_marker(self):
        self.write_complete_set()
        path = self.root/"commit-marker.json"
        for content in (b"null", b"true", b"false", b"0", b"1.5", b'"synthetic"', b"[]", b"[{}]"):
            path.write_bytes(content)
            before = {p: p.read_bytes() for p in self.root.iterdir()}
            with self.subTest(content=content), self.assertRaisesRegex(
                    ArtifactSetDirectoryVerificationError, "^commit_marker_json_invalid$"):
                verify_published_artifact_set(self.root, self.expected)
            self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_nonstandard_json_constants_are_rejected_at_any_marker_depth(self):
        self.write_complete_set()
        path = self.root/"commit-marker.json"
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            for content in (constant, b'{"schema_version":'+constant+b'}',
                    b'{"nested":[{"value":'+constant+b'}]}'):
                path.write_bytes(content)
                with self.subTest(content=content), self.assertRaisesRegex(
                        ArtifactSetDirectoryVerificationError, "^commit_marker_json_invalid$"):
                    verify_published_artifact_set(self.root, self.expected)
                self.assertEqual(content, path.read_bytes())

    def test_nested_duplicate_marker_keys_are_rejected(self):
        self.write_complete_set()
        path = self.root/"commit-marker.json"
        marker = path.read_bytes()
        key = b'"manifest.json":'
        digest = json.dumps(self.expected["manifest.json"]).encode("ascii")
        marker = marker.replace(key, key+digest+b", "+key)
        path.write_bytes(marker)
        with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^commit_marker_json_invalid$"):
            verify_published_artifact_set(self.root, self.expected)
        self.assertEqual(marker, path.read_bytes())

    def test_excessive_marker_nesting_is_a_sanitized_parse_failure(self):
        self.write_complete_set()
        content = b'{"nested":'+b"["*2048+b"0"+b"]"*2048+b"}"
        path = self.root/"commit-marker.json"
        path.write_bytes(content)
        with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^commit_marker_json_invalid$"):
            verify_published_artifact_set(self.root, self.expected)
        self.assertEqual(content, path.read_bytes())

    def test_expected_transaction_is_independently_bound_and_optional(self):
        self.write_complete_set()
        self.assertTrue(verify_published_artifact_set(self.root, self.expected,
            expected_transaction_id=self.transaction_id).may_report_committed)
        result = verify_published_artifact_set(self.root, self.expected,
            expected_transaction_id="123e4567-e89b-42d3-a456-426614174001")
        self.assertEqual("commit_marker_transaction_id_mismatch", result.reason_code)
        self.assertFalse(result.may_report_committed)
        self.assertTrue(verify_published_artifact_set(self.root, self.expected).may_report_committed)

    def test_all_observed_files_are_rechecked_after_classification(self):
        for name in ("manifest.json", "report.json", "commit-marker.json"):
            with self.subTest(name=name):
                self.write_complete_set()
                real = verification.classify_artifact_set
                def changed(**kwargs):
                    decision = real(**kwargs)
                    if kwargs.get("commit_marker") is not None:
                        path = self.root / name
                        path.write_bytes(path.read_bytes() + b"\n")
                    return decision
                with patch.object(verification, "classify_artifact_set", side_effect=changed):
                    with self.assertRaises(ArtifactSetDirectoryVerificationError):
                        verify_published_artifact_set(self.root, self.expected)

    def test_directory_addition_after_classification_is_rejected(self):
        self.write_complete_set()
        real = verification.classify_artifact_set
        def changed(**kwargs):
            result = real(**kwargs)
            if kwargs.get("commit_marker") is not None:
                (self.root / "unexpected.tmp").write_bytes(b"synthetic")
            return result
        with patch.object(verification, "classify_artifact_set", side_effect=changed):
            with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "unexpected_directory_entry"):
                verify_published_artifact_set(self.root, self.expected)

    def test_opened_handle_identity_and_mid_read_changes_are_rejected(self):
        self.write_complete_set()
        real = os.fstat
        def wrong_handle(fd):
            info = real(fd)
            values = {name: getattr(info, name) for name in
                ("st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")}
            values["st_ino"] += 1
            return SimpleNamespace(**values)
        with patch.object(verification.os, "fstat", side_effect=wrong_handle):
            with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "artifact_changed"):
                verify_published_artifact_set(self.root, self.expected)
        calls = 0
        def mid_read(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                for path in self.root.iterdir(): path.write_bytes(path.read_bytes() + b"\n")
            return real(fd)
        with patch.object(verification.os, "fstat", side_effect=mid_read):
            with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "artifact_changed"):
                verify_published_artifact_set(self.root, self.expected)

    def test_expected_hashes_are_copied_before_observing_the_directory(self):
        self.write_complete_set()
        original = dict(self.expected)
        real = verification._read_stable
        def changed(*args):
            self.expected.clear()
            return real(*args)
        with patch.object(verification, "_read_stable", side_effect=changed):
            self.assertTrue(verify_published_artifact_set(self.root, self.expected).may_report_committed)
        self.assertEqual({}, self.expected)
        self.assertEqual(original, json.loads((self.root / "commit-marker.json").read_bytes())["artifact_sha256"])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payloads = {
            "manifest.json": b'{"status":"success"}\n',
            "report.json": b'{"items":2}\n',
        }
        self.transaction_id = "123e4567-e89b-42d3-a456-426614174000"
        self.expected = {
            name: hashlib.sha256(data).hexdigest()
            for name, data in self.payloads.items()
        }

    def write_complete_set(self):
        for name, data in self.payloads.items():
            (self.root / name).write_bytes(data)
        marker = {
            "schema_version": 1,
            "transaction_id": self.transaction_id,
            "artifact_sha256": self.expected,
        }
        (self.root / "commit-marker.json").write_text(
            json.dumps(marker, sort_keys=True), encoding="utf-8"
        )

    def test_reads_actual_bytes_and_validates_marker(self):
        self.write_complete_set()
        result = verify_published_artifact_set(self.root, self.expected)
        self.assertEqual(result.state, "committed")
        self.assertTrue(result.may_report_committed)
        self.assertFalse(result.requires_reconciliation)

    def test_missing_marker_never_reports_committed_and_preserves_files(self):
        for name, data in self.payloads.items():
            (self.root / name).write_bytes(data)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = verify_published_artifact_set(self.root, self.expected)
        self.assertEqual(result.state, "marker_missing")
        self.assertFalse(result.may_report_committed)
        self.assertTrue(result.requires_reconciliation)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_partial_set_never_reports_committed(self):
        (self.root / "manifest.json").write_bytes(self.payloads["manifest.json"])
        result = verify_published_artifact_set(self.root, self.expected)
        self.assertEqual(result.state, "partial_publication")
        self.assertFalse(result.may_report_committed)
        self.assertTrue(result.preserve_existing_artifacts)

    def test_tampered_artifact_is_blocked_without_mutation(self):
        self.write_complete_set()
        (self.root / "report.json").write_bytes(b"tampered")
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = verify_published_artifact_set(self.root, self.expected)
        self.assertEqual(result.state, "blocked")
        self.assertEqual(result.reason_code, "published_artifact_digest_mismatch")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_duplicate_marker_json_keys_fail_closed(self):
        for name, data in self.payloads.items():
            (self.root / name).write_bytes(data)
        marker = json.dumps({
            "schema_version": 1,
            "transaction_id": self.transaction_id,
            "artifact_sha256": self.expected,
        })
        marker = marker.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
        (self.root / "commit-marker.json").write_text(marker, encoding="utf-8")
        with self.assertRaisesRegex(
            ArtifactSetDirectoryVerificationError, "commit_marker_json_invalid"
        ):
            verify_published_artifact_set(self.root, self.expected)

    def test_unexpected_entry_and_symlink_fail_closed(self):
        self.write_complete_set()
        (self.root / "unexpected.tmp").write_bytes(b"leftover")
        with self.assertRaisesRegex(
            ArtifactSetDirectoryVerificationError, "unexpected_directory_entry"
        ):
            verify_published_artifact_set(self.root, self.expected)
        (self.root / "unexpected.tmp").unlink()

        (self.root / "manifest.json").unlink()
        link = self.root / "manifest.json"
        try:
            link.symlink_to(self.root / "report.json")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable on this test host")
        with self.assertRaisesRegex(
            ArtifactSetDirectoryVerificationError, "non_regular_artifact"
        ):
            verify_published_artifact_set(self.root, self.expected)

    def test_non_directory_and_invalid_marker_name_fail_closed(self):
        file_path = self.root / "not-a-directory"
        file_path.write_bytes(b"x")
        with self.assertRaisesRegex(
            ArtifactSetDirectoryVerificationError, "directory_unavailable"
        ):
            verify_published_artifact_set(file_path, self.expected)
        with self.assertRaisesRegex(
            ArtifactSetDirectoryVerificationError, "commit_marker_name_invalid"
        ):
            verify_published_artifact_set(self.root, self.expected, commit_marker_name="../marker.json")

    def test_empty_directory_does_not_claim_success(self):
        result = verify_published_artifact_set(self.root, self.expected)
        self.assertEqual(result.state, "nothing_published")
        self.assertFalse(result.may_report_committed)


class ArtifactSetInputPreflightTests(unittest.TestCase):
    setUp = ArtifactSetDirectoryVerificationTests.setUp
    write_complete_set = ArtifactSetDirectoryVerificationTests.write_complete_set

    def test_invalid_hash_maps_block_before_root_io(self):
        digest = "a"*64
        for expected in ({"../escape": digest}, {"/absolute": digest}, {"dir/file": digest},
                {"dir\\file": digest}, {".hidden": digest}, {"bad\x00name": digest},
                {1: digest}, {"manifest.json": "bad"}, {"manifest.json": "A"*64},
                {"manifest.json": None}):
            with self.subTest(expected=expected), patch.object(Path, "is_symlink") as inspected:
                result = verify_published_artifact_set(self.root, expected)
                self.assertEqual("blocked", result.state)
                self.assertEqual("expected_artifact_set_invalid", result.reason_code)
                self.assertFalse(result.may_report_committed)
                self.assertFalse(result.may_publish_next)
                self.assertTrue(result.preserve_existing_artifacts)
                inspected.assert_not_called()

    def test_invalid_transaction_blocks_before_root_io(self):
        for transaction in ("", "bad", True, 1, [], "11111111-2222-0333-8444-555555555555"):
            with self.subTest(transaction=transaction), patch.object(Path, "is_symlink") as inspected:
                result = verify_published_artifact_set(self.root, self.expected, expected_transaction_id=transaction)
                self.assertEqual("expected_transaction_id_invalid", result.reason_code)
                self.assertFalse(result.may_report_committed)
                inspected.assert_not_called()

    def test_invalid_container_empty_and_marker_collision_raise_before_root_io(self):
        for expected in (None, [], {}, {"commit-marker.json": "a"*64}):
            with self.subTest(expected=expected), patch.object(Path, "is_symlink") as inspected:
                with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^expected_artifact_set_invalid$"):
                    verify_published_artifact_set(self.root, expected)
                inspected.assert_not_called()

    def test_mapping_copy_failure_is_sanitized_before_root_io(self):
        from collections.abc import Mapping
        class BrokenMap(Mapping):
            def __iter__(self): raise RuntimeError("synthetic private mapping detail")
            def __len__(self): return 1
            def __getitem__(self, key): raise RuntimeError("synthetic private mapping detail")
        with patch.object(Path, "is_symlink") as inspected:
            with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^expected_artifact_set_invalid$"):
                verify_published_artifact_set(self.root, BrokenMap())
            inspected.assert_not_called()

    def test_expectations_are_copied_before_the_first_root_inspection(self):
        self.write_complete_set()
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        real = Path.is_symlink
        def inspected(path):
            if path == self.root:
                self.expected.clear()
            return real(path)
        with patch.object(Path, "is_symlink", inspected):
            result = verify_published_artifact_set(self.root, self.expected,
                expected_transaction_id=self.transaction_id)
        self.assertTrue(result.may_report_committed)
        self.assertEqual({}, self.expected)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})


class ArtifactSetReadBoundsTests(unittest.TestCase):
    setUp = ArtifactSetDirectoryVerificationTests.setUp
    write_complete_set = ArtifactSetDirectoryVerificationTests.write_complete_set

    def verify(self, **limits):
        return verify_published_artifact_set(self.root, self.expected, **limits)

    def test_exact_file_and_set_limits_preserve_classification_and_bytes(self):
        self.write_complete_set()
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        limits = dict(maximum_artifact_bytes=max(map(len, before.values())),
            maximum_total_bytes=sum(map(len, before.values())))
        self.assertEqual(self.verify(), self.verify(**limits))
        self.assertTrue(self.verify(**limits).may_report_committed)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_invalid_limits_reject_before_filesystem_access(self):
        for key in ("maximum_artifact_bytes", "maximum_total_bytes"):
            for value in (True, False, 0, -1, 1.5, "4096"):
                with self.subTest(key=key, value=value), patch.object(Path, "is_symlink") as inspected:
                    with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^artifact_read_limit_invalid$"):
                        self.verify(**{key: value})
                    inspected.assert_not_called()

    def test_each_oversized_file_including_marker_blocks_all_payload_opens(self):
        self.write_complete_set()
        paths = list(self.root.iterdir())
        ceiling = max(path.stat().st_size for path in paths)
        for path in paths:
            original = path.read_bytes()
            path.write_bytes(original+b" "*(ceiling+1-len(original)))
            with self.subTest(name=path.name), patch.object(Path, "open") as opened:
                with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^artifact_read_limit_exceeded$"):
                    self.verify(maximum_artifact_bytes=ceiling)
                opened.assert_not_called()
            self.assertEqual(ceiling+1, path.stat().st_size)
            path.write_bytes(original)

    def test_total_includes_marker_and_rejects_before_any_payload_open(self):
        self.write_complete_set()
        total = sum(p.stat().st_size for p in self.root.iterdir())
        with patch.object(Path, "open") as opened:
            with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^artifact_total_limit_exceeded$"):
                self.verify(maximum_total_bytes=total-1)
            opened.assert_not_called()

    def test_incomplete_sets_and_empty_directory_do_not_bypass_limits_or_classification(self):
        self.assertFalse(self.verify(maximum_artifact_bytes=1, maximum_total_bytes=1).may_report_committed)
        path = self.root/"manifest.json"
        path.write_bytes(self.payloads[path.name])
        self.assertEqual("partial_publication", self.verify(maximum_total_bytes=path.stat().st_size).state)
        with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^artifact_total_limit_exceeded$"):
            self.verify(maximum_total_bytes=path.stat().st_size-1)

    def test_reads_are_chunked_and_growth_stops_at_initial_size_plus_one(self):
        path = self.root/"manifest.json"
        payload = b"x"*70000
        path.write_bytes(payload)
        self.expected = {path.name: hashlib.sha256(payload).hexdigest()}
        real_open = Path.open
        for grow in (False, True):
            requests, consumed = [], []
            class Stream:
                def __init__(self, stream): self.stream = stream
                def __enter__(self): return self
                def __exit__(self, *args): self.stream.close()
                def fileno(self): return self.stream.fileno()
                def read(self, size):
                    requests.append(size)
                    block = self.stream.read(size)
                    consumed.append(len(block))
                    if grow and len(requests) == 1:
                        with real_open(path, "ab") as writer: writer.write(b"y"*70000)
                    return block
            def opened(target, *args, **kwargs): return Stream(real_open(target, *args, **kwargs))
            with self.subTest(grow=grow), patch.object(Path, "open", opened):
                if grow:
                    with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^artifact_changed$"):
                        self.verify(maximum_artifact_bytes=70000, maximum_total_bytes=70000)
                    self.assertEqual(70001, sum(consumed))
                else:
                    self.assertFalse(self.verify().may_report_committed)
                    self.assertEqual(140000, sum(consumed))  # Initial and final read.
            self.assertTrue(all(0 < size <= 65536 for size in requests))


if __name__ == "__main__":
    unittest.main()
