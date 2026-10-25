"""Read-only Windows AC observation; never a run or continuation permission."""
import ctypes
from dataclasses import dataclass, field
import os


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", ctypes.c_uint32), ("BatteryFullLifeTime", ctypes.c_uint32)]


@dataclass(frozen=True)
class PowerStatusObservation:
    ac_connected: bool | None
    reason_code: str
    may_start_run: bool = field(default=False, init=False)
    may_check: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


def _read_ac_line_status():
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    query = api.GetSystemPowerStatus
    query.argtypes = (ctypes.POINTER(_SystemPowerStatus),)
    query.restype = ctypes.c_int
    status = _SystemPowerStatus()
    if not query(ctypes.byref(status)):
        raise OSError("power_query_failed")
    return status.ACLineStatus


def observe_ac_power():
    """Query once, without caching, polling, clock/session queries or mutation.

    Only successful ACLineStatus=1 means connected. Unknown, failed and
    unsupported observations expose None, never a truthy fallback. No raw
    OS error, battery metadata or timestamp is returned. Re-query at each use
    point; this snapshot neither monitors nor cancels in-flight operations.
    """
    if os.name != "nt":
        return PowerStatusObservation(None, "power_platform_unsupported")
    try:
        value = _read_ac_line_status()
    except Exception:
        return PowerStatusObservation(None, "power_query_failed")
    if type(value) is int and value == 1:
        return PowerStatusObservation(True, "power_ac_connected")
    if type(value) is int and value == 0:
        return PowerStatusObservation(False, "power_ac_disconnected")
    return PowerStatusObservation(None, "power_status_unknown")
