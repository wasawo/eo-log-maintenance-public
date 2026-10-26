"""Byte-binding and privacy tests using in-memory synthetic old locks."""
import json
from pathlib import Path
import traceback
import unittest
from unittest.mock import patch

from Common.PrivateRecoveryEvidence import (
    PrivateRecoveryEvidenceError, build_private_recovery_evidence,
    validate_private_recovery_evidence,
)


class PrivateRecoveryEvidenceTests(unittest.TestCase):
    def test_nonlocal_schema_references_reject_build_and_validation_without_network(self):
        metadata = self.build()
        for keyword in ("$ref", "$dynamicRef"):
            for reference in ("https://synthetic.invalid/schema", "file:///synthetic-schema",
                              "relative-schema.json", "", None, 1):
                for schema in ({keyword: reference}, {"$defs": {"unused": {keyword: reference}}}):
                    with self.subTest(keyword=keyword, reference=reference), \
                            patch.object(Path, "read_text", return_value=json.dumps(schema)), \
                            patch("socket.socket", side_effect=AssertionError("must not retrieve")) as network:
                        with self.assertRaisesRegex(PrivateRecoveryEvidenceError, "^private_evidence_invalid$"):
                            self.build()
                        with self.assertRaisesRegex(PrivateRecoveryEvidenceError, "^private_evidence_invalid$"):
                            validate_private_recovery_evidence(metadata, self.raw)
                        network.assert_not_called()
        self.assertEqual(metadata, self.build())

    def test_registry_denies_retrieval_even_if_reference_preflight_is_bypassed(self):
        with patch("Common.PrivateRecoveryEvidence._require_local_schema_refs"), \
                patch.object(Path, "read_text", return_value='{"$ref":"https://synthetic.invalid/schema"}'), \
                patch("socket.socket", side_effect=AssertionError("must not retrieve")) as network:
            with self.assertRaisesRegex(PrivateRecoveryEvidenceError, "^private_evidence_invalid$"):
                self.build()
            network.assert_not_called()

    def test_local_schema_references_work_and_broken_or_invalid_schemas_fail_closed(self):
        metadata = self.build()
        path = Path(__file__).resolve().parents[1] / "contracts/private-recovery-evidence-v1.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["$defs"] = {"local": True}
        schema.setdefault("allOf", []).append({"$ref": "#/$defs/local"})
        with patch.object(Path, "read_text", return_value=json.dumps(schema)):
            self.assertEqual(metadata, self.build())
            self.assertEqual(len(self.raw), validate_private_recovery_evidence(metadata, self.raw)["raw_lock_size"])
        for invalid in ({"$ref": "#/$defs/missing"}, {"type": "synthetic-invalid"}):
            with self.subTest(schema=invalid), patch.object(Path, "read_text", return_value=json.dumps(invalid)):
                with self.assertRaisesRegex(PrivateRecoveryEvidenceError, "^private_evidence_invalid$"):
                    self.build()

    def setUp(self):
        self.raw = b'{"owner_token":"synthetic_private_token","host":"synthetic_host"}'
        self.options = dict(raw_lock_bytes=self.raw,
                            evidence_id="123e4567-e89b-42d3-a456-426614174000",
                            pc_id="PC-B", log_type="BattleLog", target_period="2026-09",
                            observed_at_utc="2026-10-23T12:00:00Z")

    def build(self, **changes):
        return build_private_recovery_evidence(**{**self.options, **changes})

    def mutated(self, **changes):
        value = json.loads(self.build())
        value.update(changes)
        return json.dumps(value).encode()

    def test_bound_metadata_does_not_contain_raw_secrets_or_grant_permission(self):
        before = self.raw
        metadata = self.build()
        self.assertNotIn(b"synthetic_private_token", metadata)
        self.assertNotIn(b"synthetic_host", metadata)
        self.assertNotIn(self.raw, metadata)
        value = validate_private_recovery_evidence(metadata, self.raw)
        self.assertIs(value["may_change_state"], False)
        self.assertEqual(value["raw_lock_size"], len(self.raw))
        self.assertEqual(self.raw, before)

    def test_other_raw_bytes_same_length_block(self):
        metadata = self.build()
        other = self.raw.replace(b"token", b"other")
        self.assertEqual(len(other), len(self.raw))
        with self.assertRaisesRegex(PrivateRecoveryEvidenceError, "private_lock_bytes_mismatch"):
            validate_private_recovery_evidence(metadata, other)

    def test_truncated_raw_bytes_block(self):
        with self.assertRaisesRegex(PrivateRecoveryEvidenceError, "private_lock_bytes_mismatch"):
            validate_private_recovery_evidence(self.build(), self.raw[:-1])

    def test_opaque_malformed_non_utf8_lock_can_be_preserved_without_interpretation(self):
        raw = b"\xff\x00synthetic_malformed_lock"
        metadata = self.build(raw_lock_bytes=raw)
        self.assertEqual(validate_private_recovery_evidence(metadata, raw)["raw_lock_size"], len(raw))
        self.assertNotIn(raw, metadata)

    def test_empty_or_mutable_lock_input_rejected(self):
        for raw in (b"", bytearray(self.raw), None, "private"):
            with self.assertRaises(PrivateRecoveryEvidenceError):
                self.build(raw_lock_bytes=raw)

    def test_unknown_fields_and_operation_permission_rejected(self):
        for changes in ({"owner_token": "synthetic_private_token"},
                        {"may_change_state": True}, {"purpose": "recovery_complete"}):
            with self.assertRaises(PrivateRecoveryEvidenceError):
                validate_private_recovery_evidence(self.mutated(**changes), self.raw)

    def test_paths_cannot_replace_fixed_raw_basename(self):
        for name in ("../lock", "C:/Example/lock", "other.bin"):
            with self.assertRaises(PrivateRecoveryEvidenceError):
                validate_private_recovery_evidence(self.mutated(raw_lock_filename=name), self.raw)

    def test_duplicate_key_invalid_json_and_utf8_rejected(self):
        duplicate = b'{"pc_id":"PC-A",' + self.build()[1:]
        for metadata in (duplicate, b"{", b"\xff", b"[]", b"null"):
            with self.assertRaises(PrivateRecoveryEvidenceError):
                validate_private_recovery_evidence(metadata, self.raw)

    def test_wrong_version_and_bool_primitives_rejected(self):
        for changes in ({"schema_version": 2}, {"schema_version": True},
                        {"raw_lock_size": True}, {"may_change_state": 0}):
            with self.assertRaises(PrivateRecoveryEvidenceError):
                validate_private_recovery_evidence(self.mutated(**changes), self.raw)

    def test_invalid_scope_id_or_time_cannot_enter_metadata(self):
        for changes in ({"evidence_id": "private"}, {"pc_id": "host"},
                        {"target_period": "2026-13"}, {"target_period": "2026-09\n"},
                        {"evidence_id": self.options["evidence_id"] + "\n"}, {"observed_at_utc": "2026-02-30T12:00:00Z"},
                        {"observed_at_utc": "2026-10-23T12:00:00+00:00"}):
            with self.assertRaises(PrivateRecoveryEvidenceError):
                self.build(**changes)

    def test_both_roles_and_period_types(self):
        for pc in ("PC-A", "PC-B"):
            for log, period in (("BattleLog", "2026-09"), ("ErrorReport", "2025")):
                metadata = self.build(pc_id=pc, log_type=log, target_period=period)
                self.assertFalse(validate_private_recovery_evidence(metadata, self.raw)["may_change_state"])

    def test_same_inputs_stable_and_result_mutation_does_not_affect_next_validation(self):
        metadata = self.build()
        self.assertEqual(metadata, self.build())
        value = validate_private_recovery_evidence(metadata, self.raw)
        value["may_change_state"] = True
        self.assertFalse(validate_private_recovery_evidence(metadata, self.raw)["may_change_state"])

    def test_schema_read_failure_is_sanitized(self):
        with patch("pathlib.Path.read_text", side_effect=OSError("synthetic_private_detail")):
            try:
                self.build()
            except PrivateRecoveryEvidenceError as error:
                self.assertEqual(str(error), "private_evidence_invalid")
                self.assertNotIn("OSError:", traceback.format_exc())
                self.assertNotIn("synthetic_private_detail", traceback.format_exc())
            else:
                self.fail("schema_failure_should_block")
