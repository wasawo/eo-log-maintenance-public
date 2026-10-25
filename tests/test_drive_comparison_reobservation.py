"""Synthetic before/download/after listing comparison without re-query authority."""
from dataclasses import replace
import hashlib
import unittest
from unittest.mock import patch

from Common.DriveContentComparison import (
    ComparisonSource, DriveFileObservation, DriveListingPage, DriveListingObservation,
    collect_drive_listing, hash_downloaded_content, compare_reobserved_drive_content,
)


DATA = b"synthetic"
SOURCE = ComparisonSource("synthetic.txt", len(DATA), hashlib.sha256(DATA).hexdigest())
FILE = DriveFileObservation("synthetic-file", SOURCE.filename, len(DATA), None)
FOLDER = "synthetic-folder"


def listing(files=(FILE,)):
    return collect_drive_listing((DriveListingPage(FOLDER, None, None, files, True),), expected_folder_id=FOLDER)


def compare(before, after, **changes):
    options = dict(source_trusted=True, expected_folder_id=FOLDER,
        downloads=(hash_downloaded_content(FILE.file_id, (b"syn", b"thetic"),
                   expected_size_bytes=9, download_completed=True),))
    options.update(changes)
    source = options.pop("source", SOURCE)
    return compare_reobserved_drive_content(source, before, after, **options)


class DriveComparisonReobservationTests(unittest.TestCase):
    def assert_held(self, result, reason):
        self.assertEqual(("held", reason, None), (result.status, result.reason_code, result.candidate_file_id))
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)

    def test_before_download_after_matching_observations_are_candidate_only(self):
        before = listing()
        after = listing()
        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
            result = compare(before, after)
        self.assertEqual(("comparison_candidate", FILE.file_id), (result.status, result.candidate_file_id))
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)
        self.assertEqual(before, after)

    def test_order_only_changes_do_not_create_a_metadata_change(self):
        other = replace(FILE, file_id="synthetic-other", filename="other.txt")
        before = listing((FILE, other))
        after = listing((other, FILE))
        self.assertEqual("comparison_candidate", compare(before, after).status)

    def test_added_removed_renamed_replaced_size_and_hash_changes_are_held(self):
        before = listing()
        variants = ((), (FILE, replace(FILE, file_id="synthetic-duplicate")),
            (replace(FILE, filename="renamed.txt"),), (replace(FILE, file_id="synthetic-replacement"),),
            (replace(FILE, size_bytes=10),), (replace(FILE, sha256=SOURCE.sha256),),
            (replace(FILE, sha256_trusted=True),))
        for files in variants:
            with self.subTest(files=files):
                after = listing(files)
                self.assert_held(compare(before, after), "comparison_listing_changed")
                self.assertEqual(before.files, (FILE,))

    def test_other_files_and_unknown_metadata_changes_also_block_the_comparison(self):
        other = replace(FILE, file_id="synthetic-other", filename="other.txt")
        before = listing((FILE, other))
        for changed in (replace(other, filename="renamed.txt"), replace(other, size_bytes=None)):
            self.assert_held(compare(before, listing((FILE, changed))), "comparison_listing_changed")

    def test_invalid_incomplete_or_wrong_folder_listing_cannot_be_used(self):
        good = listing()
        incomplete = replace(good)
        object.__setattr__(incomplete, "enumeration_completed", False)
        for bad, reason in ((None, "comparison_listing_invalid"), ({}, "comparison_listing_invalid"),
                (DriveListingObservation(FOLDER, [FILE]), "comparison_listing_invalid"),
                (incomplete, "comparison_listing_incomplete"),
                (replace(good, folder_id="another-folder"), "comparison_folder_unconfirmed"),
                (replace(good, files=(FILE, FILE)), "comparison_identity_ambiguous"),
                (replace(good, files=(replace(FILE, size_bytes=True),)), "comparison_observations_invalid")):
            for before, after in ((bad, good), (good, bad)):
                self.assert_held(compare(before, after), reason)
        for field in ("may_restore", "may_report_sync_success", "may_archive"):
            bad = replace(good)
            object.__setattr__(bad, field, 1)
            self.assert_held(compare(good, bad), "comparison_listing_invalid")

    def test_unchanged_unknown_or_multiple_candidates_still_use_strict_comparison(self):
        good = listing()
        self.assert_held(compare(good, good, downloads=()), "comparison_hash_unavailable")
        empty = listing(())
        self.assert_held(compare(empty, empty, downloads=()), "comparison_no_match")
        trusted = replace(FILE, sha256=SOURCE.sha256, sha256_trusted=True)
        duplicate = listing((trusted, replace(trusted, file_id="synthetic-second")))
        self.assert_held(compare(duplicate, duplicate, downloads=()), "comparison_multiple_matches")
        self.assert_held(compare(good, good, source=None), "comparison_source_invalid")
        for trust in (False, None, 1):
            self.assert_held(compare(good, good, source_trusted=trust), "comparison_source_untrusted")

    def test_reused_observation_is_not_a_receipt_or_proof_of_freshness(self):
        saved = listing()
        first = compare(saved, saved)
        second = compare(saved, saved)
        self.assertEqual(first, second)
        self.assertFalse(second.may_restore or second.may_report_sync_success or second.may_archive)


if __name__ == "__main__": unittest.main()
