"""Per-file four-upload cap in supplied history; no waiting or API authority."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from Common import ManifestTransitionInspection as check
from test_manifest_transition_inspection import snapshot, encode
from test_contract_schemas import MANIFEST_SCHEMA
import test_terminal_manifest_history as terminal_fixture


def trace(attempts, *, files=1, end_unknown=False):
    values = []
    states = ["pending", "staging", "ready", "pending"]
    for _ in range(attempts-1): states.extend(("unknown", "pending"))
    if end_unknown: states.append("unknown")
    for state in states:
        value = snapshot(state)
        for index in range(1, files):
            other = deepcopy(value["files"][0])
            other["relative_path"] = other["filename"] = f"2026090{index+1}_00000000@synthetic.txt"
            value["files"].append(other)
        values.append(encode(value))
    return tuple(values)


def inspect(values):
    return check.inspect_manifest_history(values, manifest_schema=MANIFEST_SCHEMA)


class ManifestHistoryRetryBudgetTests(unittest.TestCase):
    seed = terminal_fixture.TerminalManifestHistoryTests.seed
    prepare = terminal_fixture.TerminalManifestHistoryTests.prepare

    def test_one_through_four_upload_entries_and_no_automatic_failure(self):
        for count in range(1, 5):
            values = trace(count, end_unknown=True)
            original = tuple(values)
            result = inspect(values)
            self.assertEqual((1, count-1, 0), (result.upload_pending_transition_count,
                result.retry_pending_transition_count, result.upload_pending_file_count))
            self.assertEqual("unknown", json.loads(values[-1])["files"][0]["status"])
            self.assertFalse(result.aggregation_required or result.may_upload or result.may_retry)
            self.assertEqual(original, values)

    def test_fifth_upload_pending_is_rejected_before_any_subsequent_outcome(self):
        for unknown in (False, True):
            with self.assertRaisesRegex(check.ManifestTransitionError, "manifest_history_upload_attempt_limit_exceeded"):
                inspect(trace(5, end_unknown=unknown))

    def test_budget_is_per_file_not_the_sum_of_independent_files(self):
        result = inspect(trace(4, files=2))
        self.assertEqual((2, 6, 2), (result.upload_pending_transition_count,
            result.retry_pending_transition_count, result.upload_pending_file_count))
        with self.assertRaises(check.ManifestTransitionError): inspect(trace(5, files=2))

    def test_identical_snapshots_and_file_reordering_neither_consume_nor_reset_budget(self):
        values = trace(4, files=2)
        repeated = []
        for raw in values:
            value = json.loads(raw)
            value["files"].reverse()
            repeated.extend((raw, raw, encode(value)))
        result = inspect(tuple(repeated))
        self.assertEqual((2, 6), (result.upload_pending_transition_count, result.retry_pending_transition_count))
        with self.assertRaisesRegex(check.ManifestTransitionError, "manifest_history_upload_attempt_limit_exceeded"):
            inspect(tuple(repeated) + trace(5, files=2)[-2:])

    def test_registration_only_and_source_failure_do_not_consume_upload_attempts(self):
        result = inspect((encode(snapshot()),)*8 + (encode(snapshot("failed")),))
        self.assertEqual((0, 0), (result.upload_pending_transition_count, result.retry_pending_transition_count))
        self.assertFalse(result.may_upload or result.may_retry)

    def test_staging_restart_cannot_reset_an_exhausted_file_budget(self):
        values = trace(4)
        with self.assertRaisesRegex(check.ManifestTransitionError, "upload_pending_restarted_staging"):
            inspect(values + (encode(snapshot("staging")),))

    def extend_bound_history(self, attempts):
        self.seed(((9, "unknown"),))
        prefix = list(self.snapshots[:4])
        for _ in range(attempts-1):
            for state in ("unknown", "pending"):
                value = json.loads(prefix[-1])
                value["files"][0]["status"] = state
                prefix.append(encode(value))
        self.snapshots = tuple(prefix) + self.snapshots[4:]

    def test_four_attempt_unknown_remains_unresolved_in_terminal_report(self):
        self.extend_bound_history(4)
        result = self.prepare()
        self.assertEqual(3, result.history.retry_pending_transition_count)
        terminal = json.loads(result.terminal.proposed_bytes)
        self.assertEqual(("failure", "unknown"), (terminal["status"], terminal["files"][0]["status"]))
        self.assertIsNone(terminal["outcome"])
        self.assertFalse(result.may_publish or result.may_retry or result.may_archive)

    def test_bound_fifth_attempt_stops_before_report_generation(self):
        self.extend_bound_history(5)
        with patch.object(check, "prepare_terminal_manifest_transition") as report:
            with self.assertRaisesRegex(check.ManifestTransitionError, "manifest_history_upload_attempt_limit_exceeded"):
                self.prepare()
            report.assert_not_called()


if __name__ == "__main__":
    unittest.main()
