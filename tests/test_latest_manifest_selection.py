"""Synthetic C4 selection: all candidates checked, no arbitrary fallback."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import traceback
import unittest
from unittest.mock import patch
from uuid import UUID

from Common.LatestManifestSelection import (
    LatestManifestSelectionError, ManifestCandidate, parse_manifest_filename, select_latest_manifest,
)


class LatestManifestSelectionTests(unittest.TestCase):
    def test_nonlocal_schema_references_are_rejected_without_retrieval(self):
        good = self.candidate()
        for keyword in ("$ref", "$dynamicRef"):
            for reference in ("https://synthetic.invalid/private-detail", "file:///synthetic-private-detail",
                    "relative-private-detail.json", "", None, 1):
                for schema in ({keyword: reference}, {"$defs": {"unused": {keyword: reference}}}):
                    with self.subTest(keyword=keyword, reference=reference), patch.object(
                            Path, "read_text", return_value=json.dumps(schema)), \
                            patch("socket.socket", side_effect=AssertionError("unexpected retrieval")) as network:
                        self.rejected("manifest_schema_unavailable", [good])
                        network.assert_not_called()

    def test_broken_local_or_invalid_schema_is_rejected_without_retrieval(self):
        good = self.candidate()
        for schema, reason in (({"$ref": "#/$defs/missing"}, "candidate_manifest_invalid"),
                ({"type": "synthetic-invalid"}, "manifest_schema_unavailable")):
            with self.subTest(schema=schema), patch.object(Path, "read_text", return_value=json.dumps(schema)), \
                    patch("socket.socket", side_effect=AssertionError("unexpected retrieval")) as network:
                self.rejected(reason, [good])
                network.assert_not_called()

    def test_bytes_subclass_decode_cannot_hide_invalid_actual_buffer(self):
        good = self.candidate()
        class Content(bytes):
            def decode(self, *args, **kwargs): return good.content.decode("utf-8")
        content = Content(b"synthetic-invalid-json")
        bad = ManifestCandidate(good.filename, content)
        self.rejected("candidate_manifest_invalid", [bad])
        self.assertIs(content, bad.content)
        self.assertEqual(b"synthetic-invalid-json", memoryview(content).tobytes())

    def test_valid_subclass_buffer_is_selected_without_custom_decode_or_conversion(self):
        good = self.candidate()
        class Content(bytes):
            def decode(self, *args, **kwargs): raise AssertionError("must parse the actual buffer")
            def __bytes__(self): raise AssertionError("must not invoke custom conversion")
            def __len__(self): return 0
        content = Content(good.content)
        candidate = ManifestCandidate(good.filename, content)
        self.assertEqual(self.select([good]), self.select([candidate]))
        self.assertIs(content, candidate.content)
        self.assertEqual(good.content, memoryview(content).tobytes())

    def test_older_subclass_buffer_is_validated_even_with_newer_success(self):
        older = self.candidate(1, started="2026-10-22T10:00:00Z")
        newer = self.candidate(2)
        class Content(bytes):
            def decode(self, *args, **kwargs): return older.content.decode("utf-8")
        invalid = ManifestCandidate(older.filename, Content(b"synthetic-invalid-json"))
        for candidates in ([invalid, newer], [newer, invalid]):
            self.rejected("candidate_manifest_invalid", candidates)

    def candidate(self, number=1, started="2026-10-23T10:00:00Z", status="success", **changes):
        manifest = {
            "schema_version": 1, "run_id": str(UUID(int=number, version=4)),
            "pc_id": "PC-A", "log_type": "BattleLog", "target_period": "2026-09",
            "status": status, "outcome": "no_work" if status == "success" else None,
            "started_at_utc": started, "finished_at_utc": None if status == "running" else started,
            "files": [],
        }
        manifest.update(changes)
        identity = {key: manifest[key] for key in ("pc_id", "log_type", "target_period", "run_id")}
        filename = "_".join(identity[field] for field in ("pc_id", "log_type", "target_period", "run_id")) + ".json"
        return ManifestCandidate(filename, json.dumps(manifest).encode("utf-8"))

    def run_id(self, candidate):
        return json.loads(candidate.content)["run_id"]

    def select(self, candidates, **changes):
        options = dict(
            expected_pc_id="PC-A", expected_log_type="BattleLog", expected_target_period="2026-09",
            enumeration_completed=True, current_utc=datetime(2026, 10, 23, 10, tzinfo=timezone.utc),
            current_utc_reliable=True,
        )
        options.update(changes)
        return select_latest_manifest(candidates, **options)

    def rejected(self, reason, candidates, **changes):
        before = deepcopy(candidates)
        with self.assertRaises(LatestManifestSelectionError) as caught:
            self.select(candidates, **changes)
        self.assertEqual(caught.exception.reason_code, reason)
        self.assertEqual(str(caught.exception), reason)
        self.assertEqual(candidates, before)

    def test_single_success_selected_without_input_mutation(self):
        candidates = [self.candidate()]
        before = deepcopy(candidates)
        result = self.select(candidates)
        self.assertEqual(result.selected_index, 0)
        self.assertEqual(result.run_id, self.run_id(candidates[0]))
        self.assertEqual(result.status, "success")
        self.assertEqual(candidates, before)

    def test_both_pc_and_log_type_scopes(self):
        for pc in ("PC-A", "PC-B"):
            for log_type, period in (("BattleLog", "2026-09"), ("ErrorReport", "2025")):
                with self.subTest(pc=pc, log_type=log_type):
                    result = self.select([self.candidate(pc_id=pc, log_type=log_type, target_period=period)],
                                         expected_pc_id=pc, expected_log_type=log_type,
                                         expected_target_period=period)
                    self.assertEqual(result.status, "success")

    def test_unique_latest_uses_start_not_run_id_or_list_order(self):
        old = self.candidate(99, "2026-10-23T09:00:00Z")
        new = self.candidate(1)
        for candidates in ([old, new], [new, old]):
            result = self.select(candidates)
            self.assertEqual(result.run_id, self.run_id(new))
            self.assertEqual(candidates[result.selected_index], new)

    def test_equal_maximum_blocks_in_both_orders(self):
        a, b = self.candidate(1), self.candidate(2)
        for candidates in ([a, b], [b, a]):
            self.rejected("latest_manifest_ambiguous", candidates)

    def test_equivalent_fraction_spellings_are_a_tie(self):
        self.rejected("latest_manifest_ambiguous", [
            self.candidate(1, "2026-10-23T10:00:00.1Z"),
            self.candidate(2, "2026-10-23T10:00:00.1000000Z"),
        ])

    def test_submicrosecond_precision_is_not_truncated(self):
        old = self.candidate(2, "2026-10-23T10:00:00.1234567Z")
        new = self.candidate(1, "2026-10-23T10:00:00.1234568Z")
        self.assertEqual(self.select([new, old]).run_id, self.run_id(new))

    def test_all_newer_incomplete_states_block_without_old_success_fallback(self):
        old = self.candidate(1, "2026-10-23T09:00:00Z")
        for status in ("running", "partial_failure", "failure"):
            with self.subTest(status=status):
                self.rejected("latest_manifest_not_success", [old, self.candidate(2, status=status)])

    def test_inspection_mode_reports_latest_running_without_authorization(self):
        result = self.select([self.candidate(status="running")], require_current_success=False)
        self.assertEqual(result.status, "running")
        self.assertFalse(hasattr(result, "may_archive"))
        self.assertFalse(hasattr(result, "may_start_new_run"))

    def test_old_manifest_age_is_not_a_24_hour_expiration(self):
        self.assertEqual(self.select([self.candidate(started="2026-10-19T09:00:00Z")]).status, "success")

    def test_empty_candidate_set_blocks(self):
        self.rejected("candidate_set_empty", [])

    def test_incomplete_enumeration_including_truthy_non_boolean_blocks(self):
        for value in (False, None, 1, "true"):
            self.rejected("candidate_enumeration_incomplete", [self.candidate()], enumeration_completed=value)

    def test_unreadable_candidate_blocks_even_if_other_candidate_is_good(self):
        good = self.candidate()
        bad = ManifestCandidate(good.filename, None)
        self.rejected("candidate_read_failed", [self.candidate(2), bad])

    def test_malformed_older_candidate_also_blocks(self):
        bad = ManifestCandidate(self.candidate().filename, b"not-json")
        self.rejected("candidate_manifest_invalid", [bad, self.candidate(2)])

    def test_duplicate_manifest_keys_are_never_last_wins(self):
        good = self.candidate()
        for prefix in (b'{"status":"failure",', b'{"schema_version":1,'):
            self.rejected("candidate_manifest_invalid", [
                ManifestCandidate(good.filename, prefix + good.content[1:]),
            ])

    def test_invalid_utf8_and_wrong_root_shape_block(self):
        for raw in (b"\xff", b"[]", b"null", b"true"):
            self.rejected("candidate_manifest_invalid", [ManifestCandidate(self.candidate().filename, raw)])

    def test_unsupported_unknown_and_wrong_version_types_block(self):
        for changes in ({"schema_version": 2}, {"schema_version": True}, {"schema_version": 1.0},
                        {"unknown": True}):
            self.rejected("candidate_manifest_invalid", [self.candidate(**changes)])

    def test_filename_identity_mismatch_for_every_field(self):
        good = self.candidate()
        identity = parse_manifest_filename(good.filename)
        overrides = [
            {"pc_id": "PC-B"}, {"log_type": "ErrorReport", "target_period": "2026"},
            {"target_period": "2026-08"}, {"run_id": str(UUID(int=3, version=4))},
        ]
        for changes in overrides:
            changed = {**identity, **changes}
            name = "_".join(changed[field] for field in ("pc_id", "log_type", "target_period", "run_id")) + ".json"
            self.rejected("candidate_filename_identity_mismatch", [ManifestCandidate(name, good.content)])

    def test_malformed_filename_and_paths_block(self):
        good = self.candidate()
        values = (None, 1, {}, "bad.json", "../" + good.filename, "/absolute/" + good.filename,
                  "C:" + chr(92) + good.filename,
                  good.filename.replace("2026-09", "2026-13"),
                  good.filename.replace("BattleLog", "ErrorReport"),
                  good.filename.replace("PC-A", "PC-C"), good.filename + chr(10))
        for name in values:
            self.rejected("candidate_filename_invalid", [ManifestCandidate(name, good.content)])

    def test_wrong_scope_candidate_is_not_silently_filtered(self):
        self.rejected("candidate_scope_mismatch", [self.candidate(pc_id="PC-B"), self.candidate(2)])

    def test_conflicting_same_run_identity_blocks(self):
        self.rejected("candidate_run_identity_conflict",
                      [self.candidate(1, "2026-10-23T09:00:00Z"), self.candidate(1)])

    def test_future_start_and_finish_beyond_tolerance_block(self):
        self.rejected("candidate_timestamp_in_future", [self.candidate(started="2026-10-23T10:05:00.00000000001Z")])
        self.rejected("candidate_timestamp_in_future", [self.candidate(finished_at_utc="2026-10-23T10:05:01Z")])

    def test_exact_future_boundary_and_configurable_tolerance(self):
        self.assertEqual(self.select([self.candidate(started="2026-10-23T10:05:00Z")]).status, "success")
        self.rejected("candidate_timestamp_in_future", [self.candidate(started="2026-10-23T10:00:01Z")],
                      future_tolerance=timedelta(0))
        self.assertEqual(self.select([self.candidate(started="2026-10-23T10:06:00Z")],
                                     future_tolerance=timedelta(minutes=6)).status, "success")

    def test_finish_before_start_blocks(self):
        self.rejected("candidate_finish_before_start", [self.candidate(finished_at_utc="2026-10-23T09:59:59Z")])

    def test_non_utc_or_unknown_clock_blocks(self):
        for now in (None, datetime(2026, 10, 23),
                    datetime(2026, 10, 23, tzinfo=timezone(timedelta(hours=9)))):
            self.rejected("current_utc_unavailable", [self.candidate()], current_utc=now)
        for reliable in (False, None, 1, "true"):
            self.rejected("current_utc_unavailable", [self.candidate()], current_utc_reliable=reliable)

    def test_invalid_scope_mode_and_tolerance_block(self):
        for changes in ({"expected_pc_id": "unknown"}, {"expected_log_type": []},
                        {"expected_target_period": "2026-13"}):
            self.rejected("selection_scope_invalid", [self.candidate()], **changes)
        self.rejected("selection_mode_invalid", [self.candidate()], require_current_success=1)
        for tolerance in (True, 300, timedelta(seconds=-1)):
            self.rejected("future_tolerance_invalid", [self.candidate()], future_tolerance=tolerance)

    def test_invalid_collection_and_candidate_observations_block(self):
        for values in (None, {}, b"not a candidate collection"):
            self.rejected("candidate_collection_invalid", values)
        self.rejected("candidate_observation_invalid", [None])

    def test_missing_schema_fails_with_sanitized_reason(self):
        with patch("Common.LatestManifestSelection.Path.read_text", side_effect=OSError("private path detail")):
            self.rejected("manifest_schema_unavailable", [self.candidate()])



    def test_malformed_run_timestamps_block_without_fallback(self):
        for stamp in ("2026-10-23T10:00:00+00:00", "2026-10-23T10:00:00",
                      "2026-10-23T10:00:00z", "2026-02-30T10:00:00Z"):
            with self.subTest(stamp=stamp):
                candidates = [self.candidate(1, "2026-10-23T09:00:00Z"),
                              self.candidate(2, started=stamp)]
                before = deepcopy(candidates)
                with self.assertRaises(LatestManifestSelectionError) as caught:
                    self.select(candidates)
                self.assertIn(caught.exception.reason_code,
                              {"candidate_manifest_invalid", "candidate_timestamp_invalid"})
                self.assertEqual(candidates, before)

    def test_schema_maximum_fraction_precision_kept_exact(self):
        a = self.candidate(1, "2026-10-23T10:00:00.00000000001Z")
        b = self.candidate(2, "2026-10-23T10:00:00.00000000002Z")
        self.assertEqual(self.select([b, a]).run_id, self.run_id(b))

    def test_clock_tolerance_overflow_blocks(self):
        self.rejected("future_tolerance_invalid", [self.candidate()],
                      current_utc=datetime.max.replace(tzinfo=timezone.utc))



    def test_candidate_traceback_hides_original_validator_details(self):
        private = "synthetic-private-candidate-body"
        candidates = [self.candidate(private_detail=private)]
        try:
            self.select(candidates)
        except LatestManifestSelectionError as error:
            self.assertEqual(error.reason_code, "candidate_manifest_invalid")
            rendered = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            self.assertNotIn(private, rendered)
        else:
            self.fail("invalid candidate must be rejected")

    def test_schema_traceback_hides_original_read_error(self):
        private = "synthetic-private-schema-error"
        with patch("Common.LatestManifestSelection.Path.read_text", side_effect=OSError(private)):
            try:
                self.select([self.candidate()])
            except LatestManifestSelectionError as error:
                self.assertEqual(error.reason_code, "manifest_schema_unavailable")
                rendered = "".join(traceback.format_exception(type(error), error, error.__traceback__))
                self.assertNotIn(private, rendered)
            else:
                self.fail("schema uncertainty must block")


if __name__ == "__main__":
    unittest.main()
