"""Synthetic filesystem tests for read-only artifact-set directory verification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from Common.ArtifactSetDirectoryVerification import (
    ArtifactSetDirectoryVerificationError,
    verify_published_artifact_set,
)


class ArtifactSetDirectoryVerificationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
