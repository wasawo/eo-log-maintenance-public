"""Clock/session-boundary observations only; no real scheduler or runtime."""
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from Common.MonthlyScheduleObservation import observe_monthly_schedule, MonthlyScheduleError


class MonthlyScheduleObservationTests(unittest.TestCase):
    def observe(self, now=None, **changes):
        options = dict(pc_id="PC-B", current_utc=datetime(2026, 11, 1, 11, tzinfo=timezone.utc) if now is None else now,
                       current_utc_reliable=True, logged_on=True, same_account_verified=True)
        options.update(changes)
        return observe_monthly_schedule(**options)

    def test_staggered_approved_times_and_no_run_permission(self):
        for pc, hour in (("PC-B", 11), ("PC-A", 12)):
            result = self.observe(pc_id=pc)
            self.assertEqual(result.scheduled_at_utc, datetime(2026, 11, 1, hour, tzinfo=timezone.utc))
            self.assertEqual(result.schedule_month, "2026-11")
            self.assertFalse(result.may_start_run)

    def test_exact_microsecond_boundary_for_both_roles(self):
        for pc, hour in (("PC-B", 11), ("PC-A", 12)):
            boundary = datetime(2026, 11, 1, hour, tzinfo=timezone.utc)
            self.assertFalse(self.observe(boundary - timedelta(microseconds=1), pc_id=pc).boundary_reached)
            self.assertTrue(self.observe(boundary, pc_id=pc).boundary_reached)
            self.assertTrue(self.observe(boundary + timedelta(microseconds=1), pc_id=pc).boundary_reached)

    def test_between_pc_times_b_only_has_reached_boundary(self):
        now = datetime(2026, 11, 1, 11, 30, tzinfo=timezone.utc)
        self.assertTrue(self.observe(now, pc_id="PC-B").boundary_reached)
        self.assertFalse(self.observe(now, pc_id="PC-A").boundary_reached)

    def test_jst_month_rollover_differs_from_utc_date(self):
        before = self.observe(datetime(2026, 10, 31, 14, 59, 59, tzinfo=timezone.utc))
        after = self.observe(datetime(2026, 10, 31, 15, tzinfo=timezone.utc))
        self.assertEqual(before.schedule_month, "2026-10")
        self.assertTrue(before.boundary_reached)
        self.assertEqual(after.schedule_month, "2026-11")
        self.assertFalse(after.boundary_reached)

    def test_new_year_and_leap_month_boundaries(self):
        for now, month in ((datetime(2026, 12, 31, 15, tzinfo=timezone.utc), "2027-01"),
                           (datetime(2024, 2, 29, 15, tzinfo=timezone.utc), "2024-03")):
            result = self.observe(now)
            self.assertEqual(result.schedule_month, month)
            self.assertFalse(result.boundary_reached)

    def test_late_month_only_requests_further_observation_not_backlog_or_permission(self):
        result = self.observe(datetime(2026, 11, 30, 14, tzinfo=timezone.utc))
        self.assertTrue(result.boundary_reached)
        self.assertFalse(result.may_start_run)
        self.assertEqual(result.reason_code, "schedule_boundary_reached")
        # No completed-month input or inferred last-success record exists here.
        self.assertFalse(hasattr(result, "target_period"))

    def test_unreliable_naive_or_non_utc_clock_blocks(self):
        for changes in ({"current_utc_reliable": False}, {"current_utc": None},
                        {"current_utc": datetime(2026, 11, 1, 20)},
                        {"current_utc": datetime(2026, 11, 1, 20, tzinfo=timezone(timedelta(hours=9)))}):
            result = self.observe(**changes)
            self.assertEqual(result.reason_code, "schedule_clock_untrusted")
            self.assertIsNone(result.scheduled_at_utc)
            self.assertFalse(result.may_start_run)

    def test_logged_off_does_not_authorize_missed_run_or_success(self):
        result = self.observe(logged_on=False)
        self.assertEqual(result.reason_code, "schedule_session_unconfirmed")
        self.assertIsNone(result.schedule_month)
        self.assertFalse(result.boundary_reached)
        self.assertFalse(result.may_start_run)

    def test_same_account_claim_is_required(self):
        result = self.observe(same_account_verified=False)
        self.assertEqual(result.reason_code, "schedule_account_unconfirmed")
        self.assertFalse(result.may_start_run)

    def test_invalid_scope_or_truthy_primitives_rejected(self):
        for changes in ({"pc_id": "private_host"}, {"logged_on": 1},
                        {"current_utc_reliable": "true"}, {"same_account_verified": None}):
            with self.assertRaises(MonthlyScheduleError):
                self.observe(**changes)

    def test_calendar_overflow_rejected_without_fallback(self):
        with self.assertRaisesRegex(MonthlyScheduleError, "schedule_calendar_invalid"):
            self.observe(datetime.max.replace(tzinfo=timezone.utc))

    def test_repeatable_immutable_and_no_file_io(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")):
            first, second = self.observe(), self.observe()
        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.may_start_run = True
