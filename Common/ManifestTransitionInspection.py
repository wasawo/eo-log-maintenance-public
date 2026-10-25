"""Pure snapshot inspection for adopted OSD-02 transition tables.

Listed pairs do not prove their event prerequisites. No lock, staging, Drive,
aggregation, persistence or authorization is provided by this inspection.
"""
from __future__ import annotations

import re
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from Common.AggregationReportBuilder import (
    AggregationBuildError, build_aggregation_report, _parse, _validator, _validate,
)
from Common.LatestManifestSelection import _utc_key, _clock_key
from Common.RunInputEvidenceIntegrity import (
    EvidenceIntegrityError, validate_evidence_invariants, validate_evidence_matches_manifest,
    _safe_relative_path, _SHA256_RE,
)


_FILE_PAIRS = frozenset({
    ("pending", "staging"), ("staging", "ready"), ("staging", "failed"),
    ("ready", "pending"), ("pending", "uploaded"), ("pending", "unknown"),
    ("pending", "failed"), ("uploaded", "verified"), ("uploaded", "unknown"),
    ("uploaded", "failed"), ("unknown", "verified"), ("unknown", "pending"),
    ("unknown", "failed"),
})
_RUN_PAIRS = frozenset({
    ("running", "running"), ("running", "success"),
    ("running", "partial_failure"), ("running", "failure"),
})


class ManifestTransitionError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _reject(reason):
    raise ManifestTransitionError(reason) from None


def _snapshot(raw, validator):
    value = _parse(raw)
    _validate(validator, value)
    if type(value["schema_version"]) is not int:
        _reject("manifest_version_type_invalid")
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}", value["run_id"]) is None:
        _reject("run_identity_invalid")
    period = r"[0-9]{4}-(0[1-9]|1[0-2])" if value["log_type"] == "BattleLog" else r"[0-9]{4}"
    if re.fullmatch(period, value["target_period"]) is None:
        _reject("run_identity_invalid")
    start = _utc_key(value["started_at_utc"])
    finish = None if value["finished_at_utc"] is None else _utc_key(value["finished_at_utc"])
    if finish is not None and finish < start:
        _reject("manifest_time_order_invalid")
    files = {}
    for file in value["files"]:
        path, _ = _safe_relative_path(file["relative_path"])
        if path in files:
            _reject("duplicate_file_identity")
        if file["filename"] != path.rsplit("/", 1)[-1] or type(file["size_bytes"]) is not int:
            _reject("file_identity_invalid")
        verification = file["verification"]
        if (_SHA256_RE.fullmatch(file["sha256"]) is None or
                (verification["observed_sha256"] is not None and
                 _SHA256_RE.fullmatch(verification["observed_sha256"]) is None)):
            _reject("file_hash_invalid")
        result, state = verification["status"], file["status"]
        if result == "verified":
            if state != "verified" or verification["observed_sha256"] != file["sha256"]:
                _reject("verification_state_mismatch")
        elif result == "mismatch":
            if state != "failed" or verification["observed_sha256"] == file["sha256"]:
                _reject("verification_state_mismatch")
        elif result in ("unavailable", "ambiguous", "failed") and state != "unknown":
            _reject("verification_state_mismatch")
        if state == "verified" and result != "verified":
            _reject("verified_claim_unproven")
        if verification["checked_at_utc"] is not None:
            checked = _utc_key(verification["checked_at_utc"])
            if checked < start or (finish is not None and checked > finish):
                _reject("verification_time_order_invalid")
        files[path] = file
    return value, files


def inspect_manifest_transition(previous_bytes, proposed_bytes, *, manifest_schema):
    """Inspect exact snapshots; None denotes an unproven new-manifest request.

    Output contains fixed metadata only. requires_runtime_evidence never grants
    publication or execution: every listed row's real evidence remains required.
    Terminal aggregation must independently be checked against immutable B2.
    """
    try:
        validator = _validator(manifest_schema)
        after, new_files = _snapshot(proposed_bytes, validator)
        changed = 0
        if previous_bytes is None:
            if after["status"] != "running" or any(f["status"] != "pending" for f in new_files.values()):
                _reject("initial_state_invalid")
        else:
            before, old_files = _snapshot(previous_bytes, validator)
            for key in ("schema_version", "run_id", "pc_id", "log_type", "target_period", "started_at_utc"):
                if before[key] != after[key]:
                    _reject("run_identity_changed")
            if before["status"] != "running":
                if previous_bytes != proposed_bytes:
                    _reject("terminal_manifest_immutable")
                return {"status": "unchanged", "reason_code": "exact_terminal_bytes_unchanged"}
            if (before["status"], after["status"]) not in _RUN_PAIRS:
                _reject("unlisted_run_transition")
            if old_files.keys() != new_files.keys():
                _reject("frozen_inventory_changed")
            for path, old in old_files.items():
                new = new_files[path]
                if any(old[k] != new[k] for k in ("relative_path", "filename", "size_bytes", "sha256")):
                    _reject("frozen_inventory_changed")
                if old == new:
                    continue
                if old["status"] in ("verified", "failed"):
                    _reject("terminal_file_immutable")
                if (old["status"], new["status"]) not in _FILE_PAIRS:
                    _reject("unlisted_file_transition")
                if old["status"] == "uploaded" and new["status"] == "failed" and new["verification"]["status"] != "mismatch":
                    _reject("verification_state_mismatch")
                changed += 1
        return {"status": "requires_runtime_evidence", "reason_code": "listed_pairs_only",
                "file_transition_count": changed,
                "aggregation_required": after["status"] != "running"}
    except ManifestTransitionError:
        raise
    except Exception:
        _reject("manifest_transition_input_invalid")


