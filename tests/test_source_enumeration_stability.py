"""Late namespace/content changes must not certify complete B2 coverage."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from Common import SourceInventoryEvidenceBuilder as builder
from Common.SourceInventoryRevalidation import SourceRevalidationError
import test_initial_source_integration as fixture
import test_initial_source_usepoint as usepoint_fixture


def duplicate_scan_on_call(directory, repeat_call):
    """Return a synthetic scandir adapter repeating an actual entry once."""
    real_scan = builder.os.scandir
    calls = []
    class Scan:
        def __init__(self, entries): self.entries = entries
        def __enter__(self): return iter(self.entries)
        def __exit__(self, *args): pass
    def scan(path):
        with real_scan(path) as stream:
            entries = list(stream)
        if Path(path) == directory:
            calls.append(path)
            if len(calls) == repeat_call:
                entries = entries+entries
        return Scan(entries)
    return scan


class SourceEnumerationStabilityTests(unittest.TestCase):
    def test_shared_snapshot_rejects_duplicate_names_without_payload_read(self):
        source = self.source/"20260901_01020304@synthetic.txt"
        source.write_bytes(b"synthetic")
        with patch.object(builder.os, "scandir", side_effect=duplicate_scan_on_call(self.source, 1)), \
                patch.object(Path, "open") as opened:
            with self.assertRaisesRegex(builder.InventoryBuildError, "^source_directory_changed$"):
                builder._enumeration_snapshot(self.source)
            opened.assert_not_called()
        self.assertEqual(b"synthetic", source.read_bytes())

    def test_duplicate_initial_or_final_scan_never_certifies_complete_inventory(self):
        source = self.source/"20260901_01020304@synthetic.txt"
        source.write_bytes(b"synthetic")
        for repeat_call in (1, 2):
            with self.subTest(repeat_call=repeat_call), patch.object(builder.os, "scandir",
                    side_effect=duplicate_scan_on_call(self.source, repeat_call)), \
                    patch.object(builder, "_hash_stable_file", wraps=builder._hash_stable_file) as hashed:
                evidence, plan = self.build()
                self.assertEqual(0 if repeat_call == 1 else 1, hashed.call_count)
            self.assert_incomplete(evidence, plan)
            self.assertEqual(0 if repeat_call == 1 else 1, len(evidence["inventory"]["targets"]))
            self.assertEqual(b"synthetic", source.read_bytes())

    setUp = fixture.InitialSourceIntegrationTests.setUp
    cleanup = fixture.InitialSourceIntegrationTests.cleanup
    plan_context = fixture.InitialSourceIntegrationTests.plan_context
    build = fixture.InitialSourceIntegrationTests.build
    publish = fixture.InitialSourceIntegrationTests.publish
    observe = usepoint_fixture.InitialSourceUsepointTests.observe

    def assert_incomplete(self, evidence, plan):
        self.assertEqual("incomplete", evidence["enumeration"]["status"])
        self.assertEqual("incomplete", evidence["validation"]["status"])
        self.assertGreater(evidence["enumeration"]["enumeration_errors"], 0)
        self.assertEqual(("running", None), tuple(json.loads(plan.proposed_bytes)[key] for key in ("status", "outcome")))
        self.assertFalse(plan.may_publish or plan.may_upload)

    def test_add_remove_rename_and_already_hashed_content_changes_preserve_partial_evidence(self):
        real = builder._hash_stable_file
        for operation in ("add", "remove", "rename", "content", "directory"):
            source = self.source / operation; source.mkdir()
            first = source / "20260901_01020304@first.txt"; first.write_bytes(b"first")
            second = source / "20260902_01020304@second.txt"; second.write_bytes(b"second")
            calls = 0
            def changed(path):
                nonlocal calls
                result = real(path); calls += 1
                if calls == 2:
                    if operation == "add": (source / "20260903_01020304@added.txt").write_bytes(b"added")
                    if operation == "remove": first.unlink()
                    if operation == "rename": first.rename(source / "20260904_01020304@renamed.txt")
                    if operation == "content":
                        before = first.stat()
                        first.write_bytes(b"other")
                        os.utime(first, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
                    if operation == "directory":
                        nested = source / "late"; nested.mkdir()
                        (nested / "20260903_01020304@added.txt").write_bytes(b"added")
                return result
            with self.subTest(operation=operation), patch.object(builder, "_hash_stable_file", side_effect=changed):
                e, plan = self.build(source=source)
            self.assert_incomplete(e, plan)
            self.assertEqual(2, e["enumeration"]["eligible_target_count"])
            self.assertEqual(hashlib.sha256(b"first").hexdigest(), e["inventory"]["targets"][0]["expected_sha256"])

    def test_addition_after_initial_empty_scan_never_becomes_completed_no_work(self):
        real = builder._enumeration_snapshot
        calls = 0
        def changed(directory):
            nonlocal calls
            result = real(directory); calls += 1
            if calls == 1: (self.source / "20260901_01020304@late.txt").write_bytes(b"late")
            return result
        with patch.object(builder, "_enumeration_snapshot", side_effect=changed): e, plan = self.build()
        self.assert_incomplete(e, plan)
        self.assertEqual([], e["inventory"]["targets"])
        self.assertTrue((self.source / "20260901_01020304@late.txt").exists())

    def test_replaced_nested_directory_is_detected_without_discarding_hashed_target(self):
        nested = self.source / "nested"; nested.mkdir()
        name = "20260901_01020304@synthetic.txt"
        (nested / name).write_bytes(b"first")
        saved = self.root / "preserved-nested"
        real = builder._hash_stable_file
        def changed(path):
            result = real(path)
            nested.rename(saved)
            nested.mkdir()
            (nested / name).write_bytes(b"other")
            return result
        with patch.object(builder, "_hash_stable_file", side_effect=changed): e, plan = self.build()
        self.assert_incomplete(e, plan)
        self.assertEqual(1, len(e["inventory"]["targets"]))
        self.assertEqual(b"first", (saved / name).read_bytes())
        self.assertEqual(b"other", (nested / name).read_bytes())

    def test_final_rescan_failure_is_incomplete_not_a_zero_target_reset(self):
        (self.source / "20260901_01020304@synthetic.txt").write_bytes(b"first")
        real = builder._enumeration_snapshot
        calls = 0
        def failed(directory):
            nonlocal calls
            calls += 1
            if calls > 1: raise PermissionError("synthetic_private_detail")
            return real(directory)
        with patch.object(builder, "_enumeration_snapshot", side_effect=failed): e, plan = self.build()
        self.assert_incomplete(e, plan)
        self.assertEqual(1, len(e["inventory"]["targets"]))
        self.assertNotIn("synthetic_private_detail", json.dumps(e))

    def test_non_target_change_during_one_enumeration_also_blocks_complete_coverage(self):
        (self.source / "20260901_01020304@synthetic.txt").write_bytes(b"first")
        future = self.source / "20261001_01020304@future.txt"; future.write_bytes(b"future")
        real = builder._hash_stable_file
        def changed(path):
            result = real(path)
            future.write_bytes(b"different length")
            return result
        with patch.object(builder, "_hash_stable_file", side_effect=changed): e, plan = self.build()
        self.assert_incomplete(e, plan)
        self.assertEqual(1, len(e["inventory"]["targets"]))

    @unittest.skipUnless(os.name == "nt", "Windows owned candidate fixture required")
    def test_late_change_in_usepoint_enumeration_blocks_candidate_publication(self):
        (self.source / "20260901_01020304@synthetic.txt").write_bytes(b"first")
        _, plan = self.build()
        real = builder._hash_stable_file
        def changed(path):
            result = real(path)
            (self.source / "20260902_01020304@late.txt").write_bytes(b"late")
            return result
        with patch.object(builder, "_hash_stable_file", side_effect=changed):
            with self.assertRaisesRegex(SourceRevalidationError, "source_revalidation_incomplete"):
                self.publish(plan, before_publish=lambda: self.observe(plan))
        self.assertEqual([], list(self.candidate.iterdir()))
        self.assertFalse((self.root / "owner.json").exists())


if __name__ == "__main__": unittest.main()
