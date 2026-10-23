"""Cross-runtime synthetic binary descriptors; never OS ACL/account access."""
import json
import os
from pathlib import Path
import subprocess
import unittest

from Common.PrivateEvidenceAclProfile import assess_private_file_acl

USER = "S-1-5-21-101-202-303-1001"
OTHER = "S-1-5-21-101-202-303-1002"


@unittest.skipUnless(os.name == "nt", "Windows descriptor runtime required")
class PrivateAclDescriptorNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = "O:" + USER + "D:P"
        fixtures = [
            ("private", base + "(A;;0x3;;;" + USER + ")(A;;FA;;;SY)(A;;FA;;;BA)", ""),
            ("world", base + "(A;;0x3;;;" + USER + ")(A;;FR;;;WD)", ""),
            ("foreign_owner", "O:" + OTHER + "D:P(A;;0x3;;;" + USER + ")", ""),
            ("deny", base + "(D;;0x1;;;WD)(A;;0x3;;;" + USER + ")", ""),
            ("inherited", base + "(A;ID;0x3;;;" + USER + ")", ""),
            ("generic", base + "(A;;GR;;;" + USER + ")", ""),
            ("empty_dacl", base, ""),
            ("no_dacl", "O:" + USER, ""),
            ("null_dacl", "O:" + USER + "D:NO_ACCESS_CONTROL", ""),
            ("object_ace", base + "(OA;;0x3;00000000-0000-0000-0000-000000000001;;" + USER + ")", ""),
            ("callback", base + "(A;;0x3;;;" + USER + ")", "callback"),
            ("no_owner", "D:P(A;;0x3;;;" + USER + ")", ""),
            ("sacl", base + "(A;;0x3;;;" + USER + ")S:(AU;SA;FR;;;WD)", ""),
            ("trailing", base + "(A;;0x3;;;" + USER + ")", "trailing"),
            ("truncated", base, "truncated"),
            ("empty", base, "empty"),
        ]
        command = ["pwsh", "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
                   str(Path(__file__).with_name("private_acl_descriptor_fixture_worker.ps1"))]
        payload = json.dumps([dict(sddl=sddl, mutation=mutation) for name, sddl, mutation in fixtures])
        result = subprocess.run(command, input=payload, text=True, capture_output=True, timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise AssertionError("synthetic_descriptor_worker_failed")
        observations = json.loads(result.stdout)
        cls.results = {fixture[0]: observation for fixture, observation in zip(fixtures, observations, strict=True)}

    def result(self, name):
        result = self.results[name]
        self.assertTrue(result["preserved"])
        self.assertTrue(result["ok"], "normalization_should_succeed")
        return result["observation"]

    def test_private_binary_descriptor_connects_to_non_authorizing_profile(self):
        observed = self.result("private")
        decision = assess_private_file_acl(observed, execution_sid=USER)
        self.assertTrue(decision.profile_matches)
        self.assertFalse(decision.may_change_state)
        self.assertNotIn(USER, repr(decision))
        self.assertEqual(len(observed["aces"]), 3)

    def test_world_foreign_owner_and_deny_not_dropped(self):
        for name in ("world", "foreign_owner", "deny"):
            with self.subTest(name=name):
                self.assertFalse(assess_private_file_acl(self.result(name), execution_sid=USER).profile_matches)
        self.assertEqual(self.result("deny")["aces"][0]["type"], "deny")

    def test_inherited_flags_are_preserved(self):
        observed = self.result("inherited")
        self.assertEqual(observed["aces"][0]["flags"], 16)
        self.assertFalse(assess_private_file_acl(observed, execution_sid=USER).profile_matches)

    def test_generic_mask_keeps_unsigned_high_bits_and_blocks(self):
        observed = self.result("generic")
        self.assertEqual(observed["aces"][0]["mask"], 0x80000000)
        self.assertFalse(assess_private_file_acl(observed, execution_sid=USER).profile_matches)

    def test_empty_absent_and_null_dacl_are_distinct_and_block(self):
        empty, absent, null = (self.result(name) for name in ("empty_dacl", "no_dacl", "null_dacl"))
        self.assertEqual(empty["aces"], [])
        self.assertFalse(empty["dacl_null"])
        self.assertFalse(absent["dacl_present"])
        self.assertTrue(null["dacl_null"])
        for observed in (empty, absent, null):
            self.assertFalse(assess_private_file_acl(observed, execution_sid=USER).profile_matches)

    def test_unknown_descriptor_features_and_corruption_are_sanitized(self):
        for name in ("object_ace", "callback", "no_owner", "sacl", "trailing", "truncated", "empty"):
            with self.subTest(name=name):
                result = self.results[name]
                self.assertTrue(result["preserved"])
                self.assertFalse(result["ok"])
                self.assertEqual(result["reason"], "private_acl_descriptor_invalid_or_unsupported")
                self.assertNotIn(USER, result["reason"])
