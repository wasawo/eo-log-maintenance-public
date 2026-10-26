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
from Common import OwnedRunLock as owned
from Common.ArtifactSetPublication import ArtifactSetPublicationError, publish_artifact_set_marker_last
from Common.ArtifactSetDirectoryVerification import ArtifactSetDirectoryVerificationError, verify_published_artifact_set
from Common.OwnedRunLock import acquire_owned_lock, _strict_record_bytes
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
                or getattr(marker_info, "st_file_attributes", 0) & 0x400 or not atomic._same_bytes(marker, self._nonce)):
            raise RuntimeError("fixture_root_changed")

    def _guard(self):
        self._root_guard()
        for path in (self.bundle, self.prior):
            info = path.lstat()
            if getattr(info, "st_file_attributes", 0) & 0x400 or stat.S_ISLNK(info.st_mode):
                raise RuntimeError("fixture_path_changed")
        if not self.bundle.is_dir() or not self.prior.is_file() or not atomic._same_bytes(self.prior, self.plan.expected_bytes):
            raise RuntimeError("fixture_prior_changed")

    def _limits(self, *values):
        if any(value is not None and (type(value) is not int or value < 1) for value in values):
            raise RuntimeError("fixture_limit_invalid")

    def marker_bytes(self):
        return (json.dumps(dict(schema_version=1, transaction_id=self.transaction, artifact_sha256=self.hashes),
            sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

    def publish(self, *, before_publish=None, maximum_artifact_bytes=None, maximum_total_bytes=None,
                maximum_record_bytes=None):
        self._limits(maximum_artifact_bytes, maximum_total_bytes, maximum_record_bytes)
        self._guard()
        with acquire_owned_lock(self.scope, self.root / "synthetic-owner.json", timeout_seconds=0,
                maximum_record_bytes=maximum_record_bytes):
            self._guard()
            if before_publish is not None:
                before_publish()
            result = publish_artifact_set_marker_last(str(self.bundle), self.payloads, transaction_id=self.transaction,
                maximum_artifact_bytes=maximum_artifact_bytes, maximum_total_bytes=maximum_total_bytes)
            self._guard()
            return result

    def readback(self, *, maximum_artifact_bytes=None, maximum_total_bytes=None,
                 maximum_semantic_artifact_bytes=None, maximum_total_semantic_bytes=None, maximum_record_bytes=None):
        self._limits(maximum_artifact_bytes, maximum_total_bytes,
            maximum_semantic_artifact_bytes, maximum_total_semantic_bytes, maximum_record_bytes)
        verification_limits = dict(maximum_artifact_bytes=maximum_artifact_bytes, maximum_total_bytes=maximum_total_bytes)
        semantic_limits = {key: value for key, value in dict(maximum_artifact_bytes=maximum_semantic_artifact_bytes,
            maximum_total_artifact_bytes=maximum_total_semantic_bytes).items() if value is not None}
        self._guard()
        result = dict(status="held", may_update_manifest=False, may_archive=False)
        with acquire_owned_lock(self.scope, self.root / "synthetic-owner.json", timeout_seconds=0,
                maximum_record_bytes=maximum_record_bytes):
            self._guard()
            observed = verify_published_artifact_set(self.bundle, self.hashes,
                expected_transaction_id=self.transaction, **verification_limits)
            if not observed.may_report_committed:
                return result
            marker_before = self.marker_bytes()
            if not atomic._same_bytes(self.bundle / "commit-marker.json", marker_before):
                return result
            if any(not atomic._same_bytes(self.bundle / name, data) for name, data in self.payloads.items()):
                return result
            semantic = validate_referenced_artifacts(self.bundle, self.bundle / "report.json", ROOT / "contracts", **semantic_limits)
            after = verify_published_artifact_set(self.bundle, self.hashes,
                expected_transaction_id=self.transaction, **verification_limits)
            self._guard()
            if (semantic["status"] == "verified" and after.may_report_committed
                    and atomic._same_bytes(self.bundle / "commit-marker.json", marker_before)):
                result["status"] = "candidate_bundle_verified"
        return result

    def close(self):
        # Only this self-created, resolved, marked root may be removed.
        self._root_guard()
        self.temp.cleanup()


@unittest.skipUnless(os.name == "nt", "real Windows mutex/publication required")
class TerminalBundleIntegrationTests(unittest.TestCase):
    def test_record_cleanup_interruption_preserves_candidate_and_releases_real_mutex(self):
        for pc in ("PC-A", "PC-B"):
            value = self.make((), pc)
            owner = value.root / "synthetic-owner.json"
            real_matches = owned._record_matches
            observations = []
            def matches(*args, **kwargs):
                observations.append(owner.read_bytes())
                if len(observations) == 2: raise KeyboardInterrupt()
                return real_matches(*args, **kwargs)
            with patch.object(owned, "_record_matches", side_effect=matches), self.assertRaises(KeyboardInterrupt):
                value.publish()
            self.assertEqual(observations[0], owner.read_bytes())
            self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())
            self.assertEqual(set(value.payloads) | {"commit-marker.json"}, {p.name for p in value.bundle.iterdir()})
            for name, data in value.payloads.items(): self.assertEqual(data, (value.bundle / name).read_bytes())
            with acquire_owned_lock(value.scope, value.root / "probe-owner.json", timeout_seconds=0):
                self.assertEqual(observations[0], owner.read_bytes())
            self.assertFalse((value.root / "probe-owner.json").exists())

    def test_short_owner_record_write_preserves_record_blocks_candidates_and_releases_mutex(self):
        for pc in ("PC-A", "PC-B"):
            value = self.make((), pc)
            owner = value.root / "synthetic-owner.json"
            real_open = Path.open
            class Stream:
                def __init__(self, stream): self.stream = stream
                def __enter__(self): return self
                def __exit__(self, *args): self.stream.close()
                def write(self, payload): return self.stream.write(payload[:-1])
                def flush(self): raise AssertionError("must not flush after short write")
                def fileno(self): raise AssertionError("must not fsync after short write")
            def opened(path, mode="r", *args, **kwargs):
                stream = real_open(path, mode, *args, **kwargs)
                return Stream(stream) if path == owner and mode == "xb" else stream
            with patch.object(Path, "open", opened):
                with self.assertRaisesRegex(RuntimeError, "^lock_record_write_incomplete$"):
                    value.publish()
            before = owner.read_bytes()
            self.assertIsInstance(json.loads(before), dict)
            self.assertEqual([], list(value.bundle.iterdir()))
            self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())
            with acquire_owned_lock(value.scope, value.root / "probe-owner.json", timeout_seconds=0):
                self.assertEqual(before, owner.read_bytes())
            self.assertFalse((value.root / "probe-owner.json").exists())

    def test_owner_budget_excess_blocks_publication_and_readback_without_changing_candidates(self):
        for pc in ("PC-A", "PC-B"):
            value = self.make((), pc)
            with patch(__name__ + ".publish_artifact_set_marker_last") as publish:
                with self.assertRaisesRegex(RuntimeError, "^lock_record_limit_exceeded$"):
                    value.publish(maximum_record_bytes=1)
                publish.assert_not_called()
            self.assertEqual([], list(value.bundle.iterdir()))
            value.publish()
            before = {p: p.read_bytes() for p in value.bundle.iterdir()}
            with patch(__name__ + ".verify_published_artifact_set") as verify:
                with self.assertRaisesRegex(RuntimeError, "^lock_record_limit_exceeded$"):
                    value.readback(maximum_record_bytes=1)
                verify.assert_not_called()
            self.assertEqual(before, {p: p.read_bytes() for p in value.bundle.iterdir()})
            self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())
            self.assertFalse((value.root / "synthetic-owner.json").exists())

    def test_grown_owner_record_is_preserved_after_abort_and_mutex_is_available_again(self):
        for pc in ("PC-A", "PC-B"):
            value = self.make((), pc)
            limit = len(_strict_record_bytes(value.scope, "a" * 64))
            owner = value.root / "synthetic-owner.json"
            changed = b"x" * (limit + 1)
            def abort_after_growth():
                owner.write_bytes(changed)
                raise RuntimeError("synthetic_abort")
            with self.assertRaisesRegex(RuntimeError, "^synthetic_abort$"):
                value.publish(before_publish=abort_after_growth, maximum_record_bytes=limit)
            self.assertEqual(changed, owner.read_bytes())
            self.assertEqual([], list(value.bundle.iterdir()))
            self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())
            # Separate record path tests mutex release only, never record adoption.
            with acquire_owned_lock(value.scope, value.root / "probe-owner.json", timeout_seconds=0,
                    maximum_record_bytes=limit):
                self.assertEqual(changed, owner.read_bytes())
            self.assertFalse((value.root / "probe-owner.json").exists())

    def test_explicit_publication_and_readback_budgets_preserve_prior_for_both_roles(self):
        for pc in ("PC-A", "PC-B"):
            value = self.make((), pc)
            sizes = [len(data) for data in value.payloads.values()] + [len(value.marker_bytes())]
            limits = dict(maximum_artifact_bytes=max(sizes), maximum_total_bytes=sum(sizes),
                maximum_record_bytes=len(_strict_record_bytes(value.scope, "a" * 64)))
            value.publish(**limits)
            schema_sizes = [path.stat().st_size for path in (ROOT / "contracts").glob("*.schema.json")]
            result = value.readback(**limits, maximum_semantic_artifact_bytes=max(sizes + schema_sizes),
                maximum_total_semantic_bytes=10 * sum(sizes + schema_sizes))
            self.assertEqual("candidate_bundle_verified", result["status"])
            self.assertFalse(result["may_update_manifest"] or result["may_archive"])
            before = {p: p.read_bytes() for p in value.bundle.iterdir()}
            rejected = value.readback(**limits, maximum_semantic_artifact_bytes=1,
                maximum_total_semantic_bytes=1)
            self.assertEqual("held", rejected["status"])
            self.assertFalse(rejected["may_update_manifest"] or rejected["may_archive"])
            self.assertEqual(before, {p: p.read_bytes() for p in value.bundle.iterdir()})
            self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())
            self.assertFalse((value.root / "synthetic-owner.json").exists())

    def test_publication_overflow_preserves_empty_candidate_and_releases_owner(self):
        for pc in ("PC-A", "PC-B"):
            value = self.make((), pc)
            with self.assertRaisesRegex(ArtifactSetPublicationError, "^artifact_publish_total_limit_exceeded$"):
                value.publish(maximum_total_bytes=1)
            self.assertEqual([], list(value.bundle.iterdir()))
            self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())
            self.assertFalse((value.root / "synthetic-owner.json").exists())

    def test_invalid_fixture_budgets_stop_before_guards_and_owner_acquisition(self):
        value = self.make()
        for method, keys in ((value.publish, ("maximum_artifact_bytes", "maximum_total_bytes", "maximum_record_bytes")),
                (value.readback, ("maximum_artifact_bytes", "maximum_total_bytes",
                                 "maximum_semantic_artifact_bytes", "maximum_total_semantic_bytes", "maximum_record_bytes"))):
            for key in keys:
                for limit in (0, -1, True, 1.0, "1"):
                    with self.subTest(method=method.__name__, key=key, limit=limit), \
                            patch.object(value, "_guard") as guard, patch(__name__ + ".acquire_owned_lock") as owner:
                        with self.assertRaisesRegex(RuntimeError, "^fixture_limit_invalid$"):
                            method(**{key: limit})
                        guard.assert_not_called()
                        owner.assert_not_called()

    def test_growth_after_directory_verification_is_rejected_without_opening_grown_payload(self):
        for name in ("report.json", "commit-marker.json"):
            value = self.make()
            value.publish()
            target = value.bundle / name
            original = target.read_bytes()
            real_verify = verify_published_artifact_set
            real_open = Path.open
            grown = False
            def verify_then_grow(*args, **kwargs):
                nonlocal grown
                result = real_verify(*args, **kwargs)
                self.assertTrue(result.may_report_committed)
                with open(target, "wb") as stream: stream.write(original + b"x" * 4096)
                grown = True
                return result
            def guarded_open(path, *args, **kwargs):
                if grown and path == target:
                    raise AssertionError("grown candidate must fail size check before open")
                return real_open(path, *args, **kwargs)
            with self.subTest(name=name), patch(__name__ + ".verify_published_artifact_set", side_effect=verify_then_grow), \
                    patch.object(Path, "open", guarded_open):
                self.assertEqual("held", value.readback()["status"])
            self.assertEqual(original + b"x" * 4096, target.read_bytes())
            self.assertFalse((value.root / "synthetic-owner.json").exists())

    def test_duplicate_bundle_enumeration_preserves_bytes_and_releases_owner(self):
        real_iterdir = Path.iterdir
        for pc_id in ("PC-A", "PC-B"):
            value = self.make((), pc_id)
            value.publish()
            before = {p: p.read_bytes() for p in value.bundle.iterdir()}
            def repeated(directory):
                entries = list(real_iterdir(directory))
                return iter(entries+entries if directory == value.bundle else entries)
            with patch.object(Path, "iterdir", repeated):
                with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^directory_changed$"):
                    value.readback()
            self.assertFalse((value.root/"synthetic-owner.json").exists())
            self.assertEqual(before, {p: p.read_bytes() for p in value.bundle.iterdir()})
            self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())

    def test_invalid_marker_json_preserves_bundle_and_releases_owner_for_both_roles(self):
        for pc_id in ("PC-A", "PC-B"):
            for content in (b"null", b'{"schema_version":NaN}'):
                value = self.make((), pc_id)
                value.publish()
                (value.bundle/"commit-marker.json").write_bytes(content)
                before = {p: p.read_bytes() for p in value.bundle.iterdir()}
                with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^commit_marker_json_invalid$"):
                    value.readback()
                self.assertFalse((value.root/"synthetic-owner.json").exists())
                self.assertEqual(before, {p: p.read_bytes() for p in value.bundle.iterdir()})
                self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())

    def test_explicit_bundle_read_bounds_preserve_candidates_and_release_owner_on_rejection(self):
        for pc_id in ("PC-A", "PC-B"):
            value = self.make((), pc_id)
            value.publish()
            before = {p: p.read_bytes() for p in value.bundle.iterdir()}
            total = sum(map(len, before.values()))
            result = value.readback(maximum_artifact_bytes=max(map(len, before.values())), maximum_total_bytes=total)
            self.assertEqual("candidate_bundle_verified", result["status"])
            self.assertFalse(result["may_update_manifest"])
            self.assertFalse(result["may_archive"])
            with self.assertRaisesRegex(ArtifactSetDirectoryVerificationError, "^artifact_total_limit_exceeded$"):
                value.readback(maximum_total_bytes=total-1)
            self.assertFalse((value.root/"synthetic-owner.json").exists())
            self.assertEqual(before, {p: p.read_bytes() for p in value.bundle.iterdir()})
            self.assertEqual(value.plan.expected_bytes, value.prior.read_bytes())

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
