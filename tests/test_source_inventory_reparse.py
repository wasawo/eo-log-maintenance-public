"""Source inventory must not traverse Windows junction roots or entries."""
from datetime import date, datetime, timezone
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from crash_publication_harness import create_disposable_root, disposable_parent
import test_artifact_directory_reparse as artifact_reparse
from Common import SourceInventoryEvidenceBuilder as builder
from Common.SourceInventoryEvidenceBuilder import InventoryBuildError


@unittest.skipUnless(os.name == "nt", "real Windows junction required")
class SourceInventoryReparseTests(unittest.TestCase):
    make_junction = artifact_reparse.ArtifactDirectoryReparseTests.make_junction

    def setUp(self):
        self.root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
        create_disposable_root(self.root, acknowledged=True)
        self.addCleanup(self.cleanup_owned_root)
        self.source = self.root / "source"
        self.source.mkdir()
        self.external = self.root / "external"
        self.external.mkdir()
        (self.external / "20260901_01020304@synthetic.txt").write_bytes(b"preserve")

    def cleanup_owned_root(self):
        assert self.root.parent == disposable_parent()
        assert not self.root.is_symlink()
        shutil.rmtree(self.root)

    def build(self, root):
        return builder.build_run_input_evidence(
            root, root_id="synthetic", relative_scope="BattleLog",
            pc_id="PC-B", log_type="BattleLog", run_id="synthetic-run",
            reference_date=date(2026, 10, 21),
            started_at=datetime(2026, 10, 21, tzinfo=timezone.utc),
        )

    def test_junction_source_root_rejected_before_enumeration(self):
        alias = self.make_junction("alias", self.external)
        with patch.object(builder.os, "scandir") as scan:
            with self.assertRaisesRegex(InventoryBuildError, "^source_root_invalid$"):
                self.build(alias)
            scan.assert_not_called()
        self.assertEqual((self.external / "20260901_01020304@synthetic.txt").read_bytes(), b"preserve")

    def test_junction_source_ancestor_rejected_before_enumeration(self):
        nested = self.external / "nested"
        nested.mkdir()
        alias = self.make_junction("alias", self.external)
        with patch.object(builder.os, "scandir") as scan:
            with self.assertRaisesRegex(InventoryBuildError, "^source_root_invalid$"):
                self.build(alias / "nested")
            scan.assert_not_called()
        self.assertEqual(list(nested.iterdir()), [])

    def test_junction_child_is_not_followed_and_enumeration_is_incomplete(self):
        self.make_junction("source/alias", self.external)
        with patch.object(builder, "_hash_stable_file") as hash_file:
            value = self.build(self.source)
            hash_file.assert_not_called()
        self.assertEqual(value["enumeration"]["status"], "incomplete")
        self.assertGreater(value["enumeration"]["enumeration_errors"], 0)
        self.assertEqual(value["inventory"]["targets"], [])
        self.assertEqual((self.external / "20260901_01020304@synthetic.txt").read_bytes(), b"preserve")



    def test_queued_directory_replaced_by_junction_is_rechecked(self):
        child = self.source / "queued"
        child.mkdir()
        original_lstat = Path.lstat
        swapped = False

        def swap_after_entry_stat(path, *args, **kwargs):
            nonlocal swapped
            info = original_lstat(path, *args, **kwargs)
            if path == child and not swapped:
                swapped = True
                child.rename(self.root / "saved")
                self.make_junction("source/queued", self.external)
            return info

        with patch.object(Path, "lstat", swap_after_entry_stat):
            with patch.object(builder.os, "scandir", wraps=builder.os.scandir) as scan:
                with patch.object(builder, "_hash_stable_file") as hash_file:
                    value = self.build(self.source)
                    hash_file.assert_not_called()
                self.assertEqual([Path(call.args[0]) for call in scan.call_args_list], [self.source])
        self.assertTrue(swapped)
        self.assertEqual(value["enumeration"]["status"], "incomplete")
        self.assertGreater(value["enumeration"]["enumeration_errors"], 0)
        self.assertEqual(value["inventory"]["targets"], [])

    def test_unavailable_entry_attributes_mark_enumeration_incomplete(self):
        source_file = self.source / "20260901_01020304@synthetic.txt"
        source_file.write_bytes(b"preserve")
        original_lstat = Path.lstat

        def unavailable_entry(path, *args, **kwargs):
            if path == source_file:
                raise PermissionError("private detail")
            return original_lstat(path, *args, **kwargs)

        with patch.object(Path, "lstat", unavailable_entry):
            with patch.object(builder, "_hash_stable_file") as hash_file:
                value = self.build(self.source)
                hash_file.assert_not_called()
        self.assertEqual(value["enumeration"]["status"], "incomplete")
        self.assertGreater(value["enumeration"]["enumeration_errors"], 0)
        self.assertEqual(value["inventory"]["targets"], [])
        self.assertEqual(source_file.read_bytes(), b"preserve")

    def test_unavailable_root_attributes_rejected_before_enumeration(self):
        with patch.object(Path, "lstat", side_effect=PermissionError("private detail")):
            with patch.object(builder.os, "scandir") as scan:
                with self.assertRaisesRegex(InventoryBuildError, "^source_root_unavailable$"):
                    self.build(self.source)
                scan.assert_not_called()

    def test_hash_helper_rejects_junction_ancestor_before_open(self):
        alias = self.make_junction("alias", self.external)
        with patch.object(Path, "open") as opened:
            with self.assertRaisesRegex(InventoryBuildError, "^source_reparse_component$"):
                builder._hash_stable_file(alias / "20260901_01020304@synthetic.txt")
            opened.assert_not_called()


if __name__ == "__main__":
    unittest.main()
