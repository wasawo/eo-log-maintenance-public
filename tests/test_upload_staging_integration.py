"""Tests-only source -> fresh staging copy; no metadata writer or Upload gate."""
from datetime import date
import json
import os
import stat
import unittest

from Common import SourceInventoryEvidenceBuilder as builder
from Common.SourceInventoryRevalidation import revalidate_initial_manifest_source, SourceRevalidationError
from Common.OwnedRunLock import acquire_owned_lock
import test_initial_source_integration as fixture


class CopyRefused(Exception):
    pass


@unittest.skipUnless(os.name == "nt", "Windows synthetic owned lock required")
class UploadStagingIntegrationTests(unittest.TestCase):
    setUp = fixture.InitialSourceIntegrationTests.setUp
    cleanup = fixture.InitialSourceIntegrationTests.cleanup
    plan_context = fixture.InitialSourceIntegrationTests.plan_context
    build = fixture.InitialSourceIntegrationTests.build

    def seed(self, payload=b"synthetic", pc="PC-A", log="BattleLog"):
        source = self.source / (pc + log)
        source.mkdir()
        name = "20260901_01020304@synthetic.txt" if log == "BattleLog" else "20250901_01020304.txt"
        path = source / name
        path.write_bytes(payload)
        _, plan = self.build(source=source, pc=pc, log=log)
        staging = self.root / (pc + log + "-staging")
        staging.mkdir()
        return path, plan, staging

    def copy_candidate(self, path, plan, staging, *, pc="PC-A", log="BattleLog",
                       sequence=1, before_stream=None, before_verify=None, write=None):
        # Only this test's own source and staging directories are admissible.
        self.assertEqual(self.source / (pc + log), path.parent)
        self.assertEqual(self.root / (pc + log + "-staging"), staging)
        self.assertTrue(path.resolve().is_relative_to(self.root.resolve()))
        self.assertTrue(staging.resolve().is_relative_to(self.root.resolve()))
        self.assertIs(type(sequence), int)
        self.assertGreater(sequence, 0)
        target, = json.loads(plan.proposed_bytes)["files"]
        self.assertEqual(path.name, target["relative_path"])
        expected = target["size_bytes"], target["sha256"]
        destination = staging / f"{self.run}_{sequence}_{path.name}"
        owner = self.root / "owner.json"
        with acquire_owned_lock("synthetic-" + self.transaction, owner, timeout_seconds=0):
            revalidate_initial_manifest_source(path.parent, plan, **self.plan_context(pc, log),
                ac_connected=True, expected_root_id="synthetic-source", expected_relative_scope=log,
                reference_date=date(2026, 10, 1))
            if builder._hash_stable_file(path) != expected:
                raise CopyRefused("source_changed")
            try:
                # No metadata-first protocol is being simulated or adopted here.
                with destination.open("xb") as output:
                    allocated = os.fstat(output.fileno())
                    if before_stream:
                        before_stream(path)
                    count = 0
                    with path.open("rb") as source:
                        while True:
                            block = source.read(min(1024 * 1024, expected[0] - count + 1))
                            if not block:
                                break
                            count += len(block)
                            if count > expected[0]:
                                raise CopyRefused("source_grew")
                            written = output.write(block) if write is None else write(output, block)
                            if type(written) is not int or written != len(block):
                                raise CopyRefused("short_write")
                    output.flush()
                    os.fsync(output.fileno())
                if before_verify:
                    before_verify(destination)
                observed = destination.lstat()
                if (not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1
                        or builder._is_source_reparse(observed)
                        or (allocated.st_dev, allocated.st_ino) != (observed.st_dev, observed.st_ino)):
                    raise CopyRefused("staging_identity_changed")
                if builder._hash_stable_file(destination) != expected:
                    raise CopyRefused("staging_content_changed")
                if builder._hash_stable_file(path) != expected:
                    raise CopyRefused("source_changed")
            except Exception:
                # Test injection errors/raw native details never become output.
                # Partial/conflicting files are deliberately retained.
                raise CopyRefused("copy_candidate_refused") from None
        return {"status": "candidate_only", "may_upload": False, "may_change_state": False}

    def assert_released(self):
        self.assertFalse((self.root / "owner.json").exists())

    def test_both_pcs_logs_empty_and_multiblock_copies_preserve_frozen_inputs(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                payload = b"" if log == "ErrorReport" else b"x" * (1024 * 1024 + 7)
                path, plan, staging = self.seed(payload, pc, log)
                frozen = plan.proposed_bytes, plan.evidence_bytes
                result = self.copy_candidate(path, plan, staging, pc=pc, log=log)
                destination, = staging.iterdir()
                self.assertNotEqual(path, destination)
                self.assertEqual(payload, destination.read_bytes())
                self.assertEqual(payload, path.read_bytes())
                self.assertEqual(frozen, (plan.proposed_bytes, plan.evidence_bytes))
                self.assertEqual({"status": "candidate_only", "may_upload": False,
                                  "may_change_state": False}, result)
                self.assert_released()

    def test_source_changed_after_freeze_stops_before_creation(self):
        path, plan, staging = self.seed()
        path.write_bytes(b"changed")
        with self.assertRaises(SourceRevalidationError):
            self.copy_candidate(path, plan, staging)
        self.assertEqual([], list(staging.iterdir()))
        self.assertEqual(b"changed", path.read_bytes())
        self.assert_released()

    def test_source_changed_between_precheck_and_stream_is_preserved_and_refused(self):
        path, plan, staging = self.seed()
        with self.assertRaises(CopyRefused):
            self.copy_candidate(path, plan, staging, before_stream=lambda p: p.write_bytes(b"different"))
        self.assertEqual(b"different", path.read_bytes())
        self.assertEqual(1, len(list(staging.iterdir())))
        self.assert_released()

    def test_collision_never_overwrites_and_only_explicit_next_sequence_can_proceed(self):
        path, plan, staging = self.seed()
        occupied = staging / f"{self.run}_1_{path.name}"
        occupied.write_bytes(b"occupied")
        with self.assertRaises(CopyRefused):
            self.copy_candidate(path, plan, staging)
        self.assertEqual(b"occupied", occupied.read_bytes())
        self.assert_released()
        self.copy_candidate(path, plan, staging, sequence=2)
        self.assertEqual(2, len(list(staging.iterdir())))
        self.assertEqual(b"occupied", occupied.read_bytes())

    def test_injected_disk_full_retains_partial_without_retry(self):
        path, plan, staging = self.seed()
        def disk_full(output, block):
            output.write(block[:3])
            raise OSError("synthetic private failure detail")
        with self.assertRaisesRegex(CopyRefused, "^copy_candidate_refused$"):
            self.copy_candidate(path, plan, staging, write=disk_full)
        partial, = staging.iterdir()
        self.assertEqual(b"syn", partial.read_bytes())
        self.assert_released()
        self.copy_candidate(path, plan, staging, sequence=2)
        self.assertEqual(b"syn", partial.read_bytes())

    def test_short_write_is_not_accepted(self):
        path, plan, staging = self.seed()
        with self.assertRaises(CopyRefused):
            self.copy_candidate(path, plan, staging, write=lambda output, block: output.write(block[:2]))
        partial, = staging.iterdir()
        self.assertEqual(b"sy", partial.read_bytes())
        self.assert_released()

    def test_postclose_change_and_source_alias_are_refused_and_preserved(self):
        for alias in (False, True):
            path, plan, staging = self.seed(pc="PC-B" if alias else "PC-A")
            def change(destination):
                if alias:
                    destination.unlink()  # Only the self-created fixture copy.
                    os.link(path, destination)
                else:
                    destination.write_bytes(b"tampered")
            with self.assertRaises(CopyRefused):
                self.copy_candidate(path, plan, staging, pc="PC-B" if alias else "PC-A", before_verify=change)
            retained, = staging.iterdir()
            self.assertEqual(b"synthetic" if alias else b"tampered", retained.read_bytes())
            self.assertEqual(b"synthetic", path.read_bytes())
            self.assert_released()


if __name__ == "__main__":
    unittest.main()
