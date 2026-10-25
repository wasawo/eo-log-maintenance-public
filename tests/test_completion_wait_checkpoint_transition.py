"""Append-only evolution of supplied PC-A checkpoint bytes, no persistence."""
from dataclasses import FrozenInstanceError
from datetime import timedelta
import unittest
from unittest.mock import patch

from Common import CompletionWaitCheckpoint as check
from Common import CompletionWaitAttempt as attempt
from test_completion_wait_checkpoint import checkpoint, encode, stamp, START
from test_completion_wait_attempt import options, read_context


def inspect(before, after, **changes):
    context = read_context(START + timedelta(days=2))
    context.update(changes)
    return check.inspect_completion_wait_checkpoint_transition(before, after, **context)


class CompletionCheckpointTransitionTests(unittest.TestCase):
    def test_zero_to_first_and_one_hour_append_preserve_exact_bytes_without_io(self):
        before = encode(checkpoint())
        for times in ([stamp(START)], [stamp(START), stamp(START+timedelta(hours=1))]):
            proposed = encode(checkpoint(check_times_utc=times))
            with patch("builtins.open", side_effect=AssertionError("no I/O")):
                result = inspect(before, proposed)
            self.assertEqual((before, proposed), (result.expected_bytes, result.checkpoint.original_bytes))
            self.assertEqual((1, "requires_runtime_evidence"), (result.added_check_count, result.status))
            self.assertFalse(result.may_check or result.may_archive or result.may_change_state)
            with self.assertRaises(FrozenInstanceError): result.added_check_count = 0
            self.assertNotIn("123e4567", repr(result))
            before = proposed

    def test_exact_replay_is_unchanged_not_a_new_attempt_or_receipt(self):
        raw = encode(checkpoint(check_times_utc=[stamp(START)]))
        result = inspect(raw, raw)
        self.assertEqual(("unchanged", 0), (result.status, result.added_check_count))
        self.assertFalse(result.may_check or result.may_change_state)
        with self.assertRaises(check.CompletionWaitCheckpointError): inspect(raw, raw+b"\n")

    def test_shrink_replacement_and_multiappend_are_rejected_even_if_each_snapshot_is_valid(self):
        before = encode(checkpoint(check_times_utc=[stamp(START), stamp(START+timedelta(hours=1))]))
        for times in ([], [stamp(START)], [stamp(START), stamp(START+timedelta(hours=2)), stamp(START+timedelta(hours=3))],
                      [stamp(START), stamp(START+timedelta(hours=1)), stamp(START+timedelta(hours=2)), stamp(START+timedelta(hours=3))]):
            with self.assertRaisesRegex(check.CompletionWaitCheckpointError, "checkpoint_transition_history_changed"):
                inspect(before, encode(checkpoint(check_times_utc=times)))

    def test_start_and_original_timestamp_spellings_cannot_be_changed(self):
        before = encode(checkpoint(check_times_utc=[stamp(START)]))
        for changes, reason in (
                ({"started_at_utc": "2026-11-01T12:00:00.000Z",
                  "check_times_utc": [stamp(START), stamp(START+timedelta(hours=1))]}, "checkpoint_transition_start_changed"),
                ({"check_times_utc": ["2026-11-01T12:00:00.000Z", stamp(START+timedelta(hours=1))]}, "checkpoint_transition_history_changed")):
            with self.assertRaisesRegex(check.CompletionWaitCheckpointError, reason):
                inspect(before, encode(checkpoint(**changes)))

    def test_both_scopes_and_25th_attempt_keep_deadline_without_allowing_26th(self):
        for log, period in (("BattleLog", "2026-10"), ("ErrorReport", "2026")):
            times = [stamp(START+timedelta(hours=i)) for i in range(25)]
            base = dict(log_type=log, target_period=period)
            before = encode(checkpoint(**base, check_times_utc=times[:-1]))
            after = encode(checkpoint(**base, check_times_utc=times))
            context = dict(expected_log_type=log, expected_target_period=period)
            self.assertEqual(1, inspect(before, after, **context).added_check_count)
            with self.assertRaises(check.CompletionWaitCheckpointError):
                inspect(after, encode(checkpoint(**base, check_times_utc=times+[stamp(START+timedelta(hours=25))])), **context)

    def test_missing_prior_or_malformed_scope_clock_and_interval_are_not_reconstructed(self):
        before = encode(checkpoint())
        after = encode(checkpoint(check_times_utc=[stamp(START)]))
        for old in (None, b"", {}, "text"):
            with self.assertRaises(check.CompletionWaitCheckpointError): inspect(old, after)
        for changes in ({"current_utc_reliable": False}, {"expected_run_id": "different"},
                        {"schema": {"$ref": "https://invalid.example/schema"}}):
            with self.assertRaises(check.CompletionWaitCheckpointError): inspect(before, after, **changes)
        before = after
        for hour in (0.5, 25):
            with self.assertRaises(check.CompletionWaitCheckpointError):
                inspect(before, encode(checkpoint(check_times_utc=[stamp(START), stamp(START+timedelta(hours=hour))])))

    def test_submicrosecond_strings_remain_exact_without_budget_conversion(self):
        precise = "2026-11-01T12:00:00.00000000001Z"
        before = encode(checkpoint(started_at_utc=precise, check_times_utc=[precise]))
        later = "2026-11-01T13:00:00.00000000001Z"
        result = inspect(before, encode(checkpoint(started_at_utc=precise, check_times_utc=[precise, later])))
        self.assertEqual((precise, later), result.checkpoint.check_times_utc)
        with self.assertRaises(check.CompletionWaitCheckpointError): result.checkpoint.as_budget_state()

    def test_attempt_plan_generation_uses_transition_guard(self):
        raw = encode(checkpoint())
        with patch.object(attempt, "inspect_completion_wait_checkpoint_transition",
                          wraps=check.inspect_completion_wait_checkpoint_transition) as guard:
            plan = attempt.prepare_completion_wait_attempt(raw, **options())
        guard.assert_called_once()
        self.assertEqual(raw, plan.expected_bytes)
        self.assertEqual(1, plan.attempt_number)


if __name__ == "__main__":
    unittest.main()
