"""Real Win32 negative probes, confined to fresh synthetic OS-temp files."""
from datetime import timedelta
import os
import unittest

from checkpoint_replace_probe import DisposableReplaceProbe, ReplaceProbeError
from Common.CompletionWaitAttempt import prepare_completion_wait_attempt
from test_completion_wait_attempt import options
from test_completion_wait_checkpoint import START, checkpoint, encode


@unittest.skipUnless(os.name == "nt", "real Windows file APIs required")
class CheckpointReplaceProbeTests(unittest.TestCase):
    def setUp(self):
        self.prior = encode(checkpoint())
        self.plan = prepare_completion_wait_attempt(self.prior, **options())
        self.other = prepare_completion_wait_attempt(self.prior, **options(START + timedelta(seconds=1)))
        self.probe = DisposableReplaceProbe(self.prior, self.plan.proposed_bytes, self.other.proposed_bytes)
        self.addCleanup(self.probe.close)

    def test_guard_blocks_replace_and_preserves_both_files_until_closed(self):
        with self.probe.deny_write_delete_guard():
            ok, error = self.probe.replace("candidate.json")
            self.assertFalse(ok)
            self.assertNotEqual(0, error)
            self.assertEqual(self.prior, self.probe._path("checkpoint.json").read_bytes())
            self.assertEqual(self.plan.proposed_bytes, self.probe._path("candidate.json").read_bytes())
        ok, error = self.probe.replace("candidate.json")
        self.assertTrue(ok)
        self.assertEqual(0, error)
        self.assertEqual(self.plan.proposed_bytes, self.probe._path("checkpoint.json").read_bytes())

    def test_native_replace_can_overwrite_changed_target_after_inspection(self):
        result = self.probe.stale_replacement_counterexample(self.plan, options())
        self.assertEqual(dict(inspection_non_authorizing=True, changed_after_inspection=True,
                              stale_replace_overwrote_competitor=True), result)

    def test_caller_cannot_select_an_outside_destination(self):
        for name in ("../outside.json", "C:\\outside.json", "unknown.json", "checkpoint.json"):
            with self.assertRaisesRegex(ReplaceProbeError, "probe_name_invalid"): self.probe.replace(name)
        self.assertEqual(self.prior, self.probe._path("checkpoint.json").read_bytes())

    def test_hard_link_alias_blocks_native_mutation(self):
        original = self.probe._path("checkpoint.json")
        os.link(original, self.probe._root / "synthetic-alias")
        with self.assertRaisesRegex(ReplaceProbeError, "probe_file_changed"): self.probe.replace("candidate.json")
        self.assertEqual(self.prior, original.read_bytes())

    def test_changed_root_marker_blocks_native_mutation(self):
        marker = self.probe._root / ".probe-owner"
        marker.write_bytes(b"changed")
        try:
            with self.assertRaisesRegex(ReplaceProbeError, "probe_root_changed"): self.probe.replace("candidate.json")
        finally:
            marker.write_bytes(self.probe._nonce)
        self.assertEqual(self.prior, self.probe._path("checkpoint.json").read_bytes())


if __name__ == "__main__": unittest.main()
