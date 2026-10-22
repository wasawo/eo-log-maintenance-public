"""Real Windows mutex + publication + recovery-classifier integration evidence.

All state is synthetic and confined to a freshly acknowledged OS-temp test root.
No stale record is adopted/removed and no operational entry point is provided.
"""
from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from uuid import uuid4

from crash_publication_harness import (
    HarnessError, PAYLOADS, TRANSACTION_ID, _hashes, _receive, _stop,
    create_disposable_root, disposable_parent,
)
from Common.ArtifactSetDirectoryVerification import verify_published_artifact_set
from Common.ArtifactSetPublication import publish_artifact_set_marker_last
from Common.CrashRecoveryDecision import decide_crash_recovery
from Common.OwnedRunLock import (
    LockAcquisitionError, _NamedMutex, _mutex_name, acquire_owned_lock,
)


def _running_manifest():
    return {
        "schema_version": 1,
        "run_id": TRANSACTION_ID,
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "target_period": "2026-09",
        "status": "running",
        "outcome": None,
        "started_at_utc": "2026-10-21T10:00:00Z",
        "finished_at_utc": None,
        "files": [],
    }


def _owned_worker(scope, record, artifacts, prior, connection, mode):
    try:
        with acquire_owned_lock(scope, record, timeout_seconds=0):
            if mode == "owner":
                # Immutable prior-run fixture; no implicit success transition.
                with Path(prior).open("xb") as stream:
                    stream.write(json.dumps(_running_manifest()).encode("utf-8"))
            payloads = dict(PAYLOADS)
            if mode == "contender":
                payloads["report.json"] = b"conflicting-contender"
            publish_artifact_set_marker_last(
                artifacts, payloads, transaction_id=TRANSACTION_ID,
            )
            result = verify_published_artifact_set(artifacts, _hashes())
            connection.send(("owned", result.may_report_committed))
            if mode == "owner":
                command = connection.recv()
                if command == "revalidate":
                    observed = verify_published_artifact_set(artifacts, _hashes())
                    connection.send(("revalidated", observed.may_report_committed))
                    command = connection.recv()
                if command != "release":
                    raise HarnessError("worker_protocol_invalid")
        connection.send(("released",))
    except LockAcquisitionError as exc:
        connection.send(("blocked", exc.reason_code))
    except Exception:
        connection.send(("error", "owned_worker_failed"))
    finally:
        connection.close()


