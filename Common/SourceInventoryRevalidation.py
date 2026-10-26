"""Read-only re-observation against exact frozen B2; never upload authority."""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
import stat

from Common.AggregationReportBuilder import _parse, _validate, _validator
from Common.LatestManifestSelection import _utc_key, _clock_key
from Common.RunInputEvidenceIntegrity import validate_evidence_invariants, _safe_relative_path
from Common.SourceInventoryEvidenceBuilder import (build_run_input_evidence, _classify_filename,
    _source_chain, _hash_stable_file, _source_entry_signature, _is_source_reparse)
from Common.ManifestTransitionInspection import InitialManifestPlan, prepare_initial_manifest
from Common.DriveRequestPath import is_drive_request_file_path
from Common.DriveContentComparison import (ComparisonSource, ContentComparison, ContentComparisonBatch,
    compare_planned_drive_contents, _valid_source, _valid_download_plan_limits, _valid_comparison_batch)


class SourceRevalidationError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True, repr=False)
class SourceInventoryObservation:
    evidence_bytes: bytes
    target_count: int
    status: str = field(default="requires_runtime_evidence", init=False)
    may_upload: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)


@dataclass(frozen=True, repr=False)
class InitialStagingCopyObservation:
    manifest_bytes: bytes
    evidence_bytes: bytes
    relative_path: str
    sequence: int
    size_bytes: int
    sha256: str
    status: str = field(default="requires_runtime_evidence", init=False)
    may_upload: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)
    may_cleanup: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


@dataclass(frozen=True, repr=False)
class StagedDriveContentObservation:
    copies: tuple[InitialStagingCopyObservation, ...]
    comparisons: tuple[ContentComparison, ...]
    status: str
    reason_code: str
    may_upload: bool = field(default=False, init=False)
    may_retry: bool = field(default=False, init=False)
    may_report_sync_success: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


@dataclass(frozen=True, repr=False)
class RevalidatedComparisonSource:
    source: ComparisonSource
    evidence_bytes: bytes
    relative_path: str
    may_restore: bool = field(default=False, init=False)
    may_report_sync_success: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


@dataclass(frozen=True, repr=False)
class InitialInventoryFileObservation:
    relative_path: str
    source: ComparisonSource
    comparison: ContentComparison


@dataclass(frozen=True, repr=False)
class InitialInventoryObservation:
    evidence_bytes: bytes
    selected_paths: tuple[str, ...]
    files: tuple[InitialInventoryFileObservation, ...]
    status: str
    reason_code: str
    may_restore: bool = field(default=False, init=False)
    may_report_sync_success: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)
    may_publish_operational_manifest: bool = field(default=False, init=False)


@dataclass(frozen=True)
class InitialInventorySummary:
    observation_status: str
    inventory_target_count: int
    selected_count: int
    assessed_count: int
    candidate_count: int
    held_count: int
    unassessed_count: int
    validation_error_count: int
    kind: str = field(default="initial_inventory_summary", init=False)
    may_restore: bool = field(default=False, init=False)
    may_report_sync_success: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)
    may_publish_operational_manifest: bool = field(default=False, init=False)


def _reject(reason):
    raise SourceRevalidationError(reason) from None


def _observations(value):
    return (value["source_scope"], value["inventory"], value["validation"],
            {key: value["enumeration"][key] for key in (
                "status", "entries_observed", "eligible_target_count", "inventory_sha256", "enumeration_errors")})


