"""Source bytes must match the observed file identity, not only a restored path."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from Common import SourceInventoryEvidenceBuilder as builder
from Common.SourceInventoryEvidenceBuilder import InventoryBuildError


class SourceHashIdentityTests(unittest.TestCase):
    def test_unchanged_file_matches_hash_and_size(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.txt"
            source.write_bytes(b"original")
            self.assertEqual(builder._hash_stable_file(source),
                             (8, hashlib.sha256(b"original").hexdigest()))

    def test_actual_replacement_restored_after_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.txt"
            alternate = root / "alternate.txt"
            backup = root / "backup.txt"
            source.write_bytes(b"original")
            alternate.write_bytes(b"replaced")  # Same size and mtime, different identity.
            metadata = source.stat()
            os.utime(alternate, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            original_open = Path.open

            @contextmanager
            def swapped_open(path, *args, **kwargs):
                # Change the pathname between pre-stat and actual open, then
                # restore after close before the final path stat (an ABA race).
                if path != source:
                    with original_open(path, *args, **kwargs) as stream:
                        yield stream
                    return
                source.rename(backup)
                alternate.rename(source)
                try:
                    with original_open(source, *args, **kwargs) as stream:
                        yield stream
                finally:
                    source.rename(alternate)
                    backup.rename(source)

            with patch.object(Path, "open", swapped_open):
                with self.assertRaisesRegex(InventoryBuildError, "source_mutation_detected"):
                    builder._hash_stable_file(source)
            self.assertEqual(source.read_bytes(), b"original")
            self.assertEqual(alternate.read_bytes(), b"replaced")



    def test_mismatched_open_handle_is_rejected_before_reading_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.txt"
            alternate = Path(temp) / "alternate.txt"
            source.write_bytes(b"original")
            alternate.write_bytes(b"replaced")
            with alternate.open("rb") as backing:
                stream = MagicMock()
                stream.__enter__.return_value = stream
                stream.fileno.return_value = backing.fileno()
                with patch.object(Path, "open", return_value=stream):
                    with self.assertRaisesRegex(InventoryBuildError, "source_mutation_detected"):
                        builder._hash_stable_file(source)
                stream.read.assert_not_called()
                stream.__exit__.assert_called_once()

    def test_growth_stops_at_observed_size_plus_one_without_waiting_for_eof(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.txt"
            source.write_bytes(b"original")
            with source.open("rb") as backing:
                stream = MagicMock()
                stream.__enter__.return_value = stream
                stream.fileno.return_value = backing.fileno()
                # Simulate a source that never reaches EOF. Repeated reads
                # would grow forever; the first excess byte must stop it.
                stream.read.side_effect = lambda count: b"x" * count
                with patch.object(Path, "open", return_value=stream):
                    with self.assertRaisesRegex(InventoryBuildError, "source_mutation_detected"):
                        builder._hash_stable_file(source)
                stream.read.assert_called_once_with(9)
                stream.__exit__.assert_called_once()
            self.assertEqual(b"original", source.read_bytes())

    def test_short_read_cannot_produce_a_successful_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.txt"
            source.write_bytes(b"original")
            with source.open("rb") as backing:
                stream = MagicMock()
                stream.__enter__.return_value = stream
                stream.fileno.return_value = backing.fileno()
                stream.read.side_effect = [b"short", b""]
                with patch.object(Path, "open", return_value=stream):
                    with self.assertRaisesRegex(InventoryBuildError, "source_mutation_detected"):
                        builder._hash_stable_file(source)
                self.assertEqual([9, 4], [call.args[0] for call in stream.read.call_args_list])
                stream.__exit__.assert_called_once()

    def test_empty_and_chunk_boundary_files_keep_exact_bytes_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.txt"
            for size in (0, 1024 * 1024 - 1, 1024 * 1024, 1024 * 1024 + 1):
                with self.subTest(size=size):
                    data = b"x" * size
                    source.write_bytes(data)
                    self.assertEqual((size, hashlib.sha256(data).hexdigest()),
                                     builder._hash_stable_file(source))

    def test_opened_handle_stat_failure_is_sanitized(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.txt"
            source.write_bytes(b"original")
            with patch.object(builder.os, "fstat", side_effect=OSError("private detail")):
                with self.assertRaisesRegex(InventoryBuildError, "^source_file_unavailable$"):
                    builder._hash_stable_file(source)
            self.assertEqual(source.read_bytes(), b"original")

    def test_finished_handle_stat_failure_is_sanitized(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.txt"
            source.write_bytes(b"original")
            with source.open("rb") as stream:
                metadata = os.fstat(stream.fileno())
            with patch.object(builder.os, "fstat", side_effect=[metadata, OSError("private detail")]):
                with self.assertRaisesRegex(InventoryBuildError, "^source_file_unavailable$"):
                    builder._hash_stable_file(source)
            self.assertEqual(source.read_bytes(), b"original")

    def test_unavailable_handle_marks_inventory_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "20260901_01020304@synthetic.txt"
            source.write_bytes(b"original")
            with patch.object(builder.os, "fstat", side_effect=OSError("private detail")):
                value = builder.build_run_input_evidence(
                    root, root_id="synthetic", relative_scope="BattleLog",
                    pc_id="PC-B", log_type="BattleLog", run_id="synthetic-run",
                    reference_date=date(2026, 10, 21),
                    started_at=datetime(2026, 10, 21, tzinfo=timezone.utc),
                )
            self.assertEqual(value["enumeration"]["status"], "incomplete")
            self.assertGreater(value["enumeration"]["enumeration_errors"], 0)
            self.assertEqual(value["inventory"]["targets"], [])
            schema = json.loads((Path(__file__).resolve().parents[1] /
                                 "contracts/run-input-evidence-v1.schema.json").read_text(encoding="utf-8"))
            serialized = builder.serialize_evidence(value, schema)
            self.assertNotIn(b"private detail", serialized)
            self.assertNotIn(str(root).encode(), serialized)
            self.assertEqual(source.read_bytes(), b"original")

if __name__ == "__main__":
    unittest.main()
