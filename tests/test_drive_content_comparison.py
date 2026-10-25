"""Synthetic OSD-01 observations: matching content never grants authority."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import unittest
from unittest.mock import patch

from Common.DriveContentComparison import (
    ComparisonSource, DriveFileObservation, DownloadHashObservation, compare_drive_content,
)


SHA = hashlib.sha256(b"synthetic").hexdigest()
OTHER = hashlib.sha256(b"different").hexdigest()
SOURCE = ComparisonSource("20260901_01020304@synthetic.txt", 9, SHA)
FILE = DriveFileObservation("synthetic-file", SOURCE.filename, 9, SHA, True)


def compare(files=(FILE,), **changes):
    options = dict(source_trusted=True, expected_folder_id="synthetic-folder",
                   observed_folder_id="synthetic-folder", enumeration_completed=True)
    options.update(changes)
    source = options.pop("source", SOURCE)
    return compare_drive_content(source, files, **options)


class DriveContentComparisonTests(unittest.TestCase):
    def assert_held(self, result, reason):
        self.assertEqual(("held", reason, None),
                         (result.status, result.reason_code, result.candidate_file_id))
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)

    def test_unique_content_match_has_no_authority_or_io(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
            result = compare()
        self.assertEqual("comparison_candidate", result.status)
        self.assertEqual(FILE.file_id, result.candidate_file_id)
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)
        with self.assertRaises(FrozenInstanceError): result.status = "success"
        for value in (SOURCE, FILE, result):
            self.assertNotIn(SOURCE.filename, repr(value))
            self.assertNotIn(FILE.file_id, repr(value))

    def test_zero_multiple_and_duplicate_identity_are_held(self):
        self.assert_held(compare(()), "comparison_no_match")
        self.assert_held(compare((FILE, replace(FILE, file_id="synthetic-second"))), "comparison_multiple_matches")
        self.assert_held(compare((FILE, FILE)), "comparison_identity_ambiguous")

    def test_trust_completeness_and_folder_are_not_inferred(self):
        for key in ("source_trusted", "enumeration_completed"):
            reason = "comparison_source_untrusted" if key == "source_trusted" else "comparison_listing_incomplete"
            for value in (False, None, 1, "true"):
                with self.subTest(key=key, value=value): self.assert_held(compare(**{key: value}), reason)
        for key in ("expected_folder_id", "observed_folder_id"):
            for value in (None, "", "another-folder"):
                self.assert_held(compare(**{key: value}), "comparison_folder_unconfirmed")

    def test_name_size_hash_must_all_match(self):
        for changes in ({"filename": "different.txt"}, {"filename": SOURCE.filename.upper()},
                        {"size_bytes": 10}, {"sha256": OTHER}):
            with self.subTest(changes=changes):
                self.assert_held(compare((replace(FILE, **changes),)), "comparison_no_match")
        for value in (None, False, True, -1, 9.0):
            reason = "comparison_metadata_unavailable" if value is None else "comparison_observations_invalid"
            self.assert_held(compare((replace(FILE, size_bytes=value),)), reason)

    def test_missing_or_untrusted_hash_needs_download(self):
        for file in (replace(FILE, sha256=None), replace(FILE, sha256_trusted=False),
                     replace(FILE, sha256=OTHER, sha256_trusted=False)):
            self.assert_held(compare((file,)), "comparison_hash_unavailable")
            result = compare((file,), downloads=(DownloadHashObservation(FILE.file_id, 9, SHA),))
            self.assertEqual("comparison_candidate", result.status)
            self.assertFalse(result.may_archive)

    def test_unknown_same_name_candidate_blocks_known_unique_match(self):
        for changes in ({"sha256": None}, {"sha256_trusted": False}, {"size_bytes": None}):
            uncertain = replace(FILE, file_id="synthetic-unknown", **changes)
            for files in ((FILE, uncertain), (uncertain, FILE)):
                self.assertEqual("held", compare(files).status)

    def test_other_names_and_known_size_mismatches_need_no_download(self):
        unrelated = replace(FILE, file_id="synthetic-other", filename="other.txt", size_bytes=None, sha256=None)
        different_size = replace(FILE, file_id="synthetic-size", size_bytes=10, sha256=None)
        self.assertEqual("comparison_candidate", compare((unrelated, FILE, different_size)).status)

    def test_download_failure_mismatch_and_identity_binding_fail_closed(self):
        missing = replace(FILE, sha256=None)
        self.assert_held(compare((missing,)), "comparison_hash_unavailable")
        for download, reason in (
            (DownloadHashObservation(FILE.file_id, 10, SHA), "comparison_download_mismatch"),
            (DownloadHashObservation("synthetic-wrong-id", 9, SHA), "comparison_download_unbound"),
            (DownloadHashObservation(FILE.file_id, 9, "bad"), "comparison_download_invalid"),
        ):
            self.assert_held(compare((missing,), downloads=(download,)), reason)
        mismatch = DownloadHashObservation(FILE.file_id, 9, OTHER)
        self.assert_held(compare(downloads=(mismatch,)), "comparison_download_mismatch")
        self.assert_held(compare((missing,), downloads=(mismatch,)), "comparison_no_match")
        good = DownloadHashObservation(FILE.file_id, 9, SHA)
        self.assert_held(compare((missing,), downloads=(good, good)), "comparison_download_unbound")

    def test_invalid_observations_never_leak_input_details(self):
        for source in (None, {}, replace(SOURCE, size_bytes=True), replace(SOURCE, sha256="secret-invalid")):
            self.assert_held(compare(source=source), "comparison_source_invalid")
        for files in ([FILE], (None,), (replace(FILE, sha256="secret-invalid"),),
                      (replace(FILE, sha256_trusted=1),), (replace(FILE, file_id=""),)):
            result = compare(files)
            self.assert_held(result, "comparison_observations_invalid")
            self.assertNotIn("secret-invalid", result.reason_code)
        self.assert_held(compare(downloads=[]), "comparison_observations_invalid")


if __name__ == "__main__": unittest.main()