def revalidate_source_inventory(
    source_root, evidence_bytes, *, schema, expected_pc_id, expected_log_type, expected_run_id,
    expected_root_id, expected_relative_scope, reference_date, current_utc, current_utc_reliable,
):
    """Rebuild read observations using independently supplied scope/date/root.

    Only complete original coverage may be compared. Known validation errors
    remain errors, and no new B2 is returned or written. Builder timing is not
    clock evidence and is excluded from the observation comparison. Non-target
    contents/identities, qualified roots, races/ABA and later use remain outside
    this helper; all returned permission flags are false.
    """
    try:
        if (current_utc_reliable is not True or not isinstance(current_utc, datetime)
                or current_utc.tzinfo is None or current_utc.utcoffset() != timedelta(0)):
            _reject("source_revalidation_clock_untrusted")
        if type(reference_date) is not date:
            _reject("source_revalidation_reference_date_invalid")
        value = _parse(evidence_bytes)
        _validate(_validator(schema), value)
        validate_evidence_invariants(value, schema)
        if ((value["pc_id"], value["log_type"], value["run_id"]) !=
                (expected_pc_id, expected_log_type, expected_run_id)
                or value["source_scope"] != dict(root_id=expected_root_id, relative_scope=expected_relative_scope)):
            _reject("source_revalidation_scope_mismatch")
        if value["enumeration"]["status"] != "completed" or value["validation"]["status"] != "completed":
            _reject("source_frozen_coverage_incomplete")
        start, finish = (_utc_key(value["enumeration"][key]) for key in ("started_at_utc", "finished_at_utc"))
        if start > finish or finish > _clock_key(current_utc + timedelta(minutes=5)):
            _reject("source_revalidation_time_invalid")
        observed = build_run_input_evidence(source_root, root_id=expected_root_id,
            relative_scope=expected_relative_scope, pc_id=expected_pc_id, log_type=expected_log_type,
            run_id=expected_run_id, evidence_id=value["evidence_id"], reference_date=reference_date,
            started_at=current_utc)
        validate_evidence_invariants(observed, schema)
        if observed["enumeration"]["status"] != "completed" or observed["validation"]["status"] != "completed":
            _reject("source_revalidation_incomplete")
        if _observations(observed) != _observations(value):
            _reject("source_inventory_observation_changed")
        return SourceInventoryObservation(evidence_bytes, len(value["inventory"]["targets"]))
    except SourceRevalidationError:
        raise
    except Exception:
        _reject("source_revalidation_input_invalid")


def revalidate_initial_manifest_source(
    source_root, plan, *, ac_connected, expected_pc_id, expected_log_type, expected_target_period,
    expected_run_id, started_at_utc, current_utc, current_utc_reliable,
    manifest_schema, evidence_schema, expected_root_id, expected_relative_scope, reference_date,
):
    """Reconstruct a bound initial plan before making a new source observation.

    AC/context are supplied observations, not OS proof. No saved observation
    is accepted as a receipt; every invocation rechecks the actual source. A
    successful result still grants no publication/upload and is not a lease.
    """
    if (type(plan) is not InitialManifestPlan
            or any(flag is not False for flag in (plan.may_publish, plan.may_upload, plan.may_archive))):
        _reject("initial_source_plan_invalid")
    if ac_connected is not True:
        _reject("initial_source_ac_unconfirmed")
    try:
        restored = prepare_initial_manifest(plan.evidence_bytes, expected_pc_id=expected_pc_id,
            expected_log_type=expected_log_type, expected_target_period=expected_target_period,
            expected_run_id=expected_run_id, started_at_utc=started_at_utc, current_utc=current_utc,
            current_utc_reliable=current_utc_reliable, manifest_schema=manifest_schema,
            evidence_schema=evidence_schema)
        if restored != plan:
            _reject("initial_source_plan_invalid")
    except SourceRevalidationError:
        raise
    except Exception:
        _reject("initial_source_plan_invalid")
    return revalidate_source_inventory(source_root, plan.evidence_bytes, schema=evidence_schema,
        expected_pc_id=expected_pc_id, expected_log_type=expected_log_type, expected_run_id=expected_run_id,
        expected_root_id=expected_root_id, expected_relative_scope=expected_relative_scope,
        reference_date=reference_date, current_utc=current_utc, current_utc_reliable=current_utc_reliable)


def observe_initial_staging_copy(
    staging_root, plan, *, relative_path, sequence, expected_pc_id, expected_log_type,
    expected_target_period, expected_run_id, started_at_utc, current_utc,
    current_utc_reliable, manifest_schema, evidence_schema,
):
    """Single-target compatibility API; no cached observation is accepted."""
    return observe_initial_staging_copies(staging_root, plan, allocations=((relative_path, sequence),),
        expected_pc_id=expected_pc_id, expected_log_type=expected_log_type,
        expected_target_period=expected_target_period, expected_run_id=expected_run_id,
        started_at_utc=started_at_utc, current_utc=current_utc,
        current_utc_reliable=current_utc_reliable, manifest_schema=manifest_schema,
        evidence_schema=evidence_schema)[0]


