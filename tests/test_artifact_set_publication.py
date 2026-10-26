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

    def test_invalid_late_artifact_basename_rejects_entire_set_before_publish(self):
        for name in ("z-invalid.", "z-invalid ", "z-invalid. "):
            payloads = {"a-valid.json": b"synthetic first", name: b"synthetic last"}
            with self.subTest(name=name), patch.object(atomic, "publish_bytes_no_overwrite") as publish:
                with self.assertRaisesRegex(ArtifactSetPublicationError, "^artifact_name_invalid$"):
                    publish_artifact_set_marker_last(str(self.root), payloads, transaction_id=self.transaction_id)
                publish.assert_not_called()
            self.assertEqual([], list(self.root.iterdir()))

    def test_invalid_marker_basename_rejects_before_any_artifact_publish(self):
        for name in ("marker.json.", "marker.json ", "marker.json. "):
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
