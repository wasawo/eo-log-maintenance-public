"""Pure, fail-closed decision gate for crash-left run recovery.

This module classifies evidence only. It never edits lock records or manifests,
creates a run, enumerates sources, contacts Drive, or touches archive/source data.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


_RUN_ID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_ALLOWED_PC = {"PC-A", "PC-B"}
_ALLOWED_LOG_TYPE = {"BattleLog", "ErrorReport"}


@dataclass(frozen=True)
class RecoveryDecision:
    action: str
    reason_code: str
    may_start_new_run: bool = False
    requires_fresh_inventory: bool = True
    preserve_prior_manifest: bool = True
    drive_reconciliation_required: bool = True


def _blocked(reason_code: str) -> RecoveryDecision:
    return RecoveryDecision(action="block", reason_code=reason_code)


def _valid_lock_record(
    record: Any, *, expected_scope: str, expected_host: str
) -> bool:
    if not isinstance(record, Mapping):
        return False
    if set(record) != {"schema_version", "scope_id", "owner_token", "pid", "host"}:
        return False
    token = record.get("owner_token")
    pid = record.get("pid")
    return (
        type(record.get("schema_version")) is int
        and record["schema_version"] == 1
        and record.get("scope_id") == expected_scope
        and isinstance(token, str)
        and len(token) >= 32
        and token.isascii()
        and type(pid) is int
        and pid > 0
        and record.get("host") == expected_host
    )


def _parse_prior_manifest(raw: bytes) -> dict[str, Any] | None:
    if not isinstance(raw, bytes) or not raw:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    required = {
        "schema_version", "run_id", "pc_id", "log_type", "target_period",
        "status", "outcome", "started_at_utc", "finished_at_utc", "files",
    }
    if set(value) != required:
        return None
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        return None
    if not isinstance(value.get("run_id"), str) or not _RUN_ID.fullmatch(value["run_id"]):
        return None
    if value.get("pc_id") not in _ALLOWED_PC:
        return None
    if value.get("log_type") not in _ALLOWED_LOG_TYPE:
        return None
    if not isinstance(value.get("target_period"), str):
        return None
    if value.get("log_type") == "BattleLog":
        if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value["target_period"]):
            return None
    elif not re.fullmatch(r"[0-9]{4}", value["target_period"]):
        return None
    if value.get("status") not in {"running", "success", "partial_failure", "failure"}:
        return None
    if value.get("outcome") not in (None, "no_work"):
        return None
    if not isinstance(value.get("started_at_utc"), str) or not value["started_at_utc"].endswith("Z"):
        return None
    if value.get("finished_at_utc") is not None:
        return None
    if value.get("status") != "running" or value.get("files") is None or not isinstance(value["files"], list):
        return None
    if value.get("outcome") is not None:
        return None
    schema_path = Path(__file__).resolve().parent.parent / "contracts" / "manifest-v1.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)
    except Exception:
        return None
    return value


def decide_crash_recovery(
    *,
    mutex_abandoned: bool,
    lock_record: Any,
    expected_scope: str,
    expected_host: str,
    owner_termination_confirmed: bool,
    prior_manifest_bytes: bytes,
    expected_pc_id: str,
    expected_log_type: str,
    expected_target_period: str,
    latest_candidate_count: int,
    drive_reconciliation: str,
    unresolved_upload_count: int,
) -> RecoveryDecision:
    """Return an evidence-based decision; never perform recovery side effects.

    drive_reconciliation is one of: not_required, complete, incomplete, ambiguous.
    A positive unresolved_upload_count blocks recovery even when the listing was
    otherwise complete.
    """
    if not mutex_abandoned:
        return _blocked("mutex_not_abandoned")
    if not isinstance(expected_scope, str) or not expected_scope:
        return _blocked("expected_scope_invalid")
    if not isinstance(expected_host, str) or not expected_host:
        return _blocked("expected_host_invalid")
    if not _valid_lock_record(lock_record, expected_scope=expected_scope, expected_host=expected_host):
        return _blocked("lock_record_invalid_or_mismatched")
    if owner_termination_confirmed is not True:
        return _blocked("owner_termination_unconfirmed")
    if type(latest_candidate_count) is not int or latest_candidate_count != 1:
        return _blocked("latest_manifest_not_unique")
    manifest = _parse_prior_manifest(prior_manifest_bytes)
    if manifest is None:
        return _blocked("prior_manifest_invalid_or_not_running")
    if (
        manifest["pc_id"] != expected_pc_id
        or manifest["log_type"] != expected_log_type
        or manifest["target_period"] != expected_target_period
    ):
        return _blocked("prior_manifest_identity_mismatch")
    if drive_reconciliation not in {"not_required", "complete", "incomplete", "ambiguous"}:
        return _blocked("drive_reconciliation_state_invalid")
    if drive_reconciliation in {"incomplete", "ambiguous"}:
        return _blocked("drive_reconciliation_incomplete_or_ambiguous")
    if type(unresolved_upload_count) is not int or unresolved_upload_count < 0:
        return _blocked("unresolved_upload_count_invalid")
    if unresolved_upload_count:
        return _blocked("unresolved_upload_outcomes_remain")

    return RecoveryDecision(
        action="start_new_run",
        reason_code="recovery_evidence_validated",
        may_start_new_run=True,
        requires_fresh_inventory=True,
        preserve_prior_manifest=True,
        drive_reconciliation_required=False,
    )
