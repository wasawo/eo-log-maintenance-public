"""Fresh persisted-byte observation to due/wait/hold advice, no runtime action."""
from dataclasses import FrozenInstanceError
from datetime import timedelta
import unittest
from unittest.mock import patch

from Common import CompletionWaitCheckpoint as check
import test_initial_source_integration as temp_fixture
from test_completion_wait_checkpoint import checkpoint, encode, START, stamp
from test_completion_wait_attempt import options


class CompletionWaitFileAssessmentTests(unittest.TestCase):
    setUp = temp_fixture.InitialSourceIntegrationTests.setUp
    cleanup = temp_fixture.InitialSourceIntegrationTests.cleanup

    def seed(self, times=(), **changes):
        self.path = self.root / "checkpoint.json"
        self.raw = encode(checkpoint(check_times_utc=list(times), **changes))
        self.path.write_bytes(self.raw)

    def assess(self, now=START, **changes):
        context = dict(options(now), maximum_bytes=4096, ac_connected=True)
        context.update(changes)
        return check.assess_completion_wait_checkpoint_file(self.path, **context)

    def assert_observation(self, result):
        self.assertEqual("requires_runtime_evidence", result.status)
        self.assertFalse(result.may_check or result.may_wait or result.may_archive or result.may_change_state)
        self.assertFalse(result.budget.may_archive or result.budget.may_change_state)
        self.assertEqual(self.raw, result.checkpoint.original_bytes)
        self.assertEqual(self.raw, self.path.read_bytes())
        self.assertNotIn(str(self.path), repr(result))
        with self.assertRaises(FrozenInstanceError): result.status = "authorized"

    def test_first_due_is_not_a_consumed_or_authorized_attempt(self):
        self.seed()
        first = self.assess()
        self.assertEqual(("check_due", True), (first.budget.action, first.budget.check_due))
        self.assertEqual((), first.checkpoint.check_times_utc)
        self.assertEqual(first, self.assess())
        self.assert_observation(first)

    def test_wait_interval_then_due_does_not_rewrite_checkpoint(self):
        self.seed((stamp(START),))
        waiting = self.assess(START+timedelta(minutes=59))
        self.assertEqual(("wait", START+timedelta(hours=1)),
                         (waiting.budget.action, waiting.budget.next_check_at_utc))
        self.assert_observation(waiting)
        due = self.assess(START+timedelta(hours=1))
        self.assertEqual("check_due", due.budget.action)
        self.assert_observation(due)

    def test_inclusive_deadline_limit_and_no_window_hold_without_new_budget(self):
        cases = (([stamp(START+timedelta(hours=23))], START+timedelta(hours=24), "check_due", "wait_check_due"),
            ([], START+timedelta(hours=24, microseconds=1), "hold", "wait_deadline_reached"),
            ([stamp(START+timedelta(hours=i)) for i in range(25)], START+timedelta(hours=24), "hold", "wait_check_limit_reached"),
            ([stamp(START+timedelta(hours=23, minutes=30))], START+timedelta(hours=23, minutes=45), "hold", "wait_no_window_remaining"))
        for times, now, action, reason in cases:
            self.seed(times)
            result = self.assess(now)
            self.assertEqual((action, reason), (result.budget.action, result.budget.reason_code))
            self.assert_observation(result)

    def test_account_session_sync_or_wait_conditions_return_existing_hold_advice(self):
        self.seed()
        for key in ("logged_on", "same_account_verified", "own_sync_complete", "waiting_confirmed"):
            for value, reason in ((False, "wait_prerequisites_unconfirmed"), (1, "wait_context_invalid")):
                result = self.assess(**{key: value})
                self.assertEqual(("hold", reason), (result.budget.action, result.budget.reason_code))
                self.assert_observation(result)

    def test_bad_ac_stops_before_read_and_bad_clock_scope_or_precision_is_rejected(self):
        self.seed()
        for value in (False, None, 1):
            with patch.object(check, "observe_completion_wait_checkpoint_file") as read:
                with self.assertRaises(check.CompletionWaitCheckpointError): self.assess(ac_connected=value)
                read.assert_not_called()
        for changes in ({"current_utc_reliable": False}, {"expected_target_period": "2020-01"}):
            with self.assertRaises(check.CompletionWaitCheckpointError): self.assess(**changes)
        self.seed(started_at_utc="2026-11-01T12:00:00.00000000001Z")
        with self.assertRaises(check.CompletionWaitCheckpointError): self.assess(START+timedelta(seconds=1))

    def test_missing_corrupt_or_oversize_file_is_never_treated_as_zero_or_wait(self):
        self.seed()
        with self.assertRaises(check.CompletionWaitCheckpointError): self.assess(maximum_bytes=1)
        self.path.unlink()  # Self-created fixture only.
        with self.assertRaises(check.CompletionWaitCheckpointError): self.assess()
        self.assertFalse(self.path.exists())
        self.path.write_bytes(b"{}")
        with self.assertRaises(check.CompletionWaitCheckpointError): self.assess()
        self.assertEqual(b"{}", self.path.read_bytes())

    def test_every_call_observes_changed_history_instead_of_old_due_result(self):
        self.seed()
        self.assertEqual("check_due", self.assess().budget.action)
        self.seed((stamp(START),))
        result = self.assess(START+timedelta(minutes=10))
        self.assertEqual("wait", result.budget.action)
        self.assert_observation(result)

    def test_error_report_scope_uses_original_start_without_monthly_schedule_inference(self):
        self.seed((stamp(START),), log_type="ErrorReport", target_period="2026")
        result = self.assess(START+timedelta(hours=1), expected_log_type="ErrorReport", expected_target_period="2026")
        self.assertEqual("check_due", result.budget.action)
        self.assertEqual(stamp(START), result.checkpoint.started_at_utc)
        self.assert_observation(result)


if __name__ == "__main__":
    unittest.main()
