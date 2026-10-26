"""Build/verify private preservation metadata; no runtime reads or writes."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

from Common.LatestManifestSelection import _require_local_schema_refs, _no_schema_retrieval


class PrivateRecoveryEvidenceError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _reject(reason):
    raise PrivateRecoveryEvidenceError(reason) from None


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _reject("private_evidence_invalid")
        value[key] = item
    return value


def _validate_shape(value):
    try:
        schema = json.loads((Path(__file__).resolve().parent.parent / "contracts" /
                            "private-recovery-evidence-v1.schema.json").read_text(encoding="utf-8"))
        _require_local_schema_refs(schema)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker(),
            registry=Registry(retrieve=_no_schema_retrieval)).validate(value)
        # Optional JSON Schema format dependencies are not proof of a valid
        # calendar date. Enforce it independently on every installation.
        datetime.fromisoformat(value["observed_at_utc"][:-1] + "+00:00")
    except Exception:
        _reject("private_evidence_invalid")


def _raw(raw_lock_bytes):
    if type(raw_lock_bytes) is not bytes or not raw_lock_bytes:
        _reject("private_lock_bytes_invalid")


def validate_private_recovery_evidence(metadata_bytes, raw_lock_bytes):
    """Strict metadata plus byte hash/size binding, not source/root authority.

    Opaque old lock bytes may be malformed or non-UTF-8. Preservation does not
    interpret them as a supported lock schema or authorize recovery.
    """
    _raw(raw_lock_bytes)
    if type(metadata_bytes) is not bytes or not metadata_bytes:
        _reject("private_evidence_invalid")
    try:
        value = json.loads(metadata_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
    except Exception:
        _reject("private_evidence_invalid")
    _validate_shape(value)
    if (value["raw_lock_size"] != len(raw_lock_bytes)
            or value["raw_lock_sha256"] != hashlib.sha256(raw_lock_bytes).hexdigest()):
        _reject("private_lock_bytes_mismatch")
    return value


def build_private_recovery_evidence(*, raw_lock_bytes, evidence_id, pc_id,
                                    log_type, target_period, observed_at_utc):
    """Return only metadata bytes; never persist or expose raw lock content.

    UTC here is a structural observation label, not proof of clock reliability
    or freshness. Identity/root/ACL/ownership/disposition are separate gates.
    """
    _raw(raw_lock_bytes)
    value = dict(schema_version=1, evidence_id=evidence_id, pc_id=pc_id,
                 log_type=log_type, target_period=target_period,
                 observed_at_utc=observed_at_utc, purpose="lock_record_preservation",
                 raw_lock_filename="lock-record.bin", raw_lock_size=len(raw_lock_bytes),
                 raw_lock_sha256=hashlib.sha256(raw_lock_bytes).hexdigest(), may_change_state=False)
    _validate_shape(value)
    # Shape validation runs before serialization, so unsupported input objects
    # are not stringified into outputs or exception details.
    try:
        result = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except Exception:
        _reject("private_evidence_invalid")
    validate_private_recovery_evidence(result, raw_lock_bytes)
    return result
