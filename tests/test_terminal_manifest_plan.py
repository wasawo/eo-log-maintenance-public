"""Transition plus B2/report integration, with no writer or runtime authority."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta
import hashlib
import json
import unittest
from unittest.mock import patch

from Common.ManifestTransitionInspection import ManifestTransitionError, prepare_terminal_manifest_transition
from Common.RunInputEvidenceIntegrity import compute_evidence_digest
from test_aggregation_report_builder import SCHEMAS, NOW, encode, fixture, error


def prior_for(after):
    before = deepcopy(after)
    before.update(status="running", finished_at_utc=None, outcome=None)
    for file in before["files"]:
        file.update(status="uploaded" if file["status"] == "verified" else "pending", drive_file_id=None)
        file["verification"] = dict(status="not_checked", method="not_performed",
                                    checked_at_utc=None, observed_sha256=None)
    return before


def prepare(before, after, evidence, **changes):
    options = dict(manifest_path="manifests/synthetic.json", evidence_path="evidence/synthetic.json",
                   current_utc=NOW, current_utc_reliable=True, **SCHEMAS)
    options.update(changes)
    return prepare_terminal_manifest_transition(before, after, evidence, **options)


class TerminalManifestPlanTests(unittest.TestCase):
    def test_approved_aggregation_cases_connect_to_listed_pairs_for_both_log_types(self):
        cases = [
            ((), {}), (((9, "verified"),), {"enumeration": "failed"}),
            (((8, "verified"), (9, "verified")), {}),
            (((9, "verified"), (9, "failed")), {}),
            (((9, "verified"), (9, "unknown")), {}),
            (((9, "verified"),), {"errors": [error()]}),
            (((9, "unknown"),), {"errors": [error()]}),
            (((9, "failed"),), {}), ((), {"ineligible": 3}),
            ((), {"errors": [error()]}), (((8, "verified"), (9, "failed")), {}),
            (((9, "verified"),), {}),
        ]
        for log_type in ("BattleLog", "ErrorReport"):
            for outcomes, options in cases:
                with self.subTest(log_type=log_type, outcomes=outcomes, options=options):
                    after, evidence = fixture(outcomes, log_type=log_type, **options)
                    old, new, raw = encode(prior_for(after)), encode(after), encode(evidence)
                    plan = prepare(old, new, raw)
                    report = json.loads(plan.report_bytes)
                    self.assertEqual(after["status"], report["run_aggregation"]["status"])
                    self.assertEqual((old, new, raw), (plan.expected_bytes, plan.proposed_bytes, plan.evidence_bytes))
                    self.assertEqual(hashlib.sha256(new).hexdigest(), report["manifest_ref"]["sha256"])
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), report["evidence_ref"]["sha256"])
                    self.assertFalse(plan.may_publish or plan.may_archive or plan.may_change_state)

    def test_valid_aggregate_cannot_bypass_illegal_transition_or_inventory_change(self):
        after, evidence = fixture(((9, "verified"),))
        before = prior_for(after)
        before["files"][0]["status"] = "pending"
        with self.assertRaisesRegex(ManifestTransitionError, "unlisted_file_transition"):
            prepare(encode(before), encode(after), encode(evidence))
        before = prior_for(after)
        before["files"][0]["size_bytes"] += 1
        with self.assertRaisesRegex(ManifestTransitionError, "frozen_inventory_changed"):
            prepare(encode(before), encode(after), encode(evidence))

    def test_listed_pairs_cannot_bypass_wrong_aggregate_or_unfinished_file(self):
        after, evidence = fixture(((9, "unknown"),))
        before = prior_for(after)
        after["status"] = "success"
        with self.assertRaisesRegex(ManifestTransitionError, "manifest_aggregation_mismatch"):
            prepare(encode(before), encode(after), encode(evidence))
        after, evidence = fixture(((9, "failed"),))
        before = prior_for(after)
        after["files"][0]["status"] = "uploaded"
        with self.assertRaisesRegex(ManifestTransitionError, "file_not_terminal"):
            prepare(encode(before), encode(after), encode(evidence))

    def test_b2_digest_scope_and_inventory_must_all_match(self):
        after, evidence = fixture(((9, "verified"),))
        old, new = encode(prior_for(after)), encode(after)
        for corruption in ("digest", "scope", "inventory"):
            changed = deepcopy(evidence)
            if corruption == "digest": changed["integrity"]["digest"] = "0" * 64
            if corruption == "scope": changed["pc_id"] = "PC-B"
            if corruption == "inventory": changed["inventory"]["targets"][0]["size_bytes"] += 1
            if corruption != "digest": changed["integrity"]["digest"] = compute_evidence_digest(changed)
            with self.subTest(corruption=corruption), self.assertRaises(ManifestTransitionError):
                prepare(old, new, encode(changed))

    def test_relevant_errors_cannot_be_turned_into_no_work(self):
        after, evidence = fixture((), errors=[error()])
        before = prior_for(after)
        after.update(status="success", outcome="no_work")
        with self.assertRaisesRegex(ManifestTransitionError, "manifest_aggregation_mismatch"):
            prepare(encode(before), encode(after), encode(evidence))

    def test_terminal_bytes_immutable_and_exact_repeat_is_not_a_receipt(self):
        after, evidence = fixture(((9, "verified"),))
        raw = encode(after)
        first = prepare(raw, raw, encode(evidence))
        self.assertEqual(first, prepare(raw, raw, encode(evidence)))
        self.assertFalse(first.may_publish)
        with self.assertRaisesRegex(ManifestTransitionError, "terminal_manifest_immutable"):
            prepare(raw, raw + b"\n", encode(evidence))
        with self.assertRaises(FrozenInstanceError): first.report_bytes = b"other"
        self.assertNotIn("synthetic", repr(first))

    def test_missing_prior_running_proposal_bad_schema_or_clock_fail_closed(self):
        after, evidence = fixture(((9, "verified"),))
        old, new, raw = encode(prior_for(after)), encode(after), encode(evidence)
        with self.assertRaisesRegex(ManifestTransitionError, "terminal_prior_bytes_required"):
            prepare(None, new, raw)
        with self.assertRaisesRegex(ManifestTransitionError, "manifest_not_terminal"):
            prepare(old, old, raw)
        for context in ({"current_utc_reliable": False}, {"current_utc": NOW - timedelta(days=1)},
                        {"evidence_schema": {"$ref": "https://invalid.example/schema"}},
                        {"evidence_path": "../escape.json"}):
            with self.subTest(context=context), self.assertRaises(ManifestTransitionError) as caught:
                prepare(old, new, raw, **context)
            self.assertIsNone(caught.exception.__cause__)
            self.assertNotIn("synthetic", str(caught.exception))

    def test_exact_noncanonical_bytes_and_determinism_without_io(self):
        after, evidence = fixture(((9, "verified"),))
        old = encode(prior_for(after))
        new = json.dumps(after, indent=2).encode()
        raw = json.dumps(evidence, indent=3).encode()
        with patch("builtins.open", side_effect=AssertionError("unexpected_file")), \
             patch("socket.socket", side_effect=AssertionError("unexpected_network")), \
             patch("os.replace", side_effect=AssertionError("unexpected_publish")):
            plan = prepare(old, new, raw)
            self.assertEqual(plan, prepare(old, new, raw))
        self.assertEqual((old, new, raw), (plan.expected_bytes, plan.proposed_bytes, plan.evidence_bytes))
        report = json.loads(plan.report_bytes)
        self.assertEqual(hashlib.sha256(new).hexdigest(), report["manifest_ref"]["sha256"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), report["evidence_ref"]["sha256"])

    def test_pc_b_is_supported_without_archive_permission(self):
        after, evidence = fixture(((9, "verified"),))
        after["pc_id"] = evidence["pc_id"] = "PC-B"
        evidence["integrity"]["digest"] = compute_evidence_digest(evidence)
        plan = prepare(encode(prior_for(after)), encode(after), encode(evidence))
        self.assertEqual("PC-B", json.loads(plan.report_bytes)["pc_id"])
        self.assertFalse(plan.may_archive)


if __name__ == "__main__": unittest.main()
