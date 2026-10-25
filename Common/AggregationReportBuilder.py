"""Pure derived-report construction from exact immutable manifest/B2 bytes.

Schemas are trusted caller-supplied static objects. No filesystem, clock,
publication, Drive, lock, state transition or authorization is provided.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
import math

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry
from referencing.exceptions import NoSuchResource

from Common.LatestManifestSelection import _utc_key, _clock_key
from Common.RunInputEvidenceIntegrity import (
    _safe_relative_path, validate_evidence_invariants,
    validate_evidence_matches_manifest, derive_report_generated_at_utc,
)
from Common.SourceInventoryEvidenceBuilder import _classify_filename


class AggregationBuildError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _reject(reason):
    raise AggregationBuildError(reason) from None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject("artifact_json_invalid")
        result[key] = value
    return result


def _invalid_number(_value):
    _reject("artifact_json_invalid")


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        _reject("artifact_json_invalid")
    return result


def _parse(raw):
    if type(raw) is not bytes:
        _reject("artifact_bytes_required")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                       parse_constant=_invalid_number, parse_float=_finite_float)
    if type(value) is not dict:
        _reject("artifact_json_invalid")
    return value


def _no_retrieval(uri):
    raise NoSuchResource(ref=uri)


def _validator(schema):
    # The reused A2/B2 validators also receive these checked schemas. Forbid
    # nonlocal refs before any validator runs, so none can retrieve a resource.
    def inspect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("$ref", "$dynamicRef") and (
                        not isinstance(item, str) or not item.startswith("#")):
                    _reject("schema_reference_unavailable")
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    inspect(schema)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker(),
                                registry=Registry(retrieve=_no_retrieval))


def _validate(validator, value):
    if next(validator.iter_errors(value), None) is not None:
        _reject("artifact_schema_invalid")


def build_aggregation_report(
    manifest_bytes, evidence_bytes, *, manifest_path, evidence_path,
    generated_at_utc=None, current_utc, current_utc_reliable,
    future_tolerance=timedelta(minutes=5),
    manifest_schema, evidence_schema, report_schema,
):
    """Return deterministic UTF-8 report bytes; reject unproven terminal input.

    G1 derives the timestamp from exact immutable input finish times. An optional
    caller-supplied value is an assertion and must match the derived string.
    Publication, provenance and real write time remain outside this helper.
    """
    try:
        return _build(
            manifest_bytes, evidence_bytes, manifest_path=manifest_path,
            evidence_path=evidence_path, generated_at_utc=generated_at_utc,
            current_utc=current_utc, current_utc_reliable=current_utc_reliable,
            future_tolerance=future_tolerance, manifest_schema=manifest_schema,
            evidence_schema=evidence_schema, report_schema=report_schema,
        )
    except AggregationBuildError:
        raise
    except Exception:
        # No raw JSON, schema errors, reference paths, token or exception chains.
        _reject("aggregation_input_invalid")


def derive_aggregation_report(
    manifest_bytes, evidence_bytes, *, manifest_path, evidence_path,
    manifest_schema, evidence_schema, report_schema,
):
    """Re-derive historical semantics without asserting a current trusted clock.

    Input/schema/inventory/terminal/ordering/G1 rules remain enforced. The
    absence of a future/freshness observation is deliberate: this function
    cannot qualify a current run, publish or authorize archive.
    """
    try:
        return _build(
            manifest_bytes, evidence_bytes, check_current_clock=False,
            manifest_path=manifest_path, evidence_path=evidence_path,
            manifest_schema=manifest_schema, evidence_schema=evidence_schema, report_schema=report_schema,
        )
    except AggregationBuildError:
        raise
    except Exception:
        _reject("aggregation_input_invalid")


def _build(manifest_bytes, evidence_bytes, *, check_current_clock=True, **context):
    validators = [_validator(context[name]) for name in
                  ("manifest_schema", "evidence_schema", "report_schema")]
    manifest, evidence = _parse(manifest_bytes), _parse(evidence_bytes)
    for validator, value in zip(validators, (manifest, evidence)):
        _validate(validator, value)
    if (type(manifest["schema_version"]) is not int
            or type(evidence["evidence_schema_version"]) is not int):
        _reject("artifact_schema_invalid")
    for name in ("manifest_path", "evidence_path"):
        _safe_relative_path(context[name])
    if context["manifest_path"] == context["evidence_path"]:
        _reject("artifact_reference_conflict")
    validate_evidence_invariants(evidence, context["evidence_schema"])
    validate_evidence_matches_manifest(evidence, manifest, context["manifest_schema"])
    if manifest["status"] == "running":
        _reject("manifest_not_terminal")

    limit = None
    if check_current_clock:
        now, tolerance = context["current_utc"], context["future_tolerance"]
        if (context["current_utc_reliable"] is not True or not isinstance(now, datetime)
                or now.tzinfo is None or now.utcoffset() != timedelta(0)):
            _reject("current_utc_unavailable")
        if (not isinstance(tolerance, timedelta)
                or not timedelta(0) <= tolerance <= timedelta(minutes=5)):
            _reject("future_tolerance_invalid")
        limit = _clock_key(now + tolerance)
    generated_at_utc = derive_report_generated_at_utc(manifest, evidence)
    if context.get("generated_at_utc") is not None and context["generated_at_utc"] != generated_at_utc:
        _reject("generated_timestamp_mismatch")
    generated = _utc_key(generated_at_utc)

    def timestamp(value):
        key = _utc_key(value)
        if limit is not None and key > limit:
            _reject("timestamp_in_future")
        return key

    timestamp(generated_at_utc)
    for start, finish in (
        (manifest["started_at_utc"], manifest["finished_at_utc"]),
        (evidence["enumeration"]["started_at_utc"], evidence["enumeration"]["finished_at_utc"]),
    ):
        if timestamp(start) > timestamp(finish) or timestamp(finish) > generated:
            _reject("timestamp_order_invalid")

    enumeration, validation = evidence["enumeration"], evidence["validation"]
    enumeration_complete = enumeration["status"] == "completed"
    errors = validation["errors"]
    validation_complete = validation["status"] == "completed"
    # Counts prove the supplied accounting, not that an incomplete validation
    # observed every relevant input. Do not turn that flag into completeness.
    accounting_complete = enumeration_complete and validation_complete
    periods = {}

    def period_for(filename):
        day = _classify_filename(filename, manifest["log_type"])
        return f"{day.year:04d}-{day.month:02d}" if day is not None else None

    def row(period):
        return periods.setdefault(period, dict(
            period=period, eligible_count=0, verified_count=0, failed_count=0,
            unknown_count=0, relevant_error_count=0,
        ))

    for file in manifest["files"]:
        period = period_for(file["filename"])
        if period is None:
            _reject("inventory_filename_unclassifiable")
        status = file["status"]
        if status not in ("verified", "failed", "unknown"):
            _reject("file_not_terminal")
        verification = file["verification"]
        if verification["checked_at_utc"] is not None:
            checked = timestamp(verification["checked_at_utc"])
            if not (_utc_key(manifest["started_at_utc"]) <= checked
                    <= _utc_key(manifest["finished_at_utc"])):
                _reject("verification_timestamp_invalid")
        if status == "verified" and (
            verification["status"] != "verified"
            or verification["method"] not in ("drive_sha256", "download_sha256")
            or verification["observed_sha256"] != file["sha256"]
            or verification["checked_at_utc"] is None
        ):
            _reject("verified_claim_unproven")
        if (verification["status"] == "mismatch" and (
                status != "failed" or verification["observed_sha256"] == file["sha256"])):
            _reject("verification_outcome_mismatch")
        if verification["status"] in ("unavailable", "ambiguous", "failed") and status != "unknown":
            _reject("verification_outcome_mismatch")
        if verification["status"] == "verified" and status != "verified":
            _reject("verification_outcome_mismatch")
        summary = row(period)
        summary["eligible_count"] += 1
        summary[status + "_count"] += 1

    run_errors = []
    for error in errors:
        path, _ = _safe_relative_path(error["relative_path"])
        if path.rsplit("/", 1)[-1] != error["filename"]:
            _reject("error_identity_mismatch")
        period = period_for(error["filename"])
        if period is not None:
            row(period)["relevant_error_count"] += 1
        else:
            run_errors.append(dict(error, period=None, affects_run=True,
                                   affects_periods=[], message="Relevant input could not be classified."))
    for summary in periods.values():
        known_failure = sum(summary[key] for key in
                            ("failed_count", "unknown_count", "relevant_error_count"))
        summary["completion"] = ("incomplete" if known_failure else
                                 "complete" if accounting_complete else "indeterminate")
    counts = {name: sum(item[name] for item in periods.values())
              for name in ("verified_count", "failed_count", "unknown_count")}
    unresolved = (not enumeration_complete or not validation_complete or bool(errors)
                  or counts["failed_count"] or counts["unknown_count"])
    # Enumeration failure cannot establish the workload, even with observed work.
    status = ("failure" if not enumeration_complete else
              "partial_failure" if unresolved and counts["verified_count"] else
              "failure" if unresolved else "success")
    outcome = "no_work" if status == "success" and not manifest["files"] else None
    if manifest["status"] != status or manifest["outcome"] != outcome:
        _reject("manifest_aggregation_mismatch")
    report = dict(
        report_schema_version=1,
        **{key: manifest[key] for key in ("run_id", "pc_id", "log_type")},
        generated_at_utc=generated_at_utc,
        inventory_ref=dict(kind="b2_run_input_evidence_inventory",
                           eligible_target_count=len(evidence["inventory"]["targets"]),
                           inventory_sha256=enumeration["inventory_sha256"]),
        run_aggregation=dict(status=status, outcome=outcome, **counts,
                             run_scope_error_count=len(run_errors),
                             enumeration_complete=enumeration_complete,
                             validation_complete=validation_complete),
        periods=[periods[key] for key in sorted(periods)], run_scope_errors=run_errors,
    )
    for kind, raw in (("manifest", manifest_bytes), ("evidence", evidence_bytes)):
        report[kind + "_ref"] = dict(path=context[kind + "_path"], schema_version=1,
                                     sha256=hashlib.sha256(raw).hexdigest())
    _validate(validators[2], report)
    return (json.dumps(report, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
