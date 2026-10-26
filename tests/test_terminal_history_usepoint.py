"""History use-point reconstruction and tests-only owned candidate publication."""
from dataclasses import replace
import hashlib
import os
import unittest
from unittest.mock import patch

from Common import ManifestTransitionInspection as check
from Common.ArtifactSetPublication import publish_artifact_set_marker_last
from Common.OwnedRunLock import acquire_owned_lock, _strict_record_bytes
import test_terminal_manifest_history as history_fixture
from test_terminal_bundle_integration import CandidateBundleFixture


class TerminalHistoryUsepointTests(unittest.TestCase):
    seed = history_fixture.TerminalManifestHistoryTests.seed
    prepare = history_fixture.TerminalManifestHistoryTests.prepare

    def build(self, **options):
        self.seed(**options)
        return self.prepare()

    def observe(self, plan, **changes):
        options = dict(self.context, initial_plan=self.initial, expected_snapshots=self.snapshots,
            expected_previous_bytes=self.snapshots[-2], expected_evidence_bytes=self.initial.evidence_bytes,
            ac_connected=True)
        options.update(changes)
        return check.revalidate_terminal_manifest_history(plan, **options)

    def test_every_call_reconstructs_and_grants_no_authority(self):
        plan = self.build(pc="PC-B")
        with patch.object(check, "prepare_terminal_manifest_history", wraps=check.prepare_terminal_manifest_history) as build:
            first = self.observe(plan)
            self.assertEqual(first, self.observe(plan))
        self.assertEqual(2, build.call_count)
        self.assertIsNot(first, plan)
        self.assertFalse(first.may_publish or first.may_upload or first.may_retry
                         or first.may_archive or first.may_change_state)

    def test_ac_unknown_false_and_truthy_values_stop_before_reconstruction(self):
        plan = self.build()
        for ac in (None, False, 1, "true"):
            with patch.object(check, "prepare_terminal_manifest_history") as build:
                with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_history_usepoint_ac_unconfirmed"):
                    self.observe(plan, ac_connected=ac)
                build.assert_not_called()

    def test_independent_trace_prior_and_b2_changes_stop_before_reconstruction(self):
        plan = self.build()
        for changes in ({"expected_snapshots": self.snapshots[:-1]},
                {"expected_previous_bytes": self.snapshots[-2]+b"\n"},
                {"expected_evidence_bytes": self.initial.evidence_bytes+b"\n"},
                {"expected_snapshots": list(self.snapshots)}, {"expected_previous_bytes": None}):
            with self.subTest(changes=changes), patch.object(check, "prepare_terminal_manifest_history") as build:
                with self.assertRaises(check.ManifestTransitionError): self.observe(plan, **changes)
                build.assert_not_called()

    def test_report_history_counts_nested_flags_and_wrapper_flags_cannot_be_tampered(self):
        plan = self.build()
        variants = [replace(plan, terminal=replace(plan.terminal, report_bytes=plan.terminal.report_bytes+b"\n")),
                    replace(plan, history=replace(plan.history, snapshot_count=999)),
                    replace(plan, history=replace(plan.history, retry_pending_transition_count=False)),
                    replace(plan, terminal=replace(plan.terminal, report_bytes=None))]
        for attribute in ("may_publish", "may_upload", "may_retry", "may_archive", "may_change_state"):
            changed = replace(plan)
            object.__setattr__(changed, attribute, True)
            variants.append(changed)
        nested = replace(plan.terminal)
        object.__setattr__(nested, "may_change_state", True)
        variants.append(replace(plan, terminal=nested))
        for changed in variants:
            with self.assertRaises(check.ManifestTransitionError): self.observe(changed)

    def test_changed_scope_paths_clock_or_initial_plan_is_rejected(self):
        plan = self.build()
        for changes in ({"expected_pc_id": "PC-B"}, {"manifest_path": "other.json"},
                {"current_utc_reliable": False}, {"initial_plan": None},
                {"initial_plan": replace(self.initial, proposed_bytes=self.initial.proposed_bytes+b"\n")}):
            with self.assertRaises(check.ManifestTransitionError): self.observe(plan, **changes)

    def test_terminal_repetitions_keep_independent_running_prior_binding(self):
        plan = self.build()
        prior = plan.terminal.expected_bytes
        self.snapshots += (self.snapshots[-1],)
        plan = self.prepare()
        self.assertEqual(prior, self.observe(plan, expected_previous_bytes=prior).terminal.expected_bytes)
        with self.assertRaises(check.ManifestTransitionError): self.observe(plan)

    def make_bundle(self, pc="PC-A"):
        self.seed(pc=pc)
        self.context.update(manifest_path="manifest.json", evidence_path="evidence.json")
        plan = self.prepare()
        value = CandidateBundleFixture(pc_id=pc)
        self.addCleanup(value.close)
        # Reconfigure only this self-created fixture before any candidate publication.
        value._root_guard()
        value.plan = plan.terminal
        value.prior.write_bytes(plan.terminal.expected_bytes)
        value.payloads = {"manifest.json": plan.terminal.proposed_bytes,
            "evidence.json": plan.terminal.evidence_bytes, "report.json": plan.terminal.report_bytes}
        value.hashes = {name: hashlib.sha256(data).hexdigest() for name, data in value.payloads.items()}
        return value, plan

    def publish_candidate(self, value, plan, *, ac=True, before_check=None,
                          maximum_artifact_bytes=None, maximum_total_bytes=None, maximum_record_bytes=None):
        value._limits(maximum_artifact_bytes, maximum_total_bytes, maximum_record_bytes)
        value._guard()
        with acquire_owned_lock(value.scope, value.root / "synthetic-owner.json", timeout_seconds=0,
                maximum_record_bytes=maximum_record_bytes):
            value._guard()
            if before_check is not None: before_check()
            restored = self.observe(plan, expected_previous_bytes=value.prior.read_bytes(), ac_connected=ac)
            self.assertEqual(value.payloads["report.json"], restored.terminal.report_bytes)
            publish_artifact_set_marker_last(str(value.bundle), value.payloads, transaction_id=value.transaction,
                maximum_artifact_bytes=maximum_artifact_bytes, maximum_total_bytes=maximum_total_bytes)
            value._guard()

    @unittest.skipUnless(os.name == "nt", "Windows synthetic mutex/publication required")
    def test_owner_record_budget_blocks_history_reconstruction_and_all_candidate_writes(self):
        value, plan = self.make_bundle()
        for limit, reason in ((True, "fixture_limit_invalid"), (1, "lock_record_limit_exceeded")):
            with self.subTest(limit=limit), patch.object(self, "observe") as observe, \
                    patch(__name__ + ".publish_artifact_set_marker_last") as publish:
                with self.assertRaisesRegex(RuntimeError, "^" + reason + "$"):
                    self.publish_candidate(value, plan, maximum_record_bytes=limit)
                observe.assert_not_called()
                publish.assert_not_called()
            self.assertEqual([], list(value.bundle.iterdir()))
            self.assertEqual(plan.terminal.expected_bytes, value.prior.read_bytes())
            self.assertFalse((value.root / "synthetic-owner.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows synthetic mutex/publication required")
    def test_history_reconstruction_connects_explicit_publication_and_readback_budgets(self):
        for pc in ("PC-A", "PC-B"):
            value, plan = self.make_bundle(pc)
            sizes = [len(data) for data in value.payloads.values()] + [len(value.marker_bytes())]
            limits = dict(maximum_artifact_bytes=max(sizes), maximum_total_bytes=sum(sizes),
                maximum_record_bytes=len(_strict_record_bytes(value.scope, "a" * 64)))
            with self.assertRaisesRegex(RuntimeError, "^artifact_publish_total_limit_exceeded$"):
                self.publish_candidate(value, plan, maximum_total_bytes=1)
            self.assertEqual([], list(value.bundle.iterdir()))
            self.publish_candidate(value, plan, **limits)
            self.assertEqual("candidate_bundle_verified", value.readback(**limits)["status"])
            self.assertEqual(plan.terminal.expected_bytes, value.prior.read_bytes())
            self.assertFalse((value.root / "synthetic-owner.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows synthetic mutex/publication required")
    def test_owned_candidate_publication_and_semantic_readback_for_both_pcs(self):
        for pc in ("PC-A", "PC-B"):
            value, plan = self.make_bundle(pc)
            prior = value.prior.read_bytes()
            self.publish_candidate(value, plan)
            self.assertEqual("candidate_bundle_verified", value.readback()["status"])
            self.assertEqual(prior, value.prior.read_bytes())
            self.assertFalse((value.root / "synthetic-owner.json").exists())
            self.assertFalse(value.readback()["may_update_manifest"])

    @unittest.skipUnless(os.name == "nt", "Windows synthetic mutex/publication required")
    def test_changed_prior_inside_lock_preserved_and_blocks_all_candidate_writes(self):
        value, plan = self.make_bundle()
        changed = value.prior.read_bytes()+b"\n"
        with self.assertRaisesRegex(check.ManifestTransitionError, "terminal_history_usepoint_snapshot_changed"):
            self.publish_candidate(value, plan, before_check=lambda: value.prior.write_bytes(changed))
        self.assertEqual(changed, value.prior.read_bytes())
        self.assertEqual([], list(value.bundle.iterdir()))
        self.assertFalse((value.root / "synthetic-owner.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows synthetic mutex/publication required")
    def test_ac_loss_inside_owned_boundary_blocks_all_candidate_writes(self):
        value, plan = self.make_bundle()
        with self.assertRaises(check.ManifestTransitionError): self.publish_candidate(value, plan, ac=False)
        self.assertEqual([], list(value.bundle.iterdir()))
        self.assertFalse((value.root / "synthetic-owner.json").exists())


if __name__ == "__main__":
    unittest.main()
