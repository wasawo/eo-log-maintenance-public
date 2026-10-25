"""Fresh use-point observations, never a provider qualification or commit receipt."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import json
import os
import unittest
from unittest.mock import patch

from Common.CompletionWaitAttempt import (
    CompletionWaitAttemptError, prepare_completion_wait_attempt, inspect_completion_wait_attempt_usepoint,
)
from test_completion_wait_attempt import CompletionWaitAttemptFixture, FixtureFailure, options
from test_completion_wait_checkpoint import START, RUN, checkpoint, encode


class CompletionWaitUsepointTests(unittest.TestCase):
    def setUp(self):
        self.plan = prepare_completion_wait_attempt(encode(checkpoint()), **options())

    def inspect(self, *, phase="before_commit", observed=None, plan=None, **changes):
        plan = self.plan if plan is None else plan
        if observed is None: observed = plan.expected_bytes if phase == "before_commit" else plan.proposed_bytes
        return inspect_completion_wait_attempt_usepoint(plan, observed, phase=phase,
                   **{**options(), "ac_connected": True, **changes})

    def test_both_phases_remain_non_authorizing_and_repetition_is_not_a_receipt(self):
        for phase in ("before_commit", "after_commit"):
            first = self.inspect(phase=phase, current_utc=START + timedelta(minutes=5))
            self.assertEqual("requires_runtime_evidence", first["status"])
            self.assertFalse(first["may_check"] or first["may_archive"] or first["may_change_state"])
            self.assertEqual(first, self.inspect(phase=phase, current_utc=START + timedelta(minutes=5)))
            self.assertNotIn(RUN, json.dumps(first))

    def test_exact_observation_must_match_its_phase(self):
        for phase, wrong in (("before_commit", self.plan.proposed_bytes), ("after_commit", self.plan.expected_bytes)):
            with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_checkpoint_changed"):
                self.inspect(phase=phase, observed=wrong)
        for wrong in (bytearray(self.plan.expected_bytes), "not-bytes", b"unavailable"):
            with self.assertRaises(CompletionWaitAttemptError): self.inspect(observed=wrong)
        with self.assertRaises(CompletionWaitAttemptError):
            inspect_completion_wait_attempt_usepoint(self.plan, None, phase="before_commit", ac_connected=True, **options())
        for phase in ("BEFORE_COMMIT", "unknown", True):
            with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_phase_invalid"): self.inspect(phase=phase)

    def test_deadline_is_rechecked_inclusively_at_each_usepoint(self):
        for phase in ("before_commit", "after_commit"):
            self.inspect(phase=phase, current_utc=START + timedelta(hours=24))
            with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_usepoint_deadline_reached"):
                self.inspect(phase=phase, current_utc=START + timedelta(hours=24, microseconds=1))

    def test_fresh_ac_account_wait_and_clock_prerequisites(self):
        for phase in ("before_commit", "after_commit"):
            for key in ("ac_connected", "logged_on", "same_account_verified", "own_sync_complete", "waiting_confirmed", "current_utc_reliable"):
                for flag in (False, 1, None):
                    with self.subTest(phase=phase, key=key, flag=flag), self.assertRaises(CompletionWaitAttemptError):
                        self.inspect(phase=phase, **{key: flag})
            for now in (START - timedelta(microseconds=1), START.replace(tzinfo=None)):
                with self.assertRaises(CompletionWaitAttemptError): self.inspect(phase=phase, current_utc=now)

    def test_scope_must_still_match_and_no_precision_is_lost(self):
        for phase in ("before_commit", "after_commit"):
            with self.assertRaises(CompletionWaitAttemptError):
                self.inspect(phase=phase, expected_run_id="123e4567-e89b-42d3-a456-426614174001")
        value = json.loads(self.plan.proposed_bytes)
        value["check_times_utc"] = ["2026-11-01T12:00:00.0000001Z"]
        plan = replace(self.plan, proposed_bytes=encode(value))
        with self.assertRaisesRegex(CompletionWaitAttemptError, "checkpoint_precision_not_supported"):
            self.inspect(plan=plan, current_utc=START + timedelta(seconds=1))

    def test_forged_plan_counts_format_or_multiple_attempts_are_rejected(self):
        for number in (True, 0, 2):
            with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_plan_invalid"):
                self.inspect(plan=replace(self.plan, attempt_number=number))
        value = json.loads(self.plan.proposed_bytes)
        variants = [encode(value)]  # Different bytes cannot impersonate the prepared candidate.
        value["check_times_utc"].append("2026-11-01T13:00:00Z")
        variants.append(encode(value))
        value = json.loads(self.plan.proposed_bytes)
        value["started_at_utc"] = "2026-11-01T11:00:00Z"
        variants.append(encode(value))
        for raw in variants:
            with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_plan_invalid"):
                self.inspect(plan=replace(self.plan, proposed_bytes=raw), current_utc=START + timedelta(hours=2))
        with self.assertRaises(CompletionWaitAttemptError): self.inspect(plan=object(), observed=b"not-used")

    def test_checks_do_not_mutate_plan_or_touch_io(self):
        before = deepcopy(self.plan)
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")), \
             patch("pathlib.Path.open", side_effect=AssertionError("unexpected_io")):
            self.inspect()
            self.inspect(phase="after_commit")
        self.assertEqual(before, self.plan)


@unittest.skipUnless(os.name == "nt", "real Windows mutex required for isolated integration")
class CompletionWaitUsepointIntegrationTests(CompletionWaitAttemptFixture, unittest.TestCase):
    def test_before_commit_ac_loss_blocks_update_and_synthetic_check(self):
        original = self.provider.current
        with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_ac_unconfirmed"):
            self.execute_fixture(before_observations={"ac_connected": False})
        self.assertEqual(original, self.provider.current)
        self.assertEqual(0, self.checks)

    def test_after_commit_lost_prerequisite_keeps_attempt_consumed(self):
        for changes in ({"ac_connected": False}, {"logged_on": False}, {"same_account_verified": False},
                        {"waiting_confirmed": False}, {"current_utc_reliable": False},
                        {"current_utc": START + timedelta(hours=24, microseconds=1)}):
            self.provider.current = encode(checkpoint())
            with self.subTest(changes=changes), self.assertRaises(CompletionWaitAttemptError):
                self.execute_fixture(after_observations=changes)
            self.assertEqual(1, len(json.loads(self.provider.current)["check_times_utc"]))
            self.assertEqual(0, self.checks)

    def test_provider_compare_is_still_required_after_a_valid_inspection(self):
        other = prepare_completion_wait_attempt(self.provider.current, **options(START + timedelta(seconds=1))).proposed_bytes
        def race(): self.provider.current = other
        with self.assertRaisesRegex(FixtureFailure, "expected_prior_changed"):
            self.execute_fixture(at_commit=race)
        self.assertEqual(other, self.provider.current)
        self.assertEqual(0, self.checks)
