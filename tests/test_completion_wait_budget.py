"""Bounded hourly confirmation advice using immutable synthetic histories."""
from dataclasses import asdict, replace, FrozenInstanceError
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from Common.CompletionWaitBudget import (
    CompletionWaitState, CompletionWaitBudgetError,
    assess_completion_wait_budget, record_completion_check_attempt,
)

START = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
RUN = "123e4567-e89b-42d3-a456-426614174000"


class CompletionWaitBudgetTests(unittest.TestCase):
    def setUp(self):
        self.state = CompletionWaitState("PC-A", "BattleLog", "2026-10", RUN, START)

    def options(self, now=START, **changes):
        options = dict(expected_log_type="BattleLog", expected_target_period="2026-10", expected_run_id=RUN,
                       current_utc=now, current_utc_reliable=True, logged_on=True,
                       same_account_verified=True, own_sync_complete=True, waiting_confirmed=True)
        options.update(changes)
        return options

    def assess(self, state=None, now=START, **changes):
        return assess_completion_wait_budget(self.state if state is None else state, **self.options(now, **changes))

    def record(self, state=None, now=START, **changes):
        return record_completion_check_attempt(self.state if state is None else state, **self.options(now, **changes))

    def test_initial_advice_never_grants_archive_or_state_change(self):
        result = self.assess()
        self.assertTrue(result.check_due)
        self.assertFalse(result.may_archive)
        self.assertFalse(result.may_change_state)
        self.assertEqual(self.state.check_times_utc, ())

    def test_twenty_five_checks_at_hourly_boundaries_then_hold(self):
        state = self.state
        for hour in range(25):
            now = START + timedelta(hours=hour)
            self.assertTrue(self.assess(state, now).check_due)
            state = self.record(state, now)
        result = self.assess(state, START + timedelta(hours=24))
        self.assertEqual(result.reason_code, "wait_check_limit_reached")
        self.assertIsNone(result.next_check_at_utc)
        self.assertEqual(len(state.check_times_utc), 25)
        self.assertFalse(result.may_archive)

    def test_deadline_inclusive_but_one_microsecond_after_blocks(self):
        history = tuple(START + timedelta(hours=i) for i in range(24))
        state = replace(self.state, check_times_utc=history)
        self.assertTrue(self.assess(state, START + timedelta(hours=24)).check_due)
        result = self.assess(state, START + timedelta(hours=24, microseconds=1))
        self.assertEqual(result.reason_code, "wait_deadline_reached")
        self.assertFalse(result.check_due)

    def test_missed_opportunities_do_not_extend_deadline(self):
        state = self.record()
        result = self.assess(state, START + timedelta(hours=25))
        self.assertEqual(result.reason_code, "wait_deadline_reached")
        self.assertEqual(len(state.check_times_utc), 1)
        self.assertIsNone(result.next_check_at_utc)

    def test_delayed_check_does_not_compress_next_interval(self):
        state = self.record()
        state = self.record(state, START + timedelta(hours=2, minutes=30))
        result = self.assess(state, START + timedelta(hours=3))
        self.assertEqual(result.action, "wait")
        self.assertEqual(result.next_check_at_utc, START + timedelta(hours=3, minutes=30))
        self.assertFalse(result.check_due)

    def test_last_delayed_check_cannot_schedule_past_deadline(self):
        state = self.record(now=START + timedelta(hours=23, minutes=30))
        result = self.assess(state, START + timedelta(hours=23, minutes=40))
        self.assertEqual(result.reason_code, "wait_no_window_remaining")
        self.assertIsNone(result.next_check_at_utc)

    def test_reconstructed_same_state_keeps_original_deadline(self):
        state = self.record()
        restored = CompletionWaitState(**asdict(state))
        self.assertEqual(restored, state)
        self.assertEqual(self.assess(restored, START + timedelta(days=2)).reason_code,
                         "wait_deadline_reached")
        self.assertEqual(restored.started_at_utc, START)

    def test_history_corruption_repeated_or_subhour_checks_block(self):
        histories = ((START, START), (START, START + timedelta(minutes=59)),
                     (START - timedelta(seconds=1),), (START + timedelta(hours=25),),
                     tuple(START + timedelta(hours=i) for i in range(26)), [START])
        for history in histories:
            with self.subTest(history_type=type(history).__name__):
                self.assertEqual(self.assess(replace(self.state, check_times_utc=history)).action, "hold")

    def test_scope_bound_to_pc_a_log_period_and_original_run(self):
        for state in (replace(self.state, pc_id="PC-B"), replace(self.state, target_period="2026-09"),
                      replace(self.state, log_type="ErrorReport", target_period="2026"),
                      replace(self.state, run_id="123e4567-e89b-42d3-a456-426614174001")):
            self.assertEqual(self.assess(state).reason_code, "wait_scope_mismatch")

    def test_clock_rollback_unreliable_and_non_utc_hold(self):
        self.assertEqual(self.assess(now=START - timedelta(seconds=1)).reason_code, "wait_clock_rollback")
        state = self.record(now=START + timedelta(hours=2))
        self.assertEqual(self.assess(state, START + timedelta(hours=1)).reason_code, "wait_clock_rollback")
        for changes in ({"current_utc_reliable": False}, {"current_utc": START.replace(tzinfo=None)},
                        {"current_utc": START.astimezone(timezone(timedelta(hours=9)))}):
            self.assertEqual(self.assess(**changes).reason_code, "wait_clock_untrusted")

    def test_unconfirmed_context_including_bad_manifest_gate_holds(self):
        for key in ("logged_on", "same_account_verified", "own_sync_complete", "waiting_confirmed"):
            self.assertEqual(self.assess(**{key: False}).reason_code, "wait_prerequisites_unconfirmed")
        self.assertEqual(self.assess(logged_on=1).reason_code, "wait_context_invalid")

    def test_repeated_poll_does_not_consume_or_reset_history(self):
        first = self.assess()
        self.assertEqual(first, self.assess())
        self.assertEqual(self.state.check_times_utc, ())
        state = self.record()
        self.assertFalse(self.assess(state).check_due)
        self.assertEqual(state.started_at_utc, self.state.started_at_utc)

    def test_record_revalidates_not_due_context_and_cannot_force(self):
        state = self.record()
        for kwargs in ({}, {"now": START + timedelta(minutes=59)},
                       {"now": START + timedelta(hours=2), "waiting_confirmed": False},
                       {"now": START + timedelta(hours=25)}):
            with self.assertRaises(CompletionWaitBudgetError):
                self.record(state, **kwargs)
        self.assertEqual(len(state.check_times_utc), 1)

    def test_failed_external_check_still_has_a_counted_attempt(self):
        recorded = self.record()
        try:
            raise OSError("synthetic_read_failure")
        except OSError:
            pass
        self.assertFalse(self.assess(recorded).check_due)
        self.assertEqual(recorded.check_times_utc, (START,))

    def test_no_io_sleep_or_mutation_and_calendar_overflow_hold(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")),              patch("time.sleep", side_effect=AssertionError("unexpected_wait")):
            state = self.record()
            self.assertEqual(self.assess(state).action, "wait")
        with self.assertRaises(FrozenInstanceError):
            state.started_at_utc = START + timedelta(hours=1)
        self.assertEqual(self.assess(replace(self.state, started_at_utc=datetime.max.replace(tzinfo=timezone.utc))).action, "hold")
        self.assertEqual(self.state.check_times_utc, ())

    def test_last_check_at_maximum_datetime_does_not_overflow(self):
        end = datetime.max.replace(tzinfo=timezone.utc)
        state = replace(self.state, started_at_utc=end - timedelta(hours=24), check_times_utc=(end,))
        self.assertEqual(self.assess(state, end).reason_code, "wait_no_window_remaining")
