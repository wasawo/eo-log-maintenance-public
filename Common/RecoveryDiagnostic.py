"""Pure, sanitized observations for recovery diagnosis; never authorization."""
from dataclasses import dataclass, field
import re

GATES = (
    "configuration", "root", "mutex", "lock_record", "clock",
    "latest_manifest", "owner_termination", "drive_reconciliation",
)
STATES = frozenset({"satisfied", "missing", "unknown", "failed"})
_REASONS = frozenset(gate + "_" + state for gate in GATES for state in STATES - {"satisfied"})
_COMPLETE = "diagnosis_observations_complete"


class RecoveryDiagnosticError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _reject():
    raise RecoveryDiagnosticError("diagnostic_input_invalid") from None


def _scope(pc_id, log_type, target_period):
    if type(pc_id) is not str or pc_id not in {"PC-A", "PC-B"}:
        _reject()
    if type(log_type) is not str or log_type not in {"BattleLog", "ErrorReport"}:
        _reject()
    pattern = r"[0-9]{4}-(0[1-9]|1[0-2])" if log_type == "BattleLog" else r"[0-9]{4}"
    if type(target_period) is not str or not re.fullmatch(pattern, target_period):
        _reject()


@dataclass(frozen=True)
class RecoveryDiagnostic:
    pc_id: str
    log_type: str
    target_period: str
    classification: str
    reason_codes: tuple[str, ...]
    may_change_state: bool = field(default=False, init=False)

    def __post_init__(self):
        _scope(self.pc_id, self.log_type, self.target_period)
        if type(self.classification) is not str or type(self.reason_codes) is not tuple:
            _reject()
        if not self.reason_codes or any(type(item) is not str for item in self.reason_codes):
            _reject()
        if self.classification == "review_required":
            if self.reason_codes != (_COMPLETE,):
                _reject()
        elif self.classification == "blocked":
            if (any(item not in _REASONS for item in self.reason_codes)
                    or len(set(self.reason_codes)) != len(self.reason_codes)):
                _reject()
            # At most one observation reason per gate, in fixed gate order.
            gates = [item.rsplit("_", 1)[0] for item in self.reason_codes]
            if len(set(gates)) != len(gates) or gates != sorted(gates, key=GATES.index):
                _reject()
        else:
            _reject()
        if self.may_change_state is not False:
            _reject()

    def to_public_dict(self):
        # Recheck even an object tampered with outside the frozen interface.
        self.__post_init__()
        return {"schema_version": 1, "pc_id": self.pc_id, "log_type": self.log_type,
                "target_period": self.target_period, "classification": self.classification,
                "reason_codes": list(self.reason_codes), "may_change_state": False}


def build_recovery_diagnostic(*, pc_id, log_type, target_period, observations):
    """Classify supplied observations, without collecting or trusting evidence.

    Every gate is explicit: no missing gate defaults to satisfied. Even complete
    supplied observations require review and never permit recovery side effects.
    Raw records/paths/messages are not accepted or included in public output.
    """
    _scope(pc_id, log_type, target_period)
    if type(observations) is not dict or set(observations) != set(GATES):
        _reject()
    if any(type(value) is not str or value not in STATES for value in observations.values()):
        _reject()
    reasons = tuple(gate + "_" + observations[gate] for gate in GATES
                    if observations[gate] != "satisfied")
    return RecoveryDiagnostic(pc_id, log_type, target_period,
                              "blocked" if reasons else "review_required",
                              reasons or (_COMPLETE,))
