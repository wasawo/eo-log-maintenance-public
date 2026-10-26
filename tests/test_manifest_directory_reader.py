"""Synthetic filesystem observations; no operational roots or mutations."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import traceback
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common import ManifestDirectoryReader as reader
from Common.LatestManifestSelection import LatestManifestSelectionError
from crash_publication_harness import create_disposable_root, disposable_parent
import test_latest_manifest_selection as core_tests
import test_artifact_directory_reparse as reparse_tests
from test_source_enumeration_stability import duplicate_scan_on_call


class ManifestDirectoryReaderTests(unittest.TestCase):
    def test_duplicate_initial_or_final_enumeration_blocks_without_deduplication(self):
        candidate = self.put()
        for repeat_call in (1, 2):
            with self.subTest(repeat_call=repeat_call), patch.object(reader.os, "scandir",
                    side_effect=duplicate_scan_on_call(self.directory, repeat_call)):
                with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "^manifest_directory_changed$"):
                    self.read(maximum_entries=2)
            self.assertEqual(candidate.content, (self.directory/candidate.filename).read_bytes())

    candidate = core_tests.LatestManifestSelectionTests.candidate
    make_junction = reparse_tests.ArtifactDirectoryReparseTests.make_junction

    def setUp(self):
        self.root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
        create_disposable_root(self.root, acknowledged=True)
        self.addCleanup(self.cleanup)
        self.directory = self.root / "_maintenance" / "manifests" / "PC-A"
        self.directory.mkdir(parents=True)

    def cleanup(self):
        assert self.root.parent == disposable_parent()
        assert not self.root.is_symlink()
        shutil.rmtree(self.root)

    def put(self, *args, **kwargs):
        candidate = self.candidate(*args, **kwargs)
        (self.directory / candidate.filename).write_bytes(candidate.content)
        return candidate

    def read(self, root=None, **changes):
        options = dict(expected_pc_id="PC-A", expected_log_type="BattleLog",
                       expected_target_period="2026-09",
                       current_utc=datetime(2026, 10, 23, 10, tzinfo=timezone.utc),
                       current_utc_reliable=True)
        options.update(changes)
        return reader.read_latest_manifest(self.root if root is None else root, **options)

    def rejected(self, reason, **changes):
        with self.assertRaises((reader.ManifestDirectoryReadError, LatestManifestSelectionError)) as caught:
            self.read(**changes)
        self.assertEqual(caught.exception.reason_code, reason)
        return caught.exception

    def test_latest_exact_snapshot_hash_and_no_writes(self):
        self.put(1, "2026-10-23T09:00:00Z")
        latest = self.put(2)
        self.put(3, log_type="ErrorReport", target_period="2025")
        before = {p.name: p.read_bytes() for p in self.directory.iterdir()}
        result = self.read()
        self.assertEqual((result.filename, result.content), (latest.filename, latest.content))
        self.assertEqual(result.sha256, hashlib.sha256(latest.content).hexdigest())
        self.assertNotIn(str(self.root), repr(result))
        self.assertNotIn("schema_version", repr(result))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.iterdir()})

    def test_pc_b_error_report_scope(self):
        self.directory = self.directory.parent / "PC-B"
        self.directory.mkdir()
        candidate = self.put(pc_id="PC-B", log_type="ErrorReport", target_period="2025")
        result = self.read(expected_pc_id="PC-B", expected_log_type="ErrorReport", expected_target_period="2025")
        self.assertEqual(result.content, candidate.content)

    def test_no_older_success_fallback(self):
        self.put(1, "2026-10-23T09:00:00Z")
        self.put(2, status="running")
        self.rejected("latest_manifest_not_success")
        self.assertEqual(self.read(require_current_success=False).status, "running")

    def test_tie_blocks(self):
        self.put(1)
        self.put(2)
        self.rejected("latest_manifest_ambiguous")

    def test_invalid_root_does_not_create(self):
        for root in (Path("relative"), self.root / ".." / "missing"):
            self.rejected("maintenance_root_invalid", root=root)
        self.rejected("manifest_directory_read_failed", root=self.root / "missing")
        self.assertFalse((self.root / "missing").exists())

    def test_timestamp_fraction_requires_literal_dot(self):
        from Common.LatestManifestSelection import _utc_key
        with self.assertRaisesRegex(LatestManifestSelectionError, "candidate_timestamp_invalid"):
            _utc_key("2026-10-23T10:00:00x1Z")

    def test_empty_directory_blocks(self):
        with self.assertRaises(LatestManifestSelectionError):
            self.read()

    def test_clock_rejected_before_io(self):
        with patch.object(reader.os, "scandir", side_effect=AssertionError("unexpected_io")) as scan:
            with self.assertRaises(LatestManifestSelectionError):
                self.read(current_utc_reliable=False)
            scan.assert_not_called()

    def test_unknown_temp_name_blocks(self):
        self.put()
        (self.directory / "pending.tmp").write_bytes(b"synthetic")
        with self.assertRaises(LatestManifestSelectionError):
            self.read()

    def test_subdirectory_blocks(self):
        (self.directory / self.candidate().filename).mkdir()
        self.rejected("manifest_entry_untrusted")

    def test_foreign_pc_blocks(self):
        self.put(pc_id="PC-B")
        self.rejected("manifest_directory_scope_mismatch")

    def test_corrupt_foreign_period_blocks(self):
        self.put()
        other = self.put(2, target_period="2026-08")
        (self.directory / other.filename).write_bytes(b"{")
        with self.assertRaises(LatestManifestSelectionError):
            self.read()

    def test_partial_enumeration_error_is_not_success(self):
        candidate = self.put()
        class PartialScan:
            def __enter__(inner):
                return inner
            def __exit__(inner, *args):
                return False
            def __iter__(inner):
                yield type("Entry", (), {"name": candidate.filename})()
                raise OSError("synthetic_private_detail")
        with patch.object(reader.os, "scandir", return_value=PartialScan()):
            self.rejected("manifest_directory_read_failed")

    def test_read_failure_sanitized(self):
        candidate = self.put()
        original = Path.open
        def fail(path, *args, **kwargs):
            if path.name == candidate.filename:
                raise OSError("synthetic_private_detail")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", fail):
            try:
                self.read()
            except reader.ManifestDirectoryReadError:
                output = traceback.format_exc()
            else:
                self.fail("read_should_fail")
        self.assertNotIn("OSError:", output)
        self.assertNotIn("synthetic_private_detail", output)
        self.assertNotIn(str(self.root), output)

    def test_opened_replacement_rejected_before_read_and_original_restored(self):
        candidate = self.put()
        target = self.directory / candidate.filename
        backup = self.root / "backup"
        original = Path.open
        @contextmanager
        def swap(path, *args, **kwargs):
            if path != target:
                with original(path, *args, **kwargs) as stream:
                    yield stream
                return
            target.rename(backup)
            with original(target, "wb") as replacement:
                replacement.write(b"replacement")
            try:
                with original(target, *args, **kwargs) as stream:
                    with patch.object(stream, "read", side_effect=AssertionError("untrusted_read")):
                        yield stream
            finally:
                target.unlink()
                backup.rename(target)
        with patch.object(Path, "open", swap):
            self.rejected("manifest_candidate_changed")
        self.assertEqual(target.read_bytes(), candidate.content)

    def test_changes_after_selection_block(self):
        self.put()
        original = reader.select_latest_manifest
        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            if kwargs.get("require_current_success"):
                self.put(2, "2026-10-23T09:00:00Z")
            return result
        with patch.object(reader, "select_latest_manifest", mutate):
            self.rejected("manifest_directory_changed")

    @unittest.skipUnless(os.name == "nt", "real Windows junction required")
    def test_junction_root_rejected(self):
        self.put()
        alias = self.make_junction("alias", self.root)
        self.rejected("manifest_directory_untrusted", root=alias)

    @unittest.skipUnless(os.name == "nt", "real Windows junction required")
    def test_junction_manifest_ancestor_rejected(self):
        self.put()
        target = self.root / "other"
        self.directory.parent.rename(target)
        self.make_junction("_maintenance/manifests", target)
        self.rejected("manifest_directory_untrusted")

    @unittest.skipUnless(os.name == "nt", "real Windows junction required")
    def test_junction_entry_rejected(self):
        target = self.root / "other"
        target.mkdir()
        self.make_junction("_maintenance/manifests/PC-A/" + self.candidate().filename, target)
        self.rejected("manifest_entry_untrusted")
