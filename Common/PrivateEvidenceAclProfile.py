"""Conservative supplied file-ACL profile; no OS query or authorization."""
from dataclasses import dataclass, field
import re

_SYSTEM = "S-1-5-18"
_ADMINS = "S-1-5-32-544"
# Ordinary file-specific + standard access bits. Generic masks need a trusted
# OS mapper; directories and conditional/object/callback ACEs are unsupported.
_FILE_BITS = 0x001F01FF


@dataclass(frozen=True)
class PrivateAclProfileAssessment:
    profile_matches: bool
    reason_code: str
    may_change_state: bool = field(default=False, init=False)


def _result(reason, matches=False):
    return PrivateAclProfileAssessment(matches, reason)


def _sid(value):
    if type(value) is not str or len(value) > 184:
        return False
    if not re.fullmatch(r"S-1-[0-9]+(?:-[0-9]+){1,15}", value):
        return False
    parts = value.split("-")[2:]
    if any(str(int(part)) != part for part in parts):
        return False
    return int(parts[0]) < 2 ** 48 and all(int(part) < 2 ** 32 for part in parts[1:])


def _account_sid(value):
    # Initial user-SID families only. This syntax check cannot establish that
    # a SID is the authenticated token's user rather than a supplied claim.
    return _sid(value) and bool(re.fullmatch(
        r"S-1-(?:5-21-[0-9]+-[0-9]+-[0-9]+-[0-9]+|12-1-[0-9]+-[0-9]+-[0-9]+-[0-9]+)", value))


def assess_private_file_acl(snapshot, *, execution_sid):
    """Classify a complete normalized observation of one file's descriptor.

    Requires explicit protected non-null DACL, trusted owner and only explicit
    plain allow ACEs for the execution user, SYSTEM or local Administrators.
    Execution-user file read/write bits must be present explicitly. No group
    expansion, generic mapping, privilege, ancestry, root or TOCTOU qualification
    is performed. A matching profile remains non-authorizing observation only.
    """
    if not _account_sid(execution_sid):
        return _result("private_acl_input_invalid")
    expected = {"object_kind", "owner_sid", "dacl_present", "dacl_null", "dacl_protected", "aces"}
    if type(snapshot) is not dict or set(snapshot) != expected:
        return _result("private_acl_input_invalid")
    if (not _sid(snapshot["owner_sid"]) or type(snapshot["aces"]) is not list
            or any(type(snapshot[key]) is not bool for key in ("dacl_present", "dacl_null", "dacl_protected"))):
        return _result("private_acl_input_invalid")
    if type(snapshot["object_kind"]) is not str or snapshot["object_kind"] != "file":
        return _result("private_acl_object_unsupported")
    trusted = {execution_sid, _SYSTEM, _ADMINS}
    if snapshot["owner_sid"] not in trusted:
        return _result("private_acl_owner_untrusted")
    if not snapshot["dacl_present"] or snapshot["dacl_null"]:
        return _result("private_acl_unrestricted")
    if not snapshot["dacl_protected"]:
        return _result("private_acl_inheritance_unsupported")
    user_mask = 0
    for ace in snapshot["aces"]:
        if type(ace) is not dict or set(ace) != {"sid", "type", "flags", "mask"}:
            return _result("private_acl_input_invalid")
        if (not _sid(ace["sid"]) or type(ace["type"]) is not str
                or type(ace["flags"]) is not int or type(ace["mask"]) is not int):
            return _result("private_acl_input_invalid")
        if (ace["type"] != "allow" or ace["flags"] != 0
                or not 0 < ace["mask"] <= 0xFFFFFFFF or ace["mask"] & ~_FILE_BITS):
            return _result("private_acl_ace_unsupported")
        if ace["sid"] not in trusted:
            return _result("private_acl_trustee_untrusted")
        if ace["sid"] == execution_sid:
            user_mask |= ace["mask"]
    if user_mask & 3 != 3:  # FILE_READ_DATA | FILE_WRITE_DATA; no group inference.
        return _result("private_acl_executor_rights_missing")
    return _result("private_acl_profile_matches", matches=True)
