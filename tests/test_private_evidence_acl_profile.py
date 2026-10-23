"""Synthetic ACL observations only, without account collection or OS edits."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import unittest
from unittest.mock import patch

from Common.PrivateEvidenceAclProfile import assess_private_file_acl

USER = "S-1-5-21-101-202-303-1001"
OTHER = "S-1-5-21-101-202-303-1002"


def allow(sid=USER, mask=3, **changes):
    return dict(sid=sid, type="allow", flags=0, mask=mask, **changes)


class PrivateEvidenceAclProfileTests(unittest.TestCase):
    def snapshot(self, **changes):
        result = dict(object_kind="file", owner_sid=USER, dacl_present=True,
                      dacl_null=False, dacl_protected=True,
                      aces=[allow(), allow("S-1-5-18", 0x1F01FF), allow("S-1-5-32-544", 0x1F01FF)])
        result.update(changes)
        return result

    def assess(self, snapshot=None, **changes):
        return assess_private_file_acl(self.snapshot() if snapshot is None else snapshot,
                                       execution_sid=changes.get("execution_sid", USER))

    def test_narrow_explicit_profile_matches_without_permission_or_sid_output(self):
        result = self.assess()
        self.assertTrue(result.profile_matches)
        self.assertFalse(result.may_change_state)
        self.assertNotIn(USER, repr(result))
        self.assertNotIn("S-1-", json.dumps(result.__dict__))
        with self.assertRaises(FrozenInstanceError):
            result.may_change_state = True

    def test_world_and_other_account_grants_block(self):
        for sid in ("S-1-1-0", "S-1-5-11", OTHER):
            snapshot = self.snapshot()
            snapshot["aces"].append(allow(sid))
            result = self.assess(snapshot)
            self.assertFalse(result.profile_matches)
            self.assertEqual(result.reason_code, "private_acl_trustee_untrusted")

    def test_foreign_owner_blocks_even_if_dacl_is_narrow(self):
        self.assertEqual(self.assess(self.snapshot(owner_sid=OTHER)).reason_code,
                         "private_acl_owner_untrusted")

    def test_null_or_absent_dacl_is_not_empty_dacl(self):
        for changes in ({"dacl_null": True}, {"dacl_present": False}):
            self.assertEqual(self.assess(self.snapshot(**changes)).reason_code, "private_acl_unrestricted")
        self.assertEqual(self.assess(self.snapshot(aces=[])).reason_code, "private_acl_executor_rights_missing")

    def test_inheritance_requires_further_qualification(self):
        self.assertEqual(self.assess(self.snapshot(dacl_protected=False)).reason_code,
                         "private_acl_inheritance_unsupported")
        for flags in (1, 2, 8, 16):
            ace = allow()
            ace["flags"] = flags
            self.assertFalse(self.assess(self.snapshot(aces=[ace])).profile_matches)

    def test_deny_does_not_cancel_untrusted_allow_into_success(self):
        deny = allow("S-1-1-0")
        deny["type"] = "deny"
        for aces in ([deny, allow("S-1-1-0"), allow()], [allow(), allow("S-1-1-0"), deny]):
            self.assertFalse(self.assess(self.snapshot(aces=aces)).profile_matches)

    def test_generic_unknown_or_invalid_masks_block(self):
        for mask in (0, -1, True, 0x10000000, 0xC0000000, 0x200, 2 ** 32):
            self.assertFalse(self.assess(self.snapshot(aces=[allow(mask=mask)])).profile_matches)

    def test_unknown_ace_kinds_and_fields_block(self):
        for kind in ("callback", "object_allow", "audit"):
            ace = allow()
            ace["type"] = kind
            self.assertFalse(self.assess(self.snapshot(aces=[ace])).profile_matches)
        ace = allow()
        ace["private_detail"] = "synthetic_do_not_emit"
        result = self.assess(self.snapshot(aces=[ace]))
        self.assertFalse(result.profile_matches)
        self.assertNotIn("synthetic_do_not_emit", repr(result))

    def test_account_rights_not_inferred_from_admin_group(self):
        for aces in ([allow("S-1-5-32-544", 3)], [allow(mask=1)]):
            self.assertEqual(self.assess(self.snapshot(aces=aces)).reason_code,
                             "private_acl_executor_rights_missing")
        self.assertTrue(self.assess(self.snapshot(aces=[allow(mask=1), allow(mask=2)])).profile_matches)

    def test_execution_identity_cannot_be_everyone_or_unknown_family(self):
        for sid in ("S-1-1-0", "S-1-5-18", "private account name", None):
            self.assertFalse(self.assess(execution_sid=sid).profile_matches)
        azure = "S-1-12-1-101-202-303-404"
        self.assertTrue(self.assess(self.snapshot(owner_sid=azure, aces=[allow(azure)]), execution_sid=azure).profile_matches)

    def test_invalid_or_partial_observation_is_not_a_match(self):
        for snapshot in ({}, self.snapshot(dacl_present=1), self.snapshot(owner_sid="S-1-5-21-01-2-3-4")):
            self.assertFalse(self.assess(snapshot).profile_matches)
        snapshot = self.snapshot()
        snapshot["extra"] = "synthetic_private_detail"
        self.assertFalse(self.assess(snapshot).profile_matches)

    def test_directory_and_ancestor_qualification_is_not_claimed(self):
        self.assertEqual(self.assess(self.snapshot(object_kind="directory")).reason_code,
                         "private_acl_object_unsupported")

    def test_input_preservation_and_no_io(self):
        snapshot = self.snapshot()
        before = deepcopy(snapshot)
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")):
            self.assertTrue(self.assess(snapshot).profile_matches)
        self.assertEqual(snapshot, before)