def observe_initial_staging_copies(
    staging_root, plan, *, allocations, expected_pc_id, expected_log_type,
    expected_target_period, expected_run_id, started_at_utc, current_utc,
    current_utc_reliable, manifest_schema, evidence_schema,
):
    """Observe explicit (relative_path, sequence) tuples, returning all or none.

    Never reads source payloads, allocates, changes state or authorizes Upload.
    Root separation/provenance, metadata-first history, capacity, ownership and
    future payload use remain separate gates. All selection validation precedes
    I/O. Final metadata checks span the batch, not an atomic snapshot/lease.
    """
    try:
        if (type(plan) is not InitialManifestPlan
                or any(flag is not False for flag in (plan.may_publish, plan.may_upload, plan.may_archive))):
            _reject("staging_copy_plan_invalid")
        restored = prepare_initial_manifest(plan.evidence_bytes, expected_pc_id=expected_pc_id,
            expected_log_type=expected_log_type, expected_target_period=expected_target_period,
            expected_run_id=expected_run_id, started_at_utc=started_at_utc, current_utc=current_utc,
            current_utc_reliable=current_utc_reliable, manifest_schema=manifest_schema,
            evidence_schema=evidence_schema)
        if restored != plan:
            _reject("staging_copy_plan_invalid")
        if type(allocations) is not tuple:
            _reject("staging_copy_allocations_invalid")
        inventory = {item["relative_path"]: item for item in _parse(plan.proposed_bytes)["files"]}
        selected, seen_paths, seen_names = [], set(), set()
        for allocation in allocations:
            if type(allocation) is not tuple or len(allocation) != 2:
                _reject("staging_copy_allocations_invalid")
            relative_path, sequence = allocation
            _safe_relative_path(relative_path)
            if type(sequence) is not int or sequence < 1:
                _reject("staging_copy_sequence_invalid")
            if relative_path not in inventory:
                _reject("staging_copy_target_missing")
            filename = relative_path.rsplit("/", 1)[-1]
            if (not is_drive_request_file_path("C:\\Example\\Names\\" + filename)
                    or _classify_filename(filename, expected_log_type) is None):
                _reject("staging_copy_filename_invalid")
            name = f"{expected_run_id}_{sequence}_{filename}"
            # Conservative lexical alias guard; not an FS-equivalence proof.
            if relative_path in seen_paths or name.casefold() in seen_names:
                _reject("staging_copy_allocation_duplicate")
            seen_paths.add(relative_path)
            seen_names.add(name.casefold())
            selected.append((relative_path, sequence, name, inventory[relative_path]))
        root = Path(staging_root)
        if not root.is_absolute():
            _reject("staging_copy_root_invalid")
        chain = _source_chain(root)
        snapshots = []
        for relative_path, sequence, name, target in selected:
            path = root / name
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode) or _is_source_reparse(before) or before.st_nlink != 1:
                _reject("staging_copy_file_invalid")
            if before.st_size != target["size_bytes"]:
                _reject("staging_copy_content_mismatch")
            snapshots.append((path, _source_entry_signature(before)))
        results = []
        for relative_path, sequence, name, target in selected:
            size, digest = _hash_stable_file(root / name, expected_size=target["size_bytes"])
            if (size, digest) != (target["size_bytes"], target["sha256"]):
                _reject("staging_copy_content_mismatch")
            results.append(InitialStagingCopyObservation(plan.proposed_bytes, plan.evidence_bytes,
                relative_path, sequence, size, digest))
        for path, signature in snapshots:
            if _source_entry_signature(path.lstat()) != signature:
                _reject("staging_copy_observation_changed")
        if _source_chain(root) != chain:
            _reject("staging_copy_observation_changed")
        return tuple(results)
    except SourceRevalidationError:
        raise
    except Exception:
        _reject("staging_copy_observation_unavailable")


def inspect_initial_staged_drive_contents(
    staging_root, plan, *, allocations, expected_pc_id, expected_log_type,
    expected_target_period, expected_run_id, started_at_utc, current_utc,
    current_utc_reliable, manifest_schema, evidence_schema, source_trusted,
    drive_before, drive_after, download_plan, downloads, expected_folder_id,
    maximum_downloads=None, maximum_total_download_bytes=None,
):
    """Re-read staging then compare supplied complete Drive observations.

    Exact original basenames only: no PC-suffix alias/origin inference. Trust
    is supplied independently, never derived from a matching local copy. This
    neither performs API calls nor proves the remote Upload outcome.
    """
    try:
        if not _valid_download_plan_limits(maximum_downloads, maximum_total_download_bytes):
            _reject("comparison_download_limit_invalid")
        copies = observe_initial_staging_copies(staging_root, plan, allocations=allocations,
            expected_pc_id=expected_pc_id, expected_log_type=expected_log_type,
            expected_target_period=expected_target_period, expected_run_id=expected_run_id,
            started_at_utc=started_at_utc, current_utc=current_utc,
            current_utc_reliable=current_utc_reliable, manifest_schema=manifest_schema,
            evidence_schema=evidence_schema)
        sources = tuple(ComparisonSource(copy.relative_path.rsplit("/", 1)[-1],
            copy.size_bytes, copy.sha256) for copy in copies)
        compared = compare_planned_drive_contents(sources, drive_before, drive_after, download_plan,
            source_trusted=source_trusted, expected_folder_id=expected_folder_id, downloads=downloads,
            maximum_downloads=maximum_downloads, maximum_total_download_bytes=maximum_total_download_bytes)
        if not _valid_comparison_batch(compared):
            _reject("staged_drive_comparison_invalid")
        if compared.status == "held":
            return StagedDriveContentObservation(copies, (), "held", compared.reason_code)
        if compared.status != "compared" or len(compared.results) != len(copies):
            _reject("staged_drive_comparison_invalid")
        return StagedDriveContentObservation(copies, compared.results,
            "requires_runtime_evidence", "staged_drive_observations_compared")
    except SourceRevalidationError:
        raise
    except Exception:
        _reject("staged_drive_observation_invalid")