@dataclass(frozen=True, repr=False)
class TerminalManifestPlan:
    expected_bytes: bytes
    proposed_bytes: bytes
    evidence_bytes: bytes
    report_bytes: bytes
    may_publish: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)


@dataclass(frozen=True, repr=False)
class InitialManifestPlan:
    proposed_bytes: bytes
    evidence_bytes: bytes
    may_publish: bool = field(default=False, init=False)
    may_upload: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


def prepare_initial_manifest(
    evidence_bytes, *, expected_pc_id, expected_log_type, expected_target_period,
    expected_run_id, started_at_utc, current_utc, current_utc_reliable,
    manifest_schema, evidence_schema,
):
    """Build a non-authorizing running/pending snapshot from exact supplied B2.

    No run ID, clock, missing evidence or destination absence is invented.
    Incomplete/failed observations remain in B2, never become success/no_work.
    Trusted origin, fresh enumeration, locks and publication remain external.
    """
    try:
        if (current_utc_reliable is not True or not isinstance(current_utc, datetime)
                or current_utc.tzinfo is None or current_utc.utcoffset() != timedelta(0)):
            _reject("initial_clock_untrusted")
        supplied = _parse(evidence_bytes)
        _validate(_validator(evidence_schema), supplied)
        validate_evidence_invariants(supplied, evidence_schema)
        proposed = dict(schema_version=1, pc_id=expected_pc_id, log_type=expected_log_type,
            target_period=expected_target_period, run_id=expected_run_id, status="running", outcome=None,
            started_at_utc=started_at_utc, finished_at_utc=None, files=[
                dict(relative_path=item["relative_path"], filename=item["filename"], size_bytes=item["size_bytes"],
                     sha256=item["expected_sha256"], status="pending", drive_file_id=None,
                     verification=dict(status="not_checked", method="not_performed",
                                       checked_at_utc=None, observed_sha256=None))
                for item in supplied["inventory"]["targets"]])
        raw = (json.dumps(proposed, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        inspect_manifest_transition(None, raw, manifest_schema=manifest_schema)
        validate_evidence_matches_manifest(supplied, proposed, manifest_schema)
        start = _utc_key(started_at_utc)
        enum_start = _utc_key(supplied["enumeration"]["started_at_utc"])
        enum_finish = _utc_key(supplied["enumeration"]["finished_at_utc"])
        if not start <= enum_start <= enum_finish:
            _reject("initial_time_order_invalid")
        if enum_finish > _clock_key(current_utc + timedelta(minutes=5)):
            _reject("initial_timestamp_in_future")
        return InitialManifestPlan(raw, evidence_bytes)
    except ManifestTransitionError:
        raise
    except (AggregationBuildError, EvidenceIntegrityError) as exc:
        raise ManifestTransitionError(exc.reason_code) from None
    except Exception:
        _reject("initial_manifest_input_invalid")


def prepare_terminal_manifest_transition(
    previous_bytes, proposed_bytes, evidence_bytes, *, manifest_path, evidence_path,
    current_utc, current_utc_reliable, manifest_schema, evidence_schema, report_schema,
):
    """Bind a listed terminal transition and OSD-03 report to exact input bytes.

    No missing-prior initialization, status repair, I/O or publication is done.
    The supplied B2 must independently be a trusted frozen snapshot; binding it
    here does not prove provenance, currentness or immutability across calls.
    The report describes proposed bytes, not a committed manifest or receipt.
    """
    try:
        if type(previous_bytes) is not bytes:
            _reject("terminal_prior_bytes_required")
        inspect_manifest_transition(previous_bytes, proposed_bytes, manifest_schema=manifest_schema)
        report = build_aggregation_report(
            proposed_bytes, evidence_bytes, manifest_path=manifest_path, evidence_path=evidence_path,
            current_utc=current_utc, current_utc_reliable=current_utc_reliable,
            manifest_schema=manifest_schema, evidence_schema=evidence_schema, report_schema=report_schema,
        )
        return TerminalManifestPlan(previous_bytes, proposed_bytes, evidence_bytes, report)
    except ManifestTransitionError:
        raise
    except AggregationBuildError as exc:
        raise ManifestTransitionError(exc.reason_code) from None
    except Exception:
        _reject("terminal_transition_input_invalid")
