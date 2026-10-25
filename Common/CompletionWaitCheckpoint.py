"""Checkpoint byte validation and explicit existing-file observations; no writes."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re
import os
from pathlib import Path
import stat

from Common.AggregationReportBuilder import _parse, _validate, _validator
from Common.CompletionWaitBudget import (CompletionWaitState, CompletionWaitDecision,
    assess_completion_wait_budget, _identity, _utc)
from Common.ArtifactSetDirectoryVerification import _signature, _chain, _is_link_or_reparse
from Common.DriveRequestPath import is_drive_request_file_path


class CompletionWaitCheckpointError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _reject(reason):
    raise CompletionWaitCheckpointError(reason) from None


def _instant(value):
    """Compare arbitrary fractional precision without changing original strings."""
    if type(value) is not str:
        _reject("checkpoint_timestamp_invalid")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]+))?Z", value)
    if match is None:
        _reject("checkpoint_timestamp_invalid")
    whole = datetime.fromisoformat(match[1] + "+00:00")
    return whole, (match[2] or "").rstrip("0")


def _history(started, checks):
    start = _instant(started)
    deadline = (start[0] + timedelta(hours=24), start[1])
    previous = None
    for stamp in checks:
        instant = _instant(stamp)
        if not start <= instant <= deadline:
            _reject("checkpoint_history_invalid")
        if previous is not None and instant < (previous[0] + timedelta(hours=1), previous[1]):
            _reject("checkpoint_history_invalid")
        previous = instant
    return start if previous is None else previous


def _budget_datetime(stamp):
    whole, fraction = _instant(stamp)
    if len(fraction) > 6:
        _reject("checkpoint_precision_not_supported")
    return whole + timedelta(microseconds=int(fraction.ljust(6, "0") or "0"))


@dataclass(frozen=True, repr=False)
class CompletionWaitCheckpoint:
    checkpoint_schema_version: int
    pc_id: str
    log_type: str
    target_period: str
    run_id: str
    started_at_utc: str
    check_times_utc: tuple[str, ...]
    original_bytes: bytes = field(repr=False)

    def as_budget_state(self):
        """Return exact data only; never round an instant or grant execution."""
        if (type(self.checkpoint_schema_version) is not int or self.checkpoint_schema_version != 1
                or self.pc_id != "PC-A" or not _identity(self.log_type, self.target_period, self.run_id)
                or type(self.check_times_utc) is not tuple or len(self.check_times_utc) > 25):
            _reject("checkpoint_state_invalid")
        try:
            _history(self.started_at_utc, self.check_times_utc)
            return CompletionWaitState(self.pc_id, self.log_type, self.target_period, self.run_id,
                                       _budget_datetime(self.started_at_utc),
                                       tuple(_budget_datetime(stamp) for stamp in self.check_times_utc))
        except CompletionWaitCheckpointError:
            raise
        except Exception:
            _reject("checkpoint_state_invalid")


@dataclass(frozen=True, repr=False)
class CompletionWaitCheckpointTransition:
    expected_bytes: bytes
    checkpoint: CompletionWaitCheckpoint
    added_check_count: int
    status: str
    may_check: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)


def inspect_completion_wait_checkpoint_transition(
    previous_bytes, proposed_bytes, *, schema, expected_log_type, expected_target_period,
    expected_run_id, current_utc, current_utc_reliable,
):
    """Inspect supplied checkpoint evolution; never create/reset a lost prior.

    Exact byte replay is unchanged, otherwise precisely one new check is required.
    Prior trust, elapsed-time providers, durable CAS and actual checks are absent.
    """
    try:
        if type(previous_bytes) is not bytes or type(proposed_bytes) is not bytes:
            _reject("checkpoint_transition_bytes_required")
        context = dict(schema=schema, expected_log_type=expected_log_type,
            expected_target_period=expected_target_period, expected_run_id=expected_run_id,
            current_utc=current_utc, current_utc_reliable=current_utc_reliable)
        before = read_completion_wait_checkpoint(previous_bytes, **context)
        after = read_completion_wait_checkpoint(proposed_bytes, **context)
        if previous_bytes == proposed_bytes:
            return CompletionWaitCheckpointTransition(previous_bytes, after, 0, "unchanged")
        if before.started_at_utc != after.started_at_utc:
            _reject("checkpoint_transition_start_changed")
        if (len(after.check_times_utc) != len(before.check_times_utc)+1
                or after.check_times_utc[:-1] != before.check_times_utc):
            _reject("checkpoint_transition_history_changed")
        return CompletionWaitCheckpointTransition(previous_bytes, after, 1, "requires_runtime_evidence")
    except CompletionWaitCheckpointError:
        raise
    except Exception:
        _reject("checkpoint_transition_input_invalid")


@dataclass(frozen=True, repr=False)
class CompletionWaitCheckpointFileObservation:
    checkpoint: CompletionWaitCheckpoint
    status: str = field(default="requires_runtime_evidence", init=False)
    may_check: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)


def observe_completion_wait_checkpoint_file(
    checkpoint_path, *, maximum_bytes, schema, expected_log_type, expected_target_period,
    expected_run_id, current_utc, current_utc_reliable,
):
    """Bounded read of one explicit existing file, never a qualified receipt.

    No default byte limit or filename/layout policy is selected. The caller's
    limit is a resource bound, not a change to the checkpoint schema contract.
    """
    try:
        if type(maximum_bytes) is not int or maximum_bytes < 1:
            _reject("checkpoint_file_limit_invalid")
        path = Path(checkpoint_path)
        if not path.is_absolute() or (os.name == "nt" and not is_drive_request_file_path(str(path))):
            _reject("checkpoint_file_path_invalid")
        chain = _chain(path.parent)
        before = path.lstat()
        if _is_link_or_reparse(path) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _reject("checkpoint_file_not_regular")
        if before.st_size > maximum_bytes:
            _reject("checkpoint_file_limit_exceeded")
        expected = _signature(before)
        blocks, count = [], 0
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or _signature(opened) != expected:
                _reject("checkpoint_file_changed")
            while True:
                block = stream.read(min(65536, before.st_size-count+1))
                if not block:
                    break
                count += len(block)
                if count > before.st_size:
                    _reject("checkpoint_file_changed")
                blocks.append(block)
            finished = os.fstat(stream.fileno())
        if _signature(finished) != expected or count != before.st_size:
            _reject("checkpoint_file_changed")
        record = read_completion_wait_checkpoint(b"".join(blocks), schema=schema,
            expected_log_type=expected_log_type, expected_target_period=expected_target_period,
            expected_run_id=expected_run_id, current_utc=current_utc,
            current_utc_reliable=current_utc_reliable)
        if (_is_link_or_reparse(path) or _signature(path.lstat()) != expected
                or _chain(path.parent) != chain):
            _reject("checkpoint_file_changed")
        return CompletionWaitCheckpointFileObservation(record)
    except CompletionWaitCheckpointError:
        raise
    except Exception:
        _reject("checkpoint_file_observation_unavailable")


@dataclass(frozen=True, repr=False)
class CompletionWaitFileAssessment:
    checkpoint: CompletionWaitCheckpoint
    budget: CompletionWaitDecision
    status: str = field(default="requires_runtime_evidence", init=False)
    may_check: bool = field(default=False, init=False)
    may_wait: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)


def assess_completion_wait_checkpoint_file(
    checkpoint_path, *, maximum_bytes, ac_connected, schema, expected_log_type,
    expected_target_period, expected_run_id, current_utc, current_utc_reliable,
    logged_on, same_account_verified, own_sync_complete, waiting_confirmed,
):
    """Fresh read -> budget advice, without allocation, persistence or execution.

    check_due is an observation only. Missing/unreadable records are rejected,
    never converted to an empty budget or a normal waiting condition.
    """
    if ac_connected is not True:
        _reject("checkpoint_file_ac_unconfirmed")
    observation = observe_completion_wait_checkpoint_file(checkpoint_path, maximum_bytes=maximum_bytes,
        schema=schema, expected_log_type=expected_log_type, expected_target_period=expected_target_period,
        expected_run_id=expected_run_id, current_utc=current_utc, current_utc_reliable=current_utc_reliable)
    budget = assess_completion_wait_budget(observation.checkpoint.as_budget_state(),
        expected_log_type=expected_log_type, expected_target_period=expected_target_period,
        expected_run_id=expected_run_id, current_utc=current_utc, current_utc_reliable=current_utc_reliable,
        logged_on=logged_on, same_account_verified=same_account_verified,
        own_sync_complete=own_sync_complete, waiting_confirmed=waiting_confirmed)
    return CompletionWaitFileAssessment(observation.checkpoint, budget)


def read_completion_wait_checkpoint(raw_bytes, *, schema, expected_log_type, expected_target_period,
                                    expected_run_id, current_utc, current_utc_reliable):
    """Parse supplied bytes with independent scope/clock; never reconstruct a loss.

    Trusted read root, origin, freshness/rollback protection, locks and durable
    attempt-before-check publication remain unimplemented external gates.
    """
    try:
        if not _identity(expected_log_type, expected_target_period, expected_run_id):
            _reject("checkpoint_scope_invalid")
        value = _parse(raw_bytes)
        _validate(_validator(schema), value)
        if type(value["checkpoint_schema_version"]) is not int or value["checkpoint_schema_version"] != 1:
            _reject("checkpoint_version_invalid")
        if (value["pc_id"] != "PC-A" or not _identity(value["log_type"], value["target_period"], value["run_id"])
                or (value["log_type"], value["target_period"], value["run_id"]) !=
                   (expected_log_type, expected_target_period, expected_run_id)):
            _reject("checkpoint_scope_mismatch")
        if type(current_utc_reliable) is not bool or not current_utc_reliable or not _utc(current_utc):
            _reject("checkpoint_clock_untrusted")
        latest = _history(value["started_at_utc"], value["check_times_utc"])
        now = current_utc.replace(microsecond=0), f"{current_utc.microsecond:06d}".rstrip("0")
        if now < latest:
            _reject("checkpoint_clock_rollback")
        return CompletionWaitCheckpoint(**{**value, "check_times_utc": tuple(value["check_times_utc"])},
                                        original_bytes=raw_bytes)
    except CompletionWaitCheckpointError:
        raise
    except Exception:
        _reject("checkpoint_input_invalid")
