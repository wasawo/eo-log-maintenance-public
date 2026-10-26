"""Exact planned download completion, not a plan or hash-based authorization."""
from dataclasses import replace
import hashlib
import unittest

from Common import DriveContentComparison as check


DATA = b"synthetic"
SHA = hashlib.sha256(DATA).hexdigest()
SOURCE = check.ComparisonSource("synthetic.txt", 9, SHA)
FILE = check.DriveFileObservation("synthetic-file", SOURCE.filename, 9, None)
FOLDER = "synthetic-folder"


def listing(files=(FILE,)):
    return check.collect_drive_listing((check.DriveListingPage(FOLDER, None, None, files, True),), expected_folder_id=FOLDER)


def planned(sources=(SOURCE,), observed=None):
    return check.plan_content_downloads(sources, listing() if observed is None else observed,
                                       source_trusted=True, expected_folder_id=FOLDER)


def downloaded(identity=FILE.file_id, payload=DATA):
    return check.hash_downloaded_content(identity, (payload,), expected_size_bytes=len(payload), download_completed=True)


def compare(plan=None, downloads=None, **changes):
    options = dict(source_trusted=True, expected_folder_id=FOLDER)
    options.update(changes)
    sources = options.pop("sources", (SOURCE,))
    before = options.pop("before", listing())
    after = options.pop("after", listing())
    return check.compare_planned_drive_contents(sources, before, after,
        planned(sources, before) if plan is None else plan,
        downloads=(downloaded(),) if downloads is None else downloads, **options)


class PlannedDriveComparisonTests(unittest.TestCase):
    def test_plan_output_budgets_are_reapplied_before_completed_set_comparison(self):
        self.assertEqual(compare(), compare(maximum_downloads=1, maximum_total_download_bytes=9))
        self.assert_held(compare(maximum_total_download_bytes=8), "comparison_download_bytes_limit_exceeded")
        observed = listing((FILE, replace(FILE, file_id="synthetic-second")))
        self.assert_held(compare(before=observed, after=observed, maximum_downloads=1),
            "comparison_download_count_limit_exceeded")

    def test_invalid_output_budgets_hold_without_partial_comparison(self):
        for key in ("maximum_downloads", "maximum_total_download_bytes"):
            for value in (True, False, 0, -1, 1.5, "100"):
                with self.subTest(key=key, value=value):
                    self.assert_held(compare(**{key: value}), "comparison_download_limit_invalid")

    def assert_held(self, result, reason):
        self.assertEqual(("held", reason, ()), (result.status, result.reason_code, result.results))
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)

    def test_complete_exact_set_compares_and_incorrect_hash_remains_held(self):
        good = compare()
        self.assertEqual("comparison_candidate", good.results[0].status)
        self.assertFalse(good.may_restore or good.may_report_sync_success or good.may_archive)
        bad = compare(downloads=(downloaded(payload=b"different"),))
        self.assertEqual("comparison_no_match", bad.results[0].reason_code)
        self.assertFalse(bad.may_report_sync_success)

    def test_missing_extra_duplicate_and_wrong_size_downloads_return_no_partial_results(self):
        self.assert_held(compare(downloads=()), "comparison_download_set_mismatch")
        self.assert_held(compare(downloads=(downloaded(), downloaded())), "comparison_download_unbound")
        self.assert_held(compare(downloads=(downloaded(identity="another-id"),)), "comparison_download_unbound")
        self.assert_held(compare(downloads=(replace(downloaded(), size_bytes=8),)), "comparison_download_size_mismatch")
        extra = replace(FILE, file_id="synthetic-other", filename="other.txt")
        observed = listing((FILE, extra))
        self.assert_held(compare(before=observed, after=observed,
            downloads=(downloaded(), downloaded(identity=extra.file_id))), "comparison_download_set_mismatch")

    def test_one_missing_from_multiple_requirements_blocks_all_comparison_results(self):
        second = replace(FILE, file_id="synthetic-second")
        observed = listing((FILE, second))
        plan = planned(observed=observed)
        self.assert_held(compare(plan, before=observed, after=observed), "comparison_download_set_mismatch")
        full = compare(plan, (downloaded(), downloaded(identity=second.file_id)), before=observed, after=observed)
        self.assertEqual("comparison_multiple_matches", full.results[0].reason_code)

    def test_modified_plan_status_requirements_flags_and_foreign_type_are_rejected(self):
        original = planned()
        for bad in ({}, replace(original, status="comparison_inputs_available"),
                    replace(original, requirements=()), replace(original, reason_code="other"),
                    replace(original, requirements=(check.DownloadRequirement(FILE.file_id, 8),)),
                    replace(original, requirements=(check.DownloadRequirement(FILE.file_id, True),)),
                    replace(original, requirements=list(original.requirements))):
            result = compare(bad)
            self.assertEqual(("held", ()), (result.status, result.results))
        for flag in ("may_download", "may_restore", "may_report_sync_success", "may_archive"):
            bad = replace(original)
            object.__setattr__(bad, flag, 1)
            self.assert_held(compare(bad), "comparison_download_plan_invalid")

    def test_source_context_and_listing_changes_are_rechecked(self):
        original = planned()
        other = replace(SOURCE, filename="another.txt")
        self.assert_held(compare(original, sources=(other,)), "comparison_download_plan_changed")
        self.assert_held(compare(original, after=listing(())), "comparison_listing_changed")
        self.assert_held(compare(original, source_trusted=False), "comparison_source_untrusted")
        self.assert_held(compare(original, expected_folder_id="another-folder"), "comparison_folder_unconfirmed")

    def test_no_download_required_still_compares_and_rejects_unplanned_hashes(self):
        known = replace(FILE, sha256=SHA, sha256_trusted=True)
        observed = listing((known,))
        ready = planned(observed=observed)
        result = compare(ready, (), before=observed, after=observed)
        self.assertEqual("comparison_candidate", result.results[0].status)
        self.assert_held(compare(ready, before=observed, after=observed), "comparison_download_set_mismatch")
        empty = listing(())
        result = compare(planned((), empty), (), sources=(), before=empty, after=empty)
        self.assertEqual(("compared", ()), (result.status, result.results))
        self.assertFalse(result.may_report_sync_success)

    def test_stored_plan_and_observations_cannot_become_receipts(self):
        saved = planned()
        first = compare(saved)
        self.assertEqual(first, compare(saved))
        self.assertFalse(first.may_restore or first.may_archive or first.may_report_sync_success)


if __name__ == "__main__": unittest.main()
