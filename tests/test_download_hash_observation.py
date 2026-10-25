"""Synthetic streaming bytes -> download hash -> OSD-01 comparison, no API."""
import hashlib
import unittest
from unittest.mock import patch

from Common.DriveContentComparison import (
    ComparisonSource, DriveFileObservation, DownloadObservationError,
    hash_downloaded_content, compare_drive_content,
)


class DownloadHashObservationTests(unittest.TestCase):
    def observe(self, chunks, size, **changes):
        options = dict(expected_size_bytes=size, download_completed=True)
        options.update(changes)
        return hash_downloaded_content("synthetic-file", chunks, **options)

    def compare(self, data, observations, **changes):
        source = ComparisonSource("synthetic.txt", len(data), hashlib.sha256(data).hexdigest())
        files = (DriveFileObservation("synthetic-file", source.filename, len(data), None),)
        options = dict(source_trusted=True, expected_folder_id="synthetic-folder",
            observed_folder_id="synthetic-folder", enumeration_completed=True, downloads=observations)
        options.update(changes)
        return compare_drive_content(source, files, **options)

    def test_exact_bytes_and_hash_are_independent_of_chunk_boundaries(self):
        for data in (b"", b"synthetic\x00\xff", b"x" * (1024 * 1024 + 1)):
            for width in (1, 4096, 1024 * 1024):
                with self.subTest(size=len(data), width=width):
                    chunks = (data[i:i+width] for i in range(0, len(data), width))
                    with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
                        observed = self.observe(chunks, len(data))
                    self.assertEqual(("synthetic-file", len(data), hashlib.sha256(data).hexdigest()),
                        (observed.file_id, observed.size_bytes, observed.sha256))
                    self.assertNotIn("synthetic-file", repr(observed))
                    result = self.compare(data, (observed,))
                    self.assertEqual("comparison_candidate", result.status)
                    self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)

    def test_completion_and_context_are_checked_before_consuming(self):
        def forbidden():
            raise AssertionError("must not consume")
            yield b"unreachable"
        for flag in (False, None, 1, "true"):
            with self.assertRaisesRegex(DownloadObservationError, "download_completion_unconfirmed"):
                self.observe(forbidden(), 1, download_completed=flag)
        for size in (-1, True, 1.0, None):
            with self.assertRaisesRegex(DownloadObservationError, "download_context_invalid"):
                self.observe(forbidden(), size)
        for identity in (None, "", 1, "bad\x00id"):
            with self.assertRaisesRegex(DownloadObservationError, "download_context_invalid"):
                hash_downloaded_content(identity, forbidden(), expected_size_bytes=1, download_completed=True)

    def test_oversize_stops_without_consuming_the_rest(self):
        def oversized():
            yield b"too large"
            raise AssertionError("must stop after excess bytes")
        with self.assertRaisesRegex(DownloadObservationError, "^download_size_mismatch$"):
            self.observe(oversized(), 1)
        with self.assertRaisesRegex(DownloadObservationError, "^download_size_mismatch$"):
            self.observe((b"x",), 0)

    def test_truncated_payload_never_returns_an_observation(self):
        for chunks in ((), (b"part",)):
            with self.assertRaisesRegex(DownloadObservationError, "^download_size_mismatch$"):
                self.observe(chunks, 9)

    def test_stream_failure_even_after_expected_bytes_is_sanitized(self):
        for first in (b"part", b"complete!"):
            for failure in (OSError, DownloadObservationError):
                def failed():
                    yield first
                    raise failure("synthetic-private-detail")
                with self.assertRaisesRegex(DownloadObservationError, "^download_read_failed$") as caught:
                    self.observe(failed(), 9)
                self.assertIsNone(caught.exception.__cause__)
                self.assertNotIn("synthetic-private-detail", str(caught.exception))
        self.assertEqual("held", self.compare(b"complete!", ()).status)

    def test_invalid_containers_and_chunks_are_not_coerced(self):
        for chunks in (b"x", bytearray(b"x"), "x"):
            with self.assertRaisesRegex(DownloadObservationError, "download_chunks_invalid"):
                self.observe(chunks, 1)
        for chunk in (b"", bytearray(b"x"), memoryview(b"x"), "x", 1, None):
            with self.assertRaisesRegex(DownloadObservationError, "download_chunk_invalid"):
                self.observe((chunk,), 1)
        with self.assertRaisesRegex(DownloadObservationError, "download_read_failed"):
            self.observe(None, 0)

    def test_actual_download_hash_mismatch_remains_held(self):
        observed = self.observe((b"different",), 9)
        result = self.compare(b"synthetic", (observed,))
        self.assertEqual(("held", "comparison_no_match", None),
            (result.status, result.reason_code, result.candidate_file_id))
        self.assertFalse(result.may_restore or result.may_report_sync_success or result.may_archive)

    def test_read_does_not_close_or_retry_caller_owned_stream(self):
        events = []
        def chunks():
            events.append("start")
            try:
                yield b"x"
                yield b"y"
            finally:
                events.append("closed")
        stream = chunks()
        with self.assertRaisesRegex(DownloadObservationError, "download_size_mismatch"):
            self.observe(stream, 0)
        self.assertEqual(["start"], events)
        stream.close()
        self.assertEqual(["start", "closed"], events)


if __name__ == "__main__": unittest.main()
