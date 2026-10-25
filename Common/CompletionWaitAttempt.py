"""Pure attempt-before-check plan; no publication, retry, wait or live query."""
from dataclasses import dataclass, field
from datetime import timedelta
import json

from Common.CompletionWaitBudget import CompletionWaitBudgetError, record_completion_check_attempt
from Common.CompletionWaitCheckpoint import (CompletionWaitCheckpointError, read_completion_wait_checkpoint,
    inspect_completion_wait_checkpoint_transition)


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
        transition = inspect_completion_wait_checkpoint_transition(record.original_bytes, candidate, **read_context)
        restored = transition.checkpoint
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


def inspect_completion_wait_attempt_usepoint(plan, observed_bytes, *, phase, ac_connected, schema,
                                            expected_log_type, expected_target_period, expected_run_id,
                                            current_utc, current_utc_reliable, logged_on,
                                            same_account_verified, own_sync_complete, waiting_confirmed):
    """Reject stale/expired candidates using fresh observations, never grant a check.

    before_commit requires exact expected bytes; after_commit requires exact new
    bytes. Neither result is a unique commit receipt or proof of a trusted read,
    owner/root/FS qualification, elapsed-time bounds or in-flight cancellation.
    """
    try:
        if type(phase) is not str or phase not in ("before_commit", "after_commit"):
            raise CompletionWaitAttemptError("attempt_phase_invalid")
        if (type(plan) is not CompletionWaitAttemptPlan or type(plan.attempt_number) is not int
                or any(flag is not False for flag in (plan.may_check, plan.may_archive, plan.may_change_state))):
            raise CompletionWaitAttemptError("attempt_plan_invalid")
        if type(ac_connected) is not bool or not ac_connected:
            raise CompletionWaitAttemptError("attempt_ac_unconfirmed")
        expected = plan.expected_bytes if phase == "before_commit" else plan.proposed_bytes
        if type(observed_bytes) is not bytes or observed_bytes != expected:
            raise CompletionWaitAttemptError("attempt_checkpoint_changed")
        read_context = dict(schema=schema, expected_log_type=expected_log_type,
                            expected_target_period=expected_target_period, expected_run_id=expected_run_id,
                            current_utc=current_utc, current_utc_reliable=current_utc_reliable)
        before = read_completion_wait_checkpoint(plan.expected_bytes, **read_context)
        after = read_completion_wait_checkpoint(plan.proposed_bytes, **read_context)
        state = after.as_budget_state()
        if not state.check_times_utc:
            raise CompletionWaitAttemptError("attempt_plan_invalid")
        if current_utc > state.started_at_utc + timedelta(hours=24):
            raise CompletionWaitAttemptError("attempt_usepoint_deadline_reached")
        # Reconstruct the exact original candidate at its allocated timestamp,
        # while checking fresh prerequisites. Never allocate a second attempt.
        reconstructed = prepare_completion_wait_attempt(
            before.original_bytes, schema=schema, expected_log_type=expected_log_type,
            expected_target_period=expected_target_period, expected_run_id=expected_run_id,
            current_utc=state.check_times_utc[-1], current_utc_reliable=current_utc_reliable,
            logged_on=logged_on, same_account_verified=same_account_verified,
            own_sync_complete=own_sync_complete, waiting_confirmed=waiting_confirmed)
        if reconstructed != plan:
            raise CompletionWaitAttemptError("attempt_plan_invalid")
        return {"status": "requires_runtime_evidence", "reason_code": "attempt_observations_consistent",
                "may_check": False, "may_archive": False, "may_change_state": False}
    except CompletionWaitAttemptError:
        raise
    except CompletionWaitCheckpointError as exc:
        raise CompletionWaitAttemptError(exc.reason_code) from None
    except Exception:
        raise CompletionWaitAttemptError("attempt_usepoint_input_invalid") from None
