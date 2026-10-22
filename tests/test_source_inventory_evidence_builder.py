"""Synthetic tests for read-only source enumeration and B2 evidence construction."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Common.SourceInventoryEvidenceBuilder import (
    InventoryBuildError,
    build_run_input_evidence,
    serialize_evidence,
)
import Common.SourceInventoryEvidenceBuilder as builder


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contracts/run-input-evidence-v1.schema.json").read_text(encoding="utf-8"))


class SourceInventoryEvidenceBuilderTests(unittest.TestCase):
    def build(self, root: Path, **kwargs):
        options = {
            "root_id": "source-a",
            "relative_scope": "BattleLog",
            "pc_id": "PC-A",
            "log_type": "BattleLog",
            "run_id": "11111111-2222-4333-8444-555555555555",
            "evidence_id": "evidence-test",
            "reference_date": date(2026, 10, 21),
            "started_at": datetime(2026, 10, 21, tzinfo=timezone.utc),
        }
        options.update(kwargs)
        return build_run_input_evidence(root, **options)

    def test_builds_sorted_inventory_with_sha256_and_valid_b2_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "20260902_01020304@b.txt").write_bytes(b"bravo")
            (root / "20260901_01020304@a.txt").write_bytes(b"alpha")
            (root / "20261001_01020304@future.txt").write_bytes(b"future")
            value = self.build(root)
            self.assertEqual(value["enumeration"]["status"], "completed")
            self.assertEqual(value["enumeration"]["entries_observed"], 3)
            self.assertEqual(value["enumeration"]["eligible_target_count"], 2)
            self.assertEqual(value["validation"]["valid_ineligible_count"], 1)
            self.assertEqual(
                [item["filename"] for item in value["inventory"]["targets"]],
                ["20260901_01020304@a.txt", "20260902_01020304@b.txt"],
            )
            self.assertEqual(len(serialize_evidence(value, SCHEMA)) > 0, True)

    def test_invalid_relevant_filename_is_recorded_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "unexpected.txt").write_bytes(b"x")
            value = self.build(root)
            self.assertEqual(value["validation"]["status"], "incomplete")
            self.assertEqual(value["validation"]["invalid_relevant_count"], 1)
            self.assertEqual(value["validation"]["errors"][0]["code"], "unclassifiable_relevant_filename")
            self.assertEqual(value["validation"]["errors"][0]["error_id"], "VAL-000001")
            serialize_evidence(value, SCHEMA)

    def test_nested_files_use_forward_slash_relative_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "2026" / "09"
            nested.mkdir(parents=True)
            (nested / "20260901_01020304@a.txt").write_bytes(b"payload")
            value = self.build(root)
            self.assertEqual(value["inventory"]["targets"][0]["relative_path"], "2026/09/20260901_01020304@a.txt")

    def test_unknown_pc_and_invalid_scope_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(InventoryBuildError, "unsupported_pc_id"):
                self.build(Path(temp), pc_id="PC-C")
            with self.assertRaisesRegex(InventoryBuildError, "invalid_relative_scope"):
                self.build(Path(temp), relative_scope="../BattleLog")


    def test_directory_enumeration_failure_marks_evidence_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(builder.os, "scandir", side_effect=OSError("synthetic")):
                value = self.build(Path(temp))
            self.assertEqual(value["enumeration"]["status"], "incomplete")
            self.assertGreater(value["enumeration"]["enumeration_errors"], 0)
            serialize_evidence(value, SCHEMA)

    def test_hash_uncertainty_marks_evidence_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "20260901_01020304@a.txt").write_bytes(b"payload")
            with patch.object(builder, "_hash_stable_file", side_effect=InventoryBuildError("source_mutation_detected")):
                value = self.build(root)
            self.assertEqual(value["enumeration"]["status"], "incomplete")
            self.assertGreater(value["enumeration"]["enumeration_errors"], 0)
            self.assertEqual(value["inventory"]["targets"], [])
            serialize_evidence(value, SCHEMA)

    def test_serialization_is_stable_for_same_frozen_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "20260901_01020304@a.txt").write_bytes(b"payload")
            value = self.build(root)
            first = serialize_evidence(value, SCHEMA)
            second = serialize_evidence(value, SCHEMA)
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
