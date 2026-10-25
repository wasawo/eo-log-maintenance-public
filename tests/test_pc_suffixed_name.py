"""Approved suffix projection keeps source identity and grants no file action."""
from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from Common.DriveContentComparison import DriveNameObservationError, observe_pc_suffixed_name


class PcSuffixedNameTests(unittest.TestCase):
    def test_both_pcs_and_log_types_append_before_last_extension_without_io(self):
        for log, original in (("BattleLog", "20260901_01020304@合成.txt"),
                              ("ErrorReport", "20250901_01020304.txt")):
            for pc, suffix in (("PC-A", "_PCA"), ("PC-B", "_PCB")):
                with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
                    result = observe_pc_suffixed_name(original, pc_id=pc, log_type=log)
                self.assertEqual(original, result.original_filename)
                self.assertEqual(original[:-4]+suffix+".txt", result.proposed_filename)
                self.assertEqual((pc, log), (result.pc_id, result.log_type))
                self.assertFalse(result.may_rename or result.may_upload or result.may_overwrite or result.may_archive)
                self.assertNotIn(original, repr(result))
                with self.assertRaises(FrozenInstanceError): result.proposed_filename = "other.txt"

    def test_unicode_case_spacing_and_extra_dots_are_preserved_exactly(self):
        for title in ("Café", "Cafe\u0301", "MIXED.case.txt", "name ", "合成"):
            original = "20260901_01020304@"+title+".txt"
            result = observe_pc_suffixed_name(original, pc_id="PC-A", log_type="BattleLog")
            self.assertEqual(original[:-4]+"_PCA.txt", result.proposed_filename)
            self.assertEqual(original, result.original_filename)

    def test_suffix_text_never_infers_or_repairs_origin(self):
        original = "20260901_01020304@synthetic_PCB.txt"
        result = observe_pc_suffixed_name(original, pc_id="PC-A", log_type="BattleLog")
        self.assertEqual("20260901_01020304@synthetic_PCB_PCA.txt", result.proposed_filename)
        self.assertEqual(result, observe_pc_suffixed_name(original, pc_id="PC-A", log_type="BattleLog"))
        self.assertFalse(result.may_rename or result.may_overwrite)

    def test_invalid_pc_log_date_extension_and_type_are_sanitized(self):
        for pc in (None, True, "pc-a", "PC-C"):
            with self.assertRaisesRegex(DriveNameObservationError, "^naming_pc_invalid$"):
                observe_pc_suffixed_name("private-input", pc_id=pc, log_type="BattleLog")
        for log in (None, True, "battlelog", "Other"):
            with self.assertRaisesRegex(DriveNameObservationError, "^naming_log_type_invalid$"):
                observe_pc_suffixed_name("private-input", pc_id="PC-A", log_type=log)
        for original in (None, True, "unexpected.txt", "20260230_01020304@x.txt",
                         "20260901_01020304@x.TXT", "20260901_01020304_PCA.txt"):
            log = "ErrorReport" if isinstance(original, str) and "@" not in original else "BattleLog"
            with self.assertRaisesRegex(DriveNameObservationError, "^naming_filename_invalid$") as caught:
                observe_pc_suffixed_name(original, pc_id="PC-A", log_type=log)
            self.assertIsNone(caught.exception.__cause__)

    def test_windows_forbidden_basename_characters_and_unencodable_text_are_rejected(self):
        for character in ("/", "\\", ":", "<", ">", '"', "|", "?", "*", "\x00", "\x1f", "\x7f", "\ud800"):
            original = "20260901_01020304@x"+character+"y.txt"
            with self.assertRaisesRegex(DriveNameObservationError, "^naming_filename_invalid$"):
                observe_pc_suffixed_name(original, pc_id="PC-B", log_type="BattleLog")


if __name__ == "__main__": unittest.main()
