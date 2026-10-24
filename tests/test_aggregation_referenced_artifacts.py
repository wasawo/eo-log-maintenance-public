"""Synthetic tests for exact-byte, schema, and identity validation."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

from Common.RunInputEvidenceIntegrity import compute_evidence_digest, compute_inventory_digest
from Common.validate_aggregation_artifacts import validate_referenced_artifacts
from test_run_input_evidence_integrity import legacy_float_digest


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
RUN_ID = "11111111-2222-4333-8444-555555555555"
DIGEST = compute_inventory_digest([])


def manifest() -> dict:
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "target_period": "2026-09",
        "status": "success",
        "outcome": None,
        "started_at_utc": "2026-10-21T00:00:00Z",
        "finished_at_utc": "2026-10-21T00:00:01Z",
        "files": [],
    }


def evidence() -> dict:
    value = {
        "evidence_schema_version": 1,
        "evidence_id": "evidence-1",
        "run_id": RUN_ID,
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "source_scope": {"root_id": "source-a", "relative_scope": "BattleLog"},
        "enumeration": {
            "status": "completed",
            "started_at_utc": "2026-10-21T00:00:00Z",
            "finished_at_utc": "2026-10-21T00:00:01Z",
            "entries_observed": 0,
            "eligible_target_count": 0,
            "inventory_sha256": DIGEST,
            "enumeration_errors": 0,
        },
        "validation": {
            "status": "completed",
            "valid_eligible_count": 0,
            "valid_ineligible_count": 0,
            "invalid_relevant_count": 0,
            "ignored_entries_count": 0,
            "errors": [],
        },
        "inventory": {"kind": "embedded", "targets": []},
        "integrity": {
            "algorithm": "sha256",
            "canonicalization": "EO-LOG-MAINTENANCE-RUN-INPUT-EVIDENCE-V1",
            "digest": DIGEST,
        },
    }
    value["integrity"]["digest"] = compute_evidence_digest(value)
    return value


def report(manifest_bytes: bytes, evidence_bytes: bytes) -> dict:
    return {
        "report_schema_version": 1,
        "run_id": RUN_ID,
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "manifest_ref": {
            "path": "_maintenance/manifests/PC-A/manifest.json",
            "schema_version": 1,
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        },
        "evidence_ref": {
            "path": "_maintenance/run-input-evidence/PC-A/evidence.json",
            "schema_version": 1,
            "sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        },
        "generated_at_utc": "2026-10-21T00:00:01Z",
        "inventory_ref": {
            "kind": "b2_run_input_evidence_inventory",
            "eligible_target_count": 0,
            "inventory_sha256": DIGEST,
        },
        "run_aggregation": {
            "status": "success",
            "outcome": "no_work",
            "verified_count": 0,
            "failed_count": 0,
            "unknown_count": 0,
            "run_scope_error_count": 0,
            "enumeration_complete": True,
            "validation_complete": True,
        },
        "periods": [],
        "run_scope_errors": [],
    }


class ReferencedArtifactValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "maintenance"
        (self.root / "_maintenance/manifests/PC-A").mkdir(parents=True)
        (self.root / "_maintenance/run-input-evidence/PC-A").mkdir(parents=True)
        self.manifest_bytes = json.dumps(manifest(), separators=(",", ":")).encode()
        self.evidence_bytes = json.dumps(evidence(), separators=(",", ":")).encode()
        (self.root / "_maintenance/manifests/PC-A/manifest.json").write_bytes(self.manifest_bytes)
        (self.root / "_maintenance/run-input-evidence/PC-A/evidence.json").write_bytes(self.evidence_bytes)
        self.report_path = Path(self.temp.name) / "report.json"
        self.write_report(report(self.manifest_bytes, self.evidence_bytes))

    def write_report(self, value: dict) -> None:
        self.report_path.write_text(json.dumps(value), encoding="utf-8")

    def validate(self) -> dict:
        return validate_referenced_artifacts(self.root, self.report_path, CONTRACTS)

    def test_valid_referenced_bytes_and_identity_are_accepted(self) -> None:
        result = self.validate()
        self.assertEqual("verified", result["status"])
        self.assertEqual("verified", result["artifacts"]["manifest_ref"]["status"])
        self.assertEqual("verified", result["artifacts"]["evidence_ref"]["status"])

    def test_direct_script_entrypoint_uses_the_same_g1_validation(self):
        command = [sys.executable, "-B", str(ROOT / "Common/validate_aggregation_artifacts.py"),
                   "--root", str(self.root), "--report", str(self.report_path),
                   "--contracts", str(CONTRACTS)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode)
        self.assertEqual("verified", json.loads(result.stdout)["status"])
        value = report(self.manifest_bytes, self.evidence_bytes)
        value["generated_at_utc"] = "2026-10-21T00:00:02Z"
        self.write_report(value)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(2, result.returncode)
        self.assertEqual("generated_timestamp_mismatch", json.loads(result.stdout)["reason_code"])

    def test_float_evidence_is_rejected_even_with_matching_exact_ref_and_old_digest(self):
        for token in ("1.0", "-0.0", "1e0", "1.25", "NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token):
                changed = evidence()
                if token == "-0.0":
                    changed["enumeration"]["enumeration_errors"] = -0.0
                else:
                    changed["evidence_schema_version"] = json.loads(token)
                if token not in ("NaN", "Infinity", "-Infinity"):
                    changed["integrity"]["digest"] = legacy_float_digest(changed)
                raw = json.dumps(changed, separators=(",", ":")).encode()
                if token == "1e0":
                    raw = raw.replace(b'"evidence_schema_version":1.0', b'"evidence_schema_version":1e0')
                path = self.root / "_maintenance/run-input-evidence/PC-A/evidence.json"
                path.write_bytes(raw)
                self.write_report(report(self.manifest_bytes, raw))
                result = self.validate()
                self.assertEqual("rejected", result["status"])
                if token in ("1.0", "-0.0", "1e0"):
                    self.assertEqual("evidence_integrity:floating_point_evidence_value", result["reason_code"])
                self.assertEqual(raw, path.read_bytes())
                self.assertNotIn(str(self.root), json.dumps(result))

    def test_all_count_fields_and_nested_float_shapes_are_rejected_at_reference_boundary(self):
        paths = [("enumeration", field) for field in (
            "entries_observed", "eligible_target_count", "enumeration_errors")]
        paths += [("validation", field) for field in (
            "valid_eligible_count", "valid_ineligible_count", "invalid_relevant_count", "ignored_entries_count")]
        cases = []
        for path in paths:
            changed = evidence()
            changed[path[0]][path[1]] = 0.0
            cases.append(changed)
        for nested in ([{"inner": 1.0}], {"inner": [1.0]}):
            changed = evidence()
            changed["synthetic"] = nested
            cases.append(changed)
        changed = evidence()
        changed["inventory"]["targets"] = [{
            "filename": "synthetic.txt", "relative_path": "synthetic.txt",
            "size_bytes": 1.0, "expected_sha256": "0" * 64,
        }]
        cases.append(changed)
        for index, changed in enumerate(cases):
            with self.subTest(case=index):
                changed["integrity"]["digest"] = legacy_float_digest(changed)
                raw = json.dumps(changed, separators=(",", ":")).encode()
                path = self.root / "_maintenance/run-input-evidence/PC-A/evidence.json"
                path.write_bytes(raw)
                self.write_report(report(self.manifest_bytes, raw))
                self.assertEqual("rejected", self.validate()["status"])
                self.assertEqual(raw, path.read_bytes())

    def test_byte_digest_mismatch_is_rejected(self) -> None:
        value = json.loads(self.report_path.read_text(encoding="utf-8"))
        value["manifest_ref"]["sha256"] = "0" * 64
        self.write_report(value)
        self.assertEqual("sha256_mismatch:manifest_ref", self.validate()["reason_code"])

    def test_generated_timestamp_must_match_exact_g1_anchor(self):
        for stamp in ("2026-10-21T00:00:02Z", "2026-10-21T00:00:01.0Z"):
            with self.subTest(stamp=stamp):
                value = report(self.manifest_bytes, self.evidence_bytes)
                value["generated_at_utc"] = stamp
                self.write_report(value)
                self.assertEqual("generated_timestamp_mismatch", self.validate()["reason_code"])

    def test_evidence_later_anchor_is_bound_without_rewriting_inputs(self):
        changed = evidence()
        changed["enumeration"]["finished_at_utc"] = "2026-10-21T00:00:02.00000000001Z"
        changed["integrity"]["digest"] = compute_evidence_digest(changed)
        raw = json.dumps(changed).encode()
        path = self.root / "_maintenance/run-input-evidence/PC-A/evidence.json"
        path.write_bytes(raw)
        value = report(self.manifest_bytes, raw)
        value["generated_at_utc"] = changed["enumeration"]["finished_at_utc"]
        self.write_report(value)
        self.assertEqual("verified", self.validate()["status"])
        self.assertEqual(raw, path.read_bytes())

    def test_cross_artifact_identity_mismatch_is_rejected(self) -> None:
        changed = manifest()
        changed["pc_id"] = "PC-B"
        raw = json.dumps(changed, separators=(",", ":")).encode()
        (self.root / "_maintenance/manifests/PC-A/manifest.json").write_bytes(raw)
        value = json.loads(self.report_path.read_text(encoding="utf-8"))
        value["manifest_ref"]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.write_report(value)
        self.assertEqual("identity_mismatch:manifest_ref:pc_id", self.validate()["reason_code"])

    def test_malformed_json_is_rejected_without_content_disclosure(self) -> None:
        (self.root / "_maintenance/manifests/PC-A/manifest.json").write_text("{", encoding="utf-8")
        value = json.loads(self.report_path.read_text(encoding="utf-8"))
        raw = (self.root / "_maintenance/manifests/PC-A/manifest.json").read_bytes()
        value["manifest_ref"]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.write_report(value)
        result = self.validate()
        self.assertEqual("malformed_json", result["reason_code"])
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_manifest_frozen_target_set_must_match_b2_inventory(self) -> None:
        changed = manifest()
        changed["files"] = [{
            "relative_path": "2026/09/a.txt",
            "filename": "a.txt",
            "size_bytes": 1,
            "sha256": "0" * 64,
            "status": "pending",
            "drive_file_id": None,
            "verification": {
                "status": "not_checked",
                "method": "not_performed",
                "checked_at_utc": None,
                "observed_sha256": None,
            },
        }]
        raw = json.dumps(changed, separators=(",", ":")).encode()
        (self.root / "_maintenance/manifests/PC-A/manifest.json").write_bytes(raw)
        value = json.loads(self.report_path.read_text(encoding="utf-8"))
        value["manifest_ref"]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.write_report(value)
        self.assertEqual("evidence_integrity:manifest_inventory_mismatch", self.validate()["reason_code"])

    def test_unsafe_reference_path_is_rejected(self) -> None:
        value = json.loads(self.report_path.read_text(encoding="utf-8"))
        value["manifest_ref"]["path"] = "../outside.json"
        self.write_report(value)
        self.assertEqual("schema_invalid:report", self.validate()["reason_code"])


if __name__ == "__main__":
    unittest.main()
