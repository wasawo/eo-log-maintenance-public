"""Synthetic exact-byte checkpoint restoration, never trusted persistence."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker
from Common.CompletionWaitCheckpoint import CompletionWaitCheckpointError, read_completion_wait_checkpoint
from Common.CompletionWaitBudget import assess_completion_wait_budget, record_completion_check_attempt


SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "contracts/completion-wait-checkpoint-v1.schema.json").read_text(encoding="utf-8"))
START = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
RUN = "123e4567-e89b-42d3-a456-426614174000"


def stamp(value):
    return value.isoformat().replace("+00:00", "Z")


def checkpoint(**changes):
    value = dict(checkpoint_schema_version=1, pc_id="PC-A", log_type="BattleLog", target_period="2026-10",
                 run_id=RUN, started_at_utc=stamp(START), check_times_utc=[])
    value.update(changes)
    return value


def encode(value):
    return json.dumps(value, indent=2).encode()


def read(value, **changes):
    args = dict(schema=SCHEMA, expected_log_type="BattleLog", expected_target_period="2026-10",
                expected_run_id=RUN, current_utc=START + timedelta(days=2), current_utc_reliable=True)
    args.update(changes)
    return read_completion_wait_checkpoint(encode(value), **args)


class CompletionWaitCheckpointTests(unittest.TestCase):
    def test_schema_and_both_scopes_without_extra_period_year_limits(self):
        Draft202012Validator.check_schema(SCHEMA)
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        for log_type, period in (("BattleLog", "0000-01"), ("ErrorReport", "0000")):
            value = checkpoint(log_type=log_type, target_period=period)
            validator.validate(value)
            self.assertEqual(period, read(value, expected_log_type=log_type, expected_target_period=period).target_period)

    def test_original_bytes_strings_history_and_frozen_result_are_preserved(self):
        value = checkpoint(started_at_utc="2026-11-01T12:00:00.0000000000000Z",
                           check_times_utc=["2026-11-01T12:00:00.1000000000000Z", "2026-11-01T13:00:00.1000000000000Z"])
        before = deepcopy((value, SCHEMA))
        record = read(value)
        self.assertEqual(encode(value), record.original_bytes)
        self.assertEqual(tuple(value["check_times_utc"]), record.check_times_utc)
        self.assertEqual(value["started_at_utc"], record.started_at_utc)
        self.assertEqual(before, (value, SCHEMA))
        self.assertEqual(100000, record.as_budget_state().check_times_utc[0].microsecond)
        with self.assertRaises(FrozenInstanceError): record.run_id = "changed"
        self.assertNotIn(RUN, repr(record))

    def test_each_required_field_missing_or_null_and_unknown_fields_reject(self):
        for name in checkpoint():
            for mode in ("missing", "null"):
                value = checkpoint()
                if mode == "missing": del value[name]
                else: value[name] = None
                with self.subTest(field=name, mode=mode), self.assertRaises(CompletionWaitCheckpointError): read(value)
        for field in ("may_archive", "next_check_at_utc", "success", "original_bytes"):
            with self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(**{field: True}))

    def test_version_scope_uuid_and_implicit_casts_reject(self):
        for value in (True, 1.0, "1", 0, 2):
            with self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(checkpoint_schema_version=value))
        for field, value in (("pc_id", "PC-B"), ("log_type", "battlelog"), ("target_period", "2026-13"),
                             ("target_period", "2026-10\n"), ("run_id", RUN + "\n"),
                             ("run_id", "123e4567-e89b-42d3-a456-426614174001")):
            with self.subTest(field=field), self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(**{field: value}))
        with self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(), expected_run_id=1)

    def test_25_attempts_and_expired_state_restore_without_a_reset(self):
        value = checkpoint(check_times_utc=[stamp(START + timedelta(hours=i)) for i in range(25)])
        record = read(value)
        state = record.as_budget_state()
        result = assess_completion_wait_budget(state, expected_log_type="BattleLog", expected_target_period="2026-10",
            expected_run_id=RUN, current_utc=START + timedelta(days=2), current_utc_reliable=True,
            logged_on=True, same_account_verified=True, own_sync_complete=True, waiting_confirmed=True)
        self.assertEqual(25, len(state.check_times_utc))
        self.assertEqual("wait_check_limit_reached", result.reason_code)
        self.assertFalse(result.may_archive)
        with self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(check_times_utc=value["check_times_utc"] + [stamp(START + timedelta(hours=25))]))

    def test_recording_is_separate_and_never_modifies_restored_bytes(self):
        record = read(checkpoint(), current_utc=START)
        state = record.as_budget_state()
        updated = record_completion_check_attempt(state, expected_log_type="BattleLog", expected_target_period="2026-10",
            expected_run_id=RUN, current_utc=START, current_utc_reliable=True, logged_on=True,
            same_account_verified=True, own_sync_complete=True, waiting_confirmed=True)
        self.assertEqual(1, len(updated.check_times_utc))
        self.assertEqual((), record.check_times_utc)
        self.assertEqual(encode(checkpoint()), record.original_bytes)

    def test_history_order_window_and_subhour_precision_are_exact(self):
        cases = (
            ["2026-11-01T11:59:59.9999999999999Z"],
            ["2026-11-02T12:00:00.0000000000001Z"],
            [stamp(START), stamp(START)],
            ["2026-11-01T12:00:00.0000000000001Z", "2026-11-01T13:00:00Z"],
            [stamp(START + timedelta(hours=2)), stamp(START + timedelta(hours=1))],
        )
        for history in cases:
            with self.subTest(history=history), self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(check_times_utc=history))
        value = checkpoint(started_at_utc="2026-11-01T12:00:00.0000000000001Z",
                           check_times_utc=["2026-11-02T12:00:00.0000000000001Z"])
        self.assertEqual(tuple(value["check_times_utc"]), read(value).check_times_utc)

    def test_non_microsecond_precision_is_kept_but_not_rounded_into_budget(self):
        value = checkpoint(check_times_utc=["2026-11-01T12:00:00.0000001Z"])
        record = read(value)
        self.assertEqual(tuple(value["check_times_utc"]), record.check_times_utc)
        with self.assertRaisesRegex(CompletionWaitCheckpointError, "checkpoint_precision_not_supported"):
            record.as_budget_state()

    def test_current_clock_must_be_reliable_utc_and_not_behind_history(self):
        for changes in ({"current_utc_reliable": False}, {"current_utc_reliable": 1},
                        {"current_utc": START.replace(tzinfo=None)},
                        {"current_utc": START.astimezone(timezone(timedelta(hours=9)))},
                        {"current_utc": START - timedelta(microseconds=1)}):
            with self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(), **changes)
        with self.assertRaises(CompletionWaitCheckpointError):
            read(checkpoint(check_times_utc=["2026-11-01T12:00:00.0000001Z"]), current_utc=START)

    def test_bad_dates_offsets_and_overflow_do_not_fall_back(self):
        for value in ("2026-02-30T12:00:00Z", "2026-11-01T12:00:00+00:00", "2026-11-01T12:00:00", "bad"):
            with self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(started_at_utc=value))
        with self.assertRaises(CompletionWaitCheckpointError):
            read(checkpoint(started_at_utc="9999-12-31T23:59:59Z"), current_utc=datetime.max.replace(tzinfo=timezone.utc))

    def test_raw_input_failures_and_unavailable_data_never_create_empty_state(self):
        bad = (None, b"", b"\xff", b"\xef\xbb\xbf{}", b"null", b'{"run_id":"private-secret","run_id":"duplicate"}',
               b'{"x":NaN}', b'{"x":1e999}', "not bytes")
        for raw in bad:
            with self.assertRaises(CompletionWaitCheckpointError) as caught:
                read_completion_wait_checkpoint(raw, schema=SCHEMA, expected_log_type="BattleLog", expected_target_period="2026-10",
                    expected_run_id=RUN, current_utc=START, current_utc_reliable=True)
            self.assertNotIn("private-secret", str(caught.exception))
            self.assertTrue(caught.exception.__suppress_context__)

    def test_reader_has_no_io_or_remote_schema_retrieval(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")), \
             patch("pathlib.Path.open", side_effect=AssertionError("unexpected_io")):
            self.assertEqual(encode(checkpoint()), read(checkpoint()).original_bytes)
            schema = deepcopy(SCHEMA)
            schema["$ref"] = "https://synthetic.invalid/not-loaded"
            with self.assertRaises(CompletionWaitCheckpointError): read(checkpoint(), schema=schema)


if __name__ == "__main__": unittest.main()
