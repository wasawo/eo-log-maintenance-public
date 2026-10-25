"""Pure plans + isolated Windows ownership/staging and a MOCK checkpoint CAS.

Only candidate staging uses real file publication. The authoritative checkpoint
store below is memory, so these tests do not qualify an OS replacement provider.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common.AtomicArtifactPublication import ArtifactPublicationError, publish_bytes_no_overwrite
from Common.CompletionWaitAttempt import CompletionWaitAttemptError, prepare_completion_wait_attempt
from Common.CompletionWaitCheckpoint import read_completion_wait_checkpoint
from Common.OwnedRunLock import LockAcquisitionError, acquire_owned_lock
from test_completion_wait_checkpoint import SCHEMA, START, RUN, checkpoint, encode, stamp


def options(now=START, **changes):
    value = dict(schema=SCHEMA, expected_log_type="BattleLog", expected_target_period="2026-10",
                 expected_run_id=RUN, current_utc=now, current_utc_reliable=True, logged_on=True,
                 same_account_verified=True, own_sync_complete=True, waiting_confirmed=True)
    value.update(changes)
    return value


def read_context(now):
    return {key: value for key, value in options(now).items()
            if key not in ("logged_on", "same_account_verified", "own_sync_complete", "waiting_confirmed")}


class CompletionWaitAttemptPlanTests(unittest.TestCase):
    def test_exact_prior_strings_and_one_new_attempt_roundtrip(self):
        value = checkpoint(started_at_utc="2026-11-01T12:00:00.0000000000Z",
                           check_times_utc=["2026-11-01T12:00:00.0000000000Z"])
        raw = encode(value)
        before = deepcopy((value, SCHEMA))
        plan = prepare_completion_wait_attempt(raw, **options(START + timedelta(hours=1)))
        candidate = json.loads(plan.proposed_bytes)
        self.assertEqual(raw, plan.expected_bytes)
        self.assertEqual(value["started_at_utc"], candidate["started_at_utc"])
        self.assertEqual(value["check_times_utc"], candidate["check_times_utc"][:-1])
        self.assertEqual(stamp(START + timedelta(hours=1)), candidate["check_times_utc"][-1])
        self.assertEqual(set(value), set(candidate))
        self.assertEqual(2, plan.attempt_number)
        self.assertEqual(before, (value, SCHEMA))
        self.assertFalse(plan.may_check or plan.may_archive or plan.may_change_state)
        with self.assertRaises(FrozenInstanceError): plan.attempt_number = 0
        self.assertNotIn(RUN, repr(plan))

    def test_not_due_prerequisites_and_limits_never_produce_a_plan(self):
        raw = encode(checkpoint(check_times_utc=[stamp(START)]))
        with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_not_due"):
            prepare_completion_wait_attempt(raw, **options())
        for key in ("logged_on", "same_account_verified", "own_sync_complete", "waiting_confirmed"):
            for flag in (False, 1):
                with self.subTest(key=key, flag=flag), self.assertRaises(CompletionWaitAttemptError):
                    prepare_completion_wait_attempt(encode(checkpoint()), **options(**{key: flag}))
        full = checkpoint(check_times_utc=[stamp(START + timedelta(hours=i)) for i in range(25)])
        for raw, now in ((encode(full), START + timedelta(hours=24)), (encode(checkpoint()), START + timedelta(days=2))):
            with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_not_due"):
                prepare_completion_wait_attempt(raw, **options(now))

    def test_unavailable_corrupt_scope_clock_and_precision_are_not_reset(self):
        for raw in (None, b"", b'not-json-private-secret', encode(checkpoint(run_id="123e4567-e89b-42d3-a456-426614174001"))):
            with self.assertRaises(CompletionWaitAttemptError) as caught:
                prepare_completion_wait_attempt(raw, **options())
            self.assertNotIn("private-secret", str(caught.exception))
            self.assertTrue(caught.exception.__suppress_context__)
        with self.assertRaises(CompletionWaitAttemptError):
            prepare_completion_wait_attempt(encode(checkpoint()), **options(current_utc_reliable=False))
        raw = encode(checkpoint(started_at_utc="2026-11-01T12:00:00.0000001Z"))
        with self.assertRaisesRegex(CompletionWaitAttemptError, "checkpoint_precision_not_supported"):
            prepare_completion_wait_attempt(raw, **options(START + timedelta(seconds=1)))

    def test_plan_is_deterministic_and_has_no_io(self):
        raw = encode(checkpoint())
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")), \
             patch("pathlib.Path.open", side_effect=AssertionError("unexpected_io")):
            first = prepare_completion_wait_attempt(raw, **options())
            second = prepare_completion_wait_attempt(raw, **options())
        self.assertEqual(first, second)
        self.assertEqual((), read_completion_wait_checkpoint(raw, **read_context(START)).check_times_utc)


class FixtureFailure(RuntimeError):
    pass


class MockCheckpointProvider:
    """Test-only controlled memory compare-and-publish; NOT a filesystem provider."""
    def __init__(self, raw):
        self.current = raw
        self.mode = None
        self.readback_override = None

    def compare_and_publish(self, expected, proposed):
        if self.current != expected:
            raise FixtureFailure("expected_prior_changed")
        if self.mode == "fail_before": raise FixtureFailure("publication_failed")
        if self.mode == "ack_without_commit": return
        self.current = proposed
        if self.mode == "fail_after": raise FixtureFailure("receipt_lost_after_commit")

    def readback(self):
        return self.current if self.readback_override is None else self.readback_override


@unittest.skipUnless(os.name == "nt", "real Windows mutex required for isolated integration")
class CompletionWaitAttemptIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eolm-wait-attempt-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scope = "synthetic-" + uuid4().hex
        self.owner = self.root / "synthetic-owner.json"
        self.provider = MockCheckpointProvider(encode(checkpoint()))
        self.stages = 0
        self.checks = 0

    def execute_fixture(self, *, now=START, plan=None, stage=None, fault=None, before_commit=None):
        # This driver is deliberately test-only; it supplies no runtime root,
        # qualification boolean, real Drive callback or replacement primitive.
        with acquire_owned_lock(self.scope, self.owner, timeout_seconds=0):
            plan = plan or prepare_completion_wait_attempt(self.provider.current, **options(now))
            if fault == "before_stage": raise FixtureFailure("before_publication")
            path = stage or self.root / ("candidate-" + str(self.stages) + ".json")
            self.stages += 1
            publish_bytes_no_overwrite(path, plan.proposed_bytes)
            if fault == "tamper_stage": path.write_bytes(b"malformed")
            staged = path.read_bytes()
            if staged != plan.proposed_bytes: raise FixtureFailure("staged_bytes_changed")
            read_completion_wait_checkpoint(staged, **read_context(now))
            if fault == "before_commit": raise FixtureFailure("before_commit")
            if before_commit is not None: before_commit()
            self.provider.compare_and_publish(plan.expected_bytes, staged)
            if fault == "after_commit": raise FixtureFailure("after_commit_before_check")
            observed = self.provider.readback()
            if observed != staged: raise FixtureFailure("publication_unconfirmed")
            read_completion_wait_checkpoint(observed, **read_context(now))
            self.checks += 1  # Synthetic check occurs ONLY after commit + readback.
            if fault == "check_failed": raise FixtureFailure("synthetic_check_failed")
            return plan

    def test_record_is_visible_before_synthetic_check(self):
        plan = self.execute_fixture()
        self.assertEqual(1, self.checks)
        self.assertEqual(plan.proposed_bytes, self.provider.current)
        self.assertEqual(1, len(json.loads(self.provider.current)["check_times_utc"]))

    def test_precommit_failures_leave_prior_bytes_and_never_check(self):
        original = self.provider.current
        for fault in ("before_stage", "tamper_stage", "before_commit"):
            with self.subTest(fault=fault), self.assertRaises(FixtureFailure): self.execute_fixture(fault=fault)
            self.assertEqual(original, self.provider.current)
            self.assertEqual(0, self.checks)
        self.provider.mode = "fail_before"
        with self.assertRaises(FixtureFailure): self.execute_fixture()
        self.assertEqual(original, self.provider.current)
        self.assertEqual(0, self.checks)

    def test_atomic_staging_unavailable_never_reaches_checkpoint_commit(self):
        original = self.provider.current
        with patch("Common.AtomicArtifactPublication.os.link", side_effect=OSError("synthetic")):
            with self.assertRaises(ArtifactPublicationError): self.execute_fixture()
        self.assertEqual(original, self.provider.current)
        self.assertEqual(0, self.checks)

    def test_conflicting_staging_and_existing_owner_are_preserved(self):
        path = self.root / "conflict.json"
        path.write_bytes(b"prior-candidate")
        with self.assertRaises(ArtifactPublicationError): self.execute_fixture(stage=path)
        self.assertEqual(b"prior-candidate", path.read_bytes())
        self.owner.write_bytes(b"existing-owner")
        with self.assertRaises(LockAcquisitionError): self.execute_fixture()
        self.assertEqual(b"existing-owner", self.owner.read_bytes())
        self.assertEqual(0, self.checks)

    def test_stale_plan_is_rejected_even_after_identical_staging(self):
        plan = prepare_completion_wait_attempt(self.provider.current, **options())
        path = self.root / "identical-candidate.json"
        self.execute_fixture(plan=plan, stage=path)
        committed = self.provider.current
        with self.assertRaisesRegex(FixtureFailure, "expected_prior_changed"):
            self.execute_fixture(plan=plan, stage=path)
        self.assertEqual(committed, self.provider.current)
        self.assertEqual(1, self.checks)

    def test_interleaving_update_cannot_be_overwritten(self):
        other = prepare_completion_wait_attempt(self.provider.current, **options()).proposed_bytes
        def interleave(): self.provider.current = other
        with self.assertRaisesRegex(FixtureFailure, "expected_prior_changed"):
            self.execute_fixture(before_commit=interleave)
        self.assertEqual(other, self.provider.current)
        self.assertEqual(0, self.checks)

    def test_receipt_loss_after_commit_keeps_attempt_consumed(self):
        for mode in ("fail_after", "after_commit"):
            self.provider = MockCheckpointProvider(encode(checkpoint()))
            self.provider.mode = mode if mode == "fail_after" else None
            with self.assertRaises(FixtureFailure): self.execute_fixture(fault=mode)
            self.assertEqual(1, len(json.loads(self.provider.current)["check_times_utc"]))
            with self.assertRaises(CompletionWaitAttemptError): self.execute_fixture()
            self.assertEqual(0, self.checks)

    def test_false_ack_or_readback_mismatch_never_authorizes_check(self):
        original = self.provider.current
        self.provider.mode = "ack_without_commit"
        with self.assertRaisesRegex(FixtureFailure, "publication_unconfirmed"): self.execute_fixture()
        self.assertEqual(original, self.provider.current)
        self.provider.mode = None
        self.provider.readback_override = original
        with self.assertRaisesRegex(FixtureFailure, "publication_unconfirmed"): self.execute_fixture()
        self.assertEqual(1, len(json.loads(self.provider.current)["check_times_utc"]))
        self.assertEqual(0, self.checks)

    def test_failed_check_is_not_refunded_and_next_check_requires_interval(self):
        with self.assertRaisesRegex(FixtureFailure, "synthetic_check_failed"): self.execute_fixture(fault="check_failed")
        committed = self.provider.current
        with self.assertRaises(CompletionWaitAttemptError): self.execute_fixture()
        self.assertEqual(committed, self.provider.current)
        self.execute_fixture(now=START + timedelta(hours=1))
        self.assertEqual(2, len(json.loads(self.provider.current)["check_times_utc"]))
        self.assertEqual(2, self.checks)


if __name__ == "__main__": unittest.main()
