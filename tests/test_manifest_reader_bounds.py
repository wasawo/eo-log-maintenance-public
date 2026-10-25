"""Explicit caller byte budgets, all entries preflighted, bounded growth reads."""
from pathlib import Path
import unittest
from unittest.mock import patch

from Common import ManifestDirectoryReader as reader
import test_manifest_directory_reader as fixture


class ManifestReaderBoundsTests(unittest.TestCase):
    setUp = fixture.ManifestDirectoryReaderTests.setUp
    cleanup = fixture.ManifestDirectoryReaderTests.cleanup
    candidate = fixture.ManifestDirectoryReaderTests.candidate
    put = fixture.ManifestDirectoryReaderTests.put
    read = fixture.ManifestDirectoryReaderTests.read

    def test_explicit_size_boundary_preserves_default_selection_and_exact_bytes(self):
        candidate = self.put()
        expected = self.read()
        self.assertEqual(expected, self.read(maximum_candidate_bytes=len(candidate.content),
                                             maximum_total_bytes=len(candidate.content)))
        self.assertEqual(candidate.content, expected.content)

    def test_bad_limit_types_and_values_reject_before_directory_io(self):
        for key in ("maximum_candidate_bytes", "maximum_total_bytes"):
            for value in (True, False, 0, -1, "4096", 1.5):
                with self.subTest(key=key, value=value), patch.object(reader, "_chain") as chain:
                    with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "manifest_read_limit_invalid"):
                        self.read(**{key: value})
                    chain.assert_not_called()

    def test_oversize_old_or_foreign_period_candidate_blocks_before_any_payload_open(self):
        self.put()
        older = self.put(number=2, started="2026-10-22T10:00:00Z", target_period="2026-08")
        path = self.directory / older.filename
        large = older.content+b" "*4096
        path.write_bytes(large)
        with patch.object(Path, "open", side_effect=AssertionError("must preflight every file")) as opened:
            with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "manifest_candidate_limit_exceeded"):
                self.read(maximum_candidate_bytes=4096)
            opened.assert_not_called()
        self.assertEqual(large, path.read_bytes())

    def test_aggregate_limit_includes_all_periods_and_does_not_skip_or_fall_back(self):
        first = self.put()
        second = self.put(number=2, started="2026-10-22T10:00:00Z", target_period="2026-08")
        total = len(first.content)+len(second.content)
        self.assertEqual(first.content, self.read(maximum_total_bytes=total).content)
        with patch.object(Path, "open", side_effect=AssertionError("must fail before open")) as opened:
            with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "manifest_total_limit_exceeded"):
                self.read(maximum_total_bytes=total-1)
            opened.assert_not_called()

    def test_growth_before_open_rejects_handle_before_payload_read(self):
        candidate = self.put()
        real_open = Path.open
        class Guard:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, *_): raise AssertionError("changed handle cannot read")
        def grow(path, mode="r", *args, **kwargs):
            with real_open(path, "ab") as writer: writer.write(b" "*4096)
            return Guard(real_open(path, mode, *args, **kwargs))
        with patch.object(Path, "open", grow):
            with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "manifest_candidate_changed"):
                self.read(maximum_candidate_bytes=len(candidate.content))

    def test_growth_during_read_stops_at_initial_size_plus_one(self):
        candidate = self.put()
        path = self.directory / candidate.filename
        real_open = Path.open
        requests, consumed = [], []
        class GrowingStream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, size):
                requests.append(size)
                data = self.stream.read(size)
                consumed.append(len(data))
                if len(requests) == 1:
                    with real_open(path, "ab") as writer: writer.write(b" "*4096)
                return data
        def growing_open(target, *args, **kwargs): return GrowingStream(real_open(target, *args, **kwargs))
        with patch.object(Path, "open", growing_open):
            with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "manifest_candidate_changed"):
                self.read()
        self.assertLessEqual(sum(consumed), len(candidate.content)+1)
        self.assertTrue(all(0 < size <= min(65536, len(candidate.content)+1) for size in requests))

    def test_report_selection_forwards_limits_to_both_manifest_observations(self):
        self.put()
        selected = self.read()
        from datetime import datetime, timezone
        with patch.object(reader, "read_latest_manifest", return_value=selected) as observe, \
             patch.object(reader, "validate_referenced_artifacts", return_value={"status": "verified"}):
            result = reader.read_latest_manifest_with_report(self.root, self.root/"report.json", self.root/"contracts",
                expected_pc_id="PC-A", expected_log_type="BattleLog", expected_target_period="2026-09",
                current_utc=datetime(2026, 10, 23, 10, tzinfo=timezone.utc), current_utc_reliable=True,
                maximum_candidate_bytes=4096, maximum_total_bytes=8192)
        self.assertEqual(selected, result)
        self.assertEqual(2, observe.call_count)
        for call in observe.call_args_list:
            self.assertEqual((4096, 8192), (call.kwargs["maximum_candidate_bytes"], call.kwargs["maximum_total_bytes"]))


if __name__ == "__main__":
    unittest.main()