def revalidate_comparison_source(
    source_root, evidence_bytes, *, relative_path, source_trusted, schema, expected_log_type,
    expected_run_id, expected_root_id, expected_relative_scope, reference_date,
    current_utc, current_utc_reliable,
):
    """Single-target compatibility API; a new full re-scan is still required."""
    return revalidate_comparison_sources(source_root, evidence_bytes, relative_paths=(relative_path,),
        source_trusted=source_trusted, schema=schema, expected_log_type=expected_log_type,
        expected_run_id=expected_run_id, expected_root_id=expected_root_id,
        expected_relative_scope=expected_relative_scope, reference_date=reference_date,
        current_utc=current_utc, current_utc_reliable=current_utc_reliable)[0]


def revalidate_comparison_sources(
    source_root, evidence_bytes, *, relative_paths, source_trusted, schema, expected_log_type,
    expected_run_id, expected_root_id, expected_relative_scope, reference_date,
    current_utc, current_utc_reliable,
):
    """Bind explicit PC-A targets after one fresh full inventory re-scan.

    Validate every requested path before I/O; return the whole immutable tuple
    or nothing. Empty selection still revalidates coverage, never means no_work.
    Trust, later use and every operational permission remain external gates.
    """
    if source_trusted is not True:
        _reject("comparison_source_untrusted")
    try:
        if type(evidence_bytes) is not bytes or type(relative_paths) is not tuple:
            _reject("comparison_source_input_invalid")
        seen = set()
        for path in relative_paths:
            if type(path) is not str:
                _reject("comparison_source_input_invalid")
            _safe_relative_path(path)
            if path in seen:
                _reject("comparison_source_target_duplicate")
            seen.add(path)
        value = _parse(evidence_bytes)
        _validate(_validator(schema), value)
        validate_evidence_invariants(value, schema)
        if value["pc_id"] != "PC-A":
            _reject("comparison_source_pc_invalid")
        inventory = {item["relative_path"]: item for item in value["inventory"]["targets"]}
        selected = []
        for path in relative_paths:
            if path not in inventory:
                _reject("comparison_source_target_missing")
            target = inventory[path]
            if _classify_filename(target["filename"], expected_log_type) is None:
                _reject("comparison_source_filename_invalid")
            selected.append(target)
        observed = revalidate_source_inventory(source_root, evidence_bytes, schema=schema,
            expected_pc_id="PC-A", expected_log_type=expected_log_type, expected_run_id=expected_run_id,
            expected_root_id=expected_root_id, expected_relative_scope=expected_relative_scope,
            reference_date=reference_date, current_utc=current_utc, current_utc_reliable=current_utc_reliable)
        return tuple(RevalidatedComparisonSource(
            ComparisonSource(target["filename"], target["size_bytes"], target["expected_sha256"]),
            observed.evidence_bytes, target["relative_path"]) for target in selected)
    except SourceRevalidationError:
        raise
    except Exception:
        _reject("comparison_source_input_invalid")


