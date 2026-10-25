"""Native isolated staging evidence; no SDK, production root or runtime layout."""
import hashlib
import os
import unittest

from Common.DriveContentComparison import (
    ComparisonSource, DriveFileObservation, DriveListingPage, DownloadRequirement,
    DownloadObservationError, collect_drive_listing, plan_content_downloads, compare_planned_drive_contents,
)
from download_staging_fixture import DownloadStagingFixture, StagingFixtureError


@unittest.skipUnless(os.name == "nt", "real Windows owned mutex fixture required")
class DownloadStagingIntegrationTests(unittest.TestCase):
    def make(self):
        value = DownloadStagingFixture()
        self.addCleanup(value.close)
        return value

    def assert_released(self, value):
        self.assertFalse((value.root/"owner.json").exists())

    def test_fresh_exact_staging_hashes_connect_to_plan_and_comparison(self):
        for data in (b"", b"synthetic", b"x"*(1024*1024+1)):
            with self.subTest(size=len(data)):
                value = self.make()
                source = ComparisonSource("synthetic.txt", len(data), hashlib.sha256(data).hexdigest())
                file = DriveFileObservation("synthetic-file", source.filename, len(data), None)
                def listing():
                    return collect_drive_listing((DriveListingPage("synthetic-folder", None, None, (file,), True),),
                        expected_folder_id="synthetic-folder")
                before = listing()
                plan = plan_content_downloads((source,), before, source_trusted=True, expected_folder_id="synthetic-folder")
                chunks = (data[i:i+4096] for i in range(0, len(data), 4096))
                observed = value.download(plan.requirements[0], chunks)
                result = compare_planned_drive_contents((source,), before, listing(), plan,
                    source_trusted=True, expected_folder_id="synthetic-folder", downloads=(observed,))
                self.assertEqual("comparison_candidate", result.results[0].status)
                self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)
                self.assertEqual(data, value.attempts[0].read_bytes())
                self.assert_released(value)

    def test_interrupted_attempt_is_preserved_and_retry_gets_a_fresh_file(self):
        value = self.make()
        requirement = DownloadRequirement("synthetic-file", 9)
        def interrupted():
            yield b"part"
            raise OSError("synthetic-private-detail")
        with self.assertRaisesRegex(StagingFixtureError, "^fixture_download_interrupted$") as caught:
            value.download(requirement, interrupted())
        self.assertNotIn("synthetic-private-detail", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        old = value.attempts[0]
        self.assertEqual(b"part", old.read_bytes())
        self.assert_released(value)
        observed = value.download(requirement, (b"synthetic",))
        self.assertNotEqual(old, value.attempts[1])
        self.assertEqual(b"part", old.read_bytes())
        self.assertEqual(9, observed.size_bytes)
        self.assert_released(value)

    def test_existing_destination_is_never_overwritten(self):
        value = self.make()
        with self.assertRaisesRegex(StagingFixtureError, "fixture_download_interrupted"):
            value.download(DownloadRequirement("synthetic-file", 9), (b"synthetic",),
                before_create=lambda path: path.write_bytes(b"occupied"))
        self.assertEqual(b"occupied", value.attempts[0].read_bytes())
        self.assert_released(value)

    def test_short_overlong_invalid_and_unconfirmed_downloads_return_no_hash(self):
        value = self.make()
        requirement = DownloadRequirement("synthetic-file", 9)
        for chunks, completed, error in (((b"short",), True, DownloadObservationError),
                                        ((b"too much content",), True, StagingFixtureError),
                                        ((b"",), True, StagingFixtureError),
                                        ((b"synthetic",), False, DownloadObservationError)):
            with self.subTest(completed=completed, error=error), self.assertRaises(error):
                value.download(requirement, chunks, download_completed=completed)
            self.assert_released(value)
        self.assertEqual(4, len({path.parent for path in value.attempts}))
        self.assertEqual(b"short", value.attempts[0].read_bytes())
        self.assertEqual(b"synthetic", value.attempts[-1].read_bytes())

    def test_staging_mutation_before_readback_is_rejected_and_preserved(self):
        value = self.make()
        with self.assertRaisesRegex(StagingFixtureError, "fixture_staging_changed"):
            value.download(DownloadRequirement("synthetic-file", 9), (b"synthetic",),
                before_verify=lambda path: path.write_bytes(b"changed-size"))
        self.assertEqual(b"changed-size", value.attempts[0].read_bytes())
        self.assert_released(value)

    def test_root_or_requirement_unknown_stops_before_allocating_staging(self):
        value = self.make()
        with self.assertRaisesRegex(StagingFixtureError, "fixture_requirement_invalid"):
            value.download(DownloadRequirement("synthetic-file", True), ())
        marker = value.root/".fixture-owner"
        original = marker.read_bytes()
        try:
            marker.write_bytes(b"changed")
            with self.assertRaisesRegex(StagingFixtureError, "fixture_root_changed"):
                value.download(DownloadRequirement("synthetic-file", 0), ())
        finally:
            marker.write_bytes(original)
        self.assertEqual([], value.attempts)


if __name__ == "__main__": unittest.main()
