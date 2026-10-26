"""Synthetic acceptance tests for atomic no-overwrite artifact publication."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from Common import AtomicArtifactPublication as atomic

from Common.AtomicArtifactPublication import (
    ArtifactPublicationError,
    publish_bytes_no_overwrite,
)


class AtomicArtifactPublicationTests(unittest.TestCase):
    def test_initial_size_conflict_rejects_without_payload_open_or_creation(self):
        destination = self.root/"manifest.json"
        expected = b"synthetic"
        for payload in (b"", b"x", expected+b"x"*131072):
            destination.write_bytes(payload)
            with self.subTest(size=len(payload)), patch.object(Path, "open") as opened, \
                    patch.object(atomic.tempfile, "mkstemp") as created:
                with self.assertRaisesRegex(ArtifactPublicationError, "^destination_conflict$"):
                    publish_bytes_no_overwrite(destination, expected)
                opened.assert_not_called()
                created.assert_not_called()
            self.assertEqual(payload, destination.read_bytes())
            self.assertEqual([destination], list(self.root.iterdir()))

    def test_empty_and_multichunk_identical_existing_files_remain_idempotent(self):
        destination = self.root/"manifest.json"
        for payload in (b"", b"x"*(1024*1024+7)):
            destination.write_bytes(payload)
            with self.subTest(size=len(payload)), patch.object(atomic.tempfile, "mkstemp") as created:
                self.assertEqual("already_exists_identical", publish_bytes_no_overwrite(destination, payload))
                created.assert_not_called()
            self.assertEqual(payload, destination.read_bytes())

    def test_growth_during_comparison_stops_at_expected_size_plus_one(self):
        destination = self.root/"manifest.json"
        payload = b"x"*(1024*1024+7)
        destination.write_bytes(payload)
        real_open = Path.open
        requests, consumed, closed = [], [], []
        class Stream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args):
                self.stream.close()
                closed.append(True)
            def fileno(self): return self.stream.fileno()
            def read(self, size):
                requests.append(size)
                block = self.stream.read(size)
                consumed.append(len(block))
                if len(requests) == 1:
                    with real_open(destination, "ab") as writer: writer.write(b"y"*131072)
                return block
        def opened(path, *args, **kwargs): return Stream(real_open(path, *args, **kwargs))
        with patch.object(Path, "open", opened), patch.object(atomic.tempfile, "mkstemp") as created:
            with self.assertRaisesRegex(ArtifactPublicationError, "^artifact_changed_during_read$"):
                publish_bytes_no_overwrite(destination, payload)
            created.assert_not_called()
        self.assertEqual(len(payload)+1, sum(consumed))
        self.assertTrue(all(0 < size <= 1024*1024 for size in requests))
        self.assertEqual([True], closed)
        self.assertEqual(payload+b"y"*131072, destination.read_bytes())

    def test_size_change_between_inspection_and_open_rejects_before_read(self):
        destination = self.root/"manifest.json"
        payload = b"synthetic"
        destination.write_bytes(payload)
        real_open = Path.open
        class Stream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, *_): raise AssertionError("changed handle must not read")
        def opened(path, *args, **kwargs):
            with real_open(path, "ab") as writer: writer.write(b"x")
            return Stream(real_open(path, *args, **kwargs))
        with patch.object(Path, "open", opened):
            with self.assertRaisesRegex(ArtifactPublicationError, "^artifact_changed_during_read$"):
                publish_bytes_no_overwrite(destination, payload)
        self.assertEqual(payload+b"x", destination.read_bytes())

    def test_staging_is_reread_before_atomic_link_and_final_bytes_verified(self):
        destination = self.root / "manifest.json"
        payload = b"synthetic"
        real = atomic._same_bytes
        observed = []
        def inspected(path, data):
            observed.append(path.name)
            return real(path, data)
        with patch.object(atomic, "_same_bytes", side_effect=inspected):
            self.assertEqual("published", publish_bytes_no_overwrite(destination, payload))
        self.assertTrue(observed[0].startswith(".manifest.json.tmp-"))
        self.assertIn("manifest.json", observed)
        self.assertEqual(payload, destination.read_bytes())
        self.assertEqual([], list(self.root.glob(".manifest.json.tmp-*")))

    def test_staging_content_change_blocks_link_and_preserves_unverified_temp(self):
        destination = self.root / "manifest.json"
        real = atomic._same_bytes
        changed = False
        def tamper(path, data):
            nonlocal changed
            if not changed:
                changed = True
                path.write_bytes(b"synthetic_changed")
            return real(path, data)
        with patch.object(atomic, "_same_bytes", side_effect=tamper), patch.object(atomic.os, "link") as link:
            with self.assertRaisesRegex(ArtifactPublicationError, "staging_readback_unverified"):
                publish_bytes_no_overwrite(destination, b"synthetic")
            link.assert_not_called()
        self.assertFalse(destination.exists())
        temporary = list(self.root.glob(".manifest.json.tmp-*"))
        self.assertEqual(1, len(temporary))
        self.assertEqual(b"synthetic_changed", temporary[0].read_bytes())

    def test_replaced_temp_with_equal_bytes_is_not_published_or_cleaned(self):
        destination = self.root / "manifest.json"
        real = atomic._same_bytes
        moved = self.root / "synthetic-original-temp"
        changed = False
        def substitute(path, data):
            nonlocal changed
            if not changed:
                changed = True
                path.rename(moved)
                path.write_bytes(data)
            return real(path, data)
        with patch.object(atomic, "_same_bytes", side_effect=substitute), patch.object(atomic.os, "link") as link:
            with self.assertRaisesRegex(ArtifactPublicationError, "staging_readback_unverified"):
                publish_bytes_no_overwrite(destination, b"synthetic")
            link.assert_not_called()
        self.assertEqual(b"synthetic", moved.read_bytes())
        self.assertEqual(1, len(list(self.root.glob(".manifest.json.tmp-*"))))
        self.assertFalse(destination.exists())

    def test_replacement_at_cleanup_is_preserved_after_successful_publication(self):
        destination = self.root / "manifest.json"
        real = atomic._same_bytes
        moved = self.root / "synthetic-owned-temp"
        temp_calls = 0
        def substitute(path, data):
            nonlocal temp_calls
            if path.name.startswith(".manifest.json.tmp-"):
                temp_calls += 1
                if temp_calls == 2:
                    path.rename(moved)
                    path.write_bytes(data)
            return real(path, data)
        with patch.object(atomic, "_same_bytes", side_effect=substitute):
            self.assertEqual("published", publish_bytes_no_overwrite(destination, b"synthetic"))
        self.assertEqual(b"synthetic", destination.read_bytes())
        self.assertEqual(b"synthetic", moved.read_bytes())
        self.assertEqual(1, len(list(self.root.glob(".manifest.json.tmp-*"))))

    def test_successful_link_without_expected_final_identity_is_not_reported_published(self):
        destination = self.root / "manifest.json"
        def substitute(source, target):
            Path(target).write_bytes(Path(source).read_bytes())
        with patch.object(atomic.os, "link", side_effect=substitute):
            with self.assertRaisesRegex(ArtifactPublicationError, "published_artifact_unverified"):
                publish_bytes_no_overwrite(destination, b"synthetic")
        self.assertEqual(b"synthetic", destination.read_bytes())

    def test_existing_file_handle_identity_mismatch_is_rejected(self):
        destination = self.root / "manifest.json"
        destination.write_bytes(b"synthetic")
        real = os.fstat
        def changed(fd):
            info = real(fd)
            values = {name: getattr(info, name) for name in
                ("st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")}
            values["st_ino"] += 1
            return SimpleNamespace(**values)
        with patch.object(atomic.os, "fstat", side_effect=changed):
            with self.assertRaisesRegex(ArtifactPublicationError, "artifact_changed_during_read"):
                publish_bytes_no_overwrite(destination, b"synthetic")
        self.assertEqual(b"synthetic", destination.read_bytes())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_publishes_complete_bytes_and_leaves_no_temp(self):
        destination = self.root / "manifest.json"
        result = publish_bytes_no_overwrite(destination, b'{"status":"success"}\n')
        self.assertEqual(result, "published")
        self.assertEqual(destination.read_bytes(), b'{"status":"success"}\n')
        self.assertEqual(list(self.root.glob(".manifest.json.tmp-*")), [])

    def test_identical_retry_is_idempotent(self):
        destination = self.root / "evidence.json"
        payload = b'{"evidence":1}\n'
        self.assertEqual(publish_bytes_no_overwrite(destination, payload), "published")
        self.assertEqual(publish_bytes_no_overwrite(destination, payload), "already_exists_identical")
        self.assertEqual(destination.read_bytes(), payload)

    def test_conflicting_retry_does_not_overwrite_existing_artifact(self):
        destination = self.root / "manifest.json"
        original = b'{"status":"running"}\n'
        self.assertEqual(publish_bytes_no_overwrite(destination, original), "published")
        with self.assertRaisesRegex(ArtifactPublicationError, "destination_conflict"):
            publish_bytes_no_overwrite(destination, b'{"status":"success"}\n')
        self.assertEqual(destination.read_bytes(), original)

    def test_atomic_link_failure_fails_closed_and_cleans_owned_temp(self):
        destination = self.root / "report.json"
        with patch("Common.AtomicArtifactPublication.os.link", side_effect=OSError("synthetic")):
            with self.assertRaisesRegex(ArtifactPublicationError, "atomic_publish_unavailable"):
                publish_bytes_no_overwrite(destination, b'{"report":1}\n')
        self.assertFalse(destination.exists())
        self.assertEqual(list(self.root.glob(".report.json.tmp-*")), [])

    def test_rejects_non_bytes_and_non_regular_existing_destination(self):
        with self.assertRaisesRegex(ArtifactPublicationError, "artifact_bytes_required"):
            publish_bytes_no_overwrite(self.root / "x.json", "not bytes")
        subdir = self.root / "existing"
        subdir.mkdir()
        with self.assertRaisesRegex(ArtifactPublicationError, "destination_not_regular_file"):
            publish_bytes_no_overwrite(subdir, b"payload")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_rejects_destination_symlink(self):
        target = self.root / "target.json"
        target.write_bytes(b"target")
        destination = self.root / "alias.json"
        try:
            destination.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation not permitted")
        with self.assertRaisesRegex(ArtifactPublicationError, "destination_not_regular_file"):
            publish_bytes_no_overwrite(destination, b"replacement")
        self.assertEqual(target.read_bytes(), b"target")


if __name__ == "__main__":
    unittest.main()
