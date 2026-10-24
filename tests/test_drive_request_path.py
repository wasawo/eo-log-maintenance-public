"""Shared L1 grammar corpus: schema and independent Python checker, no real paths."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from Common.DriveRequestPath import is_drive_request_file_path
from test_contract_schemas import REQUEST_VALIDATOR, request


CORPUS = json.loads((Path(__file__).parent / "fixtures/drive-request-path-l1.json").read_text(encoding="utf-8"))


class DriveRequestPathTests(unittest.TestCase):
    def check_case(self, path, expected):
        self.assertIs(expected, is_drive_request_file_path(path))
        for operation, field in (("upload_file", "local_path"), ("download_file", "staging_path")):
            parameters = ({"local_path": path, "parent_id": "synthetic-folder", "file_name": "synthetic.txt",
                           "expected_sha256": "a" * 64} if operation == "upload_file" else
                          {"file_id": "synthetic-file", "staging_path": path})
            for dry_run in (True, False):
                value = request(operation, parameters, dry_run=dry_run)
                before = json.dumps(value, ensure_ascii=True)
                self.assertEqual(expected, REQUEST_VALIDATOR.is_valid(value))
                self.assertEqual(before, json.dumps(value, ensure_ascii=True))
                self.assertIs(path, value["parameters"][field])

    def test_shared_valid_and_invalid_corpus_for_both_request_fields(self):
        for name, expected in (("valid", True), ("invalid", False)):
            for index, path in enumerate(CORPUS[name]):
                with self.subTest(group=name, index=index): self.check_case(path, expected)

    def test_no_implicit_cast(self):
        for value in (None, True, False, 0, 1, [], {}, [r"C:\synthetic.txt"]):
            with self.subTest(type=type(value).__name__): self.check_case(value, False)

    def test_no_unapproved_fixed_maximum_length(self):
        self.check_case("C:\\" + "x" * 300, True)
        self.check_case("C:\\" + "\\".join(["component"] * 100), True)

    def test_unicode_input_is_not_normalized_and_checker_has_no_io(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")), \
             patch("pathlib.Path.resolve", side_effect=AssertionError("unexpected_io")):
            for value in CORPUS["valid"]:
                original = value.encode("utf-8")
                self.assertIs(True, is_drive_request_file_path(value))
                self.assertEqual(original, value.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
