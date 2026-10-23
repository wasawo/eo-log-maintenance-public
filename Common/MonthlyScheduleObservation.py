"""Pure approved monthly-time observation; never a task or run permission."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

_JST = timezone(timedelta(hours=9), name="JST")


class MonthlyScheduleError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _reject(reason):
    raise MonthlyScheduleError(reason) from None


@dataclass(frozen=True)
class MonthlyScheduleObservation:
    pc_id: str
    reason_code: str
    schedule_month: str | None = None
    scheduled_at_utc: datetime | None = None
    boundary_reached: bool = False
    may_start_run: bool = field(default=False, init=False)


def observe_monthly_schedule(*, pc_id, current_utc, current_utc_reliable,
                             logged_on, same_account_verified):
    """Observe day 1 PC-B 20:00 / PC-A 21:00 JST from supplied context.

    No host clock/session/account query, completion read, trigger, catch-up,
    hourly polling, retry, mutex, task registration or runtime call is made.
    The schedule month is not a log target period. Supplied flags are claims,
    not proof of runtime identity/clock reliability. All results deny run start.
    """
    if type(pc_id) is not str or pc_id not in {"PC-A", "PC-B"}:
        _reject("schedule_scope_invalid")
    if any(type(value) is not bool for value in (current_utc_reliable, logged_on, same_account_verified)):
        _reject("schedule_context_invalid")
    if not current_utc_reliable or type(current_utc) is not datetime:
        return MonthlyScheduleObservation(pc_id, "schedule_clock_untrusted")
    try:
        if current_utc.tzinfo is None or current_utc.utcoffset() != timedelta(0):
            return MonthlyScheduleObservation(pc_id, "schedule_clock_untrusted")
    except Exception:
        return MonthlyScheduleObservation(pc_id, "schedule_clock_untrusted")
    if not logged_on:
        return MonthlyScheduleObservation(pc_id, "schedule_session_unconfirmed")
    if not same_account_verified:
        return MonthlyScheduleObservation(pc_id, "schedule_account_unconfirmed")
    try:
        local = current_utc.astimezone(_JST)
        hour = 20 if pc_id == "PC-B" else 21
        scheduled = datetime(local.year, local.month, 1, hour, tzinfo=_JST).astimezone(timezone.utc)
        month = f"{local.year:04d}-{local.month:02d}"
        reached = current_utc >= scheduled
    except Exception:
        _reject("schedule_calendar_invalid")
    return MonthlyScheduleObservation(
        pc_id, "schedule_boundary_reached" if reached else "schedule_boundary_pending",
        month, scheduled, reached,
    )
