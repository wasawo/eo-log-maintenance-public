"""Shared Drive observations are validated once for ordered per-source results."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import unittest
from unittest.mock import patch

from Common import DriveContentComparison as check


SHA = hashlib.sha256(b"synthetic").hexdigest()
SOURCE = check.ComparisonSource("synthetic.txt", 9, SHA)
FILE = check.DriveFileObservation("synthetic-file", SOURCE.filename, 9, SHA, True)
FOLDER = "synthetic-folder"


def listing(files=(FILE,)):
    return check.collect_drive_listing((check.DriveListingPage(FOLDER, None, None, files, True),),
                                       expected_folder_id=FOLDER)


def compare(sources, before=None, after=None, **changes):
    options = dict(source_trusted=True, expected_folder_id=FOLDER)
    options.update(changes)
    return check.compare_reobserved_drive_contents(sources,
        listing() if before is None else before, listing() if after is None else after, **options)


class DriveComparisonBatchTests(unittest.TestCase):
    def assert_global_hold(self, result, reason):
        self.assertEqual(("held", reason, ()), (result.status, result.reason_code, result.results))
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)

    def test_mixed_per_source_outcomes_keep_input_order_without_success_claim(self):
        unknown = replace(FILE, file_id="synthetic-unknown", filename="unknown.txt", sha256=None)
        sources = (replace(SOURCE, filename="missing.txt"), SOURCE, replace(SOURCE, filename="unknown.txt"))
        result = compare(sources, listing((FILE, unknown)), listing((unknown, FILE)))
        self.assertEqual("compared", result.status)
        self.assertEqual(("comparison_no_match", "comparison_unique_content_match", "comparison_hash_unavailable"),
                         tuple(item.reason_code for item in result.results))
        self.assertEqual((None, FILE.file_id, None), tuple(item.candidate_file_id for item in result.results))
        for item in (result, *result.results):
            self.assertFalse(item.may_restore or item.may_report_sync_success or item.may_archive)
        with self.assertRaises(FrozenInstanceError): result.results = ()
        self.assertNotIn(FILE.file_id, repr(result))

    def test_file_validation_cost_does_not_multiply_by_source_count(self):
        files = tuple(replace(FILE, file_id="synthetic-"+str(i), filename="file-"+str(i)) for i in range(20))
        before, after = listing(files), listing(files[::-1])
        sources = tuple(check.ComparisonSource(file.filename, 9, SHA) for file in files)
        original = check._valid_drive_file
        with patch.object(check, "_valid_drive_file", wraps=original) as validate:
            result = compare(sources, before, after)
        self.assertEqual(2*len(files), validate.call_count)
        self.assertEqual(tuple(file.file_id for file in files), tuple(item.candidate_file_id for item in result.results))

    def test_invalid_source_or_changed_global_observations_return_no_partial_results(self):
        self.assert_global_hold(compare((SOURCE, None)), "comparison_source_invalid")
        self.assert_global_hold(compare([SOURCE]), "comparison_sources_invalid")
        self.assert_global_hold(compare((SOURCE,), listing(), listing(())), "comparison_listing_changed")
        for trust in (False, None, 1):
            self.assert_global_hold(compare((SOURCE,), source_trusted=trust), "comparison_source_untrusted")

    def test_download_input_failure_is_global_and_fallback_remains_exact(self):
        missing = replace(FILE, sha256=None, sha256_trusted=False)
        before = listing((missing,))
        good = check.hash_downloaded_content(FILE.file_id, (b"synthetic",), expected_size_bytes=9, download_completed=True)
        result = compare((SOURCE,), before, before, downloads=(good,))
        self.assertEqual("comparison_candidate", result.results[0].status)
        self.assert_global_hold(compare((SOURCE,), before, before, downloads=(replace(good, file_id="wrong-id"),)),
                                "comparison_download_unbound")
        self.assert_global_hold(compare((SOURCE,), before, before, downloads=(good, good)), "comparison_download_unbound")
        changed = replace(good, sha256=hashlib.sha256(b"different").hexdigest())
        held = compare((SOURCE,), before, before, downloads=(changed,))
        self.assertEqual("comparison_no_match", held.results[0].reason_code)

    def test_empty_selection_still_validates_global_inputs_and_is_not_no_work(self):
        empty = compare(())
        self.assertEqual(("compared", ()), (empty.status, empty.results))
        self.assertFalse(empty.may_report_sync_success)
        bad = replace(listing())
        object.__setattr__(bad, "enumeration_completed", False)
        self.assert_global_hold(compare((), listing(), bad), "comparison_listing_incomplete")
        self.assert_global_hold(compare((), downloads=[]), "comparison_observations_invalid")
        self.assert_global_hold(compare((), expected_folder_id="another-folder"), "comparison_folder_unconfirmed")

    def test_repeated_sources_are_not_silently_deduplicated_or_treated_as_permissions(self):
        result = compare((SOURCE, SOURCE))
        self.assertEqual(2, len(result.results))
        self.assertEqual(result.results[0], result.results[1])
        self.assertFalse(result.may_archive or result.may_restore)
        # Caller still binds distinct local paths; this does not claim origin.

    def test_multiple_candidates_and_single_api_semantics_remain_held(self):
        observed = listing((FILE, replace(FILE, file_id="synthetic-second")))
        result = compare((SOURCE,), observed, observed)
        single = check.compare_reobserved_drive_content(SOURCE, observed, observed,
            source_trusted=True, expected_folder_id=FOLDER)
        self.assertEqual(result.results[0], single)
        self.assertEqual("comparison_multiple_matches", single.reason_code)


if __name__ == "__main__": unittest.main()