def inspect_initial_inventory(
    source_root, evidence_bytes, *, relative_paths, source_trusted, schema, expected_log_type,
    expected_run_id, expected_root_id, expected_relative_scope, reference_date,
    current_utc, current_utc_reliable, drive_before, drive_after, download_plan,
    downloads, expected_folder_id,
    maximum_downloads=None, maximum_total_download_bytes=None,
):
    """Read-only selected initial-inventory observations, separate from sync state.

    Every call reobserves PC-A source and rechecks supplied Drive/plan/hash data.
    A global hold retains the explicit selection and B2, not a completed empty
    inventory. Provenance, actual API freshness and all operations remain gates.
    """
    try:
        if not _valid_download_plan_limits(maximum_downloads, maximum_total_download_bytes):
            _reject("comparison_download_limit_invalid")
        sources = revalidate_comparison_sources(source_root, evidence_bytes, relative_paths=relative_paths,
            source_trusted=source_trusted, schema=schema, expected_log_type=expected_log_type,
            expected_run_id=expected_run_id, expected_root_id=expected_root_id,
            expected_relative_scope=expected_relative_scope, reference_date=reference_date,
            current_utc=current_utc, current_utc_reliable=current_utc_reliable)
        compared = compare_planned_drive_contents(tuple(item.source for item in sources),
            drive_before, drive_after, download_plan, source_trusted=source_trusted,
            expected_folder_id=expected_folder_id, downloads=downloads,
            maximum_downloads=maximum_downloads, maximum_total_download_bytes=maximum_total_download_bytes)
        if not _valid_comparison_batch(compared):
            _reject("initial_inventory_result_invalid")
        if compared.status == "held":
            return InitialInventoryObservation(evidence_bytes, relative_paths, (), "held", compared.reason_code)
        if compared.status != "compared" or len(compared.results) != len(sources):
            _reject("initial_inventory_result_invalid")
        files = tuple(InitialInventoryFileObservation(item.relative_path, item.source, result)
                      for item, result in zip(sources, compared.results))
        return InitialInventoryObservation(evidence_bytes, relative_paths, files,
            "requires_runtime_evidence", "initial_inventory_observations_consistent")
    except SourceRevalidationError:
        raise
    except Exception:
        _reject("initial_inventory_input_invalid")


def summarize_initial_inventory(observation, *, schema):
    """Return counts only, without paths, IDs, hashes, bytes or reason text.

    This checks historical observation consistency, not current source/Drive
    provenance or freshness. It never generates an operational run status.
    """
    try:
        if (type(observation) is not InitialInventoryObservation
                or type(observation.evidence_bytes) is not bytes
                or type(observation.selected_paths) is not tuple or type(observation.files) is not tuple
                or type(observation.status) is not str
                or observation.status not in ("held", "requires_runtime_evidence")
                or any(flag is not False for flag in (observation.may_restore,
                    observation.may_report_sync_success, observation.may_archive,
                    observation.may_publish_operational_manifest))):
            _reject("initial_inventory_summary_invalid")
        value = _parse(observation.evidence_bytes)
        _validate(_validator(schema), value)
        validate_evidence_invariants(value, schema)
        if (value["pc_id"] != "PC-A" or value["enumeration"]["status"] != "completed"
                or value["validation"]["status"] != "completed"):
            _reject("initial_inventory_summary_invalid")
        targets = {item["relative_path"]: item for item in value["inventory"]["targets"]}
        selected = set()
        for path in observation.selected_paths:
            if type(path) is not str or path in selected or path not in targets:
                _reject("initial_inventory_summary_invalid")
            _safe_relative_path(path)
            if _classify_filename(targets[path]["filename"], value["log_type"]) is None:
                _reject("initial_inventory_summary_invalid")
            selected.add(path)
        if observation.status == "held":
            if observation.files:
                _reject("initial_inventory_summary_invalid")
        elif len(observation.files) != len(observation.selected_paths):
            _reject("initial_inventory_summary_invalid")
        candidates = held = 0
        for path, item in zip(observation.selected_paths, observation.files):
            if (type(item) is not InitialInventoryFileObservation or type(item.relative_path) is not str
                    or item.relative_path != path or not _valid_source(item.source)):
                _reject("initial_inventory_summary_invalid")
            target = targets[path]
            if item.source != ComparisonSource(target["filename"], target["size_bytes"], target["expected_sha256"]):
                _reject("initial_inventory_summary_invalid")
            result = item.comparison
            if (type(result) is not ContentComparison or type(result.status) is not str
                    or any(flag is not False for flag in
                           (result.may_restore, result.may_report_sync_success, result.may_archive))):
                _reject("initial_inventory_summary_invalid")
            if result.status == "comparison_candidate":
                if (type(result.candidate_file_id) is not str or not result.candidate_file_id
                        or "\x00" in result.candidate_file_id):
                    _reject("initial_inventory_summary_invalid")
                candidates += 1
            elif result.status == "held" and result.candidate_file_id is None:
                held += 1
            else:
                _reject("initial_inventory_summary_invalid")
        assessed = len(observation.files)
        return InitialInventorySummary(observation.status, len(targets), len(selected), assessed,
            candidates, held, len(selected)-assessed, value["validation"]["invalid_relevant_count"])
    except SourceRevalidationError:
        raise
    except Exception:
        _reject("initial_inventory_summary_invalid")
