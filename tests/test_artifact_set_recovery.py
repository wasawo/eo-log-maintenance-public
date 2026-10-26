"""Synthetic tests for multi-artifact publication/recovery classification."""
from __future__ import annotations

import unittest

from Common.ArtifactSetRecovery import classify_artifact_set


class ArtifactSetRecoveryTests(unittest.TestCase):
    def test_publisher_invalid_basenames_block_every_observed_map(self):
        for name in ("", ".", "..", ".hidden", "nested/file", "nested\\file", "bad\x00name",
                     "artifact.", "artifact ", "artifact. ", None, 1):
            for slot, reason in (("expected_sha256", "expected_artifact_set_invalid"),
                                 ("published_sha256", "published_artifact_set_invalid"),
                                 ("staged_sha256", "staged_artifact_set_invalid")):
                context = dict(expected_sha256=self.expected, published_sha256={}, staged_sha256={})
                context[slot] = {name: "a" * 64}
                with self.subTest(name=name, slot=slot):
                    result = classify_artifact_set(**context)
                    self.assertEqual(("blocked", reason), (result.state, result.reason_code))
                    self.assertFalse(result.may_report_committed or result.may_publish_next)
                    self.assertTrue(result.preserve_existing_artifacts and result.requires_reconciliation)

    def test_valid_unicode_and_internal_spacing_remain_exact_distinct_names(self):
        names = ("報告 e\u0301.json", "報告 é.json", "many.parts.json", "internal space.json")
        expected = {name: "a" * 64 for name in names}
        marker = dict(self.marker, artifact_sha256=expected)
        before = dict(expected)
        result = classify_artifact_set(expected_sha256=expected, published_sha256=dict(expected),
            staged_sha256={}, commit_marker=marker)
        self.assertEqual("committed", result.state)
        self.assertTrue(result.may_report_committed)
        self.assertEqual(before, expected)
        self.assertEqual(len(names), len(expected))

    def test_copy_failures_in_all_mapping_inputs_return_fixed_blocked_decisions(self):
        from collections.abc import Mapping
        class BrokenMap(Mapping):
            def __init__(self, phase): self.phase = phase
            def __len__(self): return 2
            def __iter__(self):
                if self.phase == "iteration": raise RuntimeError("synthetic private detail")
                yield "manifest.json"
                if self.phase == "partial": raise RuntimeError("synthetic private detail")
                yield "report.json"
            def __getitem__(self, key):
                if self.phase == "item": raise RuntimeError("synthetic private detail")
                return "a"*64
        for slot, reason in (("expected_sha256", "expected_artifact_set_invalid"),
                ("published_sha256", "published_artifact_set_invalid"),
                ("staged_sha256", "staged_artifact_set_invalid"),
                ("commit_marker", "commit_marker_invalid"),
                ("marker_hashes", "commit_marker_artifact_set_mismatch")):
            for phase in ("iteration", "partial", "item"):
                args = dict(expected_sha256=self.expected, published_sha256=dict(self.expected),
                    staged_sha256={}, commit_marker=self.marker)
                if slot == "marker_hashes":
                    args["commit_marker"] = {**self.marker, "artifact_sha256": BrokenMap(phase)}
                else:
                    args[slot] = BrokenMap(phase)
                with self.subTest(slot=slot, phase=phase):
                    result = classify_artifact_set(**args)
                    self.assertEqual("blocked", result.state)
                    self.assertEqual(reason, result.reason_code)
                    self.assertFalse(result.may_publish_next or result.may_report_committed)
                    self.assertTrue(result.requires_reconciliation and result.preserve_existing_artifacts)
                    self.assertNotIn("synthetic private detail", repr(result))

    def test_deceptive_items_cannot_validate_an_empty_expected_snapshot_as_committed(self):
        from collections.abc import Mapping
        class DeceptiveMap(Mapping):
            def __len__(self): return 1
            def __iter__(self): return iter(())
            def __getitem__(self, key): return "a"*64
            def items(self): return {"manifest.json": "a"*64}.items()
        deceptive = DeceptiveMap()
        result = classify_artifact_set(expected_sha256=deceptive, published_sha256={}, staged_sha256={},
            commit_marker={**self.marker, "artifact_sha256": deceptive})
        self.assertEqual("expected_artifact_set_invalid", result.reason_code)
        self.assertFalse(result.may_report_committed or result.may_publish_next)

    def test_valid_read_only_mapping_inputs_retain_committed_and_ready_classification(self):
        from types import MappingProxyType
        marker = MappingProxyType({**self.marker, "artifact_sha256": MappingProxyType(dict(self.expected))})
        committed = classify_artifact_set(expected_sha256=MappingProxyType(self.expected),
            published_sha256=MappingProxyType(dict(self.expected)), staged_sha256=MappingProxyType({}),
            commit_marker=marker)
        self.assertEqual("committed", committed.state)
        self.assertTrue(committed.may_report_committed)
        ready = classify_artifact_set(expected_sha256=MappingProxyType(self.expected),
            published_sha256=MappingProxyType({}), staged_sha256=MappingProxyType(dict(self.expected)))
        self.assertEqual("ready", ready.state)
        self.assertTrue(ready.may_publish_next)

    def test_copied_marker_hashes_cannot_hide_an_empty_actual_mapping(self):
        from collections.abc import Mapping
        expected = dict(self.expected)
        class DeceptiveMap(Mapping):
            def __len__(self): return len(expected)
            def __iter__(self): return iter(())
            def __getitem__(self, key): return expected[key]
            def items(self): return expected.items()
        result = self.classify(published_sha256=expected, staged_sha256={},
            commit_marker={**self.marker, "artifact_sha256": DeceptiveMap()})
        self.assertEqual("commit_marker_artifact_set_mismatch", result.reason_code)
        self.assertFalse(result.may_report_committed or result.may_publish_next)

    def test_independent_transaction_binding_rejects_other_or_nonexact_identity(self):
        for expected in ("123e4567-e89b-42d3-a456-426614174000", "123e4567-e89b-42d3-a456-426614174001",
                         "123E4567-E89B-42D3-A456-426614174000"):
            result = self.classify(published_sha256=dict(self.expected), staged_sha256={},
                commit_marker=self.marker, expected_transaction_id=expected)
            self.assertEqual(result.may_report_committed, expected == self.marker["transaction_id"])
            if not result.may_report_committed:
                self.assertEqual("commit_marker_transaction_id_mismatch", result.reason_code)

    def test_invalid_transaction_expectation_is_blocked_without_coercion(self):
        for expected in ("", "not-a-uuid", True, 1, b"123e4567-e89b-42d3-a456-426614174000"):
            result = self.classify(expected_transaction_id=expected)
            self.assertEqual("expected_transaction_id_invalid", result.reason_code)
            self.assertFalse(result.may_publish_next or result.may_report_committed)

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
