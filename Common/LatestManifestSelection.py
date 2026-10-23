"""Read-only latest-manifest selection core for approved C4 policy.

The approved basename identity grammar is parsed independently of JSON.
Enumeration, runtime roots, mutation and authorization are not implemented.
The caller supplies complete read observations; only the repository schema is read.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


@dataclass(frozen=True)
class ManifestCandidate:
    filename: str
    content: bytes | None


@dataclass(frozen=True)
class LatestManifestSelection:
    selected_index: int
    run_id: str
    status: str


class LatestManifestSelectionError(ValueError):
    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _reject(reason: str):
    raise LatestManifestSelectionError(reason) from None


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _reject("candidate_manifest_invalid")
        value[key] = item
    return value


def parse_manifest_filename(filename: str) -> dict[str, str]:
    if not isinstance(filename, str):
        _reject("candidate_filename_invalid")
    match = re.fullmatch(
        r"(PC-[AB])_(BattleLog|ErrorReport)_([0-9]{4}(?:-[0-9]{2})?)_"
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})\.json",
        filename,
    )
    if match is None:
        _reject("candidate_filename_invalid")
    period_pattern = r"[0-9]{4}-(0[1-9]|1[0-2])" if match[2] == "BattleLog" else r"[0-9]{4}"
    if not re.fullmatch(period_pattern, match[3]):
        _reject("candidate_filename_invalid")
    return dict(zip(("pc_id", "log_type", "target_period", "run_id"), match.groups()))


def _utc_key(value: Any):
    # Preserve all fraction digits allowed by the schema (maxLength 32).
    # datetime alone truncates sub-microsecond digits and can fabricate a tie.
    if not isinstance(value, str):
        _reject("candidate_timestamp_invalid")
    match = re.fullmatch(
        r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]{1,11}))?Z",
        value,
    )
    if match is None:
        _reject("candidate_timestamp_invalid")
    try:
        whole = datetime.fromisoformat(match[1] + "+00:00")
    except ValueError:
        _reject("candidate_timestamp_invalid")
    return whole, (match[2] or "").ljust(11, "0")


def _clock_key(value: datetime):
    return value.replace(microsecond=0), f"{value.microsecond:06d}".ljust(11, "0")


def _validate_context(
    *, expected_pc_id, expected_log_type, expected_target_period,
    enumeration_completed, current_utc, current_utc_reliable,
    require_current_success, future_tolerance,
):
    if enumeration_completed is not True:
        _reject("candidate_enumeration_incomplete")
    if not isinstance(expected_pc_id, str) or expected_pc_id not in {"PC-A", "PC-B"}:
        _reject("selection_scope_invalid")
    if not isinstance(expected_log_type, str) or expected_log_type not in {"BattleLog", "ErrorReport"}:
        _reject("selection_scope_invalid")
    pattern = r"[0-9]{4}-(0[1-9]|1[0-2])" if expected_log_type == "BattleLog" else r"[0-9]{4}"
    if not isinstance(expected_target_period, str) or not re.fullmatch(pattern, expected_target_period):
        _reject("selection_scope_invalid")
    if type(require_current_success) is not bool:
        _reject("selection_mode_invalid")
    if (current_utc_reliable is not True or not isinstance(current_utc, datetime)
            or current_utc.tzinfo is None or current_utc.utcoffset() != timedelta(0)):
        _reject("current_utc_unavailable")
    if not isinstance(future_tolerance, timedelta) or future_tolerance < timedelta(0):
        _reject("future_tolerance_invalid")
    try:
        future_limit = _clock_key(current_utc + future_tolerance)
    except (ValueError, OverflowError):
        _reject("future_tolerance_invalid")
    return future_limit


def select_latest_manifest(
    candidates: list[ManifestCandidate] | tuple[ManifestCandidate, ...],
    *,
    expected_pc_id: str,
    expected_log_type: str,
    expected_target_period: str,
    enumeration_completed: bool,
    current_utc: datetime | None,
    current_utc_reliable: bool,
    require_current_success: bool = True,
    future_tolerance: timedelta = timedelta(minutes=5),
) -> LatestManifestSelection:
    """Select a unique latest started_at_utc; never fall back to old success.

    False require_current_success permits inspection of latest incomplete state,
    not recovery or archive. Current UTC/reliability and complete candidate
    enumeration/read observations remain caller obligations. Historical age alone does not invalidate
    a candidate; this helper does not apply 24h freshness to old manifests.
    """
    future_limit = _validate_context(
        expected_pc_id=expected_pc_id, expected_log_type=expected_log_type,
        expected_target_period=expected_target_period,
        enumeration_completed=enumeration_completed, current_utc=current_utc,
        current_utc_reliable=current_utc_reliable,
        require_current_success=require_current_success, future_tolerance=future_tolerance,
    )
    if type(candidates) not in (list, tuple):
        _reject("candidate_collection_invalid")
    if not candidates:
        _reject("candidate_set_empty")
    try:
        schema = json.loads((Path(__file__).resolve().parents[1] /
                             "contracts/manifest-v1.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
    except Exception:
        _reject("manifest_schema_unavailable")

    expected = (expected_pc_id, expected_log_type, expected_target_period)
    identity_fields = ("pc_id", "log_type", "target_period", "run_id")
    observed_ids = set()
    validated = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, ManifestCandidate):
            _reject("candidate_observation_invalid")
        identity = parse_manifest_filename(candidate.filename)
        if not isinstance(candidate.content, bytes):
            _reject("candidate_read_failed")
        try:
            manifest = json.loads(candidate.content.decode("utf-8"), object_pairs_hook=_unique_object)
            validator.validate(manifest)
        except LatestManifestSelectionError:
            raise
        except Exception:
            _reject("candidate_manifest_invalid")
        if type(manifest["schema_version"]) is not int:
            _reject("candidate_manifest_invalid")
        if any(identity[field] != manifest[field] for field in identity_fields):
            _reject("candidate_filename_identity_mismatch")
        if tuple(manifest[field] for field in identity_fields[:3]) != expected:
            _reject("candidate_scope_mismatch")
        run_id = manifest["run_id"]
        # UUID spelling case does not produce a distinct run identity.
        if run_id.lower() in observed_ids:
            _reject("candidate_run_identity_conflict")
        observed_ids.add(run_id.lower())
        started = _utc_key(manifest["started_at_utc"])
        finished = manifest["finished_at_utc"]
        if started > future_limit:
            _reject("candidate_timestamp_in_future")
        if finished is not None:
            finish_key = _utc_key(finished)
            if finish_key < started:
                _reject("candidate_finish_before_start")
            if finish_key > future_limit:
                _reject("candidate_timestamp_in_future")
        validated.append((started, index, manifest))

    maximum = max(row[0] for row in validated)
    latest = [row for row in validated if row[0] == maximum]
    if len(latest) != 1:
        _reject("latest_manifest_ambiguous")
    _, index, manifest = latest[0]
    if require_current_success and manifest["status"] != "success":
        _reject("latest_manifest_not_success")
    return LatestManifestSelection(index, manifest["run_id"], manifest["status"])
