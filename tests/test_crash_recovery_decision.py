"""Synthetic tests for pure crash-recovery evidence classification."""
from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from Common.CrashRecoveryDecision import decide_crash_recovery


class CrashRecoveryDecisionTests(unittest.TestCase):
    def test_nonlocal_schema_references_never_enable_recovery_or_network(self):
        original = self.kwargs["prior_manifest_bytes"]
        for keyword in ("$ref", "$dynamicRef"):
            for reference in ("https://synthetic.invalid/schema", "file:///synthetic-schema",
                              "relative-schema.json", "", None, 1):
                for schema in ({keyword: reference}, {"$defs": {"unused": {keyword: reference}}}):
                    with self.subTest(keyword=keyword, reference=reference), \
                            patch.object(Path, "read_text", return_value=json.dumps(schema)), \
                            patch("socket.socket", side_effect=AssertionError("must not retrieve")) as network:
                        result = self.decide()
                        self.assertEqual("prior_manifest_invalid_or_not_running", result.reason_code)
                        self.assertFalse(result.may_start_new_run)
                        self.assertTrue(result.preserve_prior_manifest)
                        network.assert_not_called()
        self.assertEqual(original, self.kwargs["prior_manifest_bytes"])

    def test_registry_blocks_retrieval_even_if_reference_preflight_is_bypassed(self):
        with patch("Common.CrashRecoveryDecision._require_local_schema_refs"), \
                patch.object(Path, "read_text", return_value='{"$ref":"https://synthetic.invalid/schema"}'), \
                patch("socket.socket", side_effect=AssertionError("must not retrieve")) as network:
            self.assertEqual("prior_manifest_invalid_or_not_running", self.decide().reason_code)
            network.assert_not_called()

    def test_local_schema_reference_support_and_broken_schema_rejection_are_preserved(self):
        expected = self.decide()
        path = Path(__file__).resolve().parents[1] / "contracts/manifest-v1.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["$defs"]["synthetic_local"] = True
        schema["allOf"].append({"$ref": "#/$defs/synthetic_local"})
        with patch.object(Path, "read_text", return_value=json.dumps(schema)):
            self.assertEqual(expected, self.decide())
        for invalid in ({"$ref": "#/$defs/missing"}, {"type": "synthetic-invalid"}):
            with self.subTest(schema=invalid), patch.object(Path, "read_text", return_value=json.dumps(invalid)):
                self.assertEqual("prior_manifest_invalid_or_not_running", self.decide().reason_code)

    def setUp(self):
        self.manifest = {
            "schema_version": 1,
            "run_id": "123e4567-e89b-42d3-a456-426614174000",
            "pc_id": "PC-A",
            "log_type": "BattleLog",
            "target_period": "2026-09",
            "status": "running",
            "outcome": None,
            "started_at_utc": "2026-10-21T10:00:00Z",
            "finished_at_utc": None,
            "files": [],
        }
        self.lock = {
            "schema_version": 1,
            "scope_id": "PC-A",
            "owner_token": "a" * 64,
            "pid": 1234,
            "host": "test-host",
        }
        self.kwargs = dict(
            mutex_abandoned=True,
            lock_record=self.lock,
            expected_scope="PC-A",
            expected_host="test-host",
            owner_termination_confirmed=True,
            prior_manifest_bytes=json.dumps(self.manifest).encode("utf-8"),
            expected_pc_id="PC-A",
            expected_log_type="BattleLog",
            expected_target_period="2026-09",
            latest_candidate_count=1,
            drive_reconciliation="not_required",
            unresolved_upload_count=0,
        )

    def decide(self, **overrides):
        values = {**self.kwargs, **overrides}
        return decide_crash_recovery(**values)

    def test_valid_evidence_allows_only_new_run_with_fresh_inventory(self):
        result = self.decide()
        self.assertEqual(result.action, "start_new_run")
        self.assertEqual(result.reason_code, "recovery_evidence_validated")
        self.assertTrue(result.may_start_new_run)
        self.assertTrue(result.requires_fresh_inventory)
        self.assertTrue(result.preserve_prior_manifest)
        self.assertFalse(result.drive_reconciliation_required)

    def test_non_abandoned_mutex_blocks(self):
        self.assertEqual(self.decide(mutex_abandoned=False).reason_code, "mutex_not_abandoned")

    def test_malformed_or_mismatched_lock_record_blocks(self):
        self.assertEqual(self.decide(lock_record={"owner_token": "x"}).reason_code,
                         "lock_record_invalid_or_mismatched")
        changed = {**self.lock, "scope_id": "PC-B"}
        self.assertEqual(self.decide(lock_record=changed).reason_code,
                         "lock_record_invalid_or_mismatched")

    def test_owner_termination_must_be_confirmed(self):
        self.assertEqual(self.decide(owner_termination_confirmed=False).reason_code,
                         "owner_termination_unconfirmed")

    def test_latest_candidate_must_be_unique(self):
        for count in (0, 2, -1, True):
            self.assertEqual(self.decide(latest_candidate_count=count).reason_code,
                             "latest_manifest_not_unique")

    def test_invalid_or_non_running_manifest_blocks_without_rewrite(self):
        original = self.kwargs["prior_manifest_bytes"]
        malformed = self.decide(prior_manifest_bytes=b"not-json")
        self.assertEqual(malformed.reason_code, "prior_manifest_invalid_or_not_running")
        failed = {**self.manifest, "status": "failure", "finished_at_utc": "2026-10-21T11:00:00Z"}
        self.assertEqual(self.decide(prior_manifest_bytes=json.dumps(failed).encode()).reason_code,
                         "prior_manifest_invalid_or_not_running")
        self.assertEqual(self.kwargs["prior_manifest_bytes"], original)

    def test_manifest_identity_mismatch_blocks(self):
        other = {**self.manifest, "target_period": "2026-08"}
        result = self.decide(prior_manifest_bytes=json.dumps(other).encode())
        self.assertEqual(result.reason_code, "prior_manifest_identity_mismatch")

    def test_incomplete_or_ambiguous_drive_reconciliation_blocks(self):
        for state in ("incomplete", "ambiguous"):
            self.assertEqual(self.decide(drive_reconciliation=state).reason_code,
                             "drive_reconciliation_incomplete_or_ambiguous")

    def test_unknown_upload_outcome_blocks_even_if_listing_complete(self):
        self.assertEqual(self.decide(drive_reconciliation="complete", unresolved_upload_count=1).reason_code,
                         "unresolved_upload_outcomes_remain")

    def test_complete_reconciliation_allows_new_run_without_touching_old_manifest(self):
        original = self.kwargs["prior_manifest_bytes"]
        result = self.decide(drive_reconciliation="complete")
        self.assertTrue(result.may_start_new_run)
        self.assertFalse(result.drive_reconciliation_required)
        self.assertEqual(self.kwargs["prior_manifest_bytes"], original)

    def test_unknown_reconciliation_state_and_invalid_count_block(self):
        self.assertEqual(self.decide(drive_reconciliation="guess").reason_code,
                         "drive_reconciliation_state_invalid")
        self.assertEqual(self.decide(unresolved_upload_count=-1).reason_code,
                         "unresolved_upload_count_invalid")


    def test_duplicate_manifest_keys_block_without_mutating_bytes(self):
        raw = self.kwargs["prior_manifest_bytes"]
        for prefix in (b'{"status":"failure",', b'{"run_id":"untrusted",'):
            with self.subTest(prefix=prefix):
                ambiguous = prefix + raw[1:]
                result = self.decide(prior_manifest_bytes=ambiguous)
                self.assertFalse(result.may_start_new_run)
                self.assertEqual(result.reason_code, "prior_manifest_invalid_or_not_running")
                self.assertEqual(self.kwargs["prior_manifest_bytes"], raw)

    def test_truthy_non_boolean_abandonment_is_not_proof(self):
        for value in (1, "true", [True], {"abandoned": True}):
            with self.subTest(kind=type(value).__name__):
                result = self.decide(mutex_abandoned=value)
                self.assertFalse(result.may_start_new_run)
                self.assertEqual(result.reason_code, "mutex_not_abandoned")



    def test_wrong_manifest_primitive_types_block_with_stable_reason(self):
        original = self.kwargs["prior_manifest_bytes"]
        for field in ("pc_id", "log_type", "status"):
            for value in ([], {}, None, True, 1):
                with self.subTest(field=field, kind=type(value).__name__):
                    raw = json.dumps({**self.manifest, field: value}).encode("utf-8")
                    result = self.decide(prior_manifest_bytes=raw)
                    self.assertFalse(result.may_start_new_run)
                    self.assertEqual(result.reason_code, "prior_manifest_invalid_or_not_running")
        self.assertEqual(self.kwargs["prior_manifest_bytes"], original)

    def test_wrong_reconciliation_primitive_types_block_with_stable_reason(self):
        for value in ([], {}, None, True, 1):
            with self.subTest(kind=type(value).__name__):
                result = self.decide(drive_reconciliation=value)
                self.assertFalse(result.may_start_new_run)
                self.assertEqual(result.reason_code, "drive_reconciliation_state_invalid")


if __name__ == "__main__":
    unittest.main()
