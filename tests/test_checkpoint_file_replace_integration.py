"""TEST ONLY: file use points plus native replacement, never a CAS provider."""
import os
import unittest

from Common.CompletionWaitAttempt import (CompletionWaitAttemptError, prepare_completion_wait_attempt,
    prepare_completion_wait_attempt_from_file, inspect_completion_wait_attempt_file_usepoint)
from Common.OwnedRunLock import acquire_owned_lock
from checkpoint_replace_probe import DisposableReplaceProbe
from test_completion_wait_checkpoint import checkpoint, encode
from test_completion_wait_attempt import options


@unittest.skipUnless(os.name == "nt", "Windows isolated native replacement probe required")
class CheckpointFileReplaceIntegrationTests(unittest.TestCase):
    def make(self, *, same_bytes=False):
        prior = encode(checkpoint())
        plan = prepare_completion_wait_attempt(prior, **options())
        probe = DisposableReplaceProbe(prior, plan.proposed_bytes, prior if same_bytes else prior+b"\n")
        self.addCleanup(probe.close)
        return probe, plan

    def observe(self, probe, plan, phase):
        return inspect_completion_wait_attempt_file_usepoint(plan, probe._path("checkpoint.json"),
            maximum_bytes=4096, phase=phase, ac_connected=True, **options())

    def assert_no_authority(self, result):
        self.assertEqual("requires_runtime_evidence", result["status"])
        self.assertFalse(result["may_check"] or result["may_archive"] or result["may_change_state"])

    def test_real_file_plan_guarded_replace_failure_and_later_readback(self):
        probe, expected = self.make()
        owner = probe._root / "synthetic-owner.json"
        with acquire_owned_lock(probe._scope, owner, timeout_seconds=0):
            plan = prepare_completion_wait_attempt_from_file(probe._path("checkpoint.json"),
                maximum_bytes=4096, ac_connected=True, **options())
            self.assertEqual(expected, plan)
            self.assert_no_authority(self.observe(probe, plan, "before_commit"))
            with probe.deny_write_delete_guard():
                replaced, _ = probe.replace("candidate.json")
                self.assertFalse(replaced)
                self.assertEqual(plan.expected_bytes, probe._path("checkpoint.json").read_bytes())
                self.assertEqual(plan.proposed_bytes, probe._path("candidate.json").read_bytes())
                with self.assertRaises(CompletionWaitAttemptError): self.observe(probe, plan, "after_commit")
            replaced, _ = probe.replace("candidate.json")
            self.assertTrue(replaced)
            self.assert_no_authority(self.observe(probe, plan, "after_commit"))
        self.assertFalse(owner.exists())

    def test_fresh_precommit_read_detects_native_competitor_and_retains_both_files(self):
        probe, plan = self.make()
        owner = probe._root / "synthetic-owner.json"
        with acquire_owned_lock(probe._scope, owner, timeout_seconds=0):
            self.observe(probe, plan, "before_commit")
            competitor = probe._path("competitor.json").read_bytes()
            replaced, _ = probe.replace("competitor.json")
            self.assertTrue(replaced)
            with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_checkpoint_changed"):
                self.observe(probe, plan, "before_commit")
            self.assertEqual(competitor, probe._path("checkpoint.json").read_bytes())
            self.assertEqual(plan.proposed_bytes, probe._path("candidate.json").read_bytes())
        self.assertFalse(owner.exists())

    def test_postreplace_match_cannot_prove_absence_of_an_intervening_writer(self):
        probe, plan = self.make()
        with acquire_owned_lock(probe._scope, probe._root / "synthetic-owner.json", timeout_seconds=0):
            self.assert_no_authority(self.observe(probe, plan, "before_commit"))
            competitor = probe._path("competitor.json").read_bytes()
            self.assertTrue(probe.replace("competitor.json")[0])
            self.assertEqual(competitor, probe._path("checkpoint.json").read_bytes())
            # Deliberate unsafe step in this negative experiment only. Native
            # replacement has no expected-bytes comparison and overwrites it.
            self.assertTrue(probe.replace("candidate.json")[0])
            self.assertEqual(plan.proposed_bytes, probe._path("checkpoint.json").read_bytes())
            self.assert_no_authority(self.observe(probe, plan, "after_commit"))
        self.assertFalse((probe._root / "synthetic-owner.json").exists())

    def test_same_bytes_native_replacement_is_not_a_cross_call_identity_lease(self):
        probe, plan = self.make(same_bytes=True)
        with acquire_owned_lock(probe._scope, probe._root / "synthetic-owner.json", timeout_seconds=0):
            first = self.observe(probe, plan, "before_commit")
            before = probe._path("checkpoint.json").stat()
            replacement = probe._path("competitor.json").stat()
            self.assertNotEqual((before.st_dev, before.st_ino), (replacement.st_dev, replacement.st_ino))
            self.assertTrue(probe.replace("competitor.json")[0])
            after = probe._path("checkpoint.json").stat()
            self.assertNotEqual((before.st_dev, before.st_ino), (after.st_dev, after.st_ino))
            self.assertEqual(plan.expected_bytes, probe._path("checkpoint.json").read_bytes())
            second = self.observe(probe, plan, "before_commit")
            self.assertEqual(first, second)
            self.assert_no_authority(second)


if __name__ == "__main__":
    unittest.main()
