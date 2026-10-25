"""Synthetic source enumeration -> B2 -> initial plan -> candidate publication."""
from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common import SourceInventoryEvidenceBuilder as builder
from Common.ArtifactSetPublication import ArtifactSetPublicationError, publish_artifact_set_marker_last
from Common.ArtifactSetDirectoryVerification import verify_published_artifact_set
from Common.ManifestTransitionInspection import ManifestTransitionError, prepare_initial_manifest
from Common.OwnedRunLock import acquire_owned_lock
from Common.RunInputEvidenceIntegrity import compute_evidence_digest, compute_inventory_digest
from test_aggregation_report_builder import SCHEMAS, NOW

START = NOW - timedelta(seconds=3)


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW - timedelta(seconds=1)


class InitialSourceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eolm-initial-source-")
        self.root = Path(self.temp.name)
        self.addCleanup(self.cleanup)
        self.source = self.root / "source"
        self.source.mkdir()
        self.candidate = self.root / "candidate"
        self.candidate.mkdir()
        self.run = str(uuid4())  # Test identity only, never a runtime allocator.
        self.transaction = str(uuid4())

    def cleanup(self):
        self.assertEqual(Path(tempfile.gettempdir()).resolve(), self.root.parent.resolve())
        self.assertTrue(self.root.name.startswith("eolm-initial-source-"))
        self.assertEqual(self.root, self.root.resolve())
        self.temp.cleanup()

    def plan_context(self, pc="PC-A", log="BattleLog", run=None):
        return dict(expected_pc_id=pc, expected_log_type=log,
            expected_target_period="2026-09" if log == "BattleLog" else "2025",
            expected_run_id=self.run if run is None else run,
            started_at_utc=START.isoformat().replace("+00:00", "Z"),
            current_utc=NOW, current_utc_reliable=True,
            manifest_schema=SCHEMAS["manifest_schema"], evidence_schema=SCHEMAS["evidence_schema"])

    def build(self, *, pc="PC-A", log="BattleLog", source=None, run=None):
        source = self.source if source is None else source
        self.assertTrue(source.resolve().is_relative_to(self.root.resolve()))
        context = self.plan_context(pc, log, run)
        with patch.object(builder, "datetime", FixedDateTime):
            e = builder.build_run_input_evidence(source, root_id="synthetic-source", relative_scope=log,
                pc_id=pc, log_type=log, run_id=context["expected_run_id"], evidence_id="synthetic-evidence",
                reference_date=date(2026, 10, 1), started_at=START)
        raw = builder.serialize_evidence(e, SCHEMAS["evidence_schema"])
        return e, prepare_initial_manifest(raw, **context)

    def publish(self, plan):
        m = json.loads(plan.proposed_bytes)
        name = f'{m["pc_id"]}_{m["log_type"]}_{m["target_period"]}_{m["run_id"]}.json'
        payloads = {name: plan.proposed_bytes, "evidence.json": plan.evidence_bytes}
        with acquire_owned_lock("synthetic-" + self.transaction, self.root / "owner.json", timeout_seconds=0):
            result = publish_artifact_set_marker_last(str(self.candidate), payloads, transaction_id=self.transaction)
            expected = {name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()}
            verified = verify_published_artifact_set(self.candidate, expected, expected_transaction_id=self.transaction)
            self.assertTrue(verified.may_report_committed)  # Immutable candidate set only.
        return payloads, result

    def test_actual_source_hashes_bind_pending_targets_for_both_pcs_and_log_types(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                source = self.source / (pc + log)
                source.mkdir()
                nested = source / "合成"; nested.mkdir()
                name = "20260901_01020304@synthetic.txt" if log == "BattleLog" else "20250901_01020304.txt"
                (nested / name).write_bytes(b"synthetic-source")
                before = (nested / name).read_bytes()
                e, plan = self.build(pc=pc, log=log, source=source)
                m = json.loads(plan.proposed_bytes)
                self.assertEqual("completed", e["enumeration"]["status"])
                self.assertEqual(("合成/" + name, len(before), hashlib.sha256(before).hexdigest(), "pending"),
                    tuple(m["files"][0][key] for key in ("relative_path", "size_bytes", "sha256", "status")))
                self.assertEqual(before, (nested / name).read_bytes())
                self.assertFalse(plan.may_publish or plan.may_upload or plan.may_archive)

    def test_empty_ineligible_and_invalid_inputs_preserve_coverage_without_success(self):
        for label, name, eligible, ineligible, invalid in (
                ("empty", None, 0, 0, 0), ("ineligible", "20261001_01020304@future.txt", 0, 1, 0),
                ("invalid", "unexpected.txt", 0, 0, 1)):
            source = self.source / label; source.mkdir()
            if name is not None: (source / name).write_bytes(b"synthetic")
            e, plan = self.build(source=source)
            self.assertEqual((eligible, ineligible, invalid), tuple(e["validation"][key] for key in
                ("valid_eligible_count", "valid_ineligible_count", "invalid_relevant_count")))
            self.assertEqual("completed", e["validation"]["status"])
            m = json.loads(plan.proposed_bytes)
            self.assertEqual(("running", None), (m["status"], m["outcome"]))

    def test_hash_failure_remains_incomplete_and_does_not_reset_to_no_work(self):
        path = self.source / "20260901_01020304@synthetic.txt"
        path.write_bytes(b"synthetic")
        with patch.object(builder, "_hash_stable_file", side_effect=builder.InventoryBuildError("source_mutation_detected")):
            e, plan = self.build()
        self.assertEqual("incomplete", e["enumeration"]["status"])
        self.assertEqual("incomplete", e["validation"]["status"])
        self.assertGreater(e["enumeration"]["enumeration_errors"], 0)
        self.assertEqual(("running", None, []), tuple(json.loads(plan.proposed_bytes)[key] for key in
            ("status", "outcome", "files")))
        self.assertEqual(b"synthetic", path.read_bytes())

    def test_source_changes_do_not_rewrite_the_frozen_plan_and_new_run_gets_fresh_hash(self):
        path = self.source / "20260901_01020304@synthetic.txt"
        path.write_bytes(b"first")
        _, plan = self.build()
        before = plan.proposed_bytes
        path.write_bytes(b"second")
        _, newer = self.build(run=str(uuid4()))
        self.assertEqual(before, plan.proposed_bytes)
        self.assertNotEqual(json.loads(before)["run_id"], json.loads(newer.proposed_bytes)["run_id"])
        self.assertNotEqual(json.loads(before)["files"][0]["sha256"], json.loads(newer.proposed_bytes)["files"][0]["sha256"])
        self.assertFalse(plan.may_upload or newer.may_upload)

    @unittest.skipUnless(os.name == "nt", "Windows mutex/publication required")
    def test_real_create_only_candidate_set_readback_leaves_sources_unchanged(self):
        path = self.source / "20260901_01020304@synthetic.txt"
        path.write_bytes(b"synthetic")
        _, plan = self.build(pc="PC-B")
        payloads, result = self.publish(plan)
        self.assertEqual(3, len(result))
        for name, raw in payloads.items(): self.assertEqual(raw, (self.candidate / name).read_bytes())
        self.assertEqual(b"synthetic", path.read_bytes())
        self.assertFalse((self.root / "owner.json").exists())
        self.assertFalse(plan.may_archive)

    @unittest.skipUnless(os.name == "nt", "Windows mutex/publication required")
    def test_conflicting_candidate_is_preserved_without_marker(self):
        _, plan = self.build()
        m = json.loads(plan.proposed_bytes)
        name = f'PC-A_BattleLog_2026-09_{m["run_id"]}.json'
        path = self.candidate / name
        path.write_bytes(b"synthetic_foreign")
        with self.assertRaises(ArtifactSetPublicationError): self.publish(plan)
        self.assertEqual(b"synthetic_foreign", path.read_bytes())
        self.assertFalse((self.candidate / "commit-marker.json").exists())

    def test_schema_valid_eligible_target_with_invalid_filename_is_rejected(self):
        (self.source / "20260901_01020304@synthetic.txt").write_bytes(b"synthetic")
        e, _ = self.build()
        for name in ("unexpected.txt", "20260230_01020304@synthetic.txt"):
            target = e["inventory"]["targets"][0]
            target["filename"] = target["relative_path"] = name
            e["enumeration"]["inventory_sha256"] = compute_inventory_digest(e["inventory"]["targets"])
            e["integrity"]["digest"] = compute_evidence_digest(e)
            raw = builder.serialize_evidence(e, SCHEMAS["evidence_schema"])
            with self.assertRaisesRegex(ManifestTransitionError, "initial_inventory_filename_unclassifiable"):
                prepare_initial_manifest(raw, **self.plan_context())

    def test_same_fixed_observations_produce_deterministic_b2_and_plan(self):
        (self.source / "20260901_01020304@synthetic.txt").write_bytes(b"synthetic")
        _, first = self.build()
        _, second = self.build()
        self.assertEqual(first, second)
        self.assertFalse(first.may_publish)


if __name__ == "__main__": unittest.main()
