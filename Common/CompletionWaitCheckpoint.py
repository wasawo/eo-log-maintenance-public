"""Pure checkpoint reader: original bytes/strings, exact time comparison, no I/O."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re

from Common.AggregationReportBuilder import _parse, _validate, _validator
from Common.CompletionWaitBudget import CompletionWaitState, _identity, _utc


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
