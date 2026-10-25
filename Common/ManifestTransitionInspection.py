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
from Common.SourceInventoryEvidenceBuilder import _classify_filename
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


@dataclass(frozen=True)
class ManifestHistoryObservation:
    snapshot_count: int
    file_transition_count: int
    upload_pending_transition_count: int
    retry_pending_transition_count: int
    registered_pending_file_count: int
    upload_pending_file_count: int
    aggregation_required: bool
    status: str = field(default="requires_runtime_evidence", init=False)
    may_publish: bool = field(default=False, init=False)
    may_upload: bool = field(default=False, init=False)
    may_retry: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


def inspect_manifest_history(snapshots, *, manifest_schema):
    """Check a supplied history from initial registration, without I/O.

    A syntactically complete trace does not authenticate event evidence,
    missing snapshots, ownership, metadata-first persistence or API outcomes.
    Never infer history from one arbitrary running/terminal snapshot.
    """
    try:
        if type(snapshots) is not tuple or not snapshots or any(type(raw) is not bytes for raw in snapshots):
            _reject("manifest_history_input_invalid")
        validator = _validator(manifest_schema)
        inspect_manifest_transition(None, snapshots[0], manifest_schema=manifest_schema)
        last, old_files = _snapshot(snapshots[0], validator)
        pending_upload = set()
        changed = upload_entries = retry_entries = 0
        for previous, proposed in zip(snapshots, snapshots[1:]):
            pair = inspect_manifest_transition(previous, proposed, manifest_schema=manifest_schema)
            last, new_files = _snapshot(proposed, validator)
            changed += pair.get("file_transition_count", 0)
            for path, old in old_files.items():
                before, after = old["status"], new_files[path]["status"]
                if before == after:
                    continue
                if before == "pending":
                    if after in ("uploaded", "unknown") and path not in pending_upload:
                        _reject("planning_pending_used_as_upload")
                    if after == "staging" and path in pending_upload:
                        _reject("upload_pending_restarted_staging")
                    pending_upload.discard(path)
                if after == "pending":
                    pending_upload.add(path)
                    if before == "ready":
                        upload_entries += 1
                    else:  # The adopted pair table permits only unknown here.
                        retry_entries += 1
            old_files = new_files
        registered = sum(item["status"] == "pending" and path not in pending_upload
                         for path, item in old_files.items())
        return ManifestHistoryObservation(len(snapshots), changed, upload_entries, retry_entries,
            registered, len(pending_upload), last["status"] != "running")
    except ManifestTransitionError:
        raise
    except Exception:
        _reject("manifest_history_input_invalid")


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
        if any(_classify_filename(item["filename"], expected_log_type) is None
               for item in supplied["inventory"]["targets"]):
            _reject("initial_inventory_filename_unclassifiable")
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


def revalidate_terminal_manifest_plan(
    plan, *, expected_previous_bytes, expected_evidence_bytes, expected_pc_id,
    expected_log_type, expected_target_period, expected_run_id, ac_connected,
    manifest_path, evidence_path, current_utc, current_utc_reliable,
    manifest_schema, evidence_schema, report_schema,
):
    """Re-derive a terminal candidate from independent use-point observations.

    Supplied previous/B2 bytes and AC are observations, not trusted OS reads or
    receipts. This pure check performs no I/O and grants no publication rights.
    Every call rebuilds the report; a saved plan is never a completed check.
    """
    if (type(plan) is not TerminalManifestPlan or any(flag is not False for flag in
            (plan.may_publish, plan.may_archive, plan.may_change_state))):
        _reject("terminal_usepoint_plan_invalid")
    if ac_connected is not True:
        _reject("terminal_usepoint_ac_unconfirmed")
    if (type(expected_previous_bytes) is not bytes or type(expected_evidence_bytes) is not bytes
            or type(plan.expected_bytes) is not bytes or type(plan.proposed_bytes) is not bytes
            or type(plan.evidence_bytes) is not bytes or type(plan.report_bytes) is not bytes):
        _reject("terminal_usepoint_snapshot_invalid")
    if (plan.expected_bytes != expected_previous_bytes or plan.evidence_bytes != expected_evidence_bytes):
        _reject("terminal_usepoint_snapshot_changed")
    try:
        restored = prepare_terminal_manifest_transition(expected_previous_bytes, plan.proposed_bytes,
            expected_evidence_bytes, manifest_path=manifest_path, evidence_path=evidence_path,
            current_utc=current_utc, current_utc_reliable=current_utc_reliable,
            manifest_schema=manifest_schema, evidence_schema=evidence_schema, report_schema=report_schema)
        value = _parse(restored.proposed_bytes)
        if ((value["pc_id"], value["log_type"], value["target_period"], value["run_id"]) !=
                (expected_pc_id, expected_log_type, expected_target_period, expected_run_id)):
            _reject("terminal_usepoint_scope_mismatch")
        if restored != plan:
            _reject("terminal_usepoint_plan_changed")
        return restored
    except ManifestTransitionError:
        raise
    except Exception:
        _reject("terminal_usepoint_context_invalid")


