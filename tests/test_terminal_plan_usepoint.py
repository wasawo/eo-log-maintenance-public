"""Pure terminal use-point checks plus isolated owned candidate publication."""
from dataclasses import replace
from datetime import timedelta
import json
import os
import unittest
from unittest.mock import patch

from Common import ManifestTransitionInspection as check
from test_aggregation_report_builder import fixture, encode, SCHEMAS, NOW
from test_terminal_manifest_plan import prior_for, prepare
import test_terminal_bundle_integration as bundle_fixture


def context(plan):
    value = json.loads(plan.proposed_bytes)
    return dict(expected_previous_bytes=plan.expected_bytes, expected_evidence_bytes=plan.evidence_bytes,
        expected_pc_id=value["pc_id"], expected_log_type=value["log_type"],
        expected_target_period=value["target_period"], expected_run_id=value["run_id"],
        ac_connected=True, manifest_path="manifests/synthetic.json", evidence_path="evidence/synthetic.json",
        current_utc=NOW, current_utc_reliable=True, **SCHEMAS)


class TerminalPlanUsepointTests(unittest.TestCase):
    def seed(self, outcomes=((9, "verified"),), log_type="BattleLog", pc_id="PC-A"):
        after, evidence = fixture(outcomes, log_type=log_type)
        after["pc_id"] = evidence["pc_id"] = pc_id
        from Common.RunInputEvidenceIntegrity import compute_evidence_digest
        evidence["integrity"]["digest"] = compute_evidence_digest(evidence)
        return prepare(encode(prior_for(after)), encode(after), encode(evidence))

    def test_matching_context_rederives_each_call_without_io_or_authority(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                for outcomes in ((), ((9, "verified"),), ((8, "verified"), (9, "unknown"))):
                    with self.subTest(pc=pc, log=log, outcomes=outcomes):
                        plan = self.seed(outcomes, log, pc)
                        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
                            result = check.revalidate_terminal_manifest_plan(plan, **context(plan))
                        self.assertEqual(plan, result)
                        self.assertIsNot(plan, result)
                        self.assertFalse(result.may_publish or result.may_archive or result.may_change_state)

    def test_invalid_type_flags_and_ac_stop_before_rederivation(self):
        plan = self.seed()
        for bad in (None, {}, object()):
            with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_usepoint_plan_invalid"):
                check.revalidate_terminal_manifest_plan(bad, **context(plan))
        for flag in ("may_publish", "may_archive", "may_change_state"):
            for value in (True, 0, None):
                bad = replace(plan)
                object.__setattr__(bad, flag, value)
                with patch.object(check, "prepare_terminal_manifest_transition") as rebuild:
                    with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_usepoint_plan_invalid"):
                        check.revalidate_terminal_manifest_plan(bad, **context(plan))
                    rebuild.assert_not_called()
        for ac in (False, None, 1, "true"):
            opts = dict(context(plan), ac_connected=ac)
            with patch.object(check, "prepare_terminal_manifest_transition") as rebuild:
                with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_usepoint_ac_unconfirmed"):
                    check.revalidate_terminal_manifest_plan(plan, **opts)
                rebuild.assert_not_called()

    def test_independent_snapshot_changes_and_nonbytes_are_rejected(self):
        plan = self.seed()
        for key in ("expected_previous_bytes", "expected_evidence_bytes"):
            for value in (None, bytearray(b"{}"), b"{}", context(plan)[key] + b"\n"):
                with self.subTest(key=key, kind=type(value)), patch.object(check, "prepare_terminal_manifest_transition") as rebuild:
                    with self.assertRaises(check.ManifestTransitionError):
                        check.revalidate_terminal_manifest_plan(plan, **dict(context(plan), **{key: value}))
                    rebuild.assert_not_called()
        for key in ("expected_bytes", "proposed_bytes", "evidence_bytes", "report_bytes"):
            with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_usepoint_snapshot_invalid"):
                check.revalidate_terminal_manifest_plan(replace(plan, **{key: bytearray(getattr(plan, key))}), **context(plan))

    def test_report_tampering_and_reference_context_changes_are_not_cached(self):
        plan = self.seed()
        report = json.loads(plan.report_bytes)
        report["run_aggregation"]["status"] = "failure"
        for bad in (replace(plan, report_bytes=encode(report)), replace(plan, report_bytes=plan.report_bytes+b"\n")):
            with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_usepoint_plan_changed"):
                check.revalidate_terminal_manifest_plan(bad, **context(plan))
        for changes in ({"manifest_path": "another.json"}, {"evidence_path": "another.json"},
                        {"current_utc_reliable": False}, {"current_utc": NOW-timedelta(days=1)},
                        {"manifest_schema": {"$ref": "https://invalid.example/schema"}}, {"report_schema": {"$ref": "https://invalid.example/schema"}}):
            with self.subTest(changes=changes), self.assertRaises(check.ManifestTransitionError):
                check.revalidate_terminal_manifest_plan(plan, **dict(context(plan), **changes))

    def test_independent_scope_and_changed_proposed_state_are_rejected(self):
        plan = self.seed()
        for key, value in (("expected_pc_id", "PC-B"), ("expected_log_type", "ErrorReport"),
                ("expected_target_period", "2020-01"), ("expected_run_id", "another-run")):
            with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_usepoint_scope_mismatch"):
                check.revalidate_terminal_manifest_plan(plan, **dict(context(plan), **{key: value}))
        value = json.loads(plan.proposed_bytes)
        value.update(status="running", finished_at_utc=None, outcome=None)
        with self.assertRaises(check.ManifestTransitionError):
            check.revalidate_terminal_manifest_plan(replace(plan, proposed_bytes=encode(value)), **context(plan))

    @unittest.skipUnless(os.name == "nt", "Windows owned publication fixture required")
    def test_owned_candidate_publication_rechecks_and_stops_before_writes(self):
        for mode in ("matching", "report", "prior", "ac"):
            with self.subTest(mode=mode):
                value = bundle_fixture.CandidateBundleFixture()
                try:
                    plan = value.plan
                    if mode == "report": plan = replace(plan, report_bytes=plan.report_bytes+b"\n")
                    observed = []
                    def guard():
                        self.assertTrue((value.root / "synthetic-owner.json").exists())
                        opts = dict(context(value.plan), manifest_path="manifest.json", evidence_path="evidence.json",
                            expected_previous_bytes=value.prior.read_bytes(), ac_connected=mode != "ac")
                        if mode == "prior": opts["expected_previous_bytes"] += b"\n"
                        observed.append(check.revalidate_terminal_manifest_plan(plan, **opts))
                    if mode == "matching":
                        value.publish(before_publish=guard)
                        self.assertEqual("candidate_bundle_verified", value.readback()["status"])
                        self.assertEqual([plan], observed)
                    else:
                        with self.assertRaises(check.ManifestTransitionError): value.publish(before_publish=guard)
                        self.assertEqual([], list(value.bundle.iterdir()))
                    self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())
                    self.assertFalse((value.root / "synthetic-owner.json").exists())
                finally:
                    value.close()


if __name__ == "__main__": unittest.main()
