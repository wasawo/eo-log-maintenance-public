"""Pure PC-A confirmation budget; no waiting, task, persistence or archive."""
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
import re

_WINDOW = timedelta(hours=24)
_INTERVAL = timedelta(hours=1)
_MAX_CHECKS = 25
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}")


@dataclass(frozen=True)
class CompletionWaitState:
    pc_id: str
    log_type: str
    target_period: str
    run_id: str
    started_at_utc: datetime
    check_times_utc: tuple[datetime, ...] = ()


@dataclass(frozen=True)
class CompletionWaitDecision:
    action: str
    reason_code: str
    next_check_at_utc: datetime | None = None
    check_due: bool = False
    may_archive: bool = field(default=False, init=False)
    may_change_state: bool = field(default=False, init=False)


class CompletionWaitBudgetError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _hold(reason):
    return CompletionWaitDecision("hold", reason)


def _utc(value):
    try:
        return type(value) is datetime and value.tzinfo is not None and value.utcoffset() == timedelta(0)
    except Exception:
        return False


def _identity(log_type, period, run_id):
    if type(log_type) is not str or log_type not in {"BattleLog", "ErrorReport"}:
        return False
    pattern = r"[0-9]{4}-(0[1-9]|1[0-2])" if log_type == "BattleLog" else r"[0-9]{4}"
    return (type(period) is str and re.fullmatch(pattern, period) is not None
            and type(run_id) is str and _UUID.fullmatch(run_id) is not None)


def assess_completion_wait_budget(
    state, *, expected_log_type, expected_target_period, expected_run_id,
    current_utc, current_utc_reliable, logged_on, same_account_verified,
    own_sync_complete, waiting_confirmed,
):
    """Return hold/wait/check_due observations for the original fixed budget.

    Supplied state/history/flags require independent trusted acquisition. No
    reconstruction from age/PID, budget reset, live query or public record is
    supplied. The deadline is inclusive for an eligible final check; after it
    or after 25 attempts there is no next-check advice. All advice is non-authorizing.
    """
    if not _identity(expected_log_type, expected_target_period, expected_run_id):
        return _hold("wait_scope_invalid")
    if type(state) is not CompletionWaitState:
        return _hold("wait_state_invalid")
    if (type(state.pc_id) is not str or state.pc_id != "PC-A"
            or not _identity(state.log_type, state.target_period, state.run_id)
            or (state.log_type, state.target_period, state.run_id) !=
               (expected_log_type, expected_target_period, expected_run_id)):
        return _hold("wait_scope_mismatch")
    if not _utc(state.started_at_utc) or type(state.check_times_utc) is not tuple:
        return _hold("wait_state_invalid")
    if len(state.check_times_utc) > _MAX_CHECKS:
        return _hold("wait_state_invalid")
    try:
        deadline = state.started_at_utc + _WINDOW
        previous = None
        for observed in state.check_times_utc:
            if (not _utc(observed) or not state.started_at_utc <= observed <= deadline
                    or (previous is not None and observed - previous < _INTERVAL)):
                return _hold("wait_history_invalid")
            previous = observed
    except Exception:
        return _hold("wait_state_invalid")
    flags = (current_utc_reliable, logged_on, same_account_verified, own_sync_complete, waiting_confirmed)
    if any(type(flag) is not bool for flag in flags):
        return _hold("wait_context_invalid")
    if not current_utc_reliable or not _utc(current_utc):
        return _hold("wait_clock_untrusted")
    if current_utc < (previous if previous is not None else state.started_at_utc):
        return _hold("wait_clock_rollback")
    if len(state.check_times_utc) == _MAX_CHECKS:
        return _hold("wait_check_limit_reached")
    if current_utc > deadline:
        return _hold("wait_deadline_reached")
    if not (logged_on and same_account_verified and own_sync_complete and waiting_confirmed):
        return _hold("wait_prerequisites_unconfirmed")
    if previous is not None and previous > deadline - _INTERVAL:
        return _hold("wait_no_window_remaining")
    next_check = state.started_at_utc if previous is None else previous + _INTERVAL
    if next_check > deadline:
        return _hold("wait_no_window_remaining")
    if current_utc < next_check:
        return CompletionWaitDecision("wait", "wait_interval_pending", next_check)
    return CompletionWaitDecision("check_due", "wait_check_due", check_due=True)


def record_completion_check_attempt(state, **observations):
    """Return immutable advanced state after rechecking every observation.

    Caller must durably bind/commit this attempt before a real check, including
    failed checks. This function performs neither persistence nor the check.
    A lost/untrusted history must block a runtime caller, never create a reset.
    """
    decision = assess_completion_wait_budget(state, **observations)
    if not decision.check_due:
        raise CompletionWaitBudgetError("wait_check_not_due") from None
    return replace(state, check_times_utc=state.check_times_utc + (observations["current_utc"],))
