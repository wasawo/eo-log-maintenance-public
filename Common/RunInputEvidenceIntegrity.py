"""Deterministic A2 inventory and B2 evidence integrity validation.

This module is validation-only. It does not enumerate source files or perform I/O
other than reading the supplied schema when requested by the caller.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker

try:
    from .LatestManifestSelection import _utc_key
except ImportError:  # Direct script execution from the Common directory.
    from LatestManifestSelection import _utc_key


INVENTORY_PREFIX = b"EO-LOG-MAINTENANCE-INVENTORY\x00V1\x00"
EVIDENCE_CANONICALIZATION = "EO-LOG-MAINTENANCE-RUN-INPUT-EVIDENCE-V1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def derive_report_generated_at_utc(manifest, evidence) -> str:
    """G1 anchor from exact input timestamps, preserving the chosen spelling.

    This checks temporal order, not input provenance, current UTC or freshness.
    Identity, digest, schema and clock checks remain the caller's responsibility.
    """
    try:
        manifest_finish = manifest["finished_at_utc"]
        evidence_finish = evidence["enumeration"]["finished_at_utc"]
        manifest_key, evidence_key = _utc_key(manifest_finish), _utc_key(evidence_finish)
        if (_utc_key(manifest["started_at_utc"]) > manifest_key
                or _utc_key(evidence["enumeration"]["started_at_utc"]) > evidence_key):
            raise EvidenceIntegrityError("report_timestamp_order_invalid")
        return evidence_finish if evidence_key > manifest_key else manifest_finish
    except EvidenceIntegrityError:
        raise
    except Exception:
        raise EvidenceIntegrityError("report_timestamp_input_invalid") from None


class EvidenceIntegrityError(ValueError):
    """Expected evidence rejection with a stable reason code."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _utf8(value: str, reason: str) -> bytes:
    try:
        return value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise EvidenceIntegrityError(reason) from exc


