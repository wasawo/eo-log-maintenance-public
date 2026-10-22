"""Safety checks for the opt-in local-volume evidence entry point."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from crash_publication_harness import HarnessError, disposable_parent
from run_local_volume_checks import local_environment, run_local_volume_checks


class LocalVolumeEntryTests(unittest.TestCase):
    def test_explicit_acknowledgement_required_before_environment_probe(self):
        with patch("run_local_volume_checks.local_environment") as probe:
            with self.assertRaisesRegex(HarnessError, "acknowledgement_required"):
                run_local_volume_checks("Z:", "PC-B")
            probe.assert_not_called()

    def test_arbitrary_volume_and_role_strings_are_rejected(self):
        for volume, role in [("relative", "PC-B"), ("Z:/arbitrary", "PC-A"), ("Z:", "unknown")]:
            with self.subTest(role=role):
                with self.assertRaises(HarnessError):
                    local_environment(volume, role)

    def test_environment_mode_accepts_only_temp_or_this_repository(self):
        with patch.dict(os.environ, {"EO_TEST_VOLUME_MODE": "untrusted-path"}):
            with self.assertRaisesRegex(HarnessError, "mode_invalid"):
                disposable_parent()
        with patch.dict(os.environ, {"EO_TEST_VOLUME_MODE": "repository-local"}):
            self.assertEqual(disposable_parent(), Path(__file__).resolve().parents[1])
        with patch.dict(os.environ, {"EO_TEST_VOLUME_MODE": "os-temp"}):
            self.assertEqual(disposable_parent(), Path(tempfile.gettempdir()).resolve())

    def test_environment_mode_is_restored_when_test_loading_fails(self):
        with patch.dict(os.environ, {"EO_TEST_VOLUME_MODE": "os-temp"}):
            with patch("run_local_volume_checks.local_environment", return_value={}):
                with patch("run_local_volume_checks.unittest.defaultTestLoader.loadTestsFromName",
                           side_effect=RuntimeError("synthetic")):
                    with self.assertRaises(RuntimeError):
                        run_local_volume_checks("Z:", "PC-B", acknowledged=True)
            self.assertEqual(os.environ["EO_TEST_VOLUME_MODE"], "os-temp")


if __name__ == "__main__":
    unittest.main()