@unittest.skipUnless(os.name == "nt", "real Windows named mutex required")
class OwnedPublicationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.root = disposable_parent() / (
            "eo-crash-harness-" + uuid4().hex
        )
        create_disposable_root(self.root, acknowledged=True)
        self.addCleanup(self.cleanup_owned_root)
        self.scope = "synthetic-" + uuid4().hex
        self.record = self.root / "run-lock.json"
        self.prior = self.root / "prior-running.json"
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.context = multiprocessing.get_context("spawn")

    def cleanup_owned_root(self):
        assert self.root.parent == disposable_parent()
        assert self.root.name.startswith("eo-crash-harness-")
        assert not self.root.is_symlink()
        shutil.rmtree(self.root)

    def start_worker(self, mode):
        parent, child = self.context.Pipe()
        process = self.context.Process(
            target=_owned_worker,
            args=(self.scope, str(self.record), str(self.artifacts),
                  str(self.prior), child, mode),
        )
        process.start()
        child.close()
        self.addCleanup(parent.close)
        self.addCleanup(_stop, process)
        return process, parent

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.artifacts.iterdir()}

    def release_owner(self, process, connection):
        connection.send("release")
        self.assertEqual(_receive(connection), ("released",))
        process.join(timeout=5)
        self.assertEqual(process.exitcode, 0)

    def test_contender_cannot_publish_and_normal_retry_retains_exact_bytes(self):
        owner, channel = self.start_worker("owner")
        self.assertEqual(_receive(channel), ("owned", True))
        record = self.record.read_bytes()
        before = self.snapshot()
        contender, outcome = self.start_worker("contender")
        self.assertEqual(_receive(outcome), ("blocked", "lock_timeout"))
        contender.join(timeout=5)
        self.assertEqual(contender.exitcode, 0)
        self.assertEqual(self.record.read_bytes(), record)
        self.assertEqual(self.snapshot(), before)
        self.release_owner(owner, channel)
        self.assertFalse(self.record.exists())

        retry, result = self.start_worker("retry")
        self.assertEqual(_receive(result), ("owned", True))
        self.assertEqual(_receive(result), ("released",))
        retry.join(timeout=5)
        self.assertEqual(retry.exitcode, 0)
        self.assertFalse(self.record.exists())
        self.assertEqual(self.snapshot(), before)

    def test_actual_abandonment_blocks_adoption_and_preserves_recovery_evidence(self):
        # Keep an OS handle open, otherwise the named object may disappear when
        # the terminated process's last handle closes and abandonment is lost.
        keeper = _NamedMutex(_mutex_name(self.scope))
        self.addCleanup(keeper.close)
        owner, channel = self.start_worker("owner")
        self.assertEqual(_receive(channel), ("owned", True))
        original_record = self.record.read_bytes()
        original_prior = self.prior.read_bytes()
        before = self.snapshot()
        _stop(owner)
        self.assertNotEqual(owner.exitcode, 0)

        probe = _NamedMutex(_mutex_name(self.scope))
        with self.assertRaisesRegex(LockAcquisitionError, "abandoned_mutex_requires_recovery"):
            with acquire_owned_lock(
                self.scope, self.record, timeout_seconds=0,
                mutex_factory=lambda _: probe,
            ):
                self.fail("abandoned mutex must not enter operational code")
        self.assertTrue(probe.abandoned)
        kwargs = dict(
            mutex_abandoned=probe.abandoned,
            lock_record=json.loads(original_record),
            expected_scope=self.scope,
            expected_host=socket.gethostname(),
            owner_termination_confirmed=owner.exitcode is not None,
            prior_manifest_bytes=original_prior,
            expected_pc_id="PC-A",
            expected_log_type="BattleLog",
            expected_target_period="2026-09",
            latest_candidate_count=1,
            drive_reconciliation="not_required",
            unresolved_upload_count=0,
        )
        eligible = decide_crash_recovery(**kwargs)
        self.assertTrue(eligible.may_start_new_run)
        self.assertTrue(eligible.requires_fresh_inventory)
        self.assertTrue(eligible.preserve_prior_manifest)
        for override in [
            {"owner_termination_confirmed": False},
            {"latest_candidate_count": 2},
            {"drive_reconciliation": "incomplete"},
            {"unresolved_upload_count": 1},
            {"lock_record": {**kwargs["lock_record"], "scope_id": "other"}},
        ]:
            with self.subTest(condition=next(iter(override))):
                self.assertFalse(decide_crash_recovery(**{**kwargs, **override}).may_start_new_run)
        # A classifier decision does NOT authorize stale-record removal/adoption.
        retry, result = self.start_worker("retry")
        self.assertEqual(_receive(result), ("blocked", "lock_record_already_exists"))
        retry.join(timeout=5)
        self.assertEqual(retry.exitcode, 0)
        self.assertEqual(self.record.read_bytes(), original_record)
        self.assertEqual(self.prior.read_bytes(), original_prior)
        self.assertEqual(self.snapshot(), before)

    def test_revalidation_detects_changed_bytes_even_while_mutex_is_owned(self):
        owner, channel = self.start_worker("owner")
        self.assertEqual(_receive(channel), ("owned", True))
        # Simulate a non-cooperating writer: a mutex cannot prevent all external
        # filesystem writes. A previously verified snapshot is not a use permit.
        changed = self.artifacts / "report.json"
        changed.write_bytes(b"changed-after-verification")
        channel.send("revalidate")
        self.assertEqual(_receive(channel), ("revalidated", False))
        self.release_owner(owner, channel)
        self.assertEqual(changed.read_bytes(), b"changed-after-verification")

    def test_owner_token_mismatch_preserves_record_and_blocks_next_publisher(self):
        owner, channel = self.start_worker("owner")
        self.assertEqual(_receive(channel), ("owned", True))
        foreign = json.loads(self.record.read_bytes())
        foreign["owner_token"] = "f" * 64
        replacement = json.dumps(foreign).encode("utf-8")
        self.record.write_bytes(replacement)
        before = self.snapshot()
        self.release_owner(owner, channel)
        self.assertEqual(self.record.read_bytes(), replacement)
        contender, result = self.start_worker("contender")
        self.assertEqual(_receive(result), ("blocked", "lock_record_already_exists"))
        contender.join(timeout=5)
        self.assertEqual(contender.exitcode, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.record.read_bytes(), replacement)


if __name__ == "__main__":
    unittest.main()
