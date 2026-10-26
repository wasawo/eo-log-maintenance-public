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


def invalid_comparison_batches(results):
    base = check.ContentComparisonBatch("compared", "synthetic", results)
    yield None
    yield {}
    yield replace(base, results=list(results))
    yield replace(base, status="success")
    yield replace(base, reason_code="")
    yield replace(base, reason_code=1)
    yield replace(base, status="held")
    yield replace(base, results=(object(),)*len(results))
    for flag in ("may_restore", "may_report_sync_success", "may_archive"):
        for value in (True, 0, None):
            batch = replace(base)
            object.__setattr__(batch, flag, value)
            yield batch
            item = replace(results[0])
            object.__setattr__(item, flag, value)
            yield replace(base, results=(item, *results[1:]))
    for changes in (dict(status="success"), dict(reason_code=""), dict(reason_code=1),
            dict(candidate_file_id=None), dict(candidate_file_id=""), dict(candidate_file_id=1),
            dict(candidate_file_id="bad\x00id"), dict(status="held")):
        yield replace(base, results=(replace(results[0], **changes), *results[1:]))


def listing(files=(FILE,)):
    return check.collect_drive_listing((check.DriveListingPage(FOLDER, None, None, files, True),),
                                       expected_folder_id=FOLDER)


def compare(sources, before=None, after=None, **changes):
    options = dict(source_trusted=True, expected_folder_id=FOLDER)
    options.update(changes)
    return check.compare_reobserved_drive_contents(sources,
        listing() if before is None else before, listing() if after is None else after, **options)


class DriveComparisonBatchTests(unittest.TestCase):
    def test_repeated_values_compare_once_while_preserving_all_ordered_slots(self):
        unique = (SOURCE, replace(SOURCE, size_bytes=10), replace(SOURCE, sha256="0"*64),
                  replace(SOURCE, filename="missing.txt"))
        sources = unique * 100
        observed = listing()
        expected = tuple(check.compare_drive_content(source, observed.files, source_trusted=True,
            expected_folder_id=FOLDER, observed_folder_id=FOLDER, enumeration_completed=True) for source in unique)
        with patch.object(check, "_compare_source", wraps=check._compare_source) as compared:
            result = compare(sources, observed, observed)
        self.assertEqual(expected * 100, result.results)
        self.assertEqual(len(unique), compared.call_count)
        for item in (result, *result.results):
            self.assertFalse(item.may_restore or item.may_report_sync_success or item.may_archive)

    def test_reuse_never_survives_an_invocation_or_skips_download_validation(self):
        observed = listing((replace(FILE, sha256=None, sha256_trusted=False),))
        good = check.hash_downloaded_content(FILE.file_id, (b"synthetic",), expected_size_bytes=9,
            download_completed=True)
        sources = (SOURCE,) * 10
        first = compare(sources, observed, observed, downloads=(good,))
        different = replace(good, sha256="0"*64)
        second = compare(sources, observed, observed, downloads=(different,))
        self.assertEqual(("comparison_unique_content_match",) * 10, tuple(x.reason_code for x in first.results))
        self.assertEqual(("comparison_no_match",) * 10, tuple(x.reason_code for x in second.results))
        with patch.object(check, "_compare_source") as compared:
            invalid = compare(sources, observed, observed, downloads=(good, good))
            self.assert_global_hold(invalid, "comparison_download_unbound")
            compared.assert_not_called()

    def test_internal_batch_validator_rejects_malformed_outputs_and_retains_valid_states(self):
        candidate = check.ContentComparison("comparison_candidate", "synthetic", FILE.file_id)
        held = check.ContentComparison("held", "synthetic")
        for batch in invalid_comparison_batches((candidate, candidate)):
            self.assertFalse(check._valid_comparison_batch(batch))
        for batch in (check.ContentComparisonBatch("compared", "synthetic", (candidate, held)),
                check.ContentComparisonBatch("compared", "synthetic"),
                check.ContentComparisonBatch("held", "synthetic")):
            self.assertTrue(check._valid_comparison_batch(batch))

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
