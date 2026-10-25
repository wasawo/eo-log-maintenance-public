"""Approved pending phases from explicit snapshots, never real event proof."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from Common.ManifestTransitionInspection import ManifestTransitionError, inspect_manifest_history
from test_manifest_transition_inspection import snapshot, encode
from test_contract_schemas import MANIFEST_SCHEMA


def history(*values):
    return inspect_manifest_history(tuple(encode(value) for value in values), manifest_schema=MANIFEST_SCHEMA)


class ManifestHistoryTests(unittest.TestCase):
    def assert_no_authority(self, result):
        self.assertEqual("requires_runtime_evidence", result.status)
        self.assertFalse(result.may_publish or result.may_upload or result.may_retry or result.may_archive)
        self.assertNotIn("synthetic", repr(result))
        with self.assertRaises(FrozenInstanceError): result.snapshot_count = 0

    def test_full_lifecycle_preserves_bytes_and_does_no_io(self):
        values = tuple(snapshot(state) for state in ("pending", "staging", "ready", "pending", "uploaded", "verified"))
        original = deepcopy(values)
        with patch("builtins.open", side_effect=AssertionError("no I/O")):
            result = history(*values)
        self.assertEqual((6, 5, 1, 0, 0, 0, False), (result.snapshot_count, result.file_transition_count,
            result.upload_pending_transition_count, result.retry_pending_transition_count,
            result.registered_pending_file_count, result.upload_pending_file_count, result.aggregation_required))
        self.assertEqual(original, values)
        self.assert_no_authority(result)

    def test_registration_and_upload_pending_are_distinct_even_with_same_final_bytes(self):
        registered = history(snapshot())
        uploading = history(*(snapshot(state) for state in ("pending", "staging", "ready", "pending")))
        self.assertEqual((1, 0), (registered.registered_pending_file_count, registered.upload_pending_file_count))
        self.assertEqual((0, 1), (uploading.registered_pending_file_count, uploading.upload_pending_file_count))
        self.assert_no_authority(registered)
        self.assert_no_authority(uploading)

    def test_planning_pending_cannot_claim_uploaded_or_unknown(self):
        for state in ("uploaded", "unknown"):
            with self.subTest(state=state), self.assertRaisesRegex(ManifestTransitionError, "planning_pending_used_as_upload"):
                history(snapshot(), snapshot(state))
        # Confirmed source failure may stop processing before staging.
        self.assert_no_authority(history(snapshot(), snapshot("failed")))

    def test_upload_pending_cannot_restart_staging_even_though_pair_is_listed(self):
        values = [snapshot(state) for state in ("pending", "staging", "ready", "pending", "staging")]
        with self.assertRaisesRegex(ManifestTransitionError, "upload_pending_restarted_staging"):
            history(*values)

    def test_unknown_retry_pending_counts_separately_without_authorizing_retry(self):
        states = ("pending", "staging", "ready", "pending", "unknown", "pending", "uploaded", "verified")
        result = history(*(snapshot(state) for state in states))
        self.assertEqual((1, 1, 7), (result.upload_pending_transition_count,
                                    result.retry_pending_transition_count, result.file_transition_count))
        self.assert_no_authority(result)

    def test_interleaved_files_track_pending_phase_by_path_not_array_position(self):
        initial = snapshot()
        other = deepcopy(initial["files"][0])
        other["filename"] = other["relative_path"] = "20260902_00000000@synthetic.txt"
        initial["files"].append(other)
        values = [initial]
        for state in ("staging", "ready", "pending"):
            value = deepcopy(values[-1])
            next(item for item in value["files"] if item["relative_path"] == initial["files"][0]["relative_path"])["status"] = state
            value["files"].reverse()
            values.append(value)
        result = history(*values)
        self.assertEqual((1, 1), (result.registered_pending_file_count, result.upload_pending_file_count))
        invalid = deepcopy(values[-1])
        next(item for item in invalid["files"] if item["relative_path"] == other["relative_path"])["status"] = "uploaded"
        with self.assertRaisesRegex(ManifestTransitionError, "planning_pending_used_as_upload"):
            history(*values, invalid)

    def test_terminal_bytes_stay_immutable_and_aggregation_is_required_not_proven(self):
        values = [snapshot(state) for state in ("pending", "staging", "ready", "pending", "uploaded", "verified")]
        terminal = snapshot("verified", status="success")
        values.append(terminal)
        result = history(*values, terminal)
        self.assertTrue(result.aggregation_required)
        self.assertEqual(5, result.file_transition_count)
        self.assert_no_authority(result)
        raw = tuple(encode(value) for value in values)
        with self.assertRaisesRegex(ManifestTransitionError, "terminal_manifest_immutable"):
            inspect_manifest_history(raw + (raw[-1]+b"\n",), manifest_schema=MANIFEST_SCHEMA)

    def test_arbitrary_suffix_empty_and_malformed_histories_are_rejected(self):
        for values in ((), [], (None,), (encode(snapshot()), "text")):
            with self.subTest(values=values), self.assertRaises(ManifestTransitionError):
                inspect_manifest_history(values, manifest_schema=MANIFEST_SCHEMA)
        for state in ("staging", "ready", "uploaded", "verified", "unknown", "failed"):
            with self.assertRaisesRegex(ManifestTransitionError, "initial_state_invalid"):
                history(snapshot(state))

    def test_illegal_pair_identity_and_inventory_changes_are_still_rejected(self):
        for invalid in (snapshot("ready"), snapshot()):
            if invalid["files"][0]["status"] == "pending": invalid["pc_id"] = "PC-B"
            with self.assertRaises(ManifestTransitionError): history(snapshot(), invalid)
        extra = snapshot()
        extra["files"] = []
        with self.assertRaises(ManifestTransitionError): history(snapshot(), extra)

    def test_empty_inventory_and_repeated_snapshot_do_not_prove_no_work(self):
        value = snapshot()
        value["files"] = []
        result = history(value, value)
        self.assertEqual((0, 0, False), (result.registered_pending_file_count,
            result.upload_pending_file_count, result.aggregation_required))
        self.assert_no_authority(result)


if __name__ == "__main__":
    unittest.main()
