"""Acceptance evidence for actual publisher termination, using temp roots only."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from uuid import uuid4

from crash_publication_harness import (
    HarnessError, MARKER, PAYLOADS, create_disposable_root,
    observe_fresh, run_crash_matrix,
)


class CrashPublicationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.gettempdir()).resolve() / (
            "eo-crash-harness-" + uuid4().hex
        )
        self.addCleanup(self.cleanup_owned_root)

    def cleanup_owned_root(self):
        if self.root.exists():
            assert self.root.parent == Path(tempfile.gettempdir()).resolve()
            assert self.root.name.startswith("eo-crash-harness-")
            assert not self.root.is_symlink()
            shutil.rmtree(self.root)

    def test_real_process_termination_at_every_file_publication_boundary(self):
        result = run_crash_matrix(self.root, acknowledged=True)
        self.assertEqual(result["evidence_tier"], "synthetic-local-temp")
        self.assertEqual(len(result["scenarios"]), 4)
        self.assertEqual(
            [row["committed_before_retry"] for row in result["scenarios"]],
            [False, False, False, True],
        )
        for row in result["scenarios"]:
            self.assertNotEqual(row["publisher_exit_code"], 0)
            self.assertTrue(row["committed_after_retry"])
            self.assertTrue(row["published_bytes_preserved"])
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_missing_explicit_acknowledgement_writes_nothing(self):
        with self.assertRaisesRegex(HarnessError, "acknowledgement_required"):
            run_crash_matrix(self.root)
        self.assertFalse(self.root.exists())

    def test_existing_root_is_never_adopted_or_modified(self):
        self.root.mkdir()
        sentinel = self.root / "operator-file.txt"
        sentinel.write_bytes(b"preserve")
        with self.assertRaisesRegex(HarnessError, "already_exists"):
            run_crash_matrix(self.root, acknowledged=True)
        self.assertEqual(sentinel.read_bytes(), b"preserve")
        self.assertEqual(list(self.root.iterdir()), [sentinel])

    def test_existing_empty_root_is_also_rejected(self):
        self.root.mkdir()
        with self.assertRaisesRegex(HarnessError, "already_exists"):
            create_disposable_root(self.root, acknowledged=True)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_non_temp_relative_and_parent_traversal_paths_rejected(self):
        values = [
            Path("relative") / self.root.name,
            Path(tempfile.gettempdir()).resolve().parent / self.root.name,
            Path(tempfile.gettempdir()).resolve() / ".." / self.root.name,
            Path(tempfile.gettempdir()).resolve(),
        ]
        for value in values:
            with self.subTest(kind=str(value.name)):
                with self.assertRaises(HarnessError):
                    create_disposable_root(value, acknowledged=True)
        self.assertFalse(self.root.exists())

    def test_tampering_and_unexpected_entries_are_not_reported_committed(self):
        run_crash_matrix(self.root, acknowledged=True)
        complete = self.root / "boundary-3"
        (complete / "report.json").write_bytes(b"tampered")
        result = observe_fresh(complete)
        self.assertFalse(result["final_committed"])
        with self.assertRaisesRegex(HarnessError, "observer_failed"):
            observe_fresh(complete, retry=True)
        self.assertEqual((complete / "report.json").read_bytes(), b"tampered")
        self.assertTrue((complete / MARKER).exists())
        (complete / "unexpected.txt").write_bytes(b"preserve")
        with self.assertRaisesRegex(HarnessError, "observer_failed"):
            observe_fresh(complete)
        self.assertEqual((complete / "unexpected.txt").read_bytes(), b"preserve")


if __name__ == "__main__":
    unittest.main()
