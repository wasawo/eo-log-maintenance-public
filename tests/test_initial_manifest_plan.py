"""Pure B2 -> running/pending construction and synthetic lifecycle connection."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

from Common.ManifestTransitionInspection import (
    ManifestTransitionError, prepare_initial_manifest, prepare_terminal_manifest_transition,
    inspect_manifest_transition,
)
from Common.RunInputEvidenceIntegrity import compute_evidence_digest, compute_inventory_digest
from test_aggregation_report_builder import fixture, encode, SCHEMAS, NOW, error


def prepare(evidence, manifest, **changes):
    options = dict(expected_pc_id=manifest["pc_id"], expected_log_type=manifest["log_type"],
        expected_target_period=manifest["target_period"], expected_run_id=manifest["run_id"],
        started_at_utc=manifest["started_at_utc"], current_utc=NOW, current_utc_reliable=True,
        manifest_schema=SCHEMAS["manifest_schema"], evidence_schema=SCHEMAS["evidence_schema"])
    options.update(changes)
    return prepare_initial_manifest(evidence, **options)


class InitialManifestPlanTests(unittest.TestCase):
    def test_both_pc_and_log_scopes_generate_only_running_pending(self):
        for pc in ("PC-A", "PC-B"):
            for log_type in ("BattleLog", "ErrorReport"):
                with self.subTest(pc=pc, log_type=log_type):
                    m, e = fixture(((8, "verified"), (9, "unknown")), log_type=log_type)
                    m["pc_id"] = e["pc_id"] = pc
                    e["integrity"]["digest"] = compute_evidence_digest(e)
                    raw = encode(e)
                    plan = prepare(raw, m)
                    value = json.loads(plan.proposed_bytes)
                    self.assertEqual(("running", None, None), (value["status"], value["outcome"], value["finished_at_utc"]))
                    self.assertEqual(raw, plan.evidence_bytes)
                    for file, target in zip(value["files"], e["inventory"]["targets"]):
                        self.assertEqual((target["relative_path"], target["size_bytes"], target["expected_sha256"]),
                            (file["relative_path"], file["size_bytes"], file["sha256"]))
                        self.assertEqual("pending", file["status"])
                        self.assertIsNone(file["drive_file_id"])
                        self.assertEqual(dict(status="not_checked", method="not_performed", checked_at_utc=None,
                            observed_sha256=None), file["verification"])
                    self.assertFalse(plan.may_publish or plan.may_upload or plan.may_archive)

    def test_empty_incomplete_failed_or_error_b2_never_become_success_no_work(self):
        for changes in ({}, {"enumeration": "failed"}, {"validation": "incomplete"}, {"errors": [error()]}):
            m, e = fixture((), **changes)
            plan = prepare(encode(e), m)
            value = json.loads(plan.proposed_bytes)
            self.assertEqual(("running", None, []), (value["status"], value["outcome"], value["files"]))
            self.assertEqual(encode(e), plan.evidence_bytes)

    def test_independent_scope_and_required_run_context_are_not_inferred(self):
        m, e = fixture(((9, "verified"),))
        for changes in ({"expected_pc_id": "PC-B"}, {"expected_log_type": "ErrorReport"},
                {"expected_run_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"}, {"expected_run_id": None},
                {"expected_target_period": "2026-13"}, {"started_at_utc": None}):
            with self.subTest(changes=changes), self.assertRaises(ManifestTransitionError):
                prepare(encode(e), m, **changes)

    def test_invalid_b2_digest_counts_duplicate_keys_and_schema_are_not_repaired(self):
        m, e = fixture(((9, "verified"),))
        variants = []
        changed = deepcopy(e); changed["integrity"]["digest"] = "0" * 64; variants.append(encode(changed))
        changed = deepcopy(e); changed["enumeration"]["eligible_target_count"] += 1
        changed["integrity"]["digest"] = compute_evidence_digest(changed); variants.append(encode(changed))
        changed = deepcopy(e); changed["unknown"] = True; variants.append(encode(changed))
        variants.extend((None, b"{}", b'{"pc_id":"PC-A","pc_id":"PC-B"}'))
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(ManifestTransitionError) as caught:
                prepare(raw, m)
            self.assertIsNone(caught.exception.__cause__)

    def test_original_start_spelling_unicode_paths_and_evidence_bytes_are_preserved(self):
        m, e = fixture(((9, "verified"),))
        e["inventory"]["targets"][0]["relative_path"] = "合成/" + e["inventory"]["targets"][0]["filename"]
        e["enumeration"]["inventory_sha256"] = compute_inventory_digest(e["inventory"]["targets"])
        e["integrity"]["digest"] = compute_evidence_digest(e)
        raw = json.dumps(e, ensure_ascii=False, indent=3).encode("utf-8")
        start = "2026-10-21T00:00:00.00000000000Z"
        plan = prepare(raw, m, started_at_utc=start)
        self.assertEqual(start, json.loads(plan.proposed_bytes)["started_at_utc"])
        self.assertIn("合成".encode(), plan.proposed_bytes)
        self.assertEqual(raw, plan.evidence_bytes)

    def test_time_order_null_untrusted_clock_and_future_boundary(self):
        m, e = fixture(((9, "verified"),))
        for changes in ({"started_at_utc": "2026-10-21T00:00:02Z"}, {"current_utc_reliable": False},
                {"current_utc_reliable": 1}, {"current_utc": NOW.replace(tzinfo=None)}):
            with self.subTest(changes=changes), self.assertRaises(ManifestTransitionError):
                prepare(encode(e), m, **changes)
        for finish in (None, "2026-10-20T23:59:59Z"):
            changed = deepcopy(e)
            changed["enumeration"]["finished_at_utc"] = finish
            changed["integrity"]["digest"] = compute_evidence_digest(changed)
            with self.assertRaises(ManifestTransitionError): prepare(encode(changed), m)
        boundary_now = NOW - timedelta(seconds=2, minutes=5)
        prepare(encode(e), m, current_utc=boundary_now)
        with self.assertRaisesRegex(ManifestTransitionError, "initial_timestamp_in_future"):
            prepare(encode(e), m, current_utc=boundary_now - timedelta(microseconds=1))

    def test_deterministic_immutable_plan_has_no_io_or_external_schema_retrieval(self):
        m, e = fixture(((9, "verified"),))
        raw = encode(e)
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")), \
             patch("socket.socket", side_effect=AssertionError("unexpected_network")):
            plan = prepare(raw, m)
            self.assertEqual(plan, prepare(raw, m))
            with self.assertRaises(ManifestTransitionError):
                prepare(raw, m, evidence_schema={"$ref": "https://synthetic.invalid/schema"})
        with self.assertRaises(FrozenInstanceError): plan.proposed_bytes = b"changed"
        self.assertNotIn(m["run_id"], repr(plan))

    def test_initial_plan_connects_through_listed_pairs_to_terminal_report(self):
        after, e = fixture(((9, "verified"),))
        raw_e = encode(e)
        plan = prepare(raw_e, after)
        previous = plan.proposed_bytes
        for state in ("staging", "ready", "pending", "uploaded"):
            value = json.loads(previous)
            value["files"][0]["status"] = state
            if state == "uploaded": value["files"][0]["drive_file_id"] = "synthetic-file"
            proposed = encode(value)
            self.assertEqual("requires_runtime_evidence", inspect_manifest_transition(previous, proposed,
                manifest_schema=SCHEMAS["manifest_schema"])["status"])
            previous = proposed
        terminal = prepare_terminal_manifest_transition(previous, encode(after), raw_e,
            manifest_path="manifest.json", evidence_path="evidence.json", current_utc=NOW,
            current_utc_reliable=True, **SCHEMAS)
        self.assertEqual("success", json.loads(terminal.report_bytes)["run_aggregation"]["status"])
        self.assertFalse(terminal.may_publish or terminal.may_archive or terminal.may_change_state)


if __name__ == "__main__": unittest.main()
