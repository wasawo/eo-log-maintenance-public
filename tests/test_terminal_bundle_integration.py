"""TEST ONLY: immutable candidate snapshots in a self-created OS-temp root.

The running record is never replaced. This is not a manifest update provider,
runtime layout contract, receipt or filesystem qualification.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common import AtomicArtifactPublication as atomic
from Common.ArtifactSetPublication import ArtifactSetPublicationError, publish_artifact_set_marker_last
from Common.ArtifactSetDirectoryVerification import verify_published_artifact_set
from Common.OwnedRunLock import acquire_owned_lock
from Common.ManifestTransitionInspection import prepare_terminal_manifest_transition
from Common.RunInputEvidenceIntegrity import compute_evidence_digest
from Common.validate_aggregation_artifacts import validate_referenced_artifacts
from test_aggregation_report_builder import fixture, encode, SCHEMAS, NOW, ROOT
from test_terminal_manifest_plan import prior_for


class CandidateBundleFixture:
    """No destination argument: all writes are confined to its own fresh temp."""
    def __init__(self, outcomes=((9, "verified"),), pc_id="PC-A"):
        after, evidence = fixture(outcomes)
        after["pc_id"] = evidence["pc_id"] = pc_id
        evidence["integrity"]["digest"] = compute_evidence_digest(evidence)
        self.plan = prepare_terminal_manifest_transition(encode(prior_for(after)), encode(after), encode(evidence),
            manifest_path="manifest.json", evidence_path="evidence.json", current_utc=NOW,
            current_utc_reliable=True, **SCHEMAS)
        self._parent = Path(tempfile.gettempdir()).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(prefix="eolm-terminal-bundle-", dir=self._parent)
        self.root = Path(self.temp.name)
        self._nonce = uuid4().hex.encode("ascii")
        (self.root / ".fixture-owner").write_bytes(self._nonce)
        self.bundle = self.root / "candidate"
        self.bundle.mkdir()
        self.prior = self.root / "prior-running.json"
        self.prior.write_bytes(self.plan.expected_bytes)
        self.transaction = str(uuid4())
        self.scope = "synthetic-" + uuid4().hex
        self.payloads = {
            "manifest.json": self.plan.proposed_bytes,
            "evidence.json": self.plan.evidence_bytes,
            "report.json": self.plan.report_bytes,
        }
        self.hashes = {name: hashlib.sha256(data).hexdigest() for name, data in self.payloads.items()}

    def _root_guard(self):
        info = self.root.lstat()
        marker = self.root / ".fixture-owner"
        marker_info = marker.lstat()
        if (self.root.parent != self._parent or not self.root.name.startswith("eolm-terminal-bundle-")
                or self.root.resolve(strict=True) != self.root or not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
                or not stat.S_ISREG(marker_info.st_mode) or marker_info.st_nlink != 1
                or getattr(marker_info, "st_file_attributes", 0) & 0x400 or marker.read_bytes() != self._nonce):
            raise RuntimeError("fixture_root_changed")

    def _guard(self):
        self._root_guard()
        for path in (self.bundle, self.prior):
            info = path.lstat()
            if getattr(info, "st_file_attributes", 0) & 0x400 or stat.S_ISLNK(info.st_mode):
                raise RuntimeError("fixture_path_changed")
        if not self.bundle.is_dir() or not self.prior.is_file() or self.prior.read_bytes() != self.plan.expected_bytes:
            raise RuntimeError("fixture_prior_changed")

    def publish(self, *, before_publish=None):
        self._guard()
        with acquire_owned_lock(self.scope, self.root / "synthetic-owner.json", timeout_seconds=0):
            self._guard()
            if before_publish is not None:
                before_publish()
            result = publish_artifact_set_marker_last(str(self.bundle), self.payloads, transaction_id=self.transaction)
            self._guard()
            return result

    def readback(self):
        self._guard()
        result = dict(status="held", may_update_manifest=False, may_archive=False)
        with acquire_owned_lock(self.scope, self.root / "synthetic-owner.json", timeout_seconds=0):
            self._guard()
            observed = verify_published_artifact_set(self.bundle, self.hashes, expected_transaction_id=self.transaction)
            if not observed.may_report_committed:
                return result
            marker_before = (self.bundle / "commit-marker.json").read_bytes()
            if json.loads(marker_before)["transaction_id"] != self.transaction:
                return result
            if any((self.bundle / name).read_bytes() != data for name, data in self.payloads.items()):
                return result
            semantic = validate_referenced_artifacts(self.bundle, self.bundle / "report.json", ROOT / "contracts")
            after = verify_published_artifact_set(self.bundle, self.hashes, expected_transaction_id=self.transaction)
            self._guard()
            if (semantic["status"] == "verified" and after.may_report_committed
                    and (self.bundle / "commit-marker.json").read_bytes() == marker_before):
                result["status"] = "candidate_bundle_verified"
        return result

    def close(self):
        # Only this self-created, resolved, marked root may be removed.
        self._root_guard()
        self.temp.cleanup()


@unittest.skipUnless(os.name == "nt", "real Windows mutex/publication required")
class TerminalBundleIntegrationTests(unittest.TestCase):
    def make(self, *args, **kwargs):
        value = CandidateBundleFixture(*args, **kwargs)
        self.addCleanup(value.close)
        return value

    def assert_candidate_only(self, value):
        self.assertEqual(dict(status="candidate_bundle_verified", may_update_manifest=False, may_archive=False), value.readback())
        self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())
        self.assertFalse((value.root / "synthetic-owner.json").exists())

    def test_real_publication_marker_and_semantic_readback_for_both_pcs(self):
        for pc_id in ("PC-A", "PC-B"):
            for outcomes in ((), ((9, "verified"),), ((8, "verified"), (9, "unknown"))):
                with self.subTest(pc_id=pc_id, outcomes=outcomes):
                    value = self.make(outcomes, pc_id)
                    result = value.publish()
                    self.assertEqual(4, len(result))
                    self.assert_candidate_only(value)

    def test_partial_failure_at_each_publication_boundary_preserves_then_retries_identically(self):
        for boundary in range(1, 5):
            with self.subTest(boundary=boundary):
                value = self.make()
                real_publish = atomic.publish_bytes_no_overwrite
                calls = 0
                def injected(destination, data):
                    nonlocal calls
                    calls += 1
                    if calls == boundary: raise atomic.ArtifactPublicationError("synthetic_interruption")
                    return real_publish(destination, data)
                with patch("Common.ArtifactSetPublication.atomic.publish_bytes_no_overwrite", side_effect=injected):
                    with self.assertRaises(ArtifactSetPublicationError): value.publish()
                before = {p.name: p.read_bytes() for p in value.bundle.iterdir()}
                self.assertEqual(boundary - 1, len(before))
                self.assertEqual("held", value.readback()["status"])
                self.assertEqual(before, {p.name: p.read_bytes() for p in value.bundle.iterdir()})
                self.assertFalse((value.bundle / "commit-marker.json").exists())
                value.publish()
                for name, data in before.items(): self.assertEqual(data, (value.bundle / name).read_bytes())
                self.assert_candidate_only(value)

    def test_existing_conflicting_candidate_is_not_replaced(self):
        value = self.make()
        (value.bundle / "manifest.json").write_bytes(value.plan.expected_bytes)
        with self.assertRaises(ArtifactSetPublicationError): value.publish()
        self.assertEqual(value.plan.expected_bytes, (value.bundle / "manifest.json").read_bytes())
        self.assertFalse((value.bundle / "commit-marker.json").exists())
        self.assertEqual("held", value.readback()["status"])
        self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())

    def test_identical_republication_is_not_a_current_manifest_commit_receipt(self):
        value = self.make()
        value.publish()
        before = {p.name: p.read_bytes() for p in value.bundle.iterdir()}
        value.publish()
        self.assertEqual(before, {p.name: p.read_bytes() for p in value.bundle.iterdir()})
        self.assert_candidate_only(value)

    def test_response_loss_after_marker_keeps_candidate_but_not_manifest_update(self):
        value = self.make()
        real_publish = atomic.publish_bytes_no_overwrite
        def injected(destination, data):
            result = real_publish(destination, data)
            if Path(destination).name == "commit-marker.json":
                raise atomic.ArtifactPublicationError("synthetic_response_loss")
            return result
        with patch("Common.ArtifactSetPublication.atomic.publish_bytes_no_overwrite", side_effect=injected):
            with self.assertRaises(ArtifactSetPublicationError): value.publish()
        self.assert_candidate_only(value)

    def test_valid_marker_from_another_transaction_does_not_bind_this_attempt(self):
        value = self.make()
        value.publish()
        path = value.bundle / "commit-marker.json"
        marker = json.loads(path.read_bytes())
        marker["transaction_id"] = str(uuid4())
        path.write_bytes(encode(marker))
        self.assertTrue(verify_published_artifact_set(value.bundle, value.hashes).may_report_committed)
        self.assertEqual("held", value.readback()["status"])

    def test_report_tamper_even_with_rebound_marker_is_not_this_plan(self):
        value = self.make()
        value.publish()
        path = value.bundle / "report.json"
        report = json.loads(path.read_bytes())
        report["run_aggregation"]["verified_count"] += 1
        raw = encode(report)
        path.write_bytes(raw)
        marker_path = value.bundle / "commit-marker.json"
        marker = json.loads(marker_path.read_bytes())
        marker["artifact_sha256"]["report.json"] = hashlib.sha256(raw).hexdigest()
        marker_path.write_bytes(encode(marker))
        self.assertEqual("held", value.readback()["status"])
        self.assertEqual("rejected", validate_referenced_artifacts(value.bundle, path, ROOT / "contracts")["status"])

    def test_change_after_semantic_validation_is_caught_by_final_observation(self):
        value = self.make()
        value.publish()
        real_validate = validate_referenced_artifacts
        def injected(*args):
            result = real_validate(*args)
            self.assertEqual("verified", result["status"])
            (value.bundle / "report.json").write_bytes(b"synthetic_changed")
            return result
        with patch(__name__ + ".validate_referenced_artifacts", side_effect=injected):
            self.assertEqual("held", value.readback()["status"])
        self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())


if __name__ == "__main__": unittest.main()
