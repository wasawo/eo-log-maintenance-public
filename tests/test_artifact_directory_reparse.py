"""Windows junction and read-failure regressions for artifact-directory trust."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch
from uuid import uuid4

from crash_publication_harness import (
    PAYLOADS, TRANSACTION_ID, _hashes, create_disposable_root, disposable_parent,
)
from Common.ArtifactSetDirectoryVerification import (
    ArtifactSetDirectoryVerificationError, verify_published_artifact_set,
)
from Common.ArtifactSetPublication import publish_artifact_set_marker_last


@unittest.skipUnless(os.name == "nt", "real Windows junction required")
class ArtifactDirectoryReparseTests(unittest.TestCase):
    def setUp(self):
        self.root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
        create_disposable_root(self.root, acknowledged=True)
        self.addCleanup(self.cleanup_owned_root)
        self.real = self.root / "real"
        self.real.mkdir()
        self.artifacts = self.real / "artifacts"
        self.artifacts.mkdir()
        publish_artifact_set_marker_last(
            str(self.artifacts), PAYLOADS, transaction_id=TRANSACTION_ID,
        )

    def cleanup_owned_root(self):
        assert self.root.parent == disposable_parent()
        assert not self.root.is_symlink()
        shutil.rmtree(self.root)

    def make_junction(self, name, target):
        link = self.root / name
        script = self.root / "make-junction.ps1"
        script.write_text(
            "param([string]$Link, [string]$Target)\n"
            "$ErrorActionPreference = 'Stop'\n"
            "New-Item -ItemType Junction -Path $Link -Target $Target | Out-Null\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["pwsh", "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
             str(script), "-Link", str(link), "-Target", str(target)],
            capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.assertEqual(result.returncode, 0, "junction_fixture_creation_failed")
        self.assertTrue(link.lstat().st_file_attributes & 0x400)
        self.addCleanup(link.rmdir)
        return link

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.artifacts.iterdir()}

    def test_junction_root_rejected_before_any_artifact_read(self):
        alias = self.make_junction("alias", self.artifacts)
        original = self.snapshot()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("untrusted_read")):
            with self.assertRaisesRegex(
                ArtifactSetDirectoryVerificationError, "directory_unavailable",
            ):
                verify_published_artifact_set(alias, _hashes())
        self.assertEqual(self.snapshot(), original)

    def test_junction_ancestor_rejected_before_any_artifact_read(self):
        alias = self.make_junction("alias", self.real)
        original = self.snapshot()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("untrusted_read")):
            with self.assertRaisesRegex(
                ArtifactSetDirectoryVerificationError, "directory_unavailable",
            ):
                verify_published_artifact_set(alias / "artifacts", _hashes())
        self.assertEqual(self.snapshot(), original)

    def test_directory_junction_as_artifact_rejected(self):
        target = self.root / "other"
        target.mkdir()
        (self.artifacts / "report.json").unlink()
        # A junction under an expected artifact name must never be traversed.
        self.make_junction("real/artifacts/report.json", target)
        with self.assertRaisesRegex(
            ArtifactSetDirectoryVerificationError, "non_regular_artifact",
        ):
            verify_published_artifact_set(self.artifacts, _hashes())
        self.assertEqual(list(target.iterdir()), [])


class ArtifactDirectoryReadFailureTests(unittest.TestCase):
    def test_read_failure_is_sanitized_without_changing_artifacts(self):
        root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
        create_disposable_root(root, acknowledged=True)
        try:
            publish_artifact_set_marker_last(str(root), PAYLOADS, transaction_id=TRANSACTION_ID)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            with patch.object(Path, "read_bytes", side_effect=PermissionError("private-value")):
                with self.assertRaisesRegex(
                    ArtifactSetDirectoryVerificationError, "^artifact_read_failed$",
                ):
                    verify_published_artifact_set(root, _hashes())
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
        finally:
            assert root.parent == disposable_parent()
            assert not root.is_symlink()
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
