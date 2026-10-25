"""Pure exact manifest/B2 -> explicit size snapshot; never selects lifecycle work."""
from dataclasses import FrozenInstanceError
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

from Common import ManifestTransitionInspection as check
from Common.RunInputEvidenceIntegrity import compute_evidence_digest, compute_inventory_digest
from test_aggregation_report_builder import fixture, encode, SCHEMAS, NOW, error
import test_initial_manifest_plan as initial


def seed(pc="PC-A", log="BattleLog", **changes):
    manifest, evidence = fixture(((8, "verified"), (9, "verified")), log_type=log, **changes)
    manifest["pc_id"] = evidence["pc_id"] = pc
    evidence["integrity"]["digest"] = compute_evidence_digest(evidence)
    plan = initial.prepare(encode(evidence), manifest)
    return plan.proposed_bytes, plan.evidence_bytes


def inspect(manifest, evidence, paths, **changes):
    value = json.loads(manifest)
    options = dict(relative_paths=paths, expected_pc_id=value["pc_id"], expected_log_type=value["log_type"],
        expected_target_period=value["target_period"], expected_run_id=value["run_id"],
        current_utc=NOW, current_utc_reliable=True,
        manifest_schema=SCHEMAS["manifest_schema"], evidence_schema=SCHEMAS["evidence_schema"])
    options.update(changes)
    return check.inspect_staging_target_sizes(manifest, evidence, **options)


class StagingSizeObservationTests(unittest.TestCase):
    def test_both_pcs_logs_explicit_order_exact_bytes_and_no_io(self):
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                manifest, evidence = seed(pc, log)
                files = json.loads(manifest)["files"]
                paths = tuple(file["relative_path"] for file in files[::-1])
                with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
                    result = inspect(manifest, evidence, paths)
                self.assertEqual(tuple(file["size_bytes"] for file in files[::-1]), result.target_sizes)
                self.assertEqual(sum(result.target_sizes), result.remaining_target_bytes)
                self.assertIs(manifest, result.manifest_bytes)
                self.assertIs(evidence, result.evidence_bytes)
                self.assertFalse(result.may_create_staging or result.may_upload or result.may_archive)
                with self.assertRaises(FrozenInstanceError): result.remaining_target_bytes = 0
                self.assertNotIn(paths[0], repr(result))

    def test_huge_sizes_sum_as_exact_integers_without_ps_wire_contract(self):
        manifest, evidence = seed()
        m, e = json.loads(manifest), json.loads(evidence)
        sizes = (10**60+1, 10**60+2)
        for file, target, size in zip(m["files"], e["inventory"]["targets"], sizes):
            file["size_bytes"] = target["size_bytes"] = size
        e["enumeration"]["inventory_sha256"] = compute_inventory_digest(e["inventory"]["targets"])
        e["integrity"]["digest"] = compute_evidence_digest(e)
        result = inspect(encode(m), encode(e), tuple(file["relative_path"] for file in m["files"]))
        self.assertEqual(sizes, result.target_sizes)
        self.assertEqual(2*10**60+3, result.remaining_target_bytes)
        self.assertIs(int, type(result.remaining_target_bytes))

    def test_no_automatic_selection_from_file_state_and_empty_is_not_success(self):
        manifest, evidence = seed()
        value = json.loads(manifest)
        value["files"][0]["status"] = "ready"
        raw = encode(value)
        result = inspect(raw, evidence, (value["files"][0]["relative_path"],))
        self.assertEqual(1, len(result.target_sizes))
        self.assertEqual("ready", json.loads(result.manifest_bytes)["files"][0]["status"])
        empty = inspect(raw, evidence, ())
        self.assertEqual(((), 0), (empty.target_sizes, empty.remaining_target_bytes))
        self.assertFalse(empty.may_create_staging or empty.may_upload or empty.may_archive)

    def test_missing_duplicate_and_noncanonical_selection_are_rejected(self):
        manifest, evidence = seed()
        path = json.loads(manifest)["files"][0]["relative_path"]
        for paths in ([path], (path, path), ("missing.txt",), ("../escape",), (None,)):
            with self.subTest(paths=paths), self.assertRaises(check.ManifestTransitionError):
                inspect(manifest, evidence, paths)

    def test_scope_clock_pair_integrity_and_coverage_cannot_be_bypassed_by_empty_selection(self):
        manifest, evidence = seed()
        for changes in ({"expected_pc_id": "PC-B"}, {"expected_run_id": "another-run"},
                {"expected_target_period": "2020-01"}, {"current_utc_reliable": False},
                {"current_utc": NOW-timedelta(days=1)}):
            with self.assertRaises(check.ManifestTransitionError): inspect(manifest, evidence, (), **changes)
        for raw in (b"{}", bytearray(evidence)):
            with self.assertRaises(check.ManifestTransitionError): inspect(manifest, raw, ())
        e = json.loads(evidence)
        e["enumeration"].update(status="incomplete", enumeration_errors=1)
        e["validation"]["status"] = "incomplete"
        e["integrity"]["digest"] = compute_evidence_digest(e)
        with self.assertRaisesRegex(check.ManifestTransitionError, "staging_size_coverage_incomplete"):
            inspect(manifest, encode(e), ())

    def test_terminal_pair_rejected_and_known_errors_not_erased(self):
        terminal, evidence = fixture(((9, "verified"),))
        with self.assertRaisesRegex(check.ManifestTransitionError, "staging_size_run_not_running"):
            inspect(encode(terminal), encode(evidence), ())
        manifest, raw = seed(errors=[error()])
        result = inspect(manifest, raw, ())
        self.assertEqual(1, json.loads(result.evidence_bytes)["validation"]["invalid_relevant_count"])
        self.assertFalse(result.may_upload)


if __name__ == "__main__": unittest.main()
