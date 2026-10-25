"""Synthetic adopted-table inspection; no runtime event evidence or I/O."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from Common.ManifestTransitionInspection import ManifestTransitionError, inspect_manifest_transition
from test_contract_schemas import MANIFEST_SCHEMA


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def snapshot(state="pending", status="running"):
    file = dict(relative_path="20260901_00000000@synthetic.txt", filename="20260901_00000000@synthetic.txt",
                size_bytes=1, sha256="a" * 64, status=state, drive_file_id=None,
                verification=dict(status="not_checked", method="not_performed", checked_at_utc=None, observed_sha256=None))
    if state == "verified":
        file["verification"].update(status="verified", method="download_sha256",
                                    checked_at_utc="2026-10-25T00:00:01Z", observed_sha256="a" * 64)
    return dict(schema_version=1, run_id="11111111-2222-4333-8444-555555555555",
                pc_id="PC-A", log_type="BattleLog", target_period="2026-09", status=status, outcome=None,
                started_at_utc="2026-10-25T00:00:00Z",
                finished_at_utc=None if status == "running" else "2026-10-25T00:00:02Z", files=[file])


def inspect(before, after, **options):
    return inspect_manifest_transition(None if before is None else encode(before), encode(after),
                                       manifest_schema=options.get("schema", MANIFEST_SCHEMA))


class ManifestTransitionInspectionTests(unittest.TestCase):
    def rejected(self, before, after, reason=None):
        original = deepcopy((before, after))
        with self.assertRaises(ManifestTransitionError) as caught:
            inspect(before, after)
        if reason is not None:
            self.assertEqual(reason, caught.exception.reason_code)
        self.assertEqual(original, (before, after))

    def test_every_file_pair_against_independent_adopted_table(self):
        approved = {
            ("pending", "staging"), ("staging", "ready"), ("staging", "failed"), ("ready", "pending"),
            ("pending", "uploaded"), ("pending", "unknown"), ("pending", "failed"),
            ("uploaded", "verified"), ("uploaded", "unknown"), ("uploaded", "failed"),
            ("unknown", "verified"), ("unknown", "pending"), ("unknown", "failed"),
        }
        states = ("pending", "staging", "ready", "uploaded", "unknown", "verified", "failed")
        for old in states:
            for new in states:
                with self.subTest(old=old, new=new):
                    before, after = snapshot(old), snapshot(new)
                    if old == "uploaded" and new == "failed":
                        after["files"][0]["verification"].update(status="mismatch", method="drive_sha256",
                            checked_at_utc="2026-10-25T00:00:01Z", observed_sha256="b" * 64)
                    if old == new or (old, new) in approved:
                        result = inspect(before, after)
                        self.assertEqual("requires_runtime_evidence", result["status"])
                        self.assertEqual(int(old != new), result["file_transition_count"])
                    else:
                        self.rejected(before, after)

    def test_run_matrix_never_certifies_terminal_aggregation(self):
        for old in ("running", "success", "partial_failure", "failure"):
            for new in ("running", "success", "partial_failure", "failure"):
                before, after = snapshot(status=old), snapshot(status=new)
                before["files"] = after["files"] = []
                for item in (before, after):
                    if item["status"] == "success": item["outcome"] = "no_work"
                with self.subTest(old=old, new=new):
                    if old == "running":
                        result = inspect(before, after)
                        self.assertEqual("requires_runtime_evidence", result["status"])
                        self.assertEqual(new != "running", result["aggregation_required"])
                    elif old == new:
                        self.assertEqual("unchanged", inspect(before, after)["status"])
                    else:
                        self.rejected(before, after, "terminal_manifest_immutable")

    def test_new_manifest_is_running_with_pending_files_only(self):
        self.assertEqual("requires_runtime_evidence", inspect(None, snapshot())["status"])
        for state in ("staging", "ready", "uploaded", "verified", "failed", "unknown"):
            self.rejected(None, snapshot(state), "initial_state_invalid")
        self.rejected(None, snapshot(status="failure"), "initial_state_invalid")

    def test_identity_and_inventory_changes_and_duplicates_are_rejected(self):
        for field, value in (("run_id", "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"), ("pc_id", "PC-B"),
                             ("target_period", "2026-08"), ("started_at_utc", "2026-10-25T00:00:00.0Z")):
            before, after = snapshot(), snapshot()
            after[field] = value
            self.rejected(before, after, "run_identity_changed")
        for field, value in (("size_bytes", 2), ("sha256", "b" * 64)):
            before, after = snapshot(), snapshot()
            after["files"][0][field] = value
            self.rejected(before, after, "frozen_inventory_changed")
        before, after = snapshot(), snapshot()
        after["files"] = []
        self.rejected(before, after, "frozen_inventory_changed")
        after = snapshot()
        after["files"].append(deepcopy(after["files"][0]))
        self.rejected(before, after, "duplicate_file_identity")

    def test_terminal_file_metadata_and_same_state_updates_are_not_edges(self):
        for state in ("verified", "failed", "pending", "unknown"):
            before, after = snapshot(state), snapshot(state)
            after["files"][0]["drive_file_id"] = "synthetic-private-id"
            self.rejected(before, after, "terminal_file_immutable" if state in ("verified", "failed") else "unlisted_file_transition")

    def test_terminal_manifest_preserves_exact_bytes_not_just_parsed_values(self):
        value = snapshot("verified", "success")
        with self.assertRaisesRegex(ManifestTransitionError, "terminal_manifest_immutable"):
            inspect_manifest_transition(encode(value), json.dumps(value, indent=2).encode(), manifest_schema=MANIFEST_SCHEMA)

    def test_verification_mapping_hash_and_real_method_combinations(self):
        before = snapshot("uploaded")
        for state in ("unavailable", "ambiguous", "failed"):
            after = snapshot("unknown")
            after["files"][0]["verification"].update(status=state, checked_at_utc="2026-10-25T00:00:01Z")
            self.assertEqual("requires_runtime_evidence", inspect(before, after)["status"])
            after["files"][0]["status"] = "failed"
            self.rejected(before, after, "verification_state_mismatch")
        self.rejected(before, snapshot("failed"), "verification_state_mismatch")
        for field, value in (("observed_sha256", "b" * 64), ("method", "not_performed")):
            after = snapshot("verified")
            after["files"][0]["verification"][field] = value
            self.rejected(before, after)

    def test_time_order_fraction_precision_and_strict_numeric_types(self):
        before, after = snapshot(), snapshot()
        after["finished_at_utc"] = "2026-10-24T23:59:59Z"
        after["status"] = "failure"
        self.rejected(before, after, "manifest_time_order_invalid")
        before, after = snapshot("uploaded"), snapshot("verified", "success")
        after["files"][0]["verification"]["checked_at_utc"] = "2026-10-25T00:00:02.00000000001Z"
        self.rejected(before, after, "verification_time_order_invalid")
        for field in ("schema_version", "size_bytes"):
            after = snapshot()
            (after if field == "schema_version" else after["files"][0])[field] = 1.0
            self.rejected(snapshot(), after)

    def test_untrusted_json_schema_and_unknown_fields_fail_without_disclosure(self):
        for raw in (b'{"status":"private-secret","status":"running"}', b'null', b'not-json-private-secret'):
            with self.assertRaises(ManifestTransitionError) as caught:
                inspect_manifest_transition(None, raw, manifest_schema=MANIFEST_SCHEMA)
            self.assertNotIn("private-secret", str(caught.exception))
            self.assertTrue(caught.exception.__suppress_context__)
        schema = deepcopy(MANIFEST_SCHEMA)
        schema["$ref"] = "https://synthetic.invalid/not-loaded"
        with self.assertRaises(ManifestTransitionError): inspect(None, snapshot(), schema=schema)
        after = snapshot()
        after["unexpected"] = True
        self.rejected(snapshot(), after)

    def test_exact_grammar_rejects_dollar_anchor_trailing_newline_cases(self):
        for field in ("run_id", "target_period", "sha256", "observed_sha256"):
            after = snapshot("verified")
            if field == "target_period":
                after.update(log_type="ErrorReport", target_period="2026\n")
            elif field == "run_id":
                after[field] += "\n"
            elif field == "sha256":
                after["files"][0][field] += "\n"
                after["files"][0]["verification"]["observed_sha256"] += "\n"
            else:
                after["files"][0]["verification"][field] += "\n"
            with self.subTest(field=field):
                self.rejected(after, deepcopy(after), "run_identity_invalid" if field in ("run_id", "target_period") else "file_hash_invalid")

    def test_input_immutability_no_io_and_no_identity_echo(self):
        before, after = snapshot("staging"), snapshot("ready")
        original = deepcopy((before, after, MANIFEST_SCHEMA))
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")), \
             patch("pathlib.Path.open", side_effect=AssertionError("unexpected_io")):
            result = inspect(before, after)
        self.assertEqual(original, (before, after, MANIFEST_SCHEMA))
        self.assertNotIn(before["run_id"], json.dumps(result))
        self.assertNotIn(before["files"][0]["filename"], json.dumps(result))


if __name__ == "__main__":
    unittest.main()
