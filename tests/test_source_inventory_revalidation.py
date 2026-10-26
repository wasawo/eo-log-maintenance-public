"""Synthetic read-only frozen-source comparisons, not runtime qualification."""
from dataclasses import FrozenInstanceError
from datetime import date
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common import SourceInventoryRevalidation as check
from Common import SourceInventoryEvidenceBuilder as builder
import test_initial_source_integration as source_fixture
from test_aggregation_report_builder import SCHEMAS, NOW


class SourceInventoryRevalidationTests(unittest.TestCase):
    def test_all_read_entrypoints_reject_invalid_budgets_before_parsing_or_io(self):
        _, plan = self.seed()
        common = dict(expected_log_type="BattleLog", expected_run_id=self.run,
            expected_root_id="synthetic-source", expected_relative_scope="BattleLog",
            reference_date=date(2026, 10, 1), current_utc=NOW, current_utc_reliable=True)
        comparison = dict(common, schema=SCHEMAS["evidence_schema"], source_trusted=True)
        initial = dict(self.plan_context(), ac_connected=True, expected_root_id="synthetic-source",
            expected_relative_scope="BattleLog", reference_date=date(2026, 10, 1))
        entries = (
            (check.revalidate_source_inventory, plan.evidence_bytes,
             dict(common, schema=SCHEMAS["evidence_schema"], expected_pc_id="PC-A")),
            (check.revalidate_initial_manifest_source, plan, initial),
            (check.revalidate_comparison_source, plan.evidence_bytes,
             dict(comparison, relative_path="20260901_01020304@synthetic.txt")),
            (check.revalidate_comparison_sources, plan.evidence_bytes, dict(comparison, relative_paths=())),
            (check.inspect_initial_inventory, plan.evidence_bytes, dict(comparison, relative_paths=(),
             drive_before=None, drive_after=None, download_plan=None, downloads=(), expected_folder_id="synthetic")),
        )
        for function, value, context in entries:
            for key in ("maximum_entries", "maximum_file_bytes", "maximum_total_hash_bytes"):
                for limit in (False, True, 0, -1, 1.0, "1"):
                    with self.subTest(entry=function.__name__, key=key, limit=limit), \
                            patch.object(check, "_parse") as parse, \
                            patch.object(check, "prepare_initial_manifest") as prepare, \
                            patch.object(check, "build_run_input_evidence") as read, \
                            patch.object(check, "compare_planned_drive_contents") as compare:
                        with self.assertRaisesRegex(check.SourceRevalidationError, "^source_revalidation_limit_invalid$"):
                            function(self.source, value, **context, **{key: limit})
                        for operation in (parse, prepare, read, compare): operation.assert_not_called()

    def test_recursive_budgets_revalidate_both_pcs_and_logs_without_changing_frozen_bytes(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                root = self.source / (pc + log); root.mkdir()
                nested = root / "nested"; nested.mkdir()
                names = (["20260901_01020304@a.txt", "20260902_01020304@b.txt"] if log == "BattleLog"
                         else ["20250901_01020304.txt", "20250902_01020304.txt"])
                for directory, name, data in zip((root, nested), names, (b"abc", b"defg")):
                    (directory / name).write_bytes(data)
                _, plan = self.build(pc=pc, log=log, source=root)
                expected = self.observe(plan.evidence_bytes, pc=pc, log=log, source=root)
                actual = self.observe(plan.evidence_bytes, pc=pc, log=log, source=root,
                    maximum_entries=3, maximum_file_bytes=4, maximum_total_hash_bytes=7)
                self.assertEqual(expected, actual)
                self.assertIs(plan.evidence_bytes, actual.evidence_bytes)
                self.assertFalse(actual.may_upload or actual.may_archive or actual.may_change_state)
                for limits in (dict(maximum_entries=2), dict(maximum_file_bytes=3),
                               dict(maximum_total_hash_bytes=6)):
                    with self.subTest(pc=pc, log=log, limits=limits), self.assertRaisesRegex(
                            check.SourceRevalidationError, "^source_revalidation_incomplete$"):
                        self.observe(plan.evidence_bytes, pc=pc, log=log, source=root, **limits)
                self.assertEqual(b"abc", (root / names[0]).read_bytes())
                self.assertEqual(b"defg", (nested / names[1]).read_bytes())

    setUp = source_fixture.InitialSourceIntegrationTests.setUp
    cleanup = source_fixture.InitialSourceIntegrationTests.cleanup
    plan_context = source_fixture.InitialSourceIntegrationTests.plan_context
    build = source_fixture.InitialSourceIntegrationTests.build

    def observe(self, raw, *, pc="PC-A", log="BattleLog", source=None, **changes):
        options = dict(schema=SCHEMAS["evidence_schema"], expected_pc_id=pc, expected_log_type=log,
            expected_run_id=self.run, expected_root_id="synthetic-source", expected_relative_scope=log,
            reference_date=date(2026, 10, 1), current_utc=NOW, current_utc_reliable=True)
        options.update(changes)
        return check.revalidate_source_inventory(self.source if source is None else source, raw, **options)

    def seed(self):
        path = self.source / "20260901_01020304@synthetic.txt"
        path.write_bytes(b"first")
        _, plan = self.build()
        return path, plan

    def test_same_observations_for_both_pcs_and_log_types_preserve_original_bytes(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                source = self.source / (pc + log); source.mkdir()
                name = "20260901_01020304@synthetic.txt" if log == "BattleLog" else "20250901_01020304.txt"
                path = source / name; path.write_bytes(b"synthetic")
                _, plan = self.build(pc=pc, log=log, source=source)
                result = self.observe(plan.evidence_bytes, pc=pc, log=log, source=source)
                self.assertEqual(plan.evidence_bytes, result.evidence_bytes)
                self.assertEqual(1, result.target_count)
                self.assertEqual("requires_runtime_evidence", result.status)
                self.assertFalse(result.may_upload or result.may_archive or result.may_change_state)
                self.assertEqual(b"synthetic", path.read_bytes())
                with self.assertRaises(FrozenInstanceError): result.target_count = 0
                self.assertNotIn(self.run, repr(result))

    def test_addition_removal_rename_and_same_size_content_change_are_rejected(self):
        for operation in ("add", "remove", "rename", "content"):
            source = self.source / operation; source.mkdir()
            path = source / "20260901_01020304@synthetic.txt"; path.write_bytes(b"first")
            _, plan = self.build(source=source)
            if operation == "add": (source / "20260902_01020304@other.txt").write_bytes(b"other")
            if operation == "remove": path.unlink()
            if operation == "rename": path.rename(source / "20260903_01020304@renamed.txt")
            if operation == "content": path.write_bytes(b"other")
            with self.subTest(operation=operation), self.assertRaisesRegex(check.SourceRevalidationError,
                    "source_inventory_observation_changed"):
                self.observe(plan.evidence_bytes, source=source)

    def test_changed_error_or_ineligible_classification_is_not_dropped(self):
        path, plan = self.seed()
        extra = self.source / "unexpected.txt"; extra.write_bytes(b"synthetic")
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_inventory_observation_changed"):
            self.observe(plan.evidence_bytes)
        extra.unlink()
        future = self.source / "20261001_01020304@future.txt"; future.write_bytes(b"future")
        with self.assertRaises(check.SourceRevalidationError): self.observe(plan.evidence_bytes)
        self.assertEqual(b"first", path.read_bytes())

    def test_known_errors_are_preserved_and_cannot_mean_run_success(self):
        (self.source / "unexpected.txt").write_bytes(b"synthetic")
        e, plan = self.build()
        self.assertEqual(1, e["validation"]["invalid_relevant_count"])
        result = self.observe(plan.evidence_bytes)
        self.assertEqual(plan.evidence_bytes, result.evidence_bytes)
        self.assertFalse(result.may_upload or result.may_change_state)

    def test_incomplete_frozen_b2_is_rejected_before_any_new_enumeration(self):
        self.seed()
        with patch.object(builder, "_hash_stable_file", side_effect=builder.InventoryBuildError("synthetic_uncertainty")):
            _, plan = self.build()
        with patch.object(check, "build_run_input_evidence") as read:
            with self.assertRaisesRegex(check.SourceRevalidationError, "source_frozen_coverage_incomplete"):
                self.observe(plan.evidence_bytes)
            read.assert_not_called()

    def test_new_scan_or_hash_failure_is_incomplete_without_mutating_the_frozen_record(self):
        _, plan = self.seed()
        original = plan.evidence_bytes
        with patch.object(builder.os, "scandir", side_effect=PermissionError("synthetic_private_detail")):
            with self.assertRaisesRegex(check.SourceRevalidationError, "source_revalidation_incomplete"):
                self.observe(original)
        with patch.object(builder, "_hash_stable_file", side_effect=builder.InventoryBuildError("synthetic_uncertainty")):
            with self.assertRaisesRegex(check.SourceRevalidationError, "source_revalidation_incomplete"):
                self.observe(original)
        self.assertEqual(original, plan.evidence_bytes)

    def test_independent_scope_clock_and_reference_date_are_checked_before_source_io(self):
        _, plan = self.seed()
        for changes in ({"expected_pc_id": "PC-B"}, {"expected_run_id": str(uuid4())},
                {"expected_root_id": "different"}, {"expected_relative_scope": "different"},
                {"current_utc_reliable": False}, {"reference_date": None}, {"reference_date": NOW}):
            with patch.object(check, "build_run_input_evidence") as read:
                with self.subTest(changes=changes), self.assertRaises(check.SourceRevalidationError):
                    self.observe(plan.evidence_bytes, **changes)
                read.assert_not_called()

    def test_non_target_contents_are_outside_the_frozen_target_comparison(self):
        self.seed()
        future = self.source / "20261001_01020304@future.txt"; future.write_bytes(b"before")
        _, plan = self.build()
        future.write_bytes(b"different content")
        result = self.observe(plan.evidence_bytes)
        self.assertEqual(1, result.target_count)
        self.assertFalse(result.may_upload)

    def test_corrupt_or_missing_frozen_bytes_cannot_generate_a_replacement(self):
        _, plan = self.seed()
        changed = json.loads(plan.evidence_bytes); changed["integrity"]["digest"] = "0" * 64
        for raw in (None, b"{}", json.dumps(changed).encode(), b'{"pc_id":"PC-A","pc_id":"PC-B"}'):
            with patch.object(check, "build_run_input_evidence") as read:
                with self.assertRaises(check.SourceRevalidationError) as caught: self.observe(raw)
                self.assertIsNone(caught.exception.__cause__)
                self.assertNotIn("synthetic_private_detail", str(caught.exception))
                read.assert_not_called()

    def test_empty_observation_is_non_authorizing_and_changed_cutoff_rejects(self):
        _, empty = self.build()
        result = self.observe(empty.evidence_bytes)
        self.assertEqual(0, result.target_count)
        self.assertFalse(result.may_upload or result.may_change_state)
        (self.source / "20261001_01020304@future.txt").write_bytes(b"future")
        _, frozen = self.build()
        with self.assertRaisesRegex(check.SourceRevalidationError, "source_inventory_observation_changed"):
            self.observe(frozen.evidence_bytes, reference_date=date(2026, 11, 1))


if __name__ == "__main__": unittest.main()
