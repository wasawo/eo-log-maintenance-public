"""Read-only immediate staging-entry counts, not metadata validation or cleanup."""
from dataclasses import dataclass, field
from pathlib import Path
import stat

from Common.SourceInventoryEvidenceBuilder import _source_chain, _enumeration_snapshot


@dataclass(frozen=True)
class StagingResidualObservation:
    status: str
    reason_code: str
    enumeration_completed: bool
    entries_observed: int
    regular_file_count: int
    directory_count: int
    other_entry_count: int
    observation_errors: int
    warning_required: bool
    kind: str = field(default="staging_directory_entries", init=False)
    may_create_staging: bool = field(default=False, init=False)
    may_upload: bool = field(default=False, init=False)
    may_cleanup: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


def _result(complete, reason, counts=(0, 0, 0)):
    observed = sum(counts)
    return StagingResidualObservation("requires_runtime_evidence" if complete else "held", reason,
        complete, observed, *counts, 0 if complete else 1, observed > 0)


def observe_staging_residual_entries(directory):
    """Count immediate entries only; no content read, traversal or mutation.

    Complete enumeration is not full residual inspection or a clean-start
    permit. Unknown roots/metadata, observed changes and reparse points hold.
    """
    try:
        root = Path(directory)
        if not root.is_absolute():
            return _result(False, "staging_residual_root_unavailable")
        _source_chain(root)
    except Exception:
        return _result(False, "staging_residual_root_unavailable")
    counts = (0, 0, 0)
    try:
        entries, initial = _enumeration_snapshot(root)
        modes = [signature[2] for signature in initial[1].values()]
        regular = sum(stat.S_ISREG(mode) for mode in modes)
        directories = sum(stat.S_ISDIR(mode) for mode in modes)
        counts = (regular, directories, len(modes)-regular-directories)
        if len(entries) != len(modes):
            return _result(False, "staging_residual_observation_incomplete", counts)
        final_entries, final = _enumeration_snapshot(root)
        if len(final_entries) != len(final[1]) or final != initial:
            return _result(False, "staging_residual_observation_incomplete", counts)
    except Exception:
        return _result(False, "staging_residual_observation_incomplete", counts)
    reason = "staging_entries_present_requires_inspection" if sum(counts) else "staging_no_entries_observed"
    return _result(True, reason, counts)
