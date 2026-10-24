"""Fail-closed validation of report-referenced manifest and B2 evidence bytes.

This module is a local runtime helper. It performs no writes and never prints artifact
contents. Paths are interpreted relative to an explicitly trusted maintenance root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

try:
    from .RunInputEvidenceIntegrity import (
        EvidenceIntegrityError,
        validate_evidence_invariants,
        validate_evidence_matches_manifest,
        derive_report_generated_at_utc,
    )
except ImportError:  # Direct script execution from the Common directory.
    from RunInputEvidenceIntegrity import (
        EvidenceIntegrityError,
        validate_evidence_invariants,
        validate_evidence_matches_manifest,
        derive_report_generated_at_utc,
    )


class ArtifactValidationError(Exception):
    """Expected validation failure with a stable reason code."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactValidationError("duplicate_json_key")
        result[key] = value
    return result


def _read_json_bytes(path: Path) -> tuple[bytes, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ArtifactValidationError("artifact_unavailable") from exc
    try:
        value = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ArtifactValidationError("invalid_json_constant")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("malformed_json") from exc
    except ArtifactValidationError:
        raise
    if not isinstance(value, dict):
        raise ArtifactValidationError("json_root_not_object")
    return raw, value


def _safe_artifact_path(root: Path, relative_path: Any) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise ArtifactValidationError("invalid_reference_path")
    if (
        relative_path.startswith("/")
        or "\\" in relative_path
        or any(ord(char) < 32 or ord(char) == 127 for char in relative_path)
        or ":" in relative_path.split("/")[0]
        or any(part in ("", ".", "..") for part in relative_path.split("/"))
    ):
        raise ArtifactValidationError("unsafe_relative_path")
    root_real = root.resolve(strict=True)
    candidate = root_real.joinpath(*relative_path.split("/"))
    current = root_real
    for part in relative_path.split("/"):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise ArtifactValidationError("artifact_unavailable") from exc
        if os.path.islink(current):
            raise ArtifactValidationError("reparse_point_not_allowed")
        if current != candidate and not current.is_dir():
            raise ArtifactValidationError("parent_component_not_directory")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root_real):
        raise ArtifactValidationError("path_escapes_root")
    if not resolved.is_file():
        raise ArtifactValidationError("artifact_not_file")
    return resolved


def _validate_schema(value: dict[str, Any], schema_path: Path, name: str) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
            key=lambda error: list(map(str, error.absolute_path)),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ArtifactValidationError(f"schema_unavailable:{name}") from exc
    if errors:
        raise ArtifactValidationError(f"schema_invalid:{name}")


def validate_referenced_artifacts(
    root_path: str | Path,
    report_path: str | Path,
    contracts_path: str | Path,
) -> dict[str, Any]:
    """Validate report and exact referenced artifact bytes, then bind identity fields."""
    try:
        root = Path(root_path).resolve(strict=True)
        if not root.is_dir():
            raise ArtifactValidationError("trusted_root_not_directory")
        report_file = Path(report_path).resolve(strict=True)
        if not report_file.is_file():
            raise ArtifactValidationError("report_not_file")
        _, report = _read_json_bytes(report_file)
        contracts = Path(contracts_path).resolve(strict=True)
        _validate_schema(report, contracts / "aggregation-report-v1.schema.json", "report")
        identity = {key: report[key] for key in ("run_id", "pc_id", "log_type")}
        checked: dict[str, dict[str, str]] = {}
        loaded_artifacts: dict[str, dict[str, Any]] = {}
        for name, schema_name, version_field in (
            ("manifest_ref", "manifest-v1.schema.json", "schema_version"),
            ("evidence_ref", "run-input-evidence-v1.schema.json", "evidence_schema_version"),
        ):
            ref = report[name]
            if ref["schema_version"] != 1:
                raise ArtifactValidationError(f"unsupported_reference_schema_version:{name}")
            artifact_path = _safe_artifact_path(root, ref["path"])
            raw, artifact = _read_json_bytes(artifact_path)
            actual_digest = hashlib.sha256(raw).hexdigest()
            if actual_digest != ref["sha256"]:
                raise ArtifactValidationError(f"sha256_mismatch:{name}")
            _validate_schema(artifact, contracts / schema_name, name)
            if artifact[version_field] != ref["schema_version"]:
                raise ArtifactValidationError(f"schema_version_mismatch:{name}")
            for key, expected in identity.items():
                if artifact.get(key) != expected:
                    raise ArtifactValidationError(f"identity_mismatch:{name}:{key}")
            checked[name] = {
                "status": "verified",
                "sha256": actual_digest,
                "schema": schema_name,
            }
            loaded_artifacts[name] = artifact

        evidence = loaded_artifacts["evidence_ref"]
        manifest = loaded_artifacts["manifest_ref"]
        evidence_schema = json.loads((contracts / "run-input-evidence-v1.schema.json").read_text(encoding="utf-8"))
        manifest_schema = json.loads((contracts / "manifest-v1.schema.json").read_text(encoding="utf-8"))
        try:
            validate_evidence_invariants(evidence, evidence_schema)
            validate_evidence_matches_manifest(evidence, manifest, manifest_schema)
            if report["generated_at_utc"] != derive_report_generated_at_utc(manifest, evidence):
                raise ArtifactValidationError("generated_timestamp_mismatch")
        except EvidenceIntegrityError as exc:
            raise ArtifactValidationError(f"evidence_integrity:{exc.reason_code}") from exc

        report_inventory = report["inventory_ref"]
        if (
            report_inventory["eligible_target_count"] != evidence["enumeration"]["eligible_target_count"]
            or report_inventory["inventory_sha256"] != evidence["enumeration"]["inventory_sha256"]
        ):
            raise ArtifactValidationError("report_evidence_inventory_mismatch")
        return {"status": "verified", "reason_code": "all_references_verified", "artifacts": checked}
    except ArtifactValidationError as exc:
        return {"status": "rejected", "reason_code": str(exc), "artifacts": {}}
    except (OSError, KeyError, TypeError, ValueError) as exc:
        # Deliberately avoid exception text: it can contain local paths or content.
        return {"status": "rejected", "reason_code": "validation_failed_closed", "artifacts": {}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="trusted maintenance root")
    parser.add_argument("--report", required=True, help="derived aggregation report JSON")
    parser.add_argument("--contracts", required=True, help="directory containing v1 JSON schemas")
    args = parser.parse_args()
    result = validate_referenced_artifacts(args.root, args.report, args.contracts)
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result["status"] == "verified" else 2


if __name__ == "__main__":
    sys.exit(main())
