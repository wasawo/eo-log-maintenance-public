"""Pure snapshot inspection for adopted OSD-02 transition tables.

Listed pairs do not prove their event prerequisites. No lock, staging, Drive,
aggregation, persistence or authorization is provided by this inspection.
"""
from __future__ import annotations

import re

from Common.AggregationReportBuilder import _parse, _validator, _validate
from Common.LatestManifestSelection import _utc_key
from Common.RunInputEvidenceIntegrity import _safe_relative_path, _SHA256_RE


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
