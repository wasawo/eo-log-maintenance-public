"""Synthetic acceptance tests for atomic no-overwrite artifact publication."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Common.AtomicArtifactPublication import (
    ArtifactPublicationError,
    publish_bytes_no_overwrite,
)


class AtomicArtifactPublicationTests(unittest.TestCase):
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
