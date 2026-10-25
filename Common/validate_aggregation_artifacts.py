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
import stat
import sys
from typing import Any

if __package__ in (None, ""):
    # Direct CLI execution must resolve the same packaged Common modules,
    # independently of the caller's working directory.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Common.AggregationReportBuilder import AggregationBuildError, derive_aggregation_report, _validator

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


def _reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _signature(info):
    # Windows 3.12 stat/fstat ctime can differ; compare explicit birthtime.
    stamp = getattr(info, "st_birthtime_ns", info.st_ctime_ns) if os.name == "nt" else info.st_ctime_ns
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, stamp, info.st_nlink


def _directory_chain(directory):
    chain = []
    for component in (directory, *directory.parents):
        info = component.lstat()
        if _reparse(info):
            raise ArtifactValidationError("reparse_point_not_allowed")
        if not stat.S_ISDIR(info.st_mode):
            raise ArtifactValidationError("parent_component_not_directory")
        chain.append((info.st_dev, info.st_ino))
    return tuple(chain)


def _stable_bytes(path):
    """Point-in-time path/handle binding, not an atomic namespace snapshot."""
    try:
        chain = _directory_chain(path.parent)
        before = path.lstat()
        if _reparse(before):
            raise ArtifactValidationError("reparse_point_not_allowed")
        if not stat.S_ISREG(before.st_mode):
            raise ArtifactValidationError("artifact_not_file")
        expected = _signature(before)
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or _signature(opened) != expected:
                raise ArtifactValidationError("artifact_changed_during_read")
            raw = stream.read()
            finished = os.fstat(stream.fileno())
        after = path.lstat()
        if (_reparse(after) or not stat.S_ISREG(after.st_mode) or _signature(finished) != expected
                or _signature(after) != expected or len(raw) != before.st_size
                or _directory_chain(path.parent) != chain):
            raise ArtifactValidationError("artifact_changed_during_read")
        return raw, expected, chain
    except OSError as exc:
        raise ArtifactValidationError("artifact_unavailable") from exc


def _read_json_bytes(path: Path, snapshots=None) -> tuple[bytes, Any]:
    snapshot = _stable_bytes(path)
    raw = snapshot[0]
    if snapshots is not None:
        if path in snapshots and snapshots[path] != snapshot:
            raise ArtifactValidationError("artifact_read_set_changed")
        snapshots[path] = snapshot
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
    _directory_chain(root)
    root_real = root.resolve(strict=True)
    candidate = root_real.joinpath(*relative_path.split("/"))
    current = root_real
    for part in relative_path.split("/"):
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise ArtifactValidationError("artifact_unavailable") from exc
        if _reparse(info):
            raise ArtifactValidationError("reparse_point_not_allowed")
        if current != candidate and not current.is_dir():
            raise ArtifactValidationError("parent_component_not_directory")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root_real):
        raise ArtifactValidationError("path_escapes_root")
    if not resolved.is_file():
        raise ArtifactValidationError("artifact_not_file")
    return candidate


def _validate_schema(value: dict[str, Any], schema_path: Path, name: str, snapshots):
    try:
        _, schema = _read_json_bytes(schema_path, snapshots)
        errors = sorted(
            _validator(schema).iter_errors(value),
            key=lambda error: list(map(str, error.absolute_path)),
        )
    except ArtifactValidationError:
        raise
    except Exception as exc:
        raise ArtifactValidationError(f"schema_unavailable:{name}") from exc
    if errors:
        raise ArtifactValidationError(f"schema_invalid:{name}")
    return schema


def validate_referenced_artifacts(
    root_path: str | Path,
    report_path: str | Path,
    contracts_path: str | Path,
    *, expected_manifest_bytes: bytes | None = None, expected_manifest_path: str | None = None,
) -> dict[str, Any]:
    """Validate report and exact referenced artifact bytes, then bind identity fields."""
    try:
        if ((expected_manifest_bytes is None) != (expected_manifest_path is None)
                or (expected_manifest_bytes is not None and
                    (type(expected_manifest_bytes) is not bytes or type(expected_manifest_path) is not str))):
            raise ArtifactValidationError("expected_manifest_binding_invalid")
        snapshots = {}
        root = Path(root_path).absolute()
        root_chain = _directory_chain(root)
        if not root.is_dir():
            raise ArtifactValidationError("trusted_root_not_directory")
        report_file = Path(report_path).absolute()
        _, report = _read_json_bytes(report_file, snapshots)
        contracts = Path(contracts_path).absolute()
        contracts_chain = _directory_chain(contracts)
        report_schema = _validate_schema(report, contracts / "aggregation-report-v1.schema.json", "report", snapshots)
        if expected_manifest_path is not None and report["manifest_ref"]["path"] != expected_manifest_path:
            raise ArtifactValidationError("selected_manifest_reference_mismatch")
        identity = {key: report[key] for key in ("run_id", "pc_id", "log_type")}
        checked: dict[str, dict[str, str]] = {}
        loaded_artifacts: dict[str, dict[str, Any]] = {}
        artifact_bytes: dict[str, bytes] = {}
        schemas = {}
        for name, schema_name, version_field in (
            ("manifest_ref", "manifest-v1.schema.json", "schema_version"),
            ("evidence_ref", "run-input-evidence-v1.schema.json", "evidence_schema_version"),
        ):
            ref = report[name]
            if ref["schema_version"] != 1:
                raise ArtifactValidationError(f"unsupported_reference_schema_version:{name}")
            artifact_path = _safe_artifact_path(root, ref["path"])
            raw, artifact = _read_json_bytes(artifact_path, snapshots)
            if name == "manifest_ref" and expected_manifest_bytes is not None and raw != expected_manifest_bytes:
                raise ArtifactValidationError("selected_manifest_bytes_mismatch")
            actual_digest = hashlib.sha256(raw).hexdigest()
            if actual_digest != ref["sha256"]:
                raise ArtifactValidationError(f"sha256_mismatch:{name}")
            schemas[name] = _validate_schema(artifact, contracts / schema_name, name, snapshots)
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
            artifact_bytes[name] = raw

        evidence = loaded_artifacts["evidence_ref"]
        manifest = loaded_artifacts["manifest_ref"]
        evidence_schema, manifest_schema = schemas["evidence_ref"], schemas["manifest_ref"]
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
        try:
            derived = derive_aggregation_report(
                artifact_bytes["manifest_ref"], artifact_bytes["evidence_ref"],
                manifest_path=report["manifest_ref"]["path"], evidence_path=report["evidence_ref"]["path"],
                manifest_schema=manifest_schema, evidence_schema=evidence_schema, report_schema=report_schema,
            )
        except AggregationBuildError:
            raise ArtifactValidationError("report_derivation_invalid") from None
        # Compare the entire derived structure while allowing JSON whitespace
        # and key order. Preserve numeric types, G1 spelling and array order.
        normalized = (json.dumps(report, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        if normalized != derived:
            raise ArtifactValidationError("report_derivation_mismatch")
        if _directory_chain(root) != root_chain or _directory_chain(contracts) != contracts_chain:
            raise ArtifactValidationError("artifact_read_set_changed")
        for path, snapshot in snapshots.items():
            if _stable_bytes(path) != snapshot:
                raise ArtifactValidationError("artifact_read_set_changed")
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
