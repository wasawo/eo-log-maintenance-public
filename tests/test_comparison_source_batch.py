"""Synthetic explicit target batches share one full B2/source re-observation."""
from datetime import date
import json
import unittest
from unittest.mock import patch

from Common import SourceInventoryRevalidation as check
from Common.RunInputEvidenceIntegrity import compute_evidence_digest
from Common.DriveContentComparison import (
    DriveFileObservation, DriveListingPage, collect_drive_listing,
    hash_downloaded_content, compare_reobserved_drive_contents,
)
import test_initial_source_integration as fixture
from test_aggregation_report_builder import SCHEMAS, NOW


class ComparisonSourceBatchTests(unittest.TestCase):
    setUp = fixture.InitialSourceIntegrationTests.setUp
    cleanup = fixture.InitialSourceIntegrationTests.cleanup
    plan_context = fixture.InitialSourceIntegrationTests.plan_context
    build = fixture.InitialSourceIntegrationTests.build

    def observe(self, raw, paths, **changes):
        options = dict(relative_paths=paths, source_trusted=True, schema=SCHEMAS["evidence_schema"],
            expected_log_type="BattleLog", expected_run_id=self.run, expected_root_id="synthetic-source",
            expected_relative_scope="BattleLog", reference_date=date(2026, 10, 1),
            current_utc=NOW, current_utc_reliable=True)
        options.update(changes)
        return check.revalidate_comparison_sources(self.source, raw, **options)

    def seed(self):
        paths = ("20260901_01020304@first.txt", "階層/20260902_01020304@second.txt")
        data = (b"first", b"second")
        (self.source/"階層").mkdir()
        for path, payload in zip(paths, data): (self.source/path).write_bytes(payload)
        _, plan = self.build()
        return plan.evidence_bytes, paths, data

    def test_batch_reobserves_once_and_preserves_caller_order_and_outputs(self):
        raw, paths, _ = self.seed()
        original = check.build_run_input_evidence
        with patch.object(check, "build_run_input_evidence", wraps=original) as scan:
            result = self.observe(raw, paths[::-1])
            self.assertEqual(1, scan.call_count)
        self.assertEqual(paths[::-1], tuple(item.relative_path for item in result))
        for item in result:
            self.assertIs(raw, item.evidence_bytes)
            self.assertFalse(item.may_restore or item.may_report_sync_success or item.may_archive)
            self.assertEqual((item,), self.observe(raw, (item.relative_path,)))

    def test_every_path_is_validated_before_any_source_io(self):
        raw, paths, _ = self.seed()
        for selected in (list(paths), paths[0], (paths[0], paths[0]),
                         (paths[0], "../escape"), (paths[0], "missing.txt"), (paths[0], None)):
            with patch.object(check, "build_run_input_evidence") as scan:
                with self.assertRaises(check.SourceRevalidationError): self.observe(raw, selected)
                scan.assert_not_called()

    def test_batch_is_not_a_cache_and_any_inventory_change_blocks_it(self):
        raw, paths, _ = self.seed()
        first = self.observe(raw, paths)
        (self.source/paths[-1]).write_bytes(b"change")
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_inventory_observation_changed"):
            self.observe(raw, paths)
        self.assertIs(raw, first[0].evidence_bytes)
        # Even selecting the unchanged first file must compare the full source.
        with self.assertRaises(check.SourceRevalidationError): self.observe(raw, paths[:1])

    def test_empty_selection_still_revalidates_and_cannot_hide_incomplete_coverage(self):
        raw, paths, _ = self.seed()
        original = check.build_run_input_evidence
        with patch.object(check, "build_run_input_evidence", wraps=original) as scan:
            self.assertEqual((), self.observe(raw, ()))
            self.assertEqual(1, scan.call_count)
        incomplete = json.loads(raw)
        incomplete["enumeration"].update(status="incomplete", enumeration_errors=1)
        incomplete["validation"]["status"] = "incomplete"
        incomplete["integrity"]["digest"] = compute_evidence_digest(incomplete)
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_frozen_coverage_incomplete"):
            self.observe(json.dumps(incomplete).encode(), ())
        (self.source/paths[0]).write_bytes(b"other")
        with self.assertRaises(check.SourceRevalidationError): self.observe(raw, ())

    def test_empty_inventory_is_observed_without_making_a_run_success_claim(self):
        _, plan = self.build()
        self.assertEqual((), self.observe(plan.evidence_bytes, ()))
        with self.assertRaisesRegex(check.SourceRevalidationError, "comparison_source_target_missing"):
            self.observe(plan.evidence_bytes, ("missing.txt",))

    def test_trust_and_pc_a_scope_remain_required_for_the_whole_batch(self):
        raw, paths, _ = self.seed()
        _, other = self.build(pc="PC-B")
        for evidence, changes in ((raw, {"source_trusted": False}),
                                  (other.evidence_bytes, {}), (raw, {"current_utc_reliable": False})):
            with patch.object(check, "build_run_input_evidence") as scan:
                with self.assertRaises(check.SourceRevalidationError): self.observe(evidence, paths, **changes)
                scan.assert_not_called()

    def test_all_batch_sources_connect_to_one_listing_and_download_set_without_authority(self):
        raw, paths, data = self.seed()
        sources = self.observe(raw, paths)
        files = tuple(DriveFileObservation("synthetic-"+str(i), item.source.filename,
            item.source.size_bytes, None) for i, item in enumerate(sources))
        before = collect_drive_listing((DriveListingPage("synthetic-folder", None, None, files, True),),
            expected_folder_id="synthetic-folder")
        downloads = tuple(hash_downloaded_content(file.file_id, (payload,),
            expected_size_bytes=len(payload), download_completed=True) for file, payload in zip(files, data))
        after = collect_drive_listing((DriveListingPage("synthetic-folder", None, None, files[::-1], True),),
            expected_folder_id="synthetic-folder")
        batch = compare_reobserved_drive_contents(tuple(item.source for item in sources), before, after,
            source_trusted=True, expected_folder_id="synthetic-folder", downloads=downloads)
        self.assertEqual("compared", batch.status)
        self.assertFalse(batch.may_restore or batch.may_report_sync_success or batch.may_archive)
        for result, expected in zip(batch.results, files):
            self.assertEqual(expected.file_id, result.candidate_file_id)
            self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)
        self.assertEqual([], list(self.candidate.iterdir()))


if __name__ == "__main__": unittest.main()
