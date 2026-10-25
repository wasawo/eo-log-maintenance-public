"""Counts-only initial inventory summaries cannot expose input payloads or grant actions."""
from dataclasses import asdict, replace, FrozenInstanceError
import json
import unittest
from unittest.mock import patch

from Common import SourceInventoryRevalidation as check
from Common.DriveContentComparison import ContentComparison
import test_initial_inventory_observation as fixture
from test_aggregation_report_builder import SCHEMAS


class InitialInventorySummaryTests(unittest.TestCase):
    setUp = fixture.InitialInventoryObservationTests.setUp
    cleanup = fixture.InitialInventoryObservationTests.cleanup
    plan_context = fixture.InitialInventoryObservationTests.plan_context
    build = fixture.InitialInventoryObservationTests.build
    seed = fixture.InitialInventoryObservationTests.seed
    observe = fixture.InitialInventoryObservationTests.observe

    def summary(self, observed):
        return check.summarize_initial_inventory(observed, schema=SCHEMAS["evidence_schema"])

    def test_mixed_candidates_and_holds_are_counts_only_without_io(self):
        raw, paths, drive = self.seed(second=False)
        observed = self.observe(raw, paths, drive)
        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
            summary = self.summary(observed)
        self.assertEqual((2, 2, 2, 1, 1, 0, 0), (summary.inventory_target_count, summary.selected_count,
            summary.assessed_count, summary.candidate_count, summary.held_count,
            summary.unassessed_count, summary.validation_error_count))
        self.assertEqual("initial_inventory_summary", summary.kind)
        serialized = json.dumps(asdict(summary))
        for private in (*paths, "synthetic-0", observed.files[0].source.sha256, self.run):
            self.assertNotIn(private, serialized)
        self.assertFalse(summary.may_restore or summary.may_report_sync_success or summary.may_archive
                         or summary.may_publish_operational_manifest)
        with self.assertRaises(FrozenInstanceError): summary.candidate_count = 99

    def test_global_hold_is_unassessed_not_zero_work_or_per_file_failure(self):
        raw, paths, drive = self.seed()
        observed = self.observe(raw, paths, drive, downloads=())
        summary = self.summary(replace(observed, reason_code="synthetic-private-reason"))
        self.assertEqual(("held", 2, 0, 0, 0, 2), (summary.observation_status, summary.selected_count,
            summary.assessed_count, summary.candidate_count, summary.held_count, summary.unassessed_count))
        self.assertNotIn("synthetic-private-reason", repr(summary))
        self.assertFalse(hasattr(summary, "reason_code"))

    def test_empty_selection_is_distinct_from_inventory_size_and_errors_are_preserved(self):
        (self.source/"unexpected.txt").write_bytes(b"synthetic-error")
        raw, paths, drive = self.seed()
        # An empty plan is needed to assess an explicitly empty selection.
        from Common.DriveContentComparison import plan_content_downloads
        plan = plan_content_downloads((), drive["drive_before"], source_trusted=True, expected_folder_id="synthetic-folder")
        observed = self.observe(raw, (), drive, download_plan=plan, downloads=())
        summary = self.summary(observed)
        self.assertEqual((2, 0, 0, 1), (summary.inventory_target_count, summary.selected_count,
                                     summary.assessed_count, summary.validation_error_count))
        self.assertFalse(summary.may_report_sync_success)

    def test_invalid_selection_count_order_source_and_evidence_are_rejected(self):
        raw, paths, drive = self.seed()
        observed = self.observe(raw, paths, drive)
        wrong_source = replace(observed.files[0], source=replace(observed.files[0].source, size_bytes=999))
        variants = (None, replace(observed, evidence_bytes=b"{}"),
            replace(observed, selected_paths=(paths[0], paths[0])), replace(observed, files=observed.files[:1]),
            replace(observed, files=observed.files[::-1]), replace(observed, selected_paths=("missing.txt",)),
            replace(observed, files=(wrong_source, observed.files[1])))
        for bad in variants:
            with self.assertRaisesRegex(check.SourceRevalidationError, "^initial_inventory_summary_invalid$"):
                self.summary(bad)

    def test_malformed_outcomes_or_true_permissions_are_not_counted(self):
        raw, paths, drive = self.seed()
        observed = self.observe(raw, paths, drive)
        for comparison in (ContentComparison("success", "private-reason"),
                           ContentComparison("comparison_candidate", "private-reason"),
                           ContentComparison("held", "private-reason", "unexpected-id")):
            bad = replace(observed, files=(replace(observed.files[0], comparison=comparison), observed.files[1]))
            with self.assertRaisesRegex(check.SourceRevalidationError, "initial_inventory_summary_invalid"):
                self.summary(bad)
        for flag in ("may_restore", "may_report_sync_success", "may_archive", "may_publish_operational_manifest"):
            bad = replace(observed)
            object.__setattr__(bad, flag, 1)
            with self.assertRaisesRegex(check.SourceRevalidationError, "initial_inventory_summary_invalid"):
                self.summary(bad)

    def test_historical_summary_is_not_a_new_source_observation_or_receipt(self):
        raw, paths, drive = self.seed()
        observed = self.observe(raw, paths, drive)
        first = self.summary(observed)
        (self.source/paths[0]).write_bytes(b"other")
        self.assertEqual(first, self.summary(observed))
        self.assertFalse(first.may_restore or first.may_archive or first.may_report_sync_success)
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_inventory_observation_changed"):
            self.observe(raw, paths, drive)


if __name__ == "__main__": unittest.main()
