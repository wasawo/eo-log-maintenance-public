"""Synthetic page continuity -> download hash -> comparison without a transport."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import unittest
from unittest.mock import patch

from Common.DriveContentComparison import (
    ComparisonSource, DriveFileObservation, DriveListingPage, DriveListingObservationError,
    collect_drive_listing, compare_drive_content, hash_downloaded_content,
)


FOLDER = "synthetic-folder"
DATA = b"synthetic"
SOURCE = ComparisonSource("synthetic.txt", len(DATA), hashlib.sha256(DATA).hexdigest())
FILE = DriveFileObservation("synthetic-file", SOURCE.filename, SOURCE.size_bytes, None)


def page(files=(), requested=None, next_token=None, **changes):
    return replace(DriveListingPage(FOLDER, requested, next_token, files, True), **changes)


class DriveListingObservationTests(unittest.TestCase):
    def collect(self, pages):
        return collect_drive_listing(pages, expected_folder_id=FOLDER)

    def test_complete_empty_listing_is_distinct_from_absent_or_failed_pages(self):
        observed = self.collect((page(),))
        self.assertEqual((), observed.files)
        self.assertIs(True, observed.enumeration_completed)
        for pages in ((), (page(next_token="synthetic-next"),)):
            with self.assertRaisesRegex(DriveListingObservationError, "listing_terminal_missing"):
                self.collect(pages)
        with self.assertRaisesRegex(DriveListingObservationError, "listing_request_unconfirmed"):
            self.collect((page(request_succeeded=False),))

    def test_multiple_pages_empty_intermediate_and_hash_fallback_connect(self):
        other = replace(FILE, file_id="synthetic-other", filename="other.txt")
        pages = (page((other,), next_token="synthetic-one"),
                 page(requested="synthetic-one", next_token="synthetic-two"),
                 page((FILE,), requested="synthetic-two"))
        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
            listing = self.collect(iter(pages))
            download = hash_downloaded_content(FILE.file_id, (b"syn", b"thetic"),
                expected_size_bytes=FILE.size_bytes, download_completed=True)
            result = compare_drive_content(SOURCE, listing.files, source_trusted=True,
                expected_folder_id=FOLDER, observed_folder_id=listing.folder_id,
                enumeration_completed=listing.enumeration_completed, downloads=(download,))
        self.assertEqual((other, FILE), listing.files)
        self.assertEqual("comparison_candidate", result.status)
        for observation in (listing, result):
            self.assertFalse(observation.may_restore or observation.may_report_sync_success or observation.may_archive)
            self.assertNotIn(FOLDER, repr(observation))
        with self.assertRaises(FrozenInstanceError): listing.files = ()

    def test_folder_and_success_are_required_on_every_page(self):
        for changes, reason in (({"folder_id": "another-folder"}, "listing_folder_mismatch"),
                                ({"folder_id": None}, "listing_folder_mismatch")):
            with self.assertRaisesRegex(DriveListingObservationError, reason):
                self.collect((page(next_token="next"), page(requested="next", **changes)))
        for flag in (False, None, 1, "true"):
            with self.assertRaisesRegex(DriveListingObservationError, "listing_request_unconfirmed"):
                self.collect((page(next_token="next"), page(requested="next", request_succeeded=flag)))
        for folder in (None, "", 1):
            with self.assertRaisesRegex(DriveListingObservationError, "listing_folder_invalid"):
                collect_drive_listing((), expected_folder_id=folder)

    def test_token_continuity_and_cycles_are_rejected_without_normalization(self):
        cases = (
            ((page(requested="unexpected"),), "listing_token_discontinuous"),
            ((page(next_token="next"), page(requested=None)), "listing_token_discontinuous"),
            ((page(next_token="next"), page(requested="NEXT")), "listing_token_discontinuous"),
            ((page(next_token="next"), page(requested="next", next_token="next")), "listing_token_cycle"),
            ((page(next_token="one"), page(requested="one", next_token="two"),
              page(requested="two", next_token="one")), "listing_token_cycle"),
        )
        for pages, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(DriveListingObservationError, reason):
                self.collect(pages)
        for value in ("", 1, False, "bad\x00token"):
            with self.assertRaisesRegex(DriveListingObservationError, "listing_token_invalid"):
                self.collect((page(next_token=value),))

    def test_terminal_page_cannot_hide_a_trailer_or_trailing_failure(self):
        with self.assertRaisesRegex(DriveListingObservationError, "listing_after_terminal"):
            self.collect((page(), page((FILE,))))
        def failing():
            yield page((FILE,))
            raise DriveListingObservationError("synthetic-private-detail")
        with self.assertRaisesRegex(DriveListingObservationError, "^listing_read_failed$") as caught:
            self.collect(failing())
        self.assertIsNone(caught.exception.__cause__)
        self.assertNotIn("synthetic-private-detail", str(caught.exception))

    def test_duplicate_file_identity_within_and_across_pages_is_ambiguous(self):
        for pages in ((page((FILE, FILE)),),
                      (page((FILE,), next_token="next"), page((FILE,), requested="next"))):
            with self.assertRaisesRegex(DriveListingObservationError, "listing_identity_ambiguous"):
                self.collect(pages)

    def test_invalid_page_or_file_cannot_form_a_partial_observation(self):
        for bad in (None, {}, page(files=[FILE])):
            with self.assertRaisesRegex(DriveListingObservationError, "listing_page_invalid"):
                self.collect((bad,))
        for bad in (None, replace(FILE, size_bytes=True), replace(FILE, sha256="invalid"),
                    replace(FILE, sha256_trusted=1), replace(FILE, file_id="")):
            with self.assertRaisesRegex(DriveListingObservationError, "listing_file_invalid"):
                self.collect((page((FILE,), next_token="next"), page((bad,), requested="next")))

    def test_iterator_failure_is_sanitized_and_does_not_retry(self):
        calls = []
        def failing():
            calls.append(1)
            yield page((FILE,), next_token="next")
            raise OSError("synthetic-private-detail")
        with self.assertRaisesRegex(DriveListingObservationError, "^listing_read_failed$"):
            self.collect(failing())
        self.assertEqual([1], calls)
        with self.assertRaisesRegex(DriveListingObservationError, "listing_read_failed"):
            self.collect(None)

    def test_multiple_content_matches_across_pages_remain_held(self):
        trusted = replace(FILE, sha256=SOURCE.sha256, sha256_trusted=True)
        listing = self.collect((page((trusted,), next_token="next"),
            page((replace(trusted, file_id="synthetic-second"),), requested="next")))
        result = compare_drive_content(SOURCE, listing.files, source_trusted=True,
            expected_folder_id=FOLDER, observed_folder_id=listing.folder_id,
            enumeration_completed=listing.enumeration_completed)
        self.assertEqual(("held", "comparison_multiple_matches"), (result.status, result.reason_code))
        self.assertFalse(result.may_archive)


if __name__ == "__main__": unittest.main()
