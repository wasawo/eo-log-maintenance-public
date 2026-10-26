"""Initial inventory combines synthetic source/Drive observations, never sync."""
from dataclasses import FrozenInstanceError, replace
from datetime import date
import json
import unittest
from unittest.mock import patch

from Common import SourceInventoryRevalidation as check
from Common.DriveContentComparison import (
    ComparisonSource, DriveFileObservation, DriveListingPage, ContentComparisonBatch,
    collect_drive_listing, hash_downloaded_content, plan_content_downloads,
)
from Common.ManifestTransitionInspection import InitialManifestPlan, TerminalManifestPlan
import test_initial_source_integration as fixture
from test_aggregation_report_builder import SCHEMAS, NOW
from test_drive_comparison_batch import invalid_comparison_batches


class InitialInventoryObservationTests(unittest.TestCase):
    def test_invalid_internal_comparison_outputs_never_become_inventory_observations(self):
        raw, paths, drive = self.seed()
        valid = self.observe(raw, paths, drive)
        before = {p: p.read_bytes() for p in self.source.iterdir()}
        for index, batch in enumerate(invalid_comparison_batches(tuple(item.comparison for item in valid.files))):
            with self.subTest(index=index), patch.object(check, "compare_planned_drive_contents", return_value=batch):
                with self.assertRaisesRegex(check.SourceRevalidationError, "^initial_inventory_result_invalid$"):
                    self.observe(raw, paths, drive)
            self.assertEqual(before, {p: p.read_bytes() for p in self.source.iterdir()})
        self.assertEqual([], list(self.candidate.iterdir()))

    def test_download_output_budgets_preserve_initial_inventory_observations(self):
        raw, paths, drive = self.seed()
        expected = self.observe(raw, paths, drive)
        result = self.observe(raw, paths, drive, maximum_downloads=2, maximum_total_download_bytes=11)
        self.assertEqual(expected, result)
        self.assert_observation_only(result)

    def test_download_budget_excess_retains_selection_and_b2_without_partial_inventory(self):
        raw, paths, drive = self.seed()
        for limits, reason in ((dict(maximum_downloads=1), "comparison_download_count_limit_exceeded"),
                (dict(maximum_total_download_bytes=10), "comparison_download_bytes_limit_exceeded")):
            result = self.observe(raw, paths, drive, **limits)
            self.assertEqual(("held", reason, paths, ()),
                (result.status, result.reason_code, result.selected_paths, result.files))
            self.assertIs(raw, result.evidence_bytes)
            self.assert_observation_only(result)

    def test_invalid_download_budgets_reject_before_source_reobservation(self):
        raw, paths, drive = self.seed()
        for key in ("maximum_downloads", "maximum_total_download_bytes"):
            for value in (True, False, 0, -1, 1.5, "100"):
                with self.subTest(key=key, value=value), patch.object(check, "revalidate_comparison_sources") as read:
                    with self.assertRaisesRegex(check.SourceRevalidationError, "^comparison_download_limit_invalid$"):
                        self.observe(raw, paths, drive, **{key: value})
                    read.assert_not_called()

    setUp = fixture.InitialSourceIntegrationTests.setUp
    cleanup = fixture.InitialSourceIntegrationTests.cleanup
    plan_context = fixture.InitialSourceIntegrationTests.plan_context
    build = fixture.InitialSourceIntegrationTests.build

    def seed(self, log="BattleLog", *, second=True):
        names = ("20260901_01020304@first.txt", "20260902_01020304@second.txt") if log == "BattleLog" else (
            "20250901_01020304.txt", "20250902_01020304.txt")
        data = (b"first", b"second")
        for name, payload in zip(names, data): (self.source/name).write_bytes(payload)
        _, initial = self.build(log=log)
        targets = json.loads(initial.evidence_bytes)["inventory"]["targets"]
        sources = tuple(ComparisonSource(item["filename"], item["size_bytes"], item["expected_sha256"]) for item in targets)
        files = tuple(DriveFileObservation("synthetic-"+str(i), source.filename, source.size_bytes, None)
                      for i, source in enumerate(sources))
        if not second: files = files[:1]
        def listing(entries):
            return collect_drive_listing((DriveListingPage("synthetic-folder", None, None, entries, True),),
                                         expected_folder_id="synthetic-folder")
        before, after = listing(files), listing(files[::-1])
        planned = plan_content_downloads(sources, before, source_trusted=True, expected_folder_id="synthetic-folder")
        downloads = tuple(hash_downloaded_content(file.file_id, (payload,),
            expected_size_bytes=len(payload), download_completed=True) for file, payload in zip(files, data))
        return initial.evidence_bytes, names, dict(drive_before=before, drive_after=after,
            download_plan=planned, downloads=downloads, expected_folder_id="synthetic-folder")

    def observe(self, raw, paths, drive, *, log="BattleLog", **changes):
        options = dict(relative_paths=paths, source_trusted=True, schema=SCHEMAS["evidence_schema"],
            expected_log_type=log, expected_run_id=self.run, expected_root_id="synthetic-source",
            expected_relative_scope=log, reference_date=date(2026, 10, 1),
            current_utc=NOW, current_utc_reliable=True, **drive)
        options.update(changes)
        return check.inspect_initial_inventory(self.source, raw, **options)

    def assert_observation_only(self, result):
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive
                         or result.may_publish_operational_manifest)
        self.assertNotIsInstance(result, (InitialManifestPlan, TerminalManifestPlan))
        self.assertEqual([], list(self.candidate.iterdir()))

    def test_both_logs_bind_exact_b2_selection_order_and_per_file_comparisons(self):
        for log in ("BattleLog", "ErrorReport"):
            # Each fixture run enumerates its own selected log scope.
            if log == "ErrorReport":
                for path in self.source.iterdir(): path.unlink()
            raw, paths, drive = self.seed(log)
            result = self.observe(raw, paths[::-1], drive, log=log)
            self.assertEqual(paths[::-1], result.selected_paths)
            self.assertEqual(paths[::-1], tuple(item.relative_path for item in result.files))
            self.assertEqual(("comparison_candidate",)*2, tuple(item.comparison.status for item in result.files))
            self.assertEqual(("synthetic-1", "synthetic-0"), tuple(item.comparison.candidate_file_id for item in result.files))
            self.assertIs(raw, result.evidence_bytes)
            self.assertEqual("requires_runtime_evidence", result.status)
            self.assert_observation_only(result)
            self.assertNotIn(paths[0], repr(result))
            with self.assertRaises(FrozenInstanceError): result.status = "success"

    def test_individual_unmatched_file_stays_held_without_sync_status(self):
        raw, paths, drive = self.seed(second=False)
        result = self.observe(raw, paths, drive)
        self.assertEqual(("comparison_candidate", "held"), tuple(item.comparison.status for item in result.files))
        self.assertEqual("comparison_no_match", result.files[-1].comparison.reason_code)
        self.assert_observation_only(result)

    def test_global_drive_plan_or_download_failure_retains_selected_paths_and_b2(self):
        raw, paths, drive = self.seed()
        for changes in ({"downloads": ()}, {"download_plan": None}, {"expected_folder_id": "another-folder"},
                        {"drive_after": replace(drive["drive_after"], files=())}):
            result = self.observe(raw, paths, drive, **changes)
            self.assertEqual(("held", paths, ()), (result.status, result.selected_paths, result.files))
            self.assertIs(raw, result.evidence_bytes)
            self.assert_observation_only(result)

    def test_source_change_and_untrusted_or_pc_b_records_never_become_inventory_completion(self):
        raw, paths, drive = self.seed()
        with self.assertRaisesRegex(check.SourceRevalidationError, "comparison_source_untrusted"):
            self.observe(raw, paths, drive, source_trusted=False)
        _, pc_b = self.build(pc="PC-B")
        with self.assertRaisesRegex(check.SourceRevalidationError, "comparison_source_pc_invalid"):
            self.observe(pc_b.evidence_bytes, paths, drive)
        saved = self.observe(raw, paths, drive)
        (self.source/paths[0]).write_bytes(b"other")
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_inventory_observation_changed"):
            self.observe(raw, paths, drive)
        self.assertIs(raw, saved.evidence_bytes)
        self.assert_observation_only(saved)

    def test_empty_explicit_selection_is_not_no_work_and_still_checks_drive_context(self):
        raw, _, drive = self.seed()
        empty_plan = plan_content_downloads((), drive["drive_before"], source_trusted=True,
                                           expected_folder_id="synthetic-folder")
        result = self.observe(raw, (), drive, download_plan=empty_plan, downloads=())
        self.assertEqual(("requires_runtime_evidence", (), ()), (result.status, result.selected_paths, result.files))
        self.assert_observation_only(result)
        held = self.observe(raw, (), drive, download_plan=empty_plan, downloads=(), expected_folder_id="other")
        self.assertEqual("held", held.status)

    def test_known_validation_errors_remain_in_b2_even_with_matching_candidates(self):
        (self.source/"unexpected.txt").write_bytes(b"synthetic-error")
        raw, paths, drive = self.seed()
        result = self.observe(raw, paths, drive)
        self.assertEqual(1, json.loads(result.evidence_bytes)["validation"]["invalid_relevant_count"])
        self.assertEqual(2, len(result.files))
        self.assert_observation_only(result)

    def test_internal_result_count_mismatch_is_rejected_without_partial_mapping(self):
        raw, paths, drive = self.seed()
        with patch.object(check, "compare_planned_drive_contents", return_value=ContentComparisonBatch("compared", "synthetic")):
            with self.assertRaisesRegex(check.SourceRevalidationError, "initial_inventory_result_invalid"):
                self.observe(raw, paths, drive)
        self.assertEqual([], list(self.candidate.iterdir()))


if __name__ == "__main__": unittest.main()
