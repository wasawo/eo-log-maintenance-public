"""Compose checked disk snapshots with recovery classification, never recovery."""
from datetime import datetime, timezone
import hashlib
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common import ManifestDirectoryReader as reader
from Common.CrashRecoveryDecision import decide_crash_recovery
from Common.LatestManifestSelection import LatestManifestSelectionError
from crash_publication_harness import create_disposable_root, disposable_parent
import test_crash_recovery_decision as recovery_tests
import test_latest_manifest_selection as selection_tests


class ManifestRecoveryIntegrationTests(unittest.TestCase):
    candidate = selection_tests.LatestManifestSelectionTests.candidate

    def setUp(self):
        self.root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
        create_disposable_root(self.root, acknowledged=True)
        self.addCleanup(self.cleanup)
        self.directory = self.root / "_maintenance" / "manifests" / "PC-A"
        self.directory.mkdir(parents=True)
        fixture = recovery_tests.CrashRecoveryDecisionTests()
        fixture.setUp()
        self.recovery_options = fixture.kwargs
        self.old = self.put(1, "2026-10-23T08:00:00Z")
        self.latest = self.put(2, "2026-10-23T09:00:00Z", status="running")

    def cleanup(self):
        assert self.root.parent == disposable_parent()
        assert not self.root.is_symlink()
        shutil.rmtree(self.root)

    def put(self, *args, **kwargs):
        candidate = self.candidate(*args, **kwargs)
        (self.directory / candidate.filename).write_bytes(candidate.content)
        return candidate

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.directory.iterdir()}

    def observe(self):
        return reader.read_latest_manifest(
            self.root, expected_pc_id="PC-A", expected_log_type="BattleLog",
            expected_target_period="2026-09",
            current_utc=datetime(2026, 10, 23, 10, tzinfo=timezone.utc),
            current_utc_reliable=True, require_current_success=False,
        )

    def decide(self, observed, **changes):
        # One unique latest, not one total file. Classification is not ownership
        # transfer or a runtime permit; all other evidence remains caller-supplied.
        options = {**self.recovery_options, "prior_manifest_bytes": observed.content,
                   "latest_candidate_count": 1, **changes}
        return decide_crash_recovery(**options)

    def test_latest_running_not_old_success_is_classified_and_bytes_preserved(self):
        before = self.snapshot()
        observed = self.observe()
        self.assertEqual(observed.filename, self.latest.filename)
        self.assertEqual(observed.content, self.latest.content)
        self.assertEqual(observed.sha256, hashlib.sha256(self.latest.content).hexdigest())
        decision = self.decide(observed)
        self.assertTrue(decision.may_start_new_run)
        self.assertTrue(decision.requires_fresh_inventory)
        self.assertTrue(decision.preserve_prior_manifest)
        self.assertEqual(before, self.snapshot())

    def test_selected_terminal_failure_blocks_instead_of_recovering_older_running(self):
        newest = self.put(3, status="failure")
        before = self.snapshot()
        observed = self.observe()
        self.assertEqual(observed.content, newest.content)
        decision = self.decide(observed)
        self.assertFalse(decision.may_start_new_run)
        self.assertEqual(decision.reason_code, "prior_manifest_invalid_or_not_running")
        self.assertEqual(before, self.snapshot())

    def test_maximum_tie_never_reaches_recovery_classifier(self):
        self.put(3, "2026-10-23T09:00:00Z", status="running")
        before = self.snapshot()
        with patch(__name__ + ".decide_crash_recovery") as classify:
            with self.assertRaisesRegex(LatestManifestSelectionError, "latest_manifest_ambiguous"):
                self.decide(self.observe())
            classify.assert_not_called()
        self.assertEqual(before, self.snapshot())

    def test_corrupt_older_candidate_never_reaches_classifier(self):
        (self.directory / self.old.filename).write_bytes(b"{")
        before = self.snapshot()
        with patch(__name__ + ".decide_crash_recovery") as classify:
            with self.assertRaises(LatestManifestSelectionError):
                self.decide(self.observe())
            classify.assert_not_called()
        self.assertEqual(before, self.snapshot())

    def test_read_uncertainty_never_reaches_classifier(self):
        before = self.snapshot()
        with patch.object(reader, "_read_stable", side_effect=OSError("synthetic")):
            with patch(__name__ + ".decide_crash_recovery") as classify:
                with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "manifest_directory_read_failed"):
                    self.decide(self.observe())
                classify.assert_not_called()
        self.assertEqual(before, self.snapshot())

    def test_other_evidence_still_blocks_after_valid_selection(self):
        observed = self.observe()
        before = self.snapshot()
        for changes in ({"owner_termination_confirmed": False},
                        {"mutex_abandoned": False},
                        {"drive_reconciliation": "incomplete"},
                        {"drive_reconciliation": "ambiguous"},
                        {"unresolved_upload_count": 1},
                        {"lock_record": {}}):
            with self.subTest(condition=next(iter(changes))):
                self.assertFalse(self.decide(observed, **changes).may_start_new_run)
        self.assertEqual(before, self.snapshot())

    def test_later_path_change_does_not_change_observed_bytes_or_authorize_use(self):
        observed = self.observe()
        path = self.directory / self.latest.filename
        changed = b"synthetic_change_after_observation"
        path.write_bytes(changed)
        # The pure classifier only sees the prior snapshot. A positive result
        # cannot establish current path state or authorize lock disposition.
        self.assertTrue(self.decide(observed).may_start_new_run)
        self.assertEqual(observed.content, self.latest.content)
        self.assertEqual(path.read_bytes(), changed)
        with self.assertRaises(LatestManifestSelectionError):
            self.observe()
        self.assertEqual(path.read_bytes(), changed)
