"""Synthetic tests for multi-artifact publication/recovery classification."""
from __future__ import annotations

import unittest

from Common.ArtifactSetRecovery import classify_artifact_set


class ArtifactSetRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.expected = {
            "manifest.json": "a" * 64,
            "report.json": "b" * 64,
        }
        self.marker = {
            "schema_version": 1,
            "transaction_id": "123e4567-e89b-42d3-a456-426614174000",
            "artifact_sha256": dict(self.expected),
        }

    def classify(self, **overrides):
        args = {
            "expected_sha256": self.expected,
            "published_sha256": {},
            "staged_sha256": dict(self.expected),
            "commit_marker": None,
        }
        args.update(overrides)
        return classify_artifact_set(**args)

    def test_exact_staging_set_is_ready_but_not_committed(self):
        result = self.classify()
        self.assertEqual(result.state, "ready")
        self.assertTrue(result.may_publish_next)
        self.assertFalse(result.may_report_committed)
        self.assertFalse(result.requires_reconciliation)

    def test_commit_marker_and_exact_published_set_are_committed(self):
        result = self.classify(
            published_sha256=dict(self.expected),
            staged_sha256={},
            commit_marker=self.marker,
        )
        self.assertEqual(result.state, "committed")
        self.assertTrue(result.may_report_committed)
        self.assertFalse(result.may_publish_next)
        self.assertFalse(result.requires_reconciliation)

    def test_marker_missing_after_all_artifacts_published_is_not_committed(self):
        result = self.classify(published_sha256=dict(self.expected), staged_sha256={})
        self.assertEqual(result.state, "marker_missing")
        self.assertFalse(result.may_report_committed)
        self.assertTrue(result.requires_reconciliation)
        self.assertTrue(result.preserve_existing_artifacts)

    def test_partial_publication_without_marker_is_preserved_and_blocked(self):
        result = self.classify(
            published_sha256={"manifest.json": self.expected["manifest.json"]},
            staged_sha256={},
        )
        self.assertEqual(result.state, "partial_publication")
        self.assertFalse(result.may_publish_next)
        self.assertTrue(result.requires_reconciliation)
        self.assertTrue(result.preserve_existing_artifacts)

    def test_partial_staging_does_not_authorize_publication(self):
        result = self.classify(staged_sha256={"manifest.json": self.expected["manifest.json"]})
        self.assertEqual(result.state, "staging_incomplete")
        self.assertFalse(result.may_publish_next)
        self.assertTrue(result.requires_reconciliation)

    def test_mismatched_published_digest_blocks(self):
        result = self.classify(
            published_sha256={"manifest.json": "c" * 64},
            staged_sha256={},
        )
        self.assertEqual(result.reason_code, "published_artifact_digest_mismatch")
        self.assertEqual(result.state, "blocked")

    def test_unexpected_published_or_staged_artifact_blocks(self):
        result = self.classify(
            published_sha256={"unexpected.json": "a" * 64},
            staged_sha256={},
        )
        self.assertEqual(result.reason_code, "unexpected_published_artifact")
        result = self.classify(
            published_sha256={},
            staged_sha256={"unexpected.json": "a" * 64},
        )
        self.assertEqual(result.reason_code, "unexpected_staged_artifact")

    def test_invalid_or_mismatched_commit_marker_blocks(self):
        invalid = {**self.marker, "schema_version": True}
        result = self.classify(
            published_sha256=dict(self.expected), staged_sha256={}, commit_marker=invalid
        )
        self.assertEqual(result.reason_code, "commit_marker_version_invalid")
        changed = {**self.marker, "artifact_sha256": {"manifest.json": "a" * 64}}
        result = self.classify(
            published_sha256=dict(self.expected), staged_sha256={}, commit_marker=changed
        )
        self.assertEqual(result.reason_code, "commit_marker_artifact_set_mismatch")

    def test_marker_with_missing_published_artifact_blocks(self):
        result = self.classify(
            published_sha256={"manifest.json": self.expected["manifest.json"]},
            staged_sha256={},
            commit_marker=self.marker,
        )
        self.assertEqual(result.reason_code, "commit_marker_published_set_incomplete")
        self.assertFalse(result.may_report_committed)

    def test_empty_or_malformed_expected_set_blocks(self):
        result = self.classify(expected_sha256={}, published_sha256={}, staged_sha256={})
        self.assertEqual(result.reason_code, "expected_artifact_set_invalid")
        result = self.classify(
            expected_sha256={"../manifest.json": "a" * 64},
            published_sha256={},
            staged_sha256={},
        )
        self.assertEqual(result.reason_code, "expected_artifact_set_invalid")

    def test_empty_staging_and_publication_is_non_destructive(self):
        result = self.classify(staged_sha256={})
        self.assertEqual(result.state, "nothing_published")
        self.assertFalse(result.may_publish_next)
        self.assertTrue(result.preserve_existing_artifacts)


if __name__ == "__main__":
    unittest.main()
