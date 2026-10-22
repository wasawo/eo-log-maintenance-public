"""Synthetic tests for exact-byte, schema, and identity validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from Common.RunInputEvidenceIntegrity import compute_evidence_digest, compute_inventory_digest
from Common.validate_aggregation_artifacts import validate_referenced_artifacts


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
        "generated_at_utc": "2026-10-21T00:00:02Z",
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

    def test_byte_digest_mismatch_is_rejected(self) -> None:
        value = json.loads(self.report_path.read_text(encoding="utf-8"))
        value["manifest_ref"]["sha256"] = "0" * 64
        self.write_report(value)
        self.assertEqual("sha256_mismatch:manifest_ref", self.validate()["reason_code"])

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
