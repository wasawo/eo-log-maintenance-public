"""Synthetic native ABI and use-point tests; no task, logs or Drive access."""
import ctypes
from dataclasses import FrozenInstanceError
import os
import unittest
from unittest.mock import Mock, patch

from Common import PowerStatusObservation as power
from Common.CompletionWaitAttempt import (CompletionWaitAttemptError,
    prepare_completion_wait_attempt, inspect_completion_wait_attempt_usepoint)
from test_completion_wait_attempt import options
from test_completion_wait_checkpoint import checkpoint, encode


class PowerStatusObservationTests(unittest.TestCase):
    def observe(self, value):
        with patch.object(power.os, "name", "nt"), patch.object(power, "_read_ac_line_status", return_value=value):
            return power.observe_ac_power()

    def test_connected_disconnected_unknown_are_distinct_and_non_authorizing(self):
        for value, expected, reason in ((1, True, "power_ac_connected"), (0, False, "power_ac_disconnected"),
                                        (255, None, "power_status_unknown"), (2, None, "power_status_unknown")):
            with self.subTest(value=value):
                result = self.observe(value)
                self.assertIs(result.ac_connected, expected)
                self.assertEqual(reason, result.reason_code)
                self.assertFalse(result.may_check or result.may_archive or result.may_start_run)
                with self.assertRaises(FrozenInstanceError): result.ac_connected = True

    def test_malformed_private_result_cannot_be_truthy_success(self):
        for value in (True, False, "1", None, -1, 256, 1.0):
            self.assertIsNone(self.observe(value).ac_connected)

    def test_failure_is_sanitized_and_not_offline_or_online(self):
        with patch.object(power.os, "name", "nt"), patch.object(power, "_read_ac_line_status", side_effect=OSError("synthetic-secret")):
            result = power.observe_ac_power()
        self.assertIsNone(result.ac_connected)
        self.assertEqual("power_query_failed", result.reason_code)
        self.assertNotIn("synthetic-secret", repr(result))

    def test_unsupported_platform_does_not_load_native_api(self):
        with patch.object(power.os, "name", "other"), patch.object(power, "_read_ac_line_status") as query:
            self.assertEqual("power_platform_unsupported", power.observe_ac_power().reason_code)
            query.assert_not_called()

    def test_native_structure_layout_and_signature(self):
        self.assertEqual(12, ctypes.sizeof(power._SystemPowerStatus))
        self.assertEqual(4, power._SystemPowerStatus.BatteryLifeTime.offset)
        self.assertEqual(8, power._SystemPowerStatus.BatteryFullLifeTime.offset)
        def fill(pointer):
            pointer._obj.ACLineStatus = 1
            pointer._obj.BatteryFlag = 255  # Do not infer AC from battery fields.
            return 1
        api = Mock()
        api.GetSystemPowerStatus.side_effect = fill
        with patch.object(power.ctypes, "WinDLL", return_value=api, create=True) as load:
            self.assertEqual(1, power._read_ac_line_status())
        load.assert_called_once_with("kernel32", use_last_error=True)
        self.assertEqual((ctypes.POINTER(power._SystemPowerStatus),), api.GetSystemPowerStatus.argtypes)
        self.assertIs(ctypes.c_int, api.GetSystemPowerStatus.restype)

    def test_native_failure_never_uses_zero_initialized_status(self):
        api = Mock()
        api.GetSystemPowerStatus.return_value = 0
        with patch.object(power.ctypes, "WinDLL", return_value=api, create=True):
            with self.assertRaisesRegex(OSError, "power_query_failed"): power._read_ac_line_status()

    def test_load_failure_is_unknown(self):
        with patch.object(power.os, "name", "nt"), patch.object(power.ctypes, "WinDLL", side_effect=OSError("synthetic-secret"), create=True):
            self.assertIsNone(power.observe_ac_power().ac_connected)

    def test_fresh_observation_at_each_phase_blocks_disconnect_without_refund(self):
        plan = prepare_completion_wait_attempt(encode(checkpoint()), **options())
        original = plan.proposed_bytes
        with patch.object(power.os, "name", "nt"), patch.object(power, "_read_ac_line_status", side_effect=[1, 0, 255, 1]) as query:
            for phase, expected in (("before_commit", True), ("after_commit", False),
                                    ("after_commit", False), ("after_commit", True)):
                ac = power.observe_ac_power()
                call = dict(phase=phase, ac_connected=ac.ac_connected, **options())
                observed = plan.expected_bytes if phase == "before_commit" else plan.proposed_bytes
                if expected:
                    self.assertFalse(inspect_completion_wait_attempt_usepoint(plan, observed, **call)["may_check"])
                else:
                    with self.assertRaisesRegex(CompletionWaitAttemptError, "attempt_ac_unconfirmed"):
                        inspect_completion_wait_attempt_usepoint(plan, observed, **call)
                self.assertEqual(original, plan.proposed_bytes)
                self.assertEqual(1, plan.attempt_number)
            self.assertEqual(4, query.call_count)

    @unittest.skipUnless(os.name == "nt", "Windows read-only API required")
    def test_native_read_returns_only_bounded_observation(self):
        result = power.observe_ac_power()
        self.assertIn(result.reason_code, ("power_ac_connected", "power_ac_disconnected", "power_status_unknown"))
        self.assertIn(result.ac_connected, (True, False, None))


if __name__ == "__main__": unittest.main()
