"""Filesystem-backed synthetic tests for marker-last artifact-set publication."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import multiprocessing

from Common import AtomicArtifactPublication as atomic
from Common.ArtifactSetPublication import (
    ArtifactSetPublicationError,
    publish_artifact_set_marker_last,
)
from Common.ArtifactSetRecovery import classify_artifact_set
from Common.ArtifactSetDirectoryVerification import verify_published_artifact_set




def _cross_process_publish(destination, report_payload, barrier, result_queue):
    payloads = {
        "manifest.json": b'{"status":"success"}\n',
        "report.json": report_payload,
    }
    try:
        barrier.wait(timeout=15)
        publish_artifact_set_marker_last(
            destination, payloads,
            transaction_id="123e4567-e89b-42d3-a456-426614174000",
        )
        result_queue.put("success")
    except ArtifactSetPublicationError as exc:
        result_queue.put(f"error:{exc.reason_code}")
    except Exception as exc:
        result_queue.put(f"unexpected:{type(exc).__name__}")


class ArtifactSetPublicationTests(unittest.TestCase):
    def test_valid_basename_grammar_roundtrips_through_marker_and_directory_verification(self):
        payloads = {"報告 e\u0301.json": b"synthetic first", "many.parts.json": b"synthetic second",
                    "internal space.json": b"synthetic third"}
        marker_name = "完了 marker.json"
        before = dict(payloads)
        result = publish_artifact_set_marker_last(str(self.root), payloads,
            transaction_id=self.transaction_id, commit_marker_name=marker_name)
        self.assertEqual(set(payloads) | {marker_name}, set(result))
        expected = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}
        decision = verify_published_artifact_set(self.root, expected,
            expected_transaction_id=self.transaction_id, commit_marker_name=marker_name)
        self.assertTrue(decision.may_report_committed)
        self.assertEqual(before, payloads)
        self.assertEqual(set(payloads) | {marker_name}, {p.name for p in self.root.iterdir()})
        for name, content in payloads.items(): self.assertEqual(content, (self.root / name).read_bytes())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payloads = {
            "manifest.json": b'{"status":"success"}\n',
            "report.json": b'{"items":2}\n',
        }
        self.transaction_id = "123e4567-e89b-42d3-a456-426614174000"

    def expected_hashes(self):
        return {name: hashlib.sha256(data).hexdigest() for name, data in self.payloads.items()}

    def test_bytes_subclass_payloads_are_snapshotted_before_hashing_and_publication(self):
        from Common import ArtifactSetPublication as publication
        class Payload(bytes):
            def __len__(self): return 0
            def __getitem__(self, key): raise AssertionError("must not call subclass slice")
            def __bytes__(self): raise AssertionError("must not call subclass conversion")
        supplied = {name: Payload(data) for name, data in self.payloads.items()}
        real_digest = publication._digest
        def digest(data):
            self.assertIs(type(data), bytes)
            return real_digest(data)
        with patch.object(publication, "_digest", side_effect=digest):
            publish_artifact_set_marker_last(str(self.root), supplied, transaction_id=self.transaction_id)
        self.assertTrue(verify_published_artifact_set(self.root, self.expected_hashes(),
            expected_transaction_id=self.transaction_id).may_report_committed)
        for name, data in self.payloads.items():
            self.assertEqual(data, (self.root/name).read_bytes())
            self.assertIs(type(supplied[name]), Payload)

    def test_bytes_subclass_cannot_mark_a_conflicting_first_artifact_idempotent(self):
        class Payload(bytes):
            def __getitem__(self, key): return b"spoofed!"[key]
        supplied = {"manifest.json": Payload(b"original"), "report.json": b"synthetic later"}
        (self.root/"manifest.json").write_bytes(b"spoofed!")
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        with self.assertRaisesRegex(ArtifactSetPublicationError, "^destination_conflict$"):
            publish_artifact_set_marker_last(str(self.root), supplied, transaction_id=self.transaction_id)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_short_write_and_close_failure_propagate_primary_reason_without_marker(self):
        real_fdopen = atomic.os.fdopen
        calls = []
        class Stream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args):
                self.stream.close()
                raise OSError("synthetic private close detail")
            def write(self, block): return self.stream.write(block[:2])
        def opened(*args, **kwargs):
            stream = real_fdopen(*args, **kwargs)
            calls.append(True)
            return Stream(stream) if len(calls) == 2 else stream
        with patch.object(atomic.os, "fdopen", opened):
            with self.assertRaisesRegex(ArtifactSetPublicationError, "^artifact_write_incomplete$"):
                publish_artifact_set_marker_last(str(self.root), self.payloads, transaction_id=self.transaction_id)
        self.assertEqual(self.payloads["manifest.json"], (self.root/"manifest.json").read_bytes())
        self.assertFalse((self.root/"report.json").exists())
        self.assertFalse((self.root/"commit-marker.json").exists())
        temporary = list(self.root.glob(".report.json.tmp-*"))
        self.assertEqual(1, len(temporary))
        self.assertEqual(self.payloads["report.json"][:2], temporary[0].read_bytes())

    def test_mapping_copy_failures_reject_before_publication_without_private_details(self):
        from collections.abc import Mapping
        class BrokenMap(Mapping):
            def __init__(self, phase): self.phase = phase
            def __len__(self):
                if self.phase == "length": raise RuntimeError("synthetic private length detail")
                return 2
            def __iter__(self):
                if self.phase == "iteration": raise RuntimeError("synthetic private iteration detail")
                yield "a-valid.json"
                if self.phase == "partial": raise RuntimeError("synthetic private partial detail")
                yield "z-valid.json"
            def __getitem__(self, key):
                if self.phase == "item": raise RuntimeError("synthetic private item detail")
                return b"synthetic"
        for phase in ("iteration", "partial", "item"):
            with self.subTest(phase=phase), patch.object(atomic, "publish_bytes_no_overwrite") as publish:
                with self.assertRaisesRegex(ArtifactSetPublicationError, "^artifact_set_empty_or_invalid$"):
                    publish_artifact_set_marker_last(str(self.root), BrokenMap(phase), transaction_id=self.transaction_id)
                publish.assert_not_called()
            self.assertEqual([], list(self.root.iterdir()))
        # dict copies this Mapping from its keys/items without consulting len;
        # an unreliable length declaration must not replace actual contents.
        publish_artifact_set_marker_last(str(self.root), BrokenMap("length"), transaction_id=self.transaction_id)
        expected = {name: hashlib.sha256(b"synthetic").hexdigest() for name in ("a-valid.json", "z-valid.json")}
        self.assertTrue(verify_published_artifact_set(self.root, expected,
            expected_transaction_id=self.transaction_id).may_report_committed)

    def test_empty_snapshot_cannot_become_an_empty_commit_marker(self):
        from collections.abc import Mapping
        class EmptyMap(Mapping):
            def __len__(self): return 1  # Caller declaration is not the copied content.
            def __iter__(self): return iter(())
            def __getitem__(self, key): raise KeyError(key)
        with patch.object(atomic, "publish_bytes_no_overwrite") as publish:
            with self.assertRaisesRegex(ArtifactSetPublicationError, "^artifact_set_empty_or_invalid$"):
                publish_artifact_set_marker_last(str(self.root), EmptyMap(), transaction_id=self.transaction_id)
            publish.assert_not_called()
        self.assertEqual([], list(self.root.iterdir()))

    def test_source_mapping_mutation_during_first_publish_does_not_change_payloads_or_marker(self):
        original = dict(self.payloads)
        expected = self.expected_hashes()
        real_publish = atomic.publish_bytes_no_overwrite
        calls = []
        def changed(destination, data):
            calls.append(Path(destination).name)
            self.payloads.clear()
            self.payloads["unexpected.json"] = b"synthetic mutation"
            return real_publish(destination, data)
        with patch.object(atomic, "publish_bytes_no_overwrite", side_effect=changed):
            publish_artifact_set_marker_last(str(self.root), self.payloads, transaction_id=self.transaction_id)
        self.assertEqual(["manifest.json", "report.json", "commit-marker.json"], calls)
        for name, data in original.items(): self.assertEqual(data, (self.root/name).read_bytes())
        self.assertFalse((self.root/"unexpected.json").exists())
        self.assertTrue(verify_published_artifact_set(self.root, expected,
            expected_transaction_id=self.transaction_id).may_report_committed)

    def test_mapping_copy_failure_preserves_existing_partial_set(self):
        from collections.abc import Mapping
        class BrokenMap(Mapping):
            def __len__(self): return 1
            def __iter__(self): raise RuntimeError("synthetic private detail")
            def __getitem__(self, key): raise KeyError(key)
        (self.root/"manifest.json").write_bytes(b"synthetic prior")
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        with self.assertRaisesRegex(ArtifactSetPublicationError, "^artifact_set_empty_or_invalid$"):
            publish_artifact_set_marker_last(str(self.root), BrokenMap(), transaction_id=self.transaction_id)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_second_artifact_short_write_preserves_first_and_never_publishes_marker(self):
        real_fdopen = atomic.os.fdopen
        opened_count = []
        class Stream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): return self.stream.__exit__(*args)
            def write(self, block): return self.stream.write(block[:2])
        def opened(*args, **kwargs):
            stream = real_fdopen(*args, **kwargs)
            opened_count.append(True)
            return Stream(stream) if len(opened_count) == 2 else stream
        with patch.object(atomic.os, "fdopen", opened):
            with self.assertRaisesRegex(ArtifactSetPublicationError, "^artifact_write_incomplete$"):
                publish_artifact_set_marker_last(str(self.root), self.payloads, transaction_id=self.transaction_id)
        self.assertEqual(2, len(opened_count))
        self.assertEqual(self.payloads["manifest.json"], (self.root/"manifest.json").read_bytes())
        self.assertFalse((self.root/"report.json").exists())
        self.assertFalse((self.root/"commit-marker.json").exists())
        temporary = list(self.root.glob(".report.json.tmp-*"))
        self.assertEqual(1, len(temporary))
        self.assertEqual(self.payloads["report.json"][:2], temporary[0].read_bytes())

    def test_invalid_late_artifact_basename_rejects_entire_set_before_publish(self):
        for name in ("z-invalid.", "z-invalid ", "z-invalid. ", "", ".", "..", ".hidden",
                     "nested/file", "nested\\file", "bad\x00name", None, 1):
            payloads = {"a-valid.json": b"synthetic first", name: b"synthetic last"}
            with self.subTest(name=name), patch.object(atomic, "publish_bytes_no_overwrite") as publish:
                with self.assertRaisesRegex(ArtifactSetPublicationError, "^artifact_name_invalid$"):
                    publish_artifact_set_marker_last(str(self.root), payloads, transaction_id=self.transaction_id)
                publish.assert_not_called()
            self.assertEqual([], list(self.root.iterdir()))

    def test_invalid_marker_basename_rejects_before_any_artifact_publish(self):
        for name in ("marker.json.", "marker.json ", "marker.json. ", "", ".", "..", ".hidden",
                     "nested/file", "nested\\file", "bad\x00name", None, 1):
            with self.subTest(name=name), patch.object(atomic, "publish_bytes_no_overwrite") as publish:
                with self.assertRaisesRegex(ArtifactSetPublicationError, "^commit_marker_name_invalid$"):
                    publish_artifact_set_marker_last(str(self.root), self.payloads,
                        transaction_id=self.transaction_id, commit_marker_name=name)
                publish.assert_not_called()
            self.assertEqual([], list(self.root.iterdir()))

    def test_invalid_names_preserve_existing_partial_set(self):
        (self.root/"a-valid.json").write_bytes(b"synthetic prior")
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        for payloads, marker in (({"a-valid.json": b"synthetic prior", "z-invalid.": b"invalid"}, "marker.json"),
                ({"a-valid.json": b"synthetic prior"}, "marker.json ")):
            with self.assertRaises(ArtifactSetPublicationError):
                publish_artifact_set_marker_last(str(self.root), payloads,
                    transaction_id=self.transaction_id, commit_marker_name=marker)
            self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_invalid_transaction_grammar_rejects_before_any_publication(self):
        for transaction in (None, True, 1, b"uuid", [], "", "bad",
                "00000000-0000-0000-0000-000000000000",
                "123e4567-e89b-02d3-a456-426614174000",
                "123e4567-e89b-92d3-a456-426614174000",
                "123e4567-e89b-42d3-7456-426614174000",
                "123e4567-e89b-42d3-c456-426614174000",
                "{123e4567-e89b-42d3-a456-426614174000}",
                "123e4567e89b42d3a456426614174000",
                "123e4567-e89b-42d3-a456-426614174000\n"):
            with self.subTest(transaction=transaction), patch.object(atomic, "publish_bytes_no_overwrite") as publish:
                with self.assertRaisesRegex(ArtifactSetPublicationError, "^transaction_id_invalid$"):
                    publish_artifact_set_marker_last(str(self.root), self.payloads, transaction_id=transaction)
                publish.assert_not_called()
            self.assertEqual([], list(self.root.iterdir()))

    def test_all_supported_versions_variants_and_case_roundtrip_through_directory_reader(self):
        for version in "12345678":
            for variant in "89ab":
                for upper in (False, True):
                    transaction = f"123e4567-e89b-{version}2d3-{variant}456-426614174000"
                    if upper: transaction = transaction.upper()
                    directory = self.root/f"v{version}-{variant}-{upper}"
                    directory.mkdir()
                    with self.subTest(version=version, variant=variant, upper=upper):
                        publish_artifact_set_marker_last(str(directory), self.payloads, transaction_id=transaction)
                        marker = json.loads((directory/"commit-marker.json").read_bytes())
                        self.assertEqual(transaction, marker["transaction_id"])
                        result = verify_published_artifact_set(directory, self.expected_hashes(),
                            expected_transaction_id=transaction)
                        self.assertTrue(result.may_report_committed)

    def test_invalid_transaction_preserves_existing_partial_set(self):
        existing = self.root/"manifest.json"
        existing.write_bytes(b"synthetic prior")
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        with self.assertRaisesRegex(ArtifactSetPublicationError, "^transaction_id_invalid$"):
            publish_artifact_set_marker_last(str(self.root), self.payloads,
                transaction_id="00000000-0000-0000-0000-000000000000")
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_marker_is_published_last_and_set_is_classifiable_as_committed(self):
        outcomes = publish_artifact_set_marker_last(
            str(self.root), self.payloads, transaction_id=self.transaction_id
        )
        self.assertEqual(set(outcomes), {"manifest.json", "report.json", "commit-marker.json"})
        marker_path = self.root / "commit-marker.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        published = {
            name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
            for name in self.payloads
        }
        result = classify_artifact_set(
            expected_sha256=self.expected_hashes(),
            published_sha256=published,
            staged_sha256={},
            commit_marker=marker,
        )
        self.assertEqual(result.state, "committed")
        self.assertTrue(result.may_report_committed)

    def test_injected_crash_after_first_artifact_leaves_no_marker_and_retry_recovers(self):
        real_publish = atomic.publish_bytes_no_overwrite
        calls = 0

        def injected(destination, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise atomic.ArtifactPublicationError("injected_crash")
            return real_publish(destination, data)

        with patch("Common.ArtifactSetPublication.atomic.publish_bytes_no_overwrite", side_effect=injected):
            with self.assertRaisesRegex(ArtifactSetPublicationError, "injected_crash"):
                publish_artifact_set_marker_last(
                    str(self.root), self.payloads, transaction_id=self.transaction_id
                )

        self.assertEqual(len([p for p in self.root.iterdir() if p.is_file()]), 1)
        self.assertFalse((self.root / "commit-marker.json").exists())
        first = next(p for p in self.root.iterdir() if p.is_file())
        self.assertIn(first.name, self.payloads)

        # A retry is idempotent for the already-published identical artifact.
        publish_artifact_set_marker_last(
            str(self.root), self.payloads, transaction_id=self.transaction_id
        )
        self.assertTrue((self.root / "commit-marker.json").is_file())
        self.assertEqual((self.root / first.name).read_bytes(), self.payloads[first.name])

    def test_conflicting_existing_artifact_is_not_overwritten_or_marked_committed(self):
        (self.root / "manifest.json").write_bytes(b'{"status":"running"}\n')
        with self.assertRaises(ArtifactSetPublicationError):
            publish_artifact_set_marker_last(
                str(self.root), self.payloads, transaction_id=self.transaction_id
            )
        self.assertEqual((self.root / "manifest.json").read_bytes(), b'{"status":"running"}\n')
        self.assertFalse((self.root / "commit-marker.json").exists())

    def test_invalid_transaction_and_marker_name_fail_before_publication(self):
        with self.assertRaisesRegex(ArtifactSetPublicationError, "transaction_id_invalid"):
            publish_artifact_set_marker_last(
                str(self.root), self.payloads, transaction_id="not-a-uuid"
            )
        with self.assertRaisesRegex(ArtifactSetPublicationError, "commit_marker_name_invalid"):
            publish_artifact_set_marker_last(
                str(self.root), self.payloads, transaction_id=self.transaction_id,
                commit_marker_name="../commit.json",
            )
        self.assertEqual(list(self.root.iterdir()), [])


    def test_cross_process_conflicting_publishers_commit_only_the_winning_set(self):
        context = multiprocessing.get_context("spawn")
        barrier = context.Barrier(2)
        results = context.Queue()
        variants = [b'{"items":2}\n', b'{"items":999}\n']
        processes = [
            context.Process(
                target=_cross_process_publish,
                args=(str(self.root), payload, barrier, results),
            )
            for payload in variants
        ]
        try:
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=30)
            self.assertTrue(all(not process.is_alive() for process in processes))
            self.assertEqual([process.exitcode for process in processes], [0, 0])
            outcomes = [results.get(timeout=5) for _ in processes]
            self.assertEqual(outcomes.count("success"), 1, outcomes)
            self.assertEqual(outcomes.count("error:destination_conflict"), 1, outcomes)

            marker = json.loads((self.root / "commit-marker.json").read_text(encoding="utf-8"))
            winner_report = (self.root / "report.json").read_bytes()
            self.assertIn(winner_report, variants)
            expected = {
                "manifest.json": hashlib.sha256(b'{"status":"success"}\n').hexdigest(),
                "report.json": hashlib.sha256(winner_report).hexdigest(),
            }
            published = {
                name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
                for name in expected
            }
            result = classify_artifact_set(
                expected_sha256=expected,
                published_sha256=published,
                staged_sha256={},
                commit_marker=marker,
            )
            self.assertEqual(result.state, "committed")
            self.assertTrue(result.may_report_committed)
            self.assertEqual(
                {p.name for p in self.root.iterdir()},
                {"manifest.json", "report.json", "commit-marker.json"},
            )
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)

    def test_concurrent_identical_publishers_are_idempotent(self):
        results = []
        failures = []

        def run():
            try:
                results.append(publish_artifact_set_marker_last(
                    str(self.root), self.payloads, transaction_id=self.transaction_id
                ))
            except Exception as exc:  # capture thread result for assertion
                failures.append(exc)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(failures, [])
        self.assertEqual(len(results), 2)
        for name, data in self.payloads.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        self.assertTrue((self.root / "commit-marker.json").is_file())


if __name__ == "__main__":
    unittest.main()
