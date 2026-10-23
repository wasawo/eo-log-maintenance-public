"""Non-authorizing diagnosis and public-output privacy boundaries."""
from dataclasses import FrozenInstanceError
import json
import traceback
import unittest
from unittest.mock import patch

from Common.RecoveryDiagnostic import (
    GATES, RecoveryDiagnostic, RecoveryDiagnosticError, build_recovery_diagnostic,
)


class RecoveryDiagnosticTests(unittest.TestCase):
    def build(self, observations=None, **changes):
        args = dict(pc_id="PC-B", log_type="BattleLog", target_period="2026-09",
                    observations=dict.fromkeys(GATES, "satisfied") if observations is None else observations)
        args.update(changes)
        return build_recovery_diagnostic(**args)

    def test_all_supplied_satisfied_is_review_not_authorization(self):
        result = self.build()
        self.assertEqual(result.classification, "review_required")
        self.assertFalse(result.may_change_state)
        self.assertEqual(result.reason_codes, ("diagnosis_observations_complete",))
        self.assertIs(result.to_public_dict()["may_change_state"], False)

    def test_unknown_owner_and_drive_block_even_if_other_gates_satisfied(self):
        gates = dict.fromkeys(GATES, "satisfied")
        gates.update(owner_termination="unknown", drive_reconciliation="missing")
        result = self.build(gates)
        self.assertEqual(result.classification, "blocked")
        self.assertEqual(result.reason_codes, ("owner_termination_unknown", "drive_reconciliation_missing"))
        self.assertFalse(result.may_change_state)

    def test_missing_gate_never_defaults_to_success(self):
        gates = dict.fromkeys(GATES, "satisfied")
        del gates["mutex"]
        with self.assertRaises(RecoveryDiagnosticError):
            self.build(gates)

    def test_raw_secret_field_is_rejected_without_value_in_error(self):
        gates = dict.fromkeys(GATES, "satisfied")
        gates["owner_token"] = "synthetic_secret_do_not_emit"
        try:
            self.build(gates)
        except RecoveryDiagnosticError as error:
            self.assertEqual(str(error), "diagnostic_input_invalid")
            self.assertNotIn("synthetic_secret_do_not_emit", traceback.format_exc())
        else:
            self.fail("raw_record_should_not_be_accepted")

    def test_free_text_or_boolean_gate_is_not_accepted(self):
        for value in (True, 1, None, "synthetic_private_path", "success", []):
            gates = dict.fromkeys(GATES, "satisfied")
            gates["root"] = value
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaisesRegex(RecoveryDiagnosticError, "diagnostic_input_invalid"):
                    self.build(gates)

    def test_invalid_scope_cannot_enter_public_output(self):
        for changes in ({"pc_id": "synthetic_private_host"},
                        {"log_type": "other"}, {"target_period": "2026-13"},
                        {"target_period": "2026-09/extra"}):
            with self.assertRaises(RecoveryDiagnosticError):
                self.build(**changes)

    def test_both_roles_and_log_scopes(self):
        for pc in ("PC-A", "PC-B"):
            for log_type, period in (("BattleLog", "2026-09"), ("ErrorReport", "2025")):
                self.assertFalse(self.build(pc_id=pc, log_type=log_type, target_period=period).may_change_state)

    def test_json_contains_only_allowlisted_public_fields(self):
        public = self.build().to_public_dict()
        self.assertEqual(set(public), {"schema_version", "pc_id", "log_type", "target_period",
                                       "classification", "reason_codes", "may_change_state"})
        self.assertEqual(json.loads(json.dumps(public)), public)

    def test_input_and_export_mutations_do_not_change_result(self):
        gates = dict.fromkeys(GATES, "satisfied")
        result = self.build(gates)
        gates["root"] = "unknown"
        public = result.to_public_dict()
        public["reason_codes"].append("arbitrary")
        public["may_change_state"] = True
        self.assertEqual(result.reason_codes, ("diagnosis_observations_complete",))
        self.assertFalse(result.to_public_dict()["may_change_state"])
        with self.assertRaises(FrozenInstanceError):
            result.may_change_state = True

    def test_no_io_is_needed_for_classification(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")):
            self.assertEqual(self.build().classification, "review_required")

    def test_direct_construction_cannot_inject_raw_reason_or_ready(self):
        for classification, reasons in (("ready", ("diagnosis_observations_complete",)),
                                        ("blocked", ("synthetic_private_detail",)),
                                        ("review_required", ("owner_termination_unknown",))):
            with self.assertRaises(RecoveryDiagnosticError):
                RecoveryDiagnostic("PC-A", "BattleLog", "2026-09", classification, reasons)

    def test_export_rejects_deliberate_permission_tampering(self):
        result = self.build()
        object.__setattr__(result, "may_change_state", True)
        with self.assertRaises(RecoveryDiagnosticError):
            result.to_public_dict()