def _safe_relative_path(value: Any) -> tuple[str, bytes]:
    if not isinstance(value, str) or not value:
        raise EvidenceIntegrityError("invalid_inventory_path")
    if (
        value.startswith("/")
        or value.endswith("/")
        or "\\" in value
        or "\x00" in value
        or ":" in value.split("/", 1)[0]
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise EvidenceIntegrityError("invalid_inventory_path")
    return value, _utf8(value, "invalid_inventory_path")


def compute_inventory_digest(targets: Iterable[Mapping[str, Any]]) -> str:
    """Compute approved A2 digest over target records."""
    records: list[tuple[bytes, tuple[bytes, bytes, bytes, bytes]]] = []
    seen_paths: set[bytes] = set()
    for target in targets:
        if not isinstance(target, Mapping):
            raise EvidenceIntegrityError("invalid_inventory_target")
        path, path_bytes = _safe_relative_path(target.get("relative_path"))
        filename = target.get("filename")
        if not isinstance(filename, str) or not filename or filename != path.rsplit("/", 1)[-1]:
            raise EvidenceIntegrityError("inventory_filename_path_mismatch")
        filename_bytes = _utf8(filename, "invalid_inventory_filename")
        size = target.get("size_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise EvidenceIntegrityError("invalid_inventory_size")
        digest = target.get("expected_sha256")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise EvidenceIntegrityError("invalid_inventory_sha256")
        if path_bytes in seen_paths:
            raise EvidenceIntegrityError("duplicate_inventory_path")
        seen_paths.add(path_bytes)
        size_bytes = str(size).encode("ascii")
        digest_bytes = digest.encode("ascii")
        records.append((path_bytes, (path_bytes, filename_bytes, size_bytes, digest_bytes)))

    records.sort(key=lambda item: item[0])
    if len(records) >= 2**64:
        raise EvidenceIntegrityError("inventory_count_overflow")
    stream = bytearray(INVENTORY_PREFIX)
    stream.extend(len(records).to_bytes(8, "big", signed=False))
    for _, fields in records:
        for field in fields:
            if len(field) >= 2**32:
                raise EvidenceIntegrityError("inventory_field_length_overflow")
            stream.extend(len(field).to_bytes(4, "big", signed=False))
            stream.extend(field)
    return hashlib.sha256(stream).hexdigest()


def _reject_surrogates(value: Any) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise EvidenceIntegrityError("invalid_unicode_scalar")
    elif isinstance(value, list):
        for item in value:
            _reject_surrogates(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_surrogates(key)
            _reject_surrogates(item)


def _reject_floats(value: Any) -> None:
    if isinstance(value, float):
        raise EvidenceIntegrityError("floating_point_evidence_value") from None
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_floats(key)
            _reject_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_floats(item)


def canonical_evidence_bytes(evidence: Mapping[str, Any]) -> bytes:
    """Serialize evidence per B2 canonicalization, excluding integrity.digest."""
    if not isinstance(evidence, Mapping):
        raise EvidenceIntegrityError("evidence_root_not_object")
    try:
        # JSON Schema's abstract integer accepts 1.0; B2's approved canonical
        # representation separately prohibits floats. Never coerce them to int.
        _reject_floats(evidence)
        value = json.loads(json.dumps(evidence, ensure_ascii=False, allow_nan=False))
    except EvidenceIntegrityError:
        raise
    except (TypeError, ValueError, RecursionError) as exc:
        raise EvidenceIntegrityError("invalid_evidence_value") from exc
    if not isinstance(value, dict):
        raise EvidenceIntegrityError("evidence_root_not_object")
    _reject_surrogates(value)
    integrity = value.get("integrity")
    if not isinstance(integrity, dict) or "digest" not in integrity:
        raise EvidenceIntegrityError("missing_integrity_digest")
    if integrity.get("algorithm") != "sha256" or integrity.get("canonicalization") != EVIDENCE_CANONICALIZATION:
        raise EvidenceIntegrityError("unsupported_evidence_canonicalization")
    del integrity["digest"]
    try:
        # Python's Unicode scalar ordering preserves UTF-8 lexicographic order.
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise EvidenceIntegrityError("invalid_evidence_value") from exc
    return encoded


def compute_evidence_digest(evidence: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_evidence_bytes(evidence)).hexdigest()


def validate_evidence_schema(evidence: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    """Raise a stable error if the evidence fails the strict v1 schema."""
    try:
        Draft202012Validator.check_schema(dict(schema))
        errors = list(Draft202012Validator(dict(schema), format_checker=FormatChecker()).iter_errors(evidence))
    except (TypeError, ValueError) as exc:
        raise EvidenceIntegrityError("evidence_schema_unavailable") from exc
    if errors:
        raise EvidenceIntegrityError("evidence_schema_invalid")



def validate_evidence_matches_manifest(
    evidence: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_schema: Mapping[str, Any],
) -> None:
    """Require the embedded B2 target set to equal the manifest's frozen file set."""
    try:
        Draft202012Validator.check_schema(dict(manifest_schema))
        errors = list(
            Draft202012Validator(
                dict(manifest_schema), format_checker=FormatChecker()
            ).iter_errors(manifest)
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceIntegrityError("manifest_schema_unavailable") from exc
    if errors:
        raise EvidenceIntegrityError("manifest_schema_invalid")

    for key in ("run_id", "pc_id", "log_type"):
        if evidence.get(key) != manifest.get(key):
            raise EvidenceIntegrityError(f"manifest_evidence_identity_mismatch:{key}")

    def index_records(records: Iterable[Mapping[str, Any]], *, is_manifest: bool) -> dict[bytes, tuple[bytes, bytes, bytes, bytes]]:
        indexed: dict[bytes, tuple[bytes, bytes, bytes, bytes]] = {}
        for record in records:
            if not isinstance(record, Mapping):
                raise EvidenceIntegrityError("invalid_manifest_inventory_record")
            _, path_bytes = _safe_relative_path(record.get("relative_path"))
            filename = record.get("filename")
            if not isinstance(filename, str) or not filename:
                raise EvidenceIntegrityError("invalid_manifest_inventory_filename")
            filename_bytes = _utf8(filename, "invalid_manifest_inventory_filename")
            size = record.get("size_bytes")
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise EvidenceIntegrityError("invalid_manifest_inventory_size")
            digest = record.get("sha256" if is_manifest else "expected_sha256")
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                raise EvidenceIntegrityError("invalid_manifest_inventory_sha256")
            if filename != record["relative_path"].rsplit("/", 1)[-1]:
                raise EvidenceIntegrityError("manifest_inventory_filename_path_mismatch")
            if path_bytes in indexed:
                raise EvidenceIntegrityError("duplicate_manifest_inventory_path" if is_manifest else "duplicate_evidence_inventory_path")
            indexed[path_bytes] = (
                filename_bytes,
                str(size).encode("ascii"),
                digest.encode("ascii"),
                path_bytes,
            )
        return indexed

    evidence_inventory = index_records(evidence["inventory"]["targets"], is_manifest=False)
    manifest_inventory = index_records(manifest["files"], is_manifest=True)
    if evidence_inventory != manifest_inventory:
        raise EvidenceIntegrityError("manifest_inventory_mismatch")

def validate_evidence_invariants(evidence: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    """Validate schema, inventory digest, exhaustive counts, and evidence digest."""
    validate_evidence_schema(evidence, schema)
    enumeration = evidence["enumeration"]
    validation = evidence["validation"]
    inventory = evidence["inventory"]["targets"]

    actual_inventory_digest = compute_inventory_digest(inventory)
    if enumeration["inventory_sha256"] != actual_inventory_digest:
        raise EvidenceIntegrityError("inventory_digest_mismatch")
    if enumeration["eligible_target_count"] != len(inventory):
        raise EvidenceIntegrityError("eligible_target_count_mismatch")
    if validation["valid_eligible_count"] != len(inventory):
        raise EvidenceIntegrityError("valid_eligible_count_mismatch")
    if validation["invalid_relevant_count"] != len(validation["errors"]):
        raise EvidenceIntegrityError("validation_error_count_mismatch")
    error_ids = [item["error_id"] for item in validation["errors"]]
    if len(set(error_ids)) != len(error_ids):
        raise EvidenceIntegrityError("duplicate_validation_error_id")
    if error_ids != sorted(error_ids, key=lambda item: _utf8(item, "invalid_validation_error_id")):
        raise EvidenceIntegrityError("validation_errors_not_canonical_order")
    inventory_paths = [
        _safe_relative_path(item["relative_path"])[1]
        for item in inventory
    ]
    if inventory_paths != sorted(inventory_paths):
        raise EvidenceIntegrityError("inventory_not_canonical_order")

    if enumeration["status"] == "completed":
        if enumeration["enumeration_errors"] != 0:
            raise EvidenceIntegrityError("completed_enumeration_has_errors")
        classified = (
            validation["valid_eligible_count"]
            + validation["valid_ineligible_count"]
            + validation["invalid_relevant_count"]
            + validation["ignored_entries_count"]
        )
        if classified != enumeration["entries_observed"]:
            raise EvidenceIntegrityError("enumeration_count_mismatch")
    actual_evidence_digest = compute_evidence_digest(evidence)
    if not hmac.compare_digest(actual_evidence_digest, evidence["integrity"]["digest"]):
        raise EvidenceIntegrityError("evidence_digest_mismatch")
