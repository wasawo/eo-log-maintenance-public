"""Pure missing-hash requirements -> synthetic bytes -> strict batch comparison."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import unittest
from unittest.mock import patch

from Common import DriveContentComparison as check


DATA = b"synthetic"
SHA = hashlib.sha256(DATA).hexdigest()
SOURCE = check.ComparisonSource("synthetic.txt", len(DATA), SHA)
FILE = check.DriveFileObservation("synthetic-file", SOURCE.filename, len(DATA), None)
FOLDER = "synthetic-folder"


def listing(files=(FILE,)):
    return check.collect_drive_listing((check.DriveListingPage(FOLDER, None, None, files, True),),
                                       expected_folder_id=FOLDER)


def plan(sources=(SOURCE,), observed=None, **changes):
    options = dict(source_trusted=True, expected_folder_id=FOLDER)
    options.update(changes)
    return check.plan_content_downloads(sources, listing() if observed is None else observed, **options)


class ContentDownloadPlanTests(unittest.TestCase):
    def test_output_limits_count_unique_ids_and_exact_total_bytes(self):
        second = replace(FILE, file_id="synthetic-second")
        sources = (SOURCE, SOURCE, replace(SOURCE, sha256="0"*64))
        observed = listing((second, FILE))
        expected = plan(sources, observed)
        bounded = plan(sources, observed, maximum_downloads=2, maximum_total_download_bytes=18)
        self.assertEqual(expected, bounded)
        self.assertEqual(2, len(bounded.requirements))
        self.assert_no_authority(bounded)

    def test_invalid_limits_hold_before_listing_inspection(self):
        for key in ("maximum_downloads", "maximum_total_download_bytes"):
            for value in (True, False, 0, -1, 1.5, "100"):
                with self.subTest(key=key, value=value), patch.object(check, "_listing_snapshot") as inspect:
                    result = plan(**{key: value})
                    self.assertEqual(("held", "comparison_download_limit_invalid", ()),
                        (result.status, result.reason_code, result.requirements))
                    inspect.assert_not_called()
                    self.assert_no_authority(result)

    def test_exceeded_plan_budgets_return_no_requirement_subset_or_constructed_requirements(self):
        observed = listing((FILE, replace(FILE, file_id="synthetic-second")))
        for limits, reason in ((dict(maximum_downloads=1), "comparison_download_count_limit_exceeded"),
                (dict(maximum_total_download_bytes=17), "comparison_download_bytes_limit_exceeded")):
            with self.subTest(limits=limits), patch.object(check, "DownloadRequirement") as requirement:
                result = plan(observed=observed, **limits)
                self.assertEqual(("held", reason, ()), (result.status, result.reason_code, result.requirements))
                requirement.assert_not_called()
                self.assert_no_authority(result)

    def test_limits_preserve_no_requirement_and_unknown_metadata_boundaries(self):
        result = plan((), listing(), maximum_downloads=1, maximum_total_download_bytes=1)
        self.assertEqual(("comparison_inputs_available", ()), (result.status, result.requirements))
        self.assert_no_authority(result)
        result = plan(observed=listing((FILE, replace(FILE, file_id="synthetic-unknown", size_bytes=None))),
            maximum_downloads=1, maximum_total_download_bytes=1)
        self.assertEqual(("held", "comparison_metadata_unavailable", ()),
            (result.status, result.reason_code, result.requirements))
        self.assert_no_authority(result)

    def assert_no_authority(self, result):
        self.assertFalse(result.may_download or result.may_restore or result.may_report_sync_success or result.may_archive)

    def test_missing_untrusted_and_absent_trusted_sha_require_download(self):
        for item in (FILE, replace(FILE, sha256=SHA), replace(FILE, sha256_trusted=True)):
            result = plan(observed=listing((item,)))
            self.assertEqual("requires_download_observations", result.status)
            self.assertEqual((check.DownloadRequirement(FILE.file_id, len(DATA)),), result.requirements)
            self.assert_no_authority(result)
            self.assertNotIn(FILE.file_id, repr(result))
            with self.assertRaises(FrozenInstanceError): result.status = "success"

    def test_known_sha_name_and_size_mismatches_need_no_download_but_are_not_success(self):
        for item in (replace(FILE, sha256=SHA, sha256_trusted=True),
                     replace(FILE, sha256="0"*64, sha256_trusted=True),
                     replace(FILE, filename="other.txt"), replace(FILE, size_bytes=100)):
            result = plan(observed=listing((item,)))
            self.assertEqual(("comparison_inputs_available", ()), (result.status, result.requirements))
            self.assert_no_authority(result)
        self.assertEqual("comparison_inputs_available", plan(observed=listing(())).status)

    def test_all_uncertain_same_name_candidates_are_planned_even_with_one_known_match(self):
        trusted = replace(FILE, sha256=SHA, sha256_trusted=True)
        other = replace(FILE, file_id="synthetic-second")
        result = plan(observed=listing((trusted, other)))
        self.assertEqual((check.DownloadRequirement(other.file_id, len(DATA)),), result.requirements)

    def test_shared_ids_are_unique_and_output_is_stable_across_source_and_page_order(self):
        second = replace(FILE, file_id="synthetic-second")
        sources = (SOURCE, replace(SOURCE, sha256="0"*64), SOURCE)
        first = plan(sources, listing((second, FILE)))
        after = plan(sources[::-1], listing((FILE, second)))
        self.assertEqual(first, after)
        self.assertEqual((FILE.file_id, second.file_id), tuple(item.file_id for item in first.requirements))
        self.assertEqual(2, len(first.requirements))

    def test_unknown_metadata_or_invalid_global_context_returns_no_partial_requirements(self):
        unknown = replace(FILE, file_id="synthetic-unknown", size_bytes=None)
        held = plan(observed=listing((FILE, unknown)))
        self.assertEqual(("held", "comparison_metadata_unavailable", ()),
                         (held.status, held.reason_code, held.requirements))
        cases = (([SOURCE], listing(), {}, "comparison_sources_invalid"),
                 ((SOURCE, None), listing(), {}, "comparison_source_invalid"),
                 ((SOURCE,), listing(), {"source_trusted": 1}, "comparison_source_untrusted"),
                 ((SOURCE,), listing(), {"expected_folder_id": "another"}, "comparison_folder_unconfirmed"),
                 ((SOURCE,), replace(listing(), files=(FILE, FILE)), {}, "comparison_identity_ambiguous"))
        for sources, observed, changes, reason in cases:
            result = plan(sources, observed, **changes)
            self.assertEqual(("held", reason, ()), (result.status, result.reason_code, result.requirements))
            self.assert_no_authority(result)

    def test_empty_sources_still_check_listing_and_do_not_make_a_no_work_claim(self):
        result = plan(())
        self.assertEqual(("comparison_inputs_available", ()), (result.status, result.requirements))
        self.assert_no_authority(result)
        incomplete = replace(listing())
        object.__setattr__(incomplete, "enumeration_completed", False)
        self.assertEqual("comparison_listing_incomplete", plan((), incomplete).reason_code)

    def test_plan_download_bytes_after_listing_and_batch_comparison_connect_without_authority(self):
        before = listing()
        required = plan(observed=before)
        downloads = tuple(check.hash_downloaded_content(item.file_id, (DATA[:3], DATA[3:]),
            expected_size_bytes=item.expected_size_bytes, download_completed=True) for item in required.requirements)
        after = listing()
        compared = check.compare_reobserved_drive_contents((SOURCE,), before, after, source_trusted=True,
            expected_folder_id=FOLDER, downloads=downloads)
        self.assertEqual("comparison_candidate", compared.results[0].status)
        self.assertFalse(compared.may_restore or compared.may_report_sync_success or compared.may_archive)
        # A plan never substitutes for completed byte observations.
        missing = check.compare_reobserved_drive_contents((SOURCE,), before, after, source_trusted=True,
            expected_folder_id=FOLDER)
        self.assertEqual("comparison_hash_unavailable", missing.results[0].reason_code)
        self.assertEqual(required, plan(observed=before))


if __name__ == "__main__": unittest.main()
