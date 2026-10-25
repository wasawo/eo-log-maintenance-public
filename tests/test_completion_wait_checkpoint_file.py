"""Existing-file metadata/handle/bounded read observations in self-owned temp."""
from dataclasses import FrozenInstanceError
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from Common import CompletionWaitCheckpoint as check
import test_initial_source_integration as temp_fixture
from test_completion_wait_checkpoint import checkpoint, encode
from test_completion_wait_attempt import read_context
from test_completion_wait_checkpoint import START


class CompletionCheckpointFileTests(unittest.TestCase):
    setUp = temp_fixture.InitialSourceIntegrationTests.setUp
    cleanup = temp_fixture.InitialSourceIntegrationTests.cleanup

    def seed(self):
        path = self.root / "checkpoint.json"
        raw = encode(checkpoint())
        path.write_bytes(raw)
        return path, raw

    def observe(self, path, *, limit=4096, **changes):
        options = read_context(START)
        options.update(changes)
        return check.observe_completion_wait_checkpoint_file(path, maximum_bytes=limit, **options)

    def test_exact_bytes_and_limit_boundary_immutable_non_authorizing_result(self):
        path, raw = self.seed()
        result = self.observe(path, limit=len(raw))
        self.assertEqual(raw, result.checkpoint.original_bytes)
        self.assertEqual(raw, path.read_bytes())
        self.assertFalse(result.may_check or result.may_archive or result.may_change_state)
        self.assertNotIn(str(path), repr(result))
        with self.assertRaises(FrozenInstanceError): result.status = "trusted"

    def test_bad_limit_relative_path_and_oversize_stop_before_payload_open(self):
        path, raw = self.seed()
        with patch.object(Path, "open", side_effect=AssertionError("payload must not open")) as opened:
            for limit in (True, 0, -1, "4096", len(raw)-1):
                with self.assertRaises(check.CompletionWaitCheckpointError): self.observe(path, limit=limit)
            with self.assertRaises(check.CompletionWaitCheckpointError): self.observe("relative.json")
            opened.assert_not_called()

    def test_missing_directory_and_hardlink_never_created_repaired_or_deleted(self):
        missing = self.root / "missing" / "checkpoint.json"
        with self.assertRaises(check.CompletionWaitCheckpointError): self.observe(missing)
        self.assertFalse(missing.parent.exists())
        with self.assertRaises(check.CompletionWaitCheckpointError): self.observe(self.source)
        path, raw = self.seed()
        alias = self.root / "alias.json"
        os.link(path, alias)
        with self.assertRaises(check.CompletionWaitCheckpointError): self.observe(path)
        self.assertEqual(raw, alias.read_bytes())

    def test_schema_and_scope_errors_preserve_existing_bytes_without_fallback(self):
        path, raw = self.seed()
        with self.assertRaises(check.CompletionWaitCheckpointError): self.observe(path, expected_run_id="other")
        self.assertEqual(raw, path.read_bytes())
        path.write_bytes(b"{}")
        with self.assertRaises(check.CompletionWaitCheckpointError): self.observe(path)
        self.assertEqual(b"{}", path.read_bytes())

    def test_change_during_schema_validation_is_detected_after_payload_read(self):
        path, _ = self.seed()
        real = check.read_completion_wait_checkpoint
        def changed(raw, **options):
            record = real(raw, **options)
            path.write_bytes(b"synthetic changed checkpoint")
            return record
        with patch.object(check, "read_completion_wait_checkpoint", side_effect=changed):
            with self.assertRaisesRegex(check.CompletionWaitCheckpointError, "checkpoint_file_changed"):
                self.observe(path)
        self.assertEqual(b"synthetic changed checkpoint", path.read_bytes())

    def test_growth_before_open_rejects_handle_without_reading_payload(self):
        path, _ = self.seed()
        real_open = Path.open
        class StreamGuard:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, *_): raise AssertionError("changed handle must not read")
        def changed_open(target, mode="r", *args, **kwargs):
            with real_open(target, "wb") as writer: writer.write(b"grown" * 1000)
            return StreamGuard(real_open(target, mode, *args, **kwargs))
        with patch.object(Path, "open", changed_open):
            with self.assertRaisesRegex(check.CompletionWaitCheckpointError, "checkpoint_file_changed"):
                self.observe(path)
        self.assertEqual(b"grown"*1000, path.read_bytes())

    def test_reparse_ancestor_change_and_native_failure_are_sanitized(self):
        path, raw = self.seed()
        with patch.object(check, "_is_link_or_reparse", return_value=True):
            with self.assertRaisesRegex(check.CompletionWaitCheckpointError, "checkpoint_file_not_regular"):
                self.observe(path)
        with patch.object(check, "_chain", side_effect=[("before",), ("after",)]):
            with self.assertRaisesRegex(check.CompletionWaitCheckpointError, "checkpoint_file_changed"):
                self.observe(path)
        with patch.object(check.os, "fstat", side_effect=OSError("synthetic private detail")):
            with self.assertRaisesRegex(check.CompletionWaitCheckpointError, "^checkpoint_file_observation_unavailable$"):
                self.observe(path)
        self.assertEqual(raw, path.read_bytes())

    def test_repeated_calls_reopen_file_and_do_not_accept_observations_as_paths(self):
        path, _ = self.seed()
        previous = self.observe(path)
        with self.assertRaises(check.CompletionWaitCheckpointError): self.observe(previous)
        path.write_bytes(b"not JSON")
        with self.assertRaises(check.CompletionWaitCheckpointError): self.observe(path)


if __name__ == "__main__":
    unittest.main()
