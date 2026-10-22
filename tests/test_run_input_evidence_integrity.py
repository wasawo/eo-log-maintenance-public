"""Synthetic contract tests for A2 inventory and B2 evidence integrity."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from Common.RunInputEvidenceIntegrity import (
    EVIDENCE_CANONICALIZATION,
    EvidenceIntegrityError,
    compute_evidence_digest,
    compute_inventory_digest,
    validate_evidence_invariants,
    validate_evidence_matches_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contracts/run-input-evidence-v1.schema.json").read_text(encoding="utf-8"))
MANIFEST_SCHEMA = json.loads((ROOT / "contracts/manifest-v1.schema.json").read_text(encoding="utf-8"))
ZERO_SHA = "0" * 64


def manifest(targets=None):
    files = []
    for target in targets or []:
        files.append({
            "relative_path": target["relative_path"],
            "filename": target["filename"],
            "size_bytes": target["size_bytes"],
            "sha256": target["expected_sha256"],
            "status": "pending",
            "drive_file_id": None,
            "verification": {
                "status": "not_checked",
                "method": "not_performed",
                "checked_at_utc": None,
                "observed_sha256": None,
            },
        })
    return {
        "schema_version": 1,
        "run_id": "11111111-2222-4333-8444-555555555555",
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "target_period": "2026-09",
        "status": "success",
        "outcome": None,
        "started_at_utc": "2026-10-21T00:00:00Z",
        "finished_at_utc": "2026-10-21T00:00:01Z",
        "files": files,
    }


def evidence(targets=None, *, entries_observed=0, valid_ineligible=0, invalid_relevant=0, ignored=0, errors=None):
    targets = list(targets or [])
    value = {
        "evidence_schema_version": 1,
        "evidence_id": "evidence-1",
        "run_id": "11111111-2222-4333-8444-555555555555",
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "source_scope": {"root_id": "source-a", "relative_scope": "BattleLog"},
        "enumeration": {
            "status": "completed",
            "started_at_utc": "2026-10-21T00:00:00Z",
            "finished_at_utc": "2026-10-21T00:00:01Z",
            "entries_observed": entries_observed,
            "eligible_target_count": len(targets),
            "inventory_sha256": compute_inventory_digest(targets),
            "enumeration_errors": 0,
        },
        "validation": {
            "status": "completed",
            "valid_eligible_count": len(targets),
            "valid_ineligible_count": valid_ineligible,
            "invalid_relevant_count": invalid_relevant,
            "ignored_entries_count": ignored,
            "errors": list(errors or []),
        },
        "inventory": {"kind": "embedded", "targets": targets},
        "integrity": {
            "algorithm": "sha256",
            "canonicalization": EVIDENCE_CANONICALIZATION,
            "digest": "0" * 64,
        },
    }
    value["integrity"]["digest"] = compute_evidence_digest(value)
    return value


class InventoryDigestTests(unittest.TestCase):
    def test_a2_empty_inventory_reference_vector(self):
        self.assertEqual(
            "453b679a83dc6d6b4fe7470294c111d4938547b92c63a6b452cba822138ab17e",
            compute_inventory_digest([]),
        )

    def test_a2_one_record_reference_vector(self):
        targets = [{
            "relative_path": "2026/09/example.txt",
            "filename": "example.txt",
            "size_bytes": 0,
            "expected_sha256": ZERO_SHA,
        }]
        self.assertEqual(
            "85cdc7c9a41c212c7b6c83ccd85813ac4152e7cea9b3092e74e5882fd53cecbd",
            compute_inventory_digest(targets),
        )

    def test_order_independent_and_sensitive_to_target_fields(self):
        a = {"relative_path": "2026/09/a.txt", "filename": "a.txt", "size_bytes": 1, "expected_sha256": ZERO_SHA}
        b = {"relative_path": "2026/09/b.txt", "filename": "b.txt", "size_bytes": 2, "expected_sha256": ZERO_SHA}
        self.assertEqual(compute_inventory_digest([a, b]), compute_inventory_digest([b, a]))
        changed = dict(a, size_bytes=3)
        self.assertNotEqual(compute_inventory_digest([a, b]), compute_inventory_digest([changed, b]))

    def test_duplicate_path_is_rejected(self):
        target = {"relative_path": "2026/09/a.txt", "filename": "a.txt", "size_bytes": 1, "expected_sha256": ZERO_SHA}
        with self.assertRaisesRegex(EvidenceIntegrityError, "duplicate_inventory_path"):
            compute_inventory_digest([target, target])

    def test_filename_path_mismatch_is_rejected(self):
        target = {"relative_path": "2026/09/a.txt", "filename": "b.txt", "size_bytes": 1, "expected_sha256": ZERO_SHA}
        with self.assertRaisesRegex(EvidenceIntegrityError, "inventory_filename_path_mismatch"):
            compute_inventory_digest([target])


class EvidenceIntegrityTests(unittest.TestCase):
    def test_valid_empty_completed_evidence(self):
        value = evidence()
        validate_evidence_invariants(value, SCHEMA)

    def test_exhaustive_count_reconciliation(self):
        value = evidence(entries_observed=3, valid_ineligible=1, ignored=2)
        validate_evidence_invariants(value, SCHEMA)
        value["validation"]["ignored_entries_count"] = 1
        value["integrity"]["digest"] = compute_evidence_digest(value)
        with self.assertRaisesRegex(EvidenceIntegrityError, "enumeration_count_mismatch"):
            validate_evidence_invariants(value, SCHEMA)

    def test_inventory_digest_mismatch_is_rejected(self):
        value = evidence()
        value["enumeration"]["inventory_sha256"] = "a" * 64
        value["integrity"]["digest"] = compute_evidence_digest(value)
        with self.assertRaisesRegex(EvidenceIntegrityError, "inventory_digest_mismatch"):
            validate_evidence_invariants(value, SCHEMA)

    def test_evidence_digest_mismatch_is_rejected(self):
        value = evidence()
        value["integrity"]["digest"] = "f" * 64
        with self.assertRaisesRegex(EvidenceIntegrityError, "evidence_digest_mismatch"):
            validate_evidence_invariants(value, SCHEMA)

    def test_inventory_array_must_use_canonical_path_order(self):
        a = {"relative_path": "2026/09/a.txt", "filename": "a.txt", "size_bytes": 1, "expected_sha256": ZERO_SHA}
        b = {"relative_path": "2026/09/b.txt", "filename": "b.txt", "size_bytes": 2, "expected_sha256": ZERO_SHA}
        value = evidence([b, a], entries_observed=2)
        with self.assertRaisesRegex(EvidenceIntegrityError, "inventory_not_canonical_order"):
            validate_evidence_invariants(value, SCHEMA)

    def test_validation_errors_must_use_error_id_order(self):
        first = {"error_id": "VAL-0001", "code": "bad_name", "filename": "bad1", "relative_path": "bad1"}
        second = {"error_id": "VAL-0002", "code": "bad_name", "filename": "bad2", "relative_path": "bad2"}
        value = evidence(entries_observed=2, invalid_relevant=2, errors=[second, first])
        with self.assertRaisesRegex(EvidenceIntegrityError, "validation_errors_not_canonical_order"):
            validate_evidence_invariants(value, SCHEMA)

    def test_manifest_and_evidence_empty_inventory_match(self):
        value = evidence()
        validate_evidence_matches_manifest(value, manifest(), MANIFEST_SCHEMA)

    def test_manifest_inventory_mismatch_is_rejected(self):
        target = {"relative_path": "2026/09/a.txt", "filename": "a.txt", "size_bytes": 1, "expected_sha256": ZERO_SHA}
        value = evidence([target], entries_observed=1)
        changed = manifest([dict(target, expected_sha256="f" * 64)])
        with self.assertRaisesRegex(EvidenceIntegrityError, "manifest_inventory_mismatch"):
            validate_evidence_matches_manifest(value, changed, MANIFEST_SCHEMA)

    def test_manifest_identity_mismatch_is_rejected(self):
        value = evidence()
        changed = manifest()
        changed["pc_id"] = "PC-B"
        with self.assertRaisesRegex(EvidenceIntegrityError, "manifest_evidence_identity_mismatch:pc_id"):
            validate_evidence_matches_manifest(value, changed, MANIFEST_SCHEMA)

    def test_completed_enumeration_with_error_is_rejected(self):
        value = evidence()
        value["enumeration"]["enumeration_errors"] = 1
        value["integrity"]["digest"] = compute_evidence_digest(value)
        with self.assertRaisesRegex(EvidenceIntegrityError, "completed_enumeration_has_errors"):
            validate_evidence_invariants(value, SCHEMA)

    def test_duplicate_validation_error_id_is_rejected(self):
        error = {"error_id": "VAL-0001", "code": "unclassifiable_relevant_filename", "filename": "bad", "relative_path": "bad"}
        value = evidence(entries_observed=1, invalid_relevant=1, errors=[error])
        value["validation"]["errors"].append(copy.deepcopy(error))
        value["validation"]["invalid_relevant_count"] = 2
        value["enumeration"]["entries_observed"] = 2
        value["integrity"]["digest"] = compute_evidence_digest(value)
        with self.assertRaisesRegex(EvidenceIntegrityError, "duplicate_validation_error_id"):
            validate_evidence_invariants(value, SCHEMA)


if __name__ == "__main__":
    unittest.main()
