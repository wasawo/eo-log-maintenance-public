"""Record-free mutex lifetime for diagnosis only; no recovery permission."""
from contextlib import contextmanager
from dataclasses import dataclass, field
import math

from Common.OwnedRunLock import _NamedMutex, _mutex_name


class DiagnosticMutexError(RuntimeError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _reject(reason):
    raise DiagnosticMutexError(reason) from None


@dataclass(frozen=True)
class DiagnosticMutexObservation:
    abandoned: bool
    may_change_state: bool = field(default=False, init=False)


@contextmanager
def acquire_diagnostic_mutex(scope_id, *, timeout_seconds=0, mutex_factory=None):
    """Acquire the existing scope mutex without any ownership-record I/O.

    The yielded abandoned flag is point-in-time evidence only. This lease never
    owns another process's token/record. Body errors remain the caller's job to
    sanitize; errors from this helper use fixed reason codes. No runtime entry
    point or approved-root qualification is provided.
    """
    try:
        name = _mutex_name(scope_id)
    except Exception:
        _reject("diagnostic_scope_invalid")
    if (type(timeout_seconds) not in (int, float) or not 0 <= timeout_seconds <= 60
            or not math.isfinite(timeout_seconds)):
        _reject("diagnostic_timeout_invalid")
    try:
        mutex = (mutex_factory or _NamedMutex)(name)
    except Exception:
        _reject("diagnostic_mutex_create_failed")
    acquired = False
    try:
        try:
            acquired = True  # Cleanup also covers an interrupted acquire.
            result = mutex.acquire(float(timeout_seconds))
            # Adapter contract: acquire returns bool, release is safe when not
            # owned. Attempt release on uncertain adapter failure as well.
            acquired = result is not False
            if type(result) is not bool:
                _reject("diagnostic_mutex_wait_failed")
        except Exception:
            acquired = True
            _reject("diagnostic_mutex_wait_failed")
        if not result:
            _reject("diagnostic_mutex_timeout")
        try:
            abandoned = mutex.abandoned
            if type(abandoned) is not bool:
                _reject("diagnostic_mutex_observation_invalid")
        except Exception:
            _reject("diagnostic_mutex_observation_invalid")
        yield DiagnosticMutexObservation(abandoned)
    finally:
        cleanup_failed = False
        try:
            if acquired:
                mutex.release()
        except Exception:
            cleanup_failed = True
        finally:
            try:
                mutex.close()
            except Exception:
                cleanup_failed = True
        if cleanup_failed:
            _reject("diagnostic_mutex_cleanup_failed")
