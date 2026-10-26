"""Bound plan/source use-point observations inside synthetic owned publication."""
from dataclasses import replace
from datetime import date
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common import SourceInventoryRevalidation as check
import test_initial_source_integration as fixture


class InitialSourceUsepointTests(unittest.TestCase):
    def test_plan_revalidation_forwards_budgets_and_preserves_exact_plan(self):
        path, plan = self.seed()
        expected = self.observe(plan)
        self.assertEqual(expected, self.observe(plan, maximum_entries=1,
            maximum_file_bytes=5, maximum_total_hash_bytes=5))
        for key in ("maximum_file_bytes", "maximum_total_hash_bytes"):
            with self.subTest(key=key), self.assertRaisesRegex(check.SourceRevalidationError,
                    "^source_revalidation_incomplete$"):
                self.observe(plan, **{key: 4})
        self.assertEqual(b"first", path.read_bytes())
        self.assertIs(plan.evidence_bytes, expected.evidence_bytes)
        self.assertFalse(expected.may_upload or expected.may_archive or expected.may_change_state)

    setUp = fixture.InitialSourceIntegrationTests.setUp
    cleanup = fixture.InitialSourceIntegrationTests.cleanup
    plan_context = fixture.InitialSourceIntegrationTests.plan_context
    build = fixture.InitialSourceIntegrationTests.build
    publish = fixture.InitialSourceIntegrationTests.publish

    def seed(self):
        path = self.source / "20260901_01020304@synthetic.txt"
        path.write_bytes(b"first")
        _, plan = self.build()
        return path, plan

    def observe(self, plan, **changes):
        options = dict(**self.plan_context(), ac_connected=True, expected_root_id="synthetic-source",
                       expected_relative_scope="BattleLog", reference_date=date(2026, 10, 1))
        options.update(changes)
        return check.revalidate_initial_manifest_source(self.source, plan, **options)

    def test_matching_plan_remains_non_authorizing_and_repeated_result_is_not_a_receipt(self):
        _, plan = self.seed()
        first = self.observe(plan)
        self.assertEqual(first, self.observe(plan))
        self.assertEqual(plan.evidence_bytes, first.evidence_bytes)
        self.assertFalse(first.may_upload or first.may_archive or first.may_change_state)

    def test_ac_unknown_false_and_truthy_nonbool_stop_before_source_io(self):
        _, plan = self.seed()
        for ac in (False, None, 1, "true"):
            with self.subTest(ac=ac), patch.object(check, "build_run_input_evidence") as read:
                with self.assertRaisesRegex(check.SourceRevalidationError, "initial_source_ac_unconfirmed"):
                    self.observe(plan, ac_connected=ac)
                read.assert_not_called()

    def test_plan_content_and_evidence_tampering_is_rejected_before_source_io(self):
        _, plan = self.seed()
        content = json.loads(plan.proposed_bytes)
        content["files"][0]["status"] = "uploaded"
        variants = (None, {"may_publish": True}, replace(plan, proposed_bytes=plan.proposed_bytes + b"\n"),
            replace(plan, proposed_bytes=json.dumps(content).encode()), replace(plan, evidence_bytes=b"{}"))
        for changed in variants:
            with patch.object(check, "build_run_input_evidence") as read:
                with self.assertRaisesRegex(check.SourceRevalidationError, "initial_source_plan_invalid"):
                    self.observe(changed)
                read.assert_not_called()

    def test_altered_permission_flags_never_authorize_a_plan(self):
        _, plan = self.seed()
        for flag in ("may_publish", "may_upload", "may_archive"):
            changed = replace(plan)
            object.__setattr__(changed, flag, True)
            with patch.object(check, "build_run_input_evidence") as read:
                with self.assertRaisesRegex(check.SourceRevalidationError, "initial_source_plan_invalid"):
                    self.observe(changed)
                read.assert_not_called()

    def test_independent_run_period_start_and_clock_are_rechecked(self):
        _, plan = self.seed()
        for changes in ({"expected_pc_id": "PC-B"}, {"expected_target_period": "2026-08"},
                {"expected_run_id": str(uuid4())}, {"started_at_utc": "2026-10-21T00:00:00.0Z"},
                {"current_utc_reliable": False}):
            with self.subTest(changes=changes), patch.object(check, "build_run_input_evidence") as read:
                with self.assertRaisesRegex(check.SourceRevalidationError, "initial_source_plan_invalid"):
                    self.observe(plan, **changes)
                read.assert_not_called()

    def test_source_change_after_preparation_is_not_hidden_by_a_valid_plan(self):
        path, plan = self.seed()
        path.write_bytes(b"other")
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_inventory_observation_changed"):
            self.observe(plan)
        self.assertEqual(b"other", path.read_bytes())
        self.assertEqual([], list(self.candidate.iterdir()))

    @unittest.skipUnless(os.name == "nt", "Windows owned publication fixture required")
    def test_matching_observation_connects_inside_owned_candidate_publication(self):
        path, plan = self.seed()
        observed = []
        def guard():
            self.assertTrue((self.root / "owner.json").exists())
            observed.append(self.observe(plan))
        self.publish(plan, before_publish=guard)
        self.assertEqual(1, len(observed))
        self.assertFalse(observed[0].may_upload or plan.may_publish)
        self.assertEqual(b"first", path.read_bytes())
        self.assertFalse((self.root / "owner.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows owned publication fixture required")
    def test_source_change_inside_lock_blocks_all_candidate_writes(self):
        path, plan = self.seed()
        def guard():
            path.write_bytes(b"other")
            self.observe(plan)
        with self.assertRaises(check.SourceRevalidationError): self.publish(plan, before_publish=guard)
        self.assertEqual([], list(self.candidate.iterdir()))
        self.assertFalse((self.root / "owner.json").exists())
        self.assertEqual(b"other", path.read_bytes())

    @unittest.skipUnless(os.name == "nt", "Windows owned publication fixture required")
    def test_ac_loss_inside_lock_blocks_candidate_and_preserves_plan(self):
        _, plan = self.seed()
        before = plan.proposed_bytes, plan.evidence_bytes
        with self.assertRaises(check.SourceRevalidationError):
            self.publish(plan, before_publish=lambda: self.observe(plan, ac_connected=False))
        self.assertEqual([], list(self.candidate.iterdir()))
        self.assertEqual(before, (plan.proposed_bytes, plan.evidence_bytes))
        self.assertFalse((self.root / "owner.json").exists())


if __name__ == "__main__": unittest.main()
