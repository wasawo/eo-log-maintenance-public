"""Synthetic PC-A B2/source -> listing/download -> comparison observation."""
from dataclasses import FrozenInstanceError
from datetime import date
import json
import unittest
from unittest.mock import patch

from Common import SourceInventoryRevalidation as check
from Common.DriveContentComparison import (
    DriveFileObservation, DriveListingPage, collect_drive_listing,
    hash_downloaded_content, compare_drive_content,
)
from Common.RunInputEvidenceIntegrity import compute_evidence_digest
import test_initial_source_integration as source_fixture
from test_aggregation_report_builder import SCHEMAS, NOW


class ComparisonSourceRevalidationTests(unittest.TestCase):
    setUp = source_fixture.InitialSourceIntegrationTests.setUp
    cleanup = source_fixture.InitialSourceIntegrationTests.cleanup
    plan_context = source_fixture.InitialSourceIntegrationTests.plan_context
    build = source_fixture.InitialSourceIntegrationTests.build

    def observe(self, raw, path, *, source=None, log="BattleLog", **changes):
        options = dict(relative_path=path, source_trusted=True, schema=SCHEMAS["evidence_schema"],
            expected_log_type=log, expected_run_id=self.run, expected_root_id="synthetic-source",
            expected_relative_scope=log, reference_date=date(2026, 10, 1),
            current_utc=NOW, current_utc_reliable=True)
        options.update(changes)
        return check.revalidate_comparison_source(self.source if source is None else source, raw, **options)

    def seed(self):
        path = self.source / "20260901_01020304@synthetic.txt"
        path.write_bytes(b"first")
        _, plan = self.build()
        return path, plan.evidence_bytes

    def test_pc_a_both_logs_and_unicode_path_bind_exact_original_evidence(self):
        for log in ("BattleLog", "ErrorReport"):
            root = self.source / log
            nested = root / "階層"; nested.mkdir(parents=True)
            name = "20260901_01020304@合成.txt" if log == "BattleLog" else "20250901_01020304.txt"
            path = nested / name; path.write_bytes(b"synthetic")
            _, plan = self.build(log=log, source=root)
            result = self.observe(plan.evidence_bytes, "階層/"+name, source=root, log=log)
            self.assertEqual((name, 9), (result.source.filename, result.source.size_bytes))
            self.assertIs(plan.evidence_bytes, result.evidence_bytes)
            self.assertEqual("階層/"+name, result.relative_path)
            self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)
            self.assertNotIn(name, repr(result))
            with self.assertRaises(FrozenInstanceError): result.relative_path = "other"

    def test_same_basename_in_different_paths_requires_exact_selected_target(self):
        name = "20260901_01020304@synthetic.txt"
        for folder, data in (("a", b"first"), ("b", b"other")):
            nested = self.source/folder; nested.mkdir()
            (nested/name).write_bytes(data)
        _, plan = self.build()
        first = self.observe(plan.evidence_bytes, "a/"+name)
        second = self.observe(plan.evidence_bytes, "b/"+name)
        self.assertEqual(first.source.filename, second.source.filename)
        self.assertNotEqual(first.source.sha256, second.source.sha256)
        with self.assertRaisesRegex(check.SourceRevalidationError, "comparison_source_target_missing"):
            self.observe(plan.evidence_bytes, name)

    def test_untrusted_source_pc_b_and_invalid_path_stop_before_source_io(self):
        path, raw = self.seed()
        for flag in (False, None, 1, "true"):
            with patch.object(check, "build_run_input_evidence") as scan:
                with self.assertRaisesRegex(check.SourceRevalidationError, "comparison_source_untrusted"):
                    self.observe(raw, path.name, source_trusted=flag)
                scan.assert_not_called()
        _, pc_b = self.build(pc="PC-B")
        for evidence, relative in ((pc_b.evidence_bytes, path.name), (raw, "../escape"),
                                  (raw, "missing.txt"), (raw, "a\\b"), (raw, None)):
            with patch.object(check, "build_run_input_evidence") as scan:
                with self.assertRaises(check.SourceRevalidationError): self.observe(evidence, relative)
                scan.assert_not_called()

    def test_scope_clock_and_incomplete_or_broken_evidence_stop_before_source_io(self):
        path, raw = self.seed()
        for changes in ({"expected_run_id": "another-run"}, {"expected_root_id": "another-root"},
                        {"expected_relative_scope": "ErrorReport"}, {"current_utc_reliable": False}):
            with patch.object(check, "build_run_input_evidence") as scan:
                with self.assertRaises(check.SourceRevalidationError): self.observe(raw, path.name, **changes)
                scan.assert_not_called()
        incomplete = json.loads(raw)
        incomplete["enumeration"].update(status="incomplete", enumeration_errors=1)
        incomplete["validation"]["status"] = "incomplete"
        incomplete["integrity"]["digest"] = compute_evidence_digest(incomplete)
        for invalid in (b"{}", bytearray(raw), json.dumps(incomplete).encode()):
            with patch.object(check, "build_run_input_evidence") as scan:
                with self.assertRaises(check.SourceRevalidationError): self.observe(invalid, path.name)
                scan.assert_not_called()

    def test_changes_anywhere_in_inventory_block_selected_source_without_rewriting_b2(self):
        path, raw = self.seed()
        other = self.source / "20260902_01020304@other.txt"
        other.write_bytes(b"other")
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_inventory_observation_changed"):
            self.observe(raw, path.name)
        self.assertEqual(b"first", path.read_bytes())
        other.unlink()
        path.write_bytes(b"other")
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_inventory_observation_changed"):
            self.observe(raw, path.name)
        self.assertEqual(b"other", path.read_bytes())

    def test_source_is_reobserved_on_every_call_and_read_failure_is_sanitized(self):
        path, raw = self.seed()
        original = check.build_run_input_evidence
        with patch.object(check, "build_run_input_evidence", wraps=original) as scan:
            self.assertEqual(self.observe(raw, path.name), self.observe(raw, path.name))
            self.assertEqual(2, scan.call_count)
        with patch.object(check, "build_run_input_evidence", side_effect=OSError("synthetic-private-detail")):
            with self.assertRaises(check.SourceRevalidationError) as caught: self.observe(raw, path.name)
        self.assertNotIn("synthetic-private-detail", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)

    def test_full_source_page_download_comparison_connection_never_grants_authority(self):
        path, raw = self.seed()
        source = self.observe(raw, path.name)
        remote = DriveFileObservation("synthetic-file", path.name, 5, None)
        listing = collect_drive_listing((DriveListingPage("synthetic-folder", None, None, (remote,), True),),
            expected_folder_id="synthetic-folder")
        downloaded = hash_downloaded_content(remote.file_id, (b"fi", b"rst"),
            expected_size_bytes=5, download_completed=True)
        result = compare_drive_content(source.source, listing.files, source_trusted=True,
            expected_folder_id="synthetic-folder", observed_folder_id=listing.folder_id,
            enumeration_completed=listing.enumeration_completed, downloads=(downloaded,))
        self.assertEqual("comparison_candidate", result.status)
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)
        self.assertEqual(raw, source.evidence_bytes)
        self.assertEqual(b"first", path.read_bytes())
        self.assertEqual([], list(self.candidate.iterdir()))
        untrusted = compare_drive_content(source.source, listing.files, source_trusted=False,
            expected_folder_id="synthetic-folder", observed_folder_id=listing.folder_id,
            enumeration_completed=True, downloads=(downloaded,))
        self.assertEqual("comparison_source_untrusted", untrusted.reason_code)


if __name__ == "__main__": unittest.main()