@dataclass(frozen=True, repr=False)
class StagingSizeObservation:
    manifest_bytes: bytes
    evidence_bytes: bytes
    relative_paths: tuple[str, ...]
    target_sizes: tuple[int, ...]
    remaining_target_bytes: int
    may_create_staging: bool = field(default=False, init=False)
    may_upload: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


def inspect_staging_target_sizes(
    manifest_bytes, evidence_bytes, *, relative_paths, expected_pc_id, expected_log_type,
    expected_target_period, expected_run_id, current_utc, current_utc_reliable,
    manifest_schema, evidence_schema,
):
    """Project explicit targets from a complete running manifest/B2 pair.

    Never infer remaining work from pending/ready or other file states. Event
    history, freshness, actual source/root/free-space and writer gates remain
    external. Empty selection is an observation, not no_work or permission.
    """
    try:
        if (current_utc_reliable is not True or not isinstance(current_utc, datetime)
                or current_utc.tzinfo is None or current_utc.utcoffset() != timedelta(0)):
            _reject("staging_size_clock_untrusted")
        if (type(manifest_bytes) is not bytes or type(evidence_bytes) is not bytes
                or type(relative_paths) is not tuple):
            _reject("staging_size_input_invalid")
        seen = set()
        for path in relative_paths:
            if type(path) is not str:
                _reject("staging_size_input_invalid")
            _safe_relative_path(path)
            if path in seen:
                _reject("staging_size_duplicate_target")
            seen.add(path)
        manifest, files = _snapshot(manifest_bytes, _validator(manifest_schema))
        if ((manifest["pc_id"], manifest["log_type"], manifest["target_period"], manifest["run_id"]) !=
                (expected_pc_id, expected_log_type, expected_target_period, expected_run_id)):
            _reject("staging_size_scope_mismatch")
        if manifest["status"] != "running":
            _reject("staging_size_run_not_running")
        evidence = _parse(evidence_bytes)
        _validate(_validator(evidence_schema), evidence)
        validate_evidence_invariants(evidence, evidence_schema)
        validate_evidence_matches_manifest(evidence, manifest, manifest_schema)
        if evidence["enumeration"]["status"] != "completed" or evidence["validation"]["status"] != "completed":
            _reject("staging_size_coverage_incomplete")
        start = _utc_key(manifest["started_at_utc"])
        enum_start, finish = (_utc_key(evidence["enumeration"][key]) for key in ("started_at_utc", "finished_at_utc"))
        if not start <= enum_start <= finish or finish > _clock_key(current_utc+timedelta(minutes=5)):
            _reject("staging_size_time_invalid")
        sizes = []
        for path in relative_paths:
            if path not in files:
                _reject("staging_size_target_missing")
            file = files[path]
            if _classify_filename(file["filename"], expected_log_type) is None:
                _reject("staging_size_filename_invalid")
            sizes.append(file["size_bytes"])
        return StagingSizeObservation(manifest_bytes, evidence_bytes, relative_paths, tuple(sizes), sum(sizes))
    except ManifestTransitionError:
        raise
    except Exception:
        _reject("staging_size_input_invalid")
