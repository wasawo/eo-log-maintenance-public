"""Actual termination inside publication; crash leftovers must fail closed."""
import json
import shutil
import unittest
from uuid import uuid4

from crash_publication_harness import (
    HarnessError, INTERNAL_STAGES, MARKER, disposable_parent,
    run_internal_crash_scenario,
)


class InternalPublicationCrashTests(unittest.TestCase):
    def check_stage(self, stage):
        for target in ("manifest.json", MARKER):
            with self.subTest(target=target):
                root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
                try:
                    result = run_internal_crash_scenario(root, target, stage, acknowledged=True)
                    self.assertNotEqual(result["publisher_exit_code"], 0)
                    self.assertEqual(result["orphan_count"], 1)
                    self.assertEqual(result["orphan_empty"], stage == "temp-created")
                    self.assertEqual(result["target_visible"], stage == "after-link")
                    self.assertEqual(result["marker_visible"], target == MARKER and stage == "after-link")
                    self.assertEqual(result["initial"], "unexpected_directory_entry")
                    self.assertEqual(result["after_retry"], "unexpected_directory_entry")
                    self.assertTrue(result["preserved"])
                    self.assertTrue(result["published_payloads_match"])
                    self.assertTrue(result["orphan_names_unchanged"])
                    self.assertNotIn(str(root), json.dumps(result))
                finally:
                    if root.exists():
                        assert root.parent == disposable_parent()
                        assert root.name.startswith("eo-crash-harness-")
                        assert not root.is_symlink()
                        shutil.rmtree(root)

    def test_after_temp_creation(self):
        self.check_stage("temp-created")

    def test_before_fsync(self):
        self.check_stage("before-fsync")

    def test_after_fsync(self):
        self.check_stage("after-fsync")

    def test_before_link(self):
        self.check_stage("before-link")

    def test_after_link_before_owned_temp_cleanup(self):
        self.check_stage("after-link")

    def test_invalid_scenario_writes_nothing(self):
        root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
        for target, stage in (("invalid.json", INTERNAL_STAGES[0]), (MARKER, "invalid")):
            with self.assertRaisesRegex(HarnessError, "internal_scenario_invalid"):
                run_internal_crash_scenario(root, target, stage, acknowledged=True)
        self.assertFalse(root.exists())

    def test_missing_acknowledgement_writes_nothing(self):
        root = disposable_parent() / ("eo-crash-harness-" + uuid4().hex)
        with self.assertRaisesRegex(HarnessError, "acknowledgement_required"):
            run_internal_crash_scenario(root, MARKER, INTERNAL_STAGES[0])
        self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
