"""Existing checkpoint file -> candidate -> fresh phase observations; no writer."""
from dataclasses import replace
from datetime import timedelta
import os
import unittest
from unittest.mock import patch

from Common import CompletionWaitAttempt as check
from Common.OwnedRunLock import acquire_owned_lock
import test_initial_source_integration as temp_fixture
from test_completion_wait_checkpoint import checkpoint, encode, START
from test_completion_wait_attempt import options


class CompletionWaitFileUsepointTests(unittest.TestCase):
    setUp = temp_fixture.InitialSourceIntegrationTests.setUp
    cleanup = temp_fixture.InitialSourceIntegrationTests.cleanup

    def seed(self):
        self.path = self.root / "checkpoint.json"
        self.raw = encode(checkpoint())
        self.path.write_bytes(self.raw)
        return self.prepare()

    def prepare(self, **changes):
        context = dict(options(), maximum_bytes=4096, ac_connected=True)
        context.update(changes)
        return check.prepare_completion_wait_attempt_from_file(self.path, **context)

    def observe(self, plan, *, phase="before_commit", **changes):
        context = dict(options(), maximum_bytes=4096, ac_connected=True, phase=phase)
        context.update(changes)
        return check.inspect_completion_wait_attempt_file_usepoint(plan, self.path, **context)

    def test_plan_binds_actual_original_bytes_without_publishing_or_consuming(self):
        plan = self.seed()
        self.assertEqual(self.raw, plan.expected_bytes)
        self.assertEqual(1, plan.attempt_number)
        self.assertEqual(self.raw, self.path.read_bytes())
        self.assertFalse(plan.may_check or plan.may_archive or plan.may_change_state)
        result = self.observe(plan)
        self.assertEqual("requires_runtime_evidence", result["status"])
        self.assertFalse(result["may_check"] or result["may_archive"] or result["may_change_state"])

    def test_before_and_after_require_different_exact_file_bytes_each_time(self):
        plan = self.seed()
        with self.assertRaises(check.CompletionWaitAttemptError): self.observe(plan, phase="after_commit")
        # Fixture only: simulate persisted bytes, without qualifying a CAS provider.
        self.path.write_bytes(plan.proposed_bytes)
        with self.assertRaises(check.CompletionWaitAttemptError): self.observe(plan)
        first = self.observe(plan, phase="after_commit")
        self.assertEqual(first, self.observe(plan, phase="after_commit"))
        self.assertEqual(plan.proposed_bytes, self.path.read_bytes())
        self.assertFalse(first["may_check"])

    def test_changed_current_file_rejected_and_retained_even_if_old_observation_succeeded(self):
        plan = self.seed()
        self.observe(plan)
        changed = self.raw+b"\n"
        self.path.write_bytes(changed)
        with self.assertRaisesRegex(check.CompletionWaitAttemptError, "attempt_checkpoint_changed"):
            self.observe(plan)
        self.assertEqual(changed, self.path.read_bytes())
        self.assertEqual(self.raw, plan.expected_bytes)

    def test_ac_and_prerequisites_stop_before_file_io_for_both_entrypoints(self):
        plan = self.seed()
        for key in ("ac_connected", "current_utc_reliable", "logged_on", "same_account_verified",
                    "own_sync_complete", "waiting_confirmed"):
            for value in (False, None, 1):
                with patch.object(check, "observe_completion_wait_checkpoint_file") as read:
                    with self.assertRaises(check.CompletionWaitAttemptError): self.prepare(**{key: value})
                    with self.assertRaises(check.CompletionWaitAttemptError): self.observe(plan, **{key: value})
                    read.assert_not_called()

    def test_plan_flags_wrong_phase_scope_and_deadline_stop_before_file_io(self):
        plan = self.seed()
        changed = replace(plan)
        object.__setattr__(changed, "may_check", True)
        with patch.object(check, "observe_completion_wait_checkpoint_file") as read:
            for wrong in (None, changed, replace(plan, attempt_number=999)):
                with self.assertRaises(check.CompletionWaitAttemptError): self.observe(wrong)
            for options_changed in ({"phase": "invalid"}, {"expected_target_period": "2020-01"},
                    {"current_utc": START+timedelta(hours=24, microseconds=1)}):
                with self.assertRaises(check.CompletionWaitAttemptError): self.observe(plan, **options_changed)
            read.assert_not_called()

    def test_limit_missing_and_malformed_file_never_fall_back_to_saved_bytes(self):
        plan = self.seed()
        with self.assertRaises(check.CompletionWaitAttemptError): self.observe(plan, maximum_bytes=len(self.raw)-1)
        self.path.unlink()  # Self-created fixture checkpoint only.
        with self.assertRaises(check.CompletionWaitAttemptError): self.observe(plan)
        with self.assertRaises(check.CompletionWaitAttemptError): self.prepare()
        self.assertFalse(self.path.exists())
        self.path.write_bytes(b"{}")
        with self.assertRaises(check.CompletionWaitAttemptError): self.observe(plan)
        self.assertEqual(b"{}", self.path.read_bytes())

    @unittest.skipUnless(os.name == "nt", "Windows synthetic owned mutex required")
    def test_owned_boundary_rereads_and_releases_owner_on_changed_checkpoint(self):
        plan = self.seed()
        owner = self.root / "owner.json"
        with self.assertRaises(check.CompletionWaitAttemptError):
            with acquire_owned_lock("synthetic-"+self.transaction, owner, timeout_seconds=0):
                self.path.write_bytes(self.raw+b"\n")
                self.observe(plan)
        self.assertFalse(owner.exists())
        self.assertEqual(self.raw+b"\n", self.path.read_bytes())

    def test_file_reader_exception_is_sanitized_via_existing_error_contract(self):
        plan = self.seed()
        from Common.CompletionWaitCheckpoint import CompletionWaitCheckpointError
        with patch.object(check, "observe_completion_wait_checkpoint_file",
                          side_effect=CompletionWaitCheckpointError("checkpoint_file_changed")):
            with self.assertRaisesRegex(check.CompletionWaitAttemptError, "^checkpoint_file_changed$"):
                self.observe(plan)
        self.assertEqual(self.raw, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
