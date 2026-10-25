"""Pure attempt-before-check plan; no publication, retry, wait or live query."""
from dataclasses import dataclass, field
import json

from Common.CompletionWaitBudget import CompletionWaitBudgetError, record_completion_check_attempt
from Common.CompletionWaitCheckpoint import CompletionWaitCheckpointError, read_completion_wait_checkpoint


class CompletionWaitAttemptError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True, repr=False)
class CompletionWaitAttemptPlan:
    expected_bytes: bytes
    proposed_bytes: bytes
    attempt_number: int
    may_check: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)


def prepare_completion_wait_attempt(raw_bytes, *, schema, expected_log_type, expected_target_period,
                                    expected_run_id, current_utc, current_utc_reliable, logged_on,
                                    same_account_verified, own_sync_complete, waiting_confirmed):
    """Bind one validated candidate to the exact supplied prior checkpoint.

    The caller still needs a qualified current read, C1/C2 compare-and-publication
    and readback before any check. Staging idempotence is not a new attempt receipt.
    """
    try:
        read_context = dict(schema=schema, expected_log_type=expected_log_type,
                            expected_target_period=expected_target_period, expected_run_id=expected_run_id,
                            current_utc=current_utc, current_utc_reliable=current_utc_reliable)
        record = read_completion_wait_checkpoint(raw_bytes, **read_context)
        advanced = record_completion_check_attempt(
            record.as_budget_state(), expected_log_type=expected_log_type,
            expected_target_period=expected_target_period, expected_run_id=expected_run_id,
            current_utc=current_utc, current_utc_reliable=current_utc_reliable,
            logged_on=logged_on, same_account_verified=same_account_verified,
            own_sync_complete=own_sync_complete, waiting_confirmed=waiting_confirmed)
        proposed = dict(checkpoint_schema_version=record.checkpoint_schema_version, pc_id=record.pc_id,
                        log_type=record.log_type, target_period=record.target_period, run_id=record.run_id,
                        started_at_utc=record.started_at_utc,
                        check_times_utc=[*record.check_times_utc, current_utc.isoformat().replace("+00:00", "Z")])
        candidate = (json.dumps(proposed, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        restored = read_completion_wait_checkpoint(candidate, **read_context)
        if restored.as_budget_state() != advanced or len(restored.check_times_utc) != len(record.check_times_utc) + 1:
            raise CompletionWaitAttemptError("attempt_roundtrip_invalid")
        return CompletionWaitAttemptPlan(record.original_bytes, candidate, len(restored.check_times_utc))
    except CompletionWaitAttemptError:
        raise
    except CompletionWaitCheckpointError as exc:
        raise CompletionWaitAttemptError(exc.reason_code) from None
    except CompletionWaitBudgetError:
        raise CompletionWaitAttemptError("attempt_not_due") from None
    except Exception:
        raise CompletionWaitAttemptError("attempt_input_invalid") from None
