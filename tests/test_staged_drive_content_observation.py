"""Fresh staging reads connected to strict supplied Drive content observations."""
from dataclasses import FrozenInstanceError, replace
import json
import unittest
from unittest.mock import patch

from Common import SourceInventoryRevalidation as check
from Common.DriveContentComparison import (ComparisonSource, ContentComparisonBatch,
    DriveFileObservation, DriveListingPage, collect_drive_listing,
    hash_downloaded_content, plan_content_downloads)
import test_initial_source_integration as fixture


class StagedDriveContentTests(unittest.TestCase):
    setUp = fixture.InitialSourceIntegrationTests.setUp
    cleanup = fixture.InitialSourceIntegrationTests.cleanup
    build = fixture.InitialSourceIntegrationTests.build
    plan_context = fixture.InitialSourceIntegrationTests.plan_context

    def listing(self, files):
        return collect_drive_listing((DriveListingPage("synthetic-folder", None, None, files, True),),
                                     expected_folder_id="synthetic-folder")

    def seed(self, pc="PC-A", log="BattleLog"):
        source = self.source / (pc + log)
        source.mkdir()
        self.staging = self.candidate / (pc + log)
        self.staging.mkdir()
        names = ("20260901_01020304@first.txt", "20260902_01020304@second.txt") if log == "BattleLog" else (
            "20250901_01020304.txt", "20250902_01020304.txt")
        data = (b"first", b"second")
        for name, payload in zip(names, data): (source / name).write_bytes(payload)
        _, self.plan = self.build(pc=pc, log=log, source=source)
        self.context = self.plan_context(pc, log)
        files = json.loads(self.plan.proposed_bytes)["files"]
        self.allocations = tuple((item["relative_path"], seq) for seq, item in enumerate(files, 1))
        self.sources = tuple(ComparisonSource(item["filename"], item["size_bytes"], item["sha256"]) for item in files)
        self.destinations = tuple(self.staging / f"{self.run}_{seq}_{name}" for name, seq in self.allocations)
        for destination, payload in zip(self.destinations, data): destination.write_bytes(payload)
        self.remote = tuple(DriveFileObservation("synthetic-"+str(i), s.filename, s.size_bytes, None)
                            for i, s in enumerate(self.sources))
        before, after = self.listing(self.remote), self.listing(self.remote[::-1])
        self.drive = dict(drive_before=before, drive_after=after, expected_folder_id="synthetic-folder",
            download_plan=plan_content_downloads(self.sources, before, source_trusted=True,
                                                expected_folder_id="synthetic-folder"),
            downloads=tuple(hash_downloaded_content(item.file_id, (payload,), expected_size_bytes=len(payload),
                download_completed=True) for item, payload in zip(self.remote, data)))
        return source

    def observe(self, **changes):
        options = dict(self.context, **self.drive, allocations=self.allocations, source_trusted=True)
        options.update(changes)
        return check.inspect_initial_staged_drive_contents(self.staging, self.plan, **options)

    def assert_no_authority(self, result):
        self.assertFalse(result.may_upload or result.may_retry or result.may_report_sync_success
                         or result.may_change_state or result.may_archive)
        self.assertNotIn("synthetic-folder", repr(result))
        with self.assertRaises(FrozenInstanceError): result.status = "success"

    def test_both_pcs_logs_preserve_selected_order_and_use_staging_without_source(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                source = self.seed(pc, log)
                for path in source.iterdir(): path.unlink()  # Self-created fixture sources only.
                result = self.observe(allocations=self.allocations[::-1])
                self.assertEqual("requires_runtime_evidence", result.status)
                self.assertEqual(tuple(path for path, _ in self.allocations[::-1]),
                                 tuple(copy.relative_path for copy in result.copies))
                self.assertEqual(("synthetic-1", "synthetic-0"),
                                 tuple(item.candidate_file_id for item in result.comparisons))
                self.assertEqual(("comparison_candidate",)*2, tuple(item.status for item in result.comparisons))
                self.assert_no_authority(result)

    def test_local_mismatch_stops_before_drive_comparison_and_preserves_copy(self):
        self.seed()
        self.destinations[0].write_bytes(b"WRONG")
        with patch.object(check, "compare_planned_drive_contents") as compare:
            with self.assertRaises(check.SourceRevalidationError): self.observe()
            compare.assert_not_called()
        self.assertEqual(b"WRONG", self.destinations[0].read_bytes())

    def test_global_drive_holds_keep_local_observations_without_partial_comparisons(self):
        self.seed()
        for changes in ({"source_trusted": False}, {"expected_folder_id": "other"},
                {"downloads": self.drive["downloads"][:1]},
                {"drive_after": self.listing(self.remote[:1])}, {"download_plan": None}):
            with self.subTest(changes=changes):
                result = self.observe(**changes)
                self.assertEqual(("held", 2, ()), (result.status, len(result.copies), result.comparisons))
                self.assert_no_authority(result)

    def test_remote_hash_mismatch_stays_per_file_held_without_state_changes(self):
        self.seed()
        wrong = hash_downloaded_content("synthetic-0", (b"WRONG",), expected_size_bytes=5, download_completed=True)
        result = self.observe(downloads=(wrong, self.drive["downloads"][1]))
        self.assertEqual(("held", "comparison_candidate"), tuple(item.status for item in result.comparisons))
        self.assertEqual(b"first", self.destinations[0].read_bytes())
        self.assert_no_authority(result)

    def test_empty_selection_still_validates_drive_and_is_not_no_work(self):
        self.seed()
        empty_plan = plan_content_downloads((), self.drive["drive_before"], source_trusted=True,
                                            expected_folder_id="synthetic-folder")
        result = self.observe(allocations=(), download_plan=empty_plan, downloads=())
        self.assertEqual(("requires_runtime_evidence", (), ()), (result.status, result.copies, result.comparisons))
        self.assert_no_authority(result)
        held = self.observe(allocations=(), download_plan=empty_plan, downloads=(), expected_folder_id="other")
        self.assertEqual("held", held.status)

    def test_every_call_rereads_staging_and_old_observation_is_not_a_plan(self):
        self.seed()
        old = self.observe()
        real_plan = self.plan
        self.plan = old
        with self.assertRaises(check.SourceRevalidationError): self.observe()
        self.plan = real_plan
        self.destinations[1].write_bytes(b"WRONG!")
        with self.assertRaises(check.SourceRevalidationError): self.observe()

    def test_suffix_name_is_not_implicitly_aliased_to_original(self):
        self.seed()
        suffixed = tuple(replace(item, filename=item.filename[:-4]+"_PCA.txt") for item in self.remote)
        listing = self.listing(suffixed)
        planned = plan_content_downloads(self.sources, listing, source_trusted=True, expected_folder_id="synthetic-folder")
        result = self.observe(drive_before=listing, drive_after=listing, download_plan=planned, downloads=())
        self.assertEqual(("held", "held"), tuple(item.status for item in result.comparisons))
        self.assert_no_authority(result)

    def test_unexpected_internal_result_shape_never_becomes_partial_success(self):
        self.seed()
        for invalid in (None, ContentComparisonBatch("compared", "synthetic"),
                ContentComparisonBatch("held", "synthetic", (object(),)),
                ContentComparisonBatch("compared", "synthetic", (object(), object()))):
            with patch.object(check, "compare_planned_drive_contents", return_value=invalid):
                with self.assertRaisesRegex(check.SourceRevalidationError, "staged_drive_comparison_invalid"):
                    self.observe()


if __name__ == "__main__":
    unittest.main()
