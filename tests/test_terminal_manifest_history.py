"""Exact initial B2/plan -> supplied lifecycle history -> terminal report plan."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
import unittest
from unittest.mock import patch

from Common import ManifestTransitionInspection as check
from Common.RunInputEvidenceIntegrity import compute_evidence_digest
from test_aggregation_report_builder import fixture, encode, SCHEMAS, NOW, error
import test_initial_manifest_plan as initial


class TerminalManifestHistoryTests(unittest.TestCase):
    def seed(self, outcomes=((9, "verified"),), *, pc="PC-A", log="BattleLog", **changes):
        terminal, evidence = fixture(outcomes, log_type=log, **changes)
        terminal["pc_id"] = evidence["pc_id"] = pc
        evidence["integrity"]["digest"] = compute_evidence_digest(evidence)
        self.initial = initial.prepare(encode(evidence), terminal)
        self.context = dict(expected_pc_id=pc, expected_log_type=log,
            expected_target_period=terminal["target_period"], expected_run_id=terminal["run_id"],
            started_at_utc=terminal["started_at_utc"], manifest_path="manifests/synthetic.json",
            evidence_path="evidence/synthetic.json", current_utc=NOW, current_utc_reliable=True, **SCHEMAS)
        values = [self.initial.proposed_bytes]
        current = json.loads(values[0])
        if outcomes:
            for state in ("staging", "ready", "pending", "uploaded"):
                current = deepcopy(current)
                for item in current["files"]: item["status"] = state
                values.append(encode(current))
            current = deepcopy(current)
            current["files"] = deepcopy(terminal["files"])
            values.append(encode(current))
        values.append(encode(terminal))
        self.snapshots = tuple(values)
        return terminal

    def prepare(self, **changes):
        options = dict(self.context)
        options.update(changes)
        return check.prepare_terminal_manifest_history(self.initial, self.snapshots, **options)

    def assert_non_authorizing(self, result):
        self.assertFalse(result.may_publish or result.may_upload or result.may_retry
                         or result.may_archive or result.may_change_state)
        self.assertFalse(result.terminal.may_publish or result.terminal.may_archive or result.terminal.may_change_state)
        self.assertNotIn("synthetic", repr(result))
        with self.assertRaises(FrozenInstanceError): result.snapshots = ()

    def test_both_pcs_logs_exact_trace_evidence_and_report_without_io(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                self.seed(pc=pc, log=log)
                with patch("builtins.open", side_effect=AssertionError("no I/O")):
                    result = self.prepare()
                self.assertIs(self.snapshots, result.snapshots)
                self.assertEqual(self.initial.evidence_bytes, result.terminal.evidence_bytes)
                self.assertEqual(self.snapshots[-2:], (result.terminal.expected_bytes, result.terminal.proposed_bytes))
                self.assertEqual("success", json.loads(result.terminal.report_bytes)["run_aggregation"]["status"])
                self.assertTrue(result.history.aggregation_required)
                self.assert_non_authorizing(result)

    def test_exact_terminal_repetitions_keep_original_running_prior(self):
        self.seed()
        previous = self.snapshots[-2]
        self.snapshots += (self.snapshots[-1],)*2
        result = self.prepare()
        self.assertEqual(previous, result.terminal.expected_bytes)
        self.assertEqual(9, result.history.snapshot_count)
        self.assert_non_authorizing(result)

    def test_initial_plan_context_flags_and_exact_first_bytes_are_required(self):
        self.seed()
        for changes in ({"expected_pc_id": "PC-B"}, {"current_utc_reliable": False},
                        {"expected_target_period": "2026-08"}):
            with self.assertRaises(check.ManifestTransitionError): self.prepare(**changes)
        real = self.initial
        self.initial = replace(real, proposed_bytes=real.proposed_bytes+b"\n")
        with self.assertRaises(check.ManifestTransitionError): self.prepare()
        self.initial = replace(real)
        object.__setattr__(self.initial, "may_publish", True)
        with self.assertRaises(check.ManifestTransitionError): self.prepare()
        self.initial = real
        self.snapshots = (self.snapshots[0]+b"\n",) + self.snapshots[1:]
        with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_history_initial_snapshot_mismatch"):
            self.prepare()

    def test_omitted_staging_history_cannot_be_hidden_by_valid_terminal_pair(self):
        self.seed()
        self.snapshots = (self.snapshots[0],) + self.snapshots[4:]
        with self.assertRaisesRegex(check.ManifestTransitionError, "planning_pending_used_as_upload"):
            self.prepare()

    def test_running_suffix_remains_incomplete_without_report_construction(self):
        self.seed()
        self.snapshots = self.snapshots[:-1]
        with patch.object(check, "prepare_terminal_manifest_transition") as build:
            with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_history_incomplete"):
                self.prepare()
            build.assert_not_called()

    def test_osd03_aggregation_cannot_be_bypassed_by_valid_history(self):
        terminal = self.seed(((9, "unknown"),))
        terminal["status"] = "success"
        self.snapshots = self.snapshots[:-1] + (encode(terminal),)
        with self.assertRaises(check.ManifestTransitionError): self.prepare()

    def test_unresolved_and_validation_errors_stay_in_report(self):
        for outcomes, options, status in (
                (((8, "verified"), (9, "unknown")), {}, "partial_failure"),
                (((9, "verified"),), {"errors": [error()]}, "partial_failure")):
            self.seed(outcomes, **options)
            result = self.prepare()
            self.assertEqual(status, json.loads(result.terminal.report_bytes)["run_aggregation"]["status"])
            self.assert_non_authorizing(result)

    def test_zero_work_requires_complete_b2_and_explicit_terminal_snapshot(self):
        self.seed(())
        result = self.prepare()
        self.assertEqual("no_work", json.loads(result.terminal.proposed_bytes)["outcome"])
        self.assert_non_authorizing(result)
        terminal = self.seed((), enumeration="failed")
        terminal.update(status="success", outcome="no_work")
        self.snapshots = (self.snapshots[0], encode(terminal))
        with self.assertRaises(check.ManifestTransitionError): self.prepare()

    def test_no_implicit_history_or_saved_result_as_initial_plan(self):
        self.seed()
        saved = self.prepare()
        for invalid in ((), [], None):
            self.snapshots = invalid
            with self.assertRaises(check.ManifestTransitionError): self.prepare()
        self.snapshots = saved.snapshots
        self.initial = saved
        with self.assertRaises(check.ManifestTransitionError): self.prepare()


if __name__ == "__main__":
    unittest.main()
