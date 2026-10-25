"""Synthetic immediate-entry observation: preserve leftovers, never infer cleanup."""
from dataclasses import asdict, FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Common import StagingResidualObservation as check
from Common.SourceInventoryEvidenceBuilder import InventoryBuildError


class StagingResidualObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eolm-residual-observe-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def assert_no_authority(self, result):
        self.assertFalse(result.may_create_staging or result.may_upload or result.may_cleanup or result.may_archive)

    def test_empty_root_is_observed_without_creating_artifacts_or_granting_upload(self):
        result = check.observe_staging_residual_entries(self.root)
        self.assertEqual((True, 0, False), (result.enumeration_completed, result.entries_observed, result.warning_required))
        self.assertEqual("requires_runtime_evidence", result.status)
        self.assertEqual([], list(self.root.iterdir()))
        self.assert_no_authority(result)
        with self.assertRaises(FrozenInstanceError): result.may_upload = True

    def test_files_invalid_json_temp_and_directory_are_counted_without_reading_contents(self):
        for name in ("synthetic.bin", "metadata.json", "orphan.tmp"):
            (self.root/name).write_bytes(b"synthetic-private-payload")
        nested = self.root/"nested"; nested.mkdir()
        (nested/"uninspected.txt").write_bytes(b"nested")
        with patch("builtins.open", side_effect=AssertionError("content read")), \
                patch.object(Path, "open", side_effect=AssertionError("content read")):
            result = check.observe_staging_residual_entries(self.root)
        self.assertEqual((4, 3, 1, 0), (result.entries_observed, result.regular_file_count,
                                     result.directory_count, result.other_entry_count))
        self.assertTrue(result.warning_required)
        self.assertTrue(result.enumeration_completed)
        serialized = json.dumps(asdict(result))
        for private in (str(self.root), "metadata.json", "synthetic-private-payload"):
            self.assertNotIn(private, serialized)
        self.assertEqual(b"synthetic-private-payload", (self.root/"metadata.json").read_bytes())
        self.assert_no_authority(result)

    def test_missing_file_relative_and_null_roots_hold_without_repair(self):
        file = self.root/"file"; file.write_bytes(b"preserve")
        missing = self.root/"missing"
        for root in (missing, file, "relative", "", None):
            result = check.observe_staging_residual_entries(root)
            self.assertEqual(("held", False, 0), (result.status, result.enumeration_completed, result.entries_observed))
            self.assert_no_authority(result)
        self.assertFalse(missing.exists())
        self.assertEqual(b"preserve", file.read_bytes())

    def test_reparse_or_initial_enumeration_failure_is_not_completed_zero_work(self):
        for failure in (OSError("private-error"), InventoryBuildError("source_reparse_component")):
            with patch.object(check, "_enumeration_snapshot", side_effect=failure):
                result = check.observe_staging_residual_entries(self.root)
            self.assertEqual(("held", False, 1), (result.status, result.enumeration_completed, result.observation_errors))
            self.assertNotIn("private-error", repr(result))
            self.assert_no_authority(result)

    def test_late_addition_preserves_observed_counts_and_all_files(self):
        first = self.root/"first.bin"; first.write_bytes(b"first")
        real = check._enumeration_snapshot
        calls = 0
        def changed(root):
            nonlocal calls
            value = real(root); calls += 1
            if calls == 1: (self.root/"late.bin").write_bytes(b"late")
            return value
        with patch.object(check, "_enumeration_snapshot", side_effect=changed):
            result = check.observe_staging_residual_entries(self.root)
        self.assertEqual(("held", False, 1, True), (result.status, result.enumeration_completed,
                                                result.entries_observed, result.warning_required))
        self.assertEqual(b"first", first.read_bytes())
        self.assertEqual(b"late", (self.root/"late.bin").read_bytes())

    def test_final_failure_keeps_initial_counts_and_does_not_emit_raw_exception(self):
        (self.root/"preserve.bin").write_bytes(b"preserve")
        real = check._enumeration_snapshot
        calls = 0
        def failed(root):
            nonlocal calls
            calls += 1
            if calls > 1: raise PermissionError("private-error")
            return real(root)
        with patch.object(check, "_enumeration_snapshot", side_effect=failed):
            result = check.observe_staging_residual_entries(self.root)
        self.assertEqual((False, 1), (result.enumeration_completed, result.entries_observed))
        self.assertNotIn("private-error", repr(result))
        self.assert_no_authority(result)

    def test_nested_directories_are_never_enumerated(self):
        nested = self.root/"nested"; nested.mkdir()
        (nested/"content.txt").write_bytes(b"preserve")
        from Common import SourceInventoryEvidenceBuilder as builder
        real = builder.os.scandir
        def root_only(path):
            if Path(path) != self.root: raise AssertionError("nested traversal")
            return real(path)
        with patch.object(builder.os, "scandir", side_effect=root_only):
            result = check.observe_staging_residual_entries(self.root)
        self.assertTrue(result.enumeration_completed)
        self.assertEqual(1, result.directory_count)

    def test_duplicate_observed_names_cannot_certify_complete_enumeration(self):
        (self.root/"one.bin").write_bytes(b"preserve")
        entries, snapshot = check._enumeration_snapshot(self.root)
        for observations in ([(entries+entries, snapshot)],
                             [(entries, snapshot), (entries+entries, snapshot)]):
            with patch.object(check, "_enumeration_snapshot", side_effect=observations):
                result = check.observe_staging_residual_entries(self.root)
            self.assertEqual((False, 1), (result.enumeration_completed, result.entries_observed))
            self.assert_no_authority(result)


if __name__ == "__main__": unittest.main()
