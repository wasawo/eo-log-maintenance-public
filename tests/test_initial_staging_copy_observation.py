"""Read-only frozen-target/staging binding, independent of source payload I/O."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
import unittest
from unittest.mock import patch

from Common import SourceInventoryRevalidation as check
import test_initial_source_integration as fixture


class InitialStagingCopyTests(unittest.TestCase):
    def test_single_copy_forwards_staging_byte_limits_without_mutating_payload(self):
        _, destination, plan = self.seed()
        expected = self.observe(plan)
        self.assertEqual(expected, self.observe(plan, maximum_staging_file_bytes=9, maximum_total_staging_bytes=9))
        for key, reason in (("maximum_staging_file_bytes", "staging_copy_file_limit_exceeded"),
                ("maximum_total_staging_bytes", "staging_copy_total_limit_exceeded")):
            with self.subTest(key=key), self.assertRaisesRegex(check.SourceRevalidationError, "^"+reason+"$"):
                self.observe(plan, **{key: 8})
        self.assertEqual(b"synthetic", destination.read_bytes())

    setUp = fixture.InitialSourceIntegrationTests.setUp
    cleanup = fixture.InitialSourceIntegrationTests.cleanup
    build = fixture.InitialSourceIntegrationTests.build
    plan_context = fixture.InitialSourceIntegrationTests.plan_context

    def seed(self, pc="PC-A", log="BattleLog", payload=b"synthetic"):
        source = self.source / (pc + log)
        source.mkdir()
        nested = source / "nested"
        nested.mkdir()
        name = "20260901_01020304@synthetic.txt" if log == "BattleLog" else "20250901_01020304.txt"
        original = nested / name
        original.write_bytes(payload)
        _, plan = self.build(pc=pc, log=log, source=source)
        destination = self.candidate / f"{self.run}_1_{name}"
        destination.write_bytes(payload)
        return original, destination, plan

    def observe(self, plan, *, pc="PC-A", log="BattleLog", **changes):
        options = dict(self.plan_context(pc, log),
            relative_path=json.loads(plan.proposed_bytes)["files"][0]["relative_path"], sequence=1)
        options.update(changes)
        return check.observe_initial_staging_copy(self.candidate, plan, **options)

    def test_both_pcs_logs_and_empty_multiblock_content_without_source_read(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                payload = b"" if log == "ErrorReport" else b"s" * (1024 * 1024 + 9)
                original, destination, plan = self.seed(pc, log, payload)
                original.unlink()  # Self-created source; observation must read only staging.
                result = self.observe(plan, pc=pc, log=log)
                self.assertEqual((len(payload), hashlib.sha256(payload).hexdigest()),
                                 (result.size_bytes, result.sha256))
                self.assertEqual((plan.proposed_bytes, plan.evidence_bytes),
                                 (result.manifest_bytes, result.evidence_bytes))
                self.assertFalse(result.may_upload or result.may_change_state or result.may_cleanup or result.may_archive)
                self.assertNotIn(destination.name, repr(result))
                with self.assertRaises(FrozenInstanceError): result.sequence = 2
                destination.unlink()

    def test_bad_context_plan_selection_and_sequence_stop_before_hash(self):
        _, _, plan = self.seed()
        for options in ({"sequence": True}, {"sequence": 0}, {"sequence": "1"},
                {"relative_path": "../escape"}, {"relative_path": "missing.txt"},
                {"expected_pc_id": "PC-B"}, {"current_utc_reliable": False}):
            with self.subTest(options=options), patch.object(check, "_hash_stable_file") as read:
                with self.assertRaises(check.SourceRevalidationError): self.observe(plan, **options)
                read.assert_not_called()
        altered_flags = replace(plan)
        object.__setattr__(altered_flags, "may_upload", True)  # Deliberately corrupt a frozen input.
        for invalid in (altered_flags, replace(plan, proposed_bytes=plan.proposed_bytes+b"\n")):
            with patch.object(check, "_hash_stable_file") as read:
                with self.assertRaises(check.SourceRevalidationError): self.observe(invalid)
                read.assert_not_called()

    def test_missing_directory_and_relative_root_never_created(self):
        _, _, plan = self.seed()
        for root in (self.root / "missing", "relative"):
            with self.assertRaises(check.SourceRevalidationError):
                check.observe_initial_staging_copy(root, plan,
                    relative_path=json.loads(plan.proposed_bytes)["files"][0]["relative_path"],
                    sequence=1, **self.plan_context())
        self.assertFalse((self.root / "missing").exists())

    def test_missing_truncated_and_same_size_wrong_content_are_retained(self):
        _, destination, plan = self.seed()
        for content in (b"", b"different"):
            destination.write_bytes(content)
            with self.assertRaisesRegex(check.SourceRevalidationError, "staging_copy_content_mismatch"):
                self.observe(plan)
            self.assertEqual(content, destination.read_bytes())
        destination.unlink()
        with self.assertRaises(check.SourceRevalidationError): self.observe(plan)
        self.assertFalse(destination.exists())

    def test_directory_and_source_hardlink_rejected_without_payload_read(self):
        source, destination, plan = self.seed()
        destination.unlink()
        destination.mkdir()
        with patch.object(check, "_hash_stable_file") as read:
            with self.assertRaises(check.SourceRevalidationError): self.observe(plan)
            read.assert_not_called()
        destination.rmdir()
        os.link(source, destination)
        with patch.object(check, "_hash_stable_file") as read:
            with self.assertRaises(check.SourceRevalidationError): self.observe(plan)
            read.assert_not_called()
        self.assertEqual(b"synthetic", source.read_bytes())

    def test_late_mutation_and_ancestor_change_rejected(self):
        _, destination, plan = self.seed()
        real_hash = check._hash_stable_file
        def changed(path, **options):
            result = real_hash(path, **options)
            path.write_bytes(b"longer changed content")
            return result
        with patch.object(check, "_hash_stable_file", side_effect=changed):
            with self.assertRaisesRegex(check.SourceRevalidationError, "staging_copy_observation_changed"):
                self.observe(plan)
        self.assertEqual(b"longer changed content", destination.read_bytes())
        destination.write_bytes(b"synthetic")
        with patch.object(check, "_source_chain", side_effect=[("before",), ("after",)]):
            with self.assertRaisesRegex(check.SourceRevalidationError, "staging_copy_observation_changed"):
                self.observe(plan)

    def test_native_provider_error_is_sanitized_and_files_preserved(self):
        _, destination, plan = self.seed()
        with patch.object(check, "_hash_stable_file", side_effect=OSError("synthetic private detail")):
            with self.assertRaisesRegex(check.SourceRevalidationError, "^staging_copy_observation_unavailable$"):
                self.observe(plan)
        self.assertEqual(b"synthetic", destination.read_bytes())

    def test_repeated_call_rehashes_and_does_not_accept_previous_observation_as_plan(self):
        _, destination, plan = self.seed()
        previous = self.observe(plan)
        with self.assertRaises(check.SourceRevalidationError):
            check.observe_initial_staging_copy(self.candidate, previous, relative_path=previous.relative_path,
                sequence=1, **self.plan_context())
        destination.write_bytes(b"different")
        with self.assertRaises(check.SourceRevalidationError): self.observe(plan)


if __name__ == "__main__":
    unittest.main()
