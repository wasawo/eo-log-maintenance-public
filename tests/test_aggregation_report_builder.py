"""Synthetic T-01--12 derivation evidence, not runtime authorization."""
import copy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

from Common.AggregationReportBuilder import AggregationBuildError, build_aggregation_report
from Common.RunInputEvidenceIntegrity import compute_evidence_digest
from Common.SourceInventoryEvidenceBuilder import build_run_input_evidence
from Common.validate_aggregation_artifacts import validate_referenced_artifacts
from test_run_input_evidence_integrity import evidence, manifest, legacy_float_digest


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {name: json.loads((ROOT / "contracts" / filename).read_text(encoding="utf-8"))
           for name, filename in (
               ("manifest_schema", "manifest-v1.schema.json"),
               ("evidence_schema", "run-input-evidence-v1.schema.json"),
               ("report_schema", "aggregation-report-v1.schema.json"))}
NOW = datetime(2026, 10, 21, 0, 0, 3, tzinfo=timezone.utc)


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def fixture(outcomes=(), *, errors=(), enumeration="completed", ineligible=0,
            log_type="BattleLog", validation=None):
    targets = []
    for index, (month, status) in enumerate(outcomes, 1):
        suffix = "@synthetic" if log_type == "BattleLog" else ""
        filename = f"2026{month:02d}{index:02d}_00000000{suffix}.txt"
        targets.append(dict(relative_path=filename, filename=filename, size_bytes=index,
                            expected_sha256="a" * 64))
    targets.sort(key=lambda item: item["relative_path"])
    states = {target["relative_path"]: outcome[1]
              for target, outcome in zip(sorted(targets, key=lambda t: t["size_bytes"]), outcomes)}
    e = evidence(targets, entries_observed=len(targets) + len(errors) + ineligible,
                 valid_ineligible=ineligible, invalid_relevant=len(errors), errors=errors)
    e["log_type"] = log_type
    e["validation"]["status"] = validation or "completed"
    e["enumeration"]["status"] = enumeration
    e["enumeration"]["enumeration_errors"] = int(enumeration != "completed")
    m = manifest(targets)
    m["log_type"] = log_type
    m["target_period"] = "2026-09" if log_type == "BattleLog" else "2026"
    for file in m["files"]:
        file["status"] = states[file["relative_path"]]
        if file["status"] == "verified":
            file["drive_file_id"] = "synthetic-file"
            file["verification"] = dict(status="verified", method="drive_sha256",
                                         checked_at_utc=m["finished_at_utc"], observed_sha256="a" * 64)
    verified = sum(status == "verified" for _, status in outcomes)
    unresolved = bool(errors) or any(status != "verified" for _, status in outcomes) or e["validation"]["status"] != "completed"
    m["status"] = ("failure" if enumeration != "completed" else
                   "partial_failure" if unresolved and verified else
                   "failure" if unresolved else "success")
    m["outcome"] = "no_work" if m["status"] == "success" and not targets else None
    e["integrity"]["digest"] = compute_evidence_digest(e)
    return m, e


def error(filename="unexpected.txt", code="unclassifiable_relevant_filename"):
    return dict(error_id="VAL-0001", code=code, filename=filename, relative_path=filename)


def build(m, e, **changes):
    options = dict(manifest_path="manifests/synthetic.json", evidence_path="evidence/synthetic.json",
                   current_utc=NOW, current_utc_reliable=True,
                   future_tolerance=timedelta(minutes=5), **SCHEMAS)
    options.update(changes)
    return build_aggregation_report(encode(m), encode(e), **options)


class AggregationReportBuilderTests(unittest.TestCase):
    def report(self, m, e, **options):
        raw = build(m, e, **options)
        result = json.loads(raw)
        Draft202012Validator(SCHEMAS["report_schema"], format_checker=FormatChecker()).validate(result)
        self.assertEqual(hashlib.sha256(encode(m)).hexdigest(), result["manifest_ref"]["sha256"])
        self.assertEqual(hashlib.sha256(encode(e)).hexdigest(), result["evidence_ref"]["sha256"])
        return result

    def test_approved_T01_to_T12(self):
        cases = [
            ("T01", (), {}, "success", "no_work", []),
            ("T02", ((9, "verified"),), {"enumeration": "failed"}, "failure", None, ["indeterminate"]),
            ("T03", ((8, "verified"), (9, "verified")), {}, "success", None, ["complete", "complete"]),
            ("T04", ((9, "verified"), (9, "failed")), {}, "partial_failure", None, ["incomplete"]),
            ("T05", ((9, "verified"), (9, "unknown")), {}, "partial_failure", None, ["incomplete"]),
            ("T06", ((9, "verified"),), {"errors": [error()]}, "partial_failure", None, ["complete"]),
            ("T07", ((9, "unknown"),), {"errors": [error()]}, "failure", None, ["incomplete"]),
            ("T08", ((9, "failed"),), {}, "failure", None, ["incomplete"]),
            ("T09", (), {"ineligible": 3}, "success", "no_work", []),
            ("T10", (), {"errors": [error()]}, "failure", None, []),
            ("T11", ((8, "verified"), (9, "failed")), {}, "partial_failure", None, ["complete", "incomplete"]),
            ("T12", ((9, "verified"),), {}, "success", None, ["complete"]),
        ]
        for log_type in ("BattleLog", "ErrorReport"):
            for name, outcomes, options, status, outcome, completions in cases:
                with self.subTest(case=name, log_type=log_type):
                    m, e = fixture(outcomes, log_type=log_type, **options)
                    r = self.report(m, e)
                    self.assertEqual((status, outcome), (r["run_aggregation"]["status"], r["run_aggregation"]["outcome"]))
                    self.assertEqual(completions, [p["completion"] for p in r["periods"]])
                    self.assertEqual(len(options.get("errors", [])), len(r["run_scope_errors"]))
                    if r["run_scope_errors"]:
                        self.assertIsNone(r["run_scope_errors"][0]["period"])
                        self.assertEqual([], r["run_scope_errors"][0]["affects_periods"])

    def test_related_error_is_not_dropped_or_guessed_from_code(self):
        m, e = fixture(((8, "verified"),), errors=[error("20260901_00000000@synthetic.txt", "synthetic_other_error")])
        r = self.report(m, e)
        self.assertEqual(["complete", "incomplete"], [p["completion"] for p in r["periods"]])
        self.assertEqual([0, 1], [p["relevant_error_count"] for p in r["periods"]])
        self.assertEqual([], r["run_scope_errors"])

    def test_incomplete_validation_without_accounting_is_indeterminate(self):
        m, e = fixture(((9, "verified"),), validation="incomplete")
        self.assertEqual("indeterminate", self.report(m, e)["periods"][0]["completion"])

    def test_real_source_builder_preserves_errors_without_poisoning_other_periods(self):
        for log_type in ("BattleLog", "ErrorReport"):
            with self.subTest(log_type=log_type), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                suffix = "@synthetic" if log_type == "BattleLog" else ""
                (root / f"20250901_00000000{suffix}.txt").write_bytes(b"synthetic")
                (root / "unexpected.txt").write_bytes(b"invalid-name")
                with patch("Common.SourceInventoryEvidenceBuilder.datetime", wraps=datetime) as clock:
                    clock.now.return_value = NOW
                    e = build_run_input_evidence(
                        root, root_id="source-a", relative_scope=log_type,
                        pc_id="PC-A", log_type=log_type,
                        run_id="11111111-2222-4333-8444-555555555555",
                        evidence_id="synthetic-evidence", reference_date=date(2026, 10, 21),
                        started_at=NOW - timedelta(seconds=3))
                m = manifest(e["inventory"]["targets"])
                m.update(log_type=log_type, target_period="2026-09" if log_type == "BattleLog" else "2026",
                         status="partial_failure")
                for file in m["files"]:
                    file.update(status="verified", drive_file_id="synthetic-file")
                    file["verification"].update(status="verified", method="download_sha256",
                                               checked_at_utc=m["finished_at_utc"],
                                               observed_sha256=file["sha256"])
                before = copy.deepcopy(e)
                r = self.report(m, e)
                self.assertTrue(r["run_aggregation"]["validation_complete"])
                self.assertEqual("partial_failure", r["run_aggregation"]["status"])
                self.assertEqual("complete", r["periods"][0]["completion"])
                self.assertEqual(1, len(r["run_scope_errors"]))
                self.assertEqual(1, e["validation"]["invalid_relevant_count"])
                self.assertEqual(before, e)

    def test_g1_later_finish_and_equal_instant_preserve_original_spelling(self):
        cases = (
            ("01Z", "02Z", "02Z"),
            ("02Z", "01Z", "02Z"),
            ("01Z", "01.00000000000Z", "01Z"),
            ("01.00000000000Z", "01Z", "01.00000000000Z"),
            ("01.12345678900Z", "01.12345678901Z", "01.12345678901Z"),
            ("01.12345678901Z", "01.12345678900Z", "01.12345678901Z"),
        )
        for mf, ef, expected in cases:
            with self.subTest(manifest=mf, evidence=ef):
                m, e = fixture()
                m["finished_at_utc"] = "2026-10-21T00:00:" + mf
                e["enumeration"]["finished_at_utc"] = "2026-10-21T00:00:" + ef
                e["integrity"]["digest"] = compute_evidence_digest(e)
                expected = "2026-10-21T00:00:" + expected
                self.assertEqual(expected, self.report(m, e)["generated_at_utc"])
                self.assertEqual(build(m, e), build(m, e, generated_at_utc=expected))

    def test_g1_missing_invalid_or_reversed_input_times_are_rejected(self):
        for artifact in ("manifest", "evidence"):
            for invalid in (None, "2026-10-20T23:59:59Z", "not-a-time"):
                with self.subTest(artifact=artifact, value=invalid):
                    m, e = fixture()
                    node = m if artifact == "manifest" else e["enumeration"]
                    node["finished_at_utc"] = invalid
                    e["integrity"]["digest"] = compute_evidence_digest(e)
                    with self.assertRaises(AggregationBuildError): build(m, e)

    def test_exact_bytes_determinism_input_immutability_and_no_io(self):
        m, e = fixture(((9, "verified"),))
        before = copy.deepcopy((m, e, SCHEMAS))
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")), patch("pathlib.Path.open", side_effect=AssertionError("unexpected_io")):
            first, second = build(m, e), build(m, e)
        self.assertEqual(first, second)
        self.assertEqual(before, (m, e, SCHEMAS))
        self.assertTrue(first.endswith(b"\n"))
        self.assertEqual(first, build(m, e, current_utc=NOW + timedelta(days=30)))
        with self.assertRaisesRegex(AggregationBuildError, 'generated_timestamp_mismatch'):
            build(m, e, generated_at_utc="2026-10-21T00:00:03Z")

    def test_exact_noncanonical_input_bytes_are_hashed(self):
        m, e = fixture()
        original = encode(m)
        spaced = json.dumps(m, indent=2).encode()
        with patch("test_aggregation_report_builder.encode", side_effect=[spaced, encode(e)]):
            result = json.loads(build(m, e))
        self.assertEqual(hashlib.sha256(spaced).hexdigest(), result["manifest_ref"]["sha256"])
        self.assertNotEqual(hashlib.sha256(original).hexdigest(), result["manifest_ref"]["sha256"])

    def test_integer_count_is_derived_without_rewriting_input(self):
        m, e = fixture(((9, "verified"),))
        original = encode(e)
        r = self.report(m, e)
        self.assertIs(type(r["inventory_ref"]["eligible_target_count"]), int)
        self.assertEqual(1, r["inventory_ref"]["eligible_target_count"])
        self.assertEqual(original, encode(e))
        self.assertEqual(hashlib.sha256(original).hexdigest(), r["evidence_ref"]["sha256"])

    def test_schema_integer_float_count_and_old_digest_are_rejected(self):
        m, e = fixture(((9, "verified"),))
        e["enumeration"]["eligible_target_count"] = 1.0
        e["integrity"]["digest"] = legacy_float_digest(e)
        original = encode(e)
        Draft202012Validator(SCHEMAS["evidence_schema"]).validate(e)
        with self.assertRaises(AggregationBuildError): build(m, e)
        self.assertEqual(original, encode(e))

    def test_raw_evidence_float_tokens_never_produce_report(self):
        m, e = fixture()
        for token in ("1.0", "-0.0", "1e0", "1.25", "NaN", "Infinity", "-Infinity"):
            field = "evidence_schema_version" if token not in ("-0.0",) else "eligible_target_count"
            parsed = copy.deepcopy(e)
            node = parsed if field == "evidence_schema_version" else parsed["enumeration"]
            node[field] = json.loads(token)
            if token not in ("NaN", "Infinity", "-Infinity"):
                parsed["integrity"]["digest"] = legacy_float_digest(parsed)
            raw = encode(parsed)
            if token == "1e0":
                raw = raw.replace(b'"evidence_schema_version":1.0', b'"evidence_schema_version":1e0')
            with self.subTest(token=token):
                with patch("test_aggregation_report_builder.encode", side_effect=[encode(m), raw]):
                    with self.assertRaises(AggregationBuildError): build(m, parsed)

    def test_rejects_identity_inventory_count_digest_and_bool_corruption(self):
        for case in ("identity", "inventory", "count", "digest", "bool"):
            with self.subTest(case=case):
                m, e = fixture(((9, "verified"),))
                if case == "identity": m["run_id"] = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
                if case == "inventory": m["files"][0]["size_bytes"] += 1
                if case == "count": e["enumeration"]["entries_observed"] += 1
                if case == "digest": e["integrity"]["digest"] = "b" * 64
                if case == "bool": e["evidence_schema_version"] = True
                if case != "digest": e["integrity"]["digest"] = compute_evidence_digest(e)
                with self.assertRaises(AggregationBuildError): build(m, e)

    def test_verified_claims_require_hash_method_status_and_time(self):
        for case in ("hash", "method", "status", "time"):
            with self.subTest(case=case):
                m, e = fixture(((9, "verified"),))
                file = m["files"][0]
                if case == "hash": file["verification"]["observed_sha256"] = "b" * 64
                if case == "method": file["verification"]["method"] = "not_performed"
                if case == "status": file["verification"]["status"] = "mismatch"
                if case == "time": file["verification"]["checked_at_utc"] = "2026-10-21T00:00:02Z"
                with self.assertRaises(AggregationBuildError): build(m, e)

    def test_nullable_drive_identity_and_incomplete_validation_errors(self):
        m, e = fixture(((9, "verified"),))
        m["files"][0]["drive_file_id"] = None
        self.assertEqual(1, self.report(m, e)["run_aggregation"]["verified_count"])
        m, e = fixture(((9, "verified"),), errors=[error()], validation="incomplete")
        r = self.report(m, e)
        self.assertEqual("indeterminate", r["periods"][0]["completion"])
        self.assertEqual(1, len(r["run_scope_errors"]))

    def test_verification_terminal_mapping_is_checked_without_mutation(self):
        for verification_status, file_status in (("mismatch", "failed"), ("unavailable", "unknown"),
                                                 ("ambiguous", "unknown"), ("failed", "unknown")):
            with self.subTest(verification_status=verification_status):
                m, e = fixture(((9, file_status),))
                v = m["files"][0]["verification"]
                v.update(status=verification_status, checked_at_utc=m["finished_at_utc"])
                if verification_status == "mismatch":
                    v.update(method="download_sha256", observed_sha256="b" * 64)
                before = copy.deepcopy(m)
                self.assertEqual("failure", self.report(m, e)["run_aggregation"]["status"])
                self.assertEqual(before, m)
                m["files"][0]["status"] = "unknown" if file_status == "failed" else "failed"
                with self.assertRaises(AggregationBuildError): build(m, e)

    def test_manifest_and_file_nonterminal_or_aggregate_mismatch_are_rejected(self):
        for case in ("running", "pending", "staging", "status", "outcome"):
            with self.subTest(case=case):
                m, e = fixture(((9, "verified"),))
                if case == "running": m.update(status="running", finished_at_utc=None)
                elif case in ("pending", "staging"): m["files"][0]["status"] = case
                elif case == "status": m["status"] = "partial_failure"
                else: m["outcome"] = "no_work"
                with self.assertRaises(AggregationBuildError): build(m, e)

    def test_strict_json_duplicate_constant_bom_and_sanitized_errors(self):
        m, e = fixture()
        for raw in (b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}',
                    b'{"x":Infinity}', b'{"x":1e999}', b'\xef\xbb\xbf{}', b'not-json-private-token'):
            with self.subTest(raw=raw):
                with patch("test_aggregation_report_builder.encode", side_effect=[raw, encode(e)]):
                    with self.assertRaises(AggregationBuildError) as caught: build(m, e)
                self.assertNotIn("private-token", str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def test_explicit_clock_precision_future_and_order(self):
        m, e = fixture()
        m["finished_at_utc"] = "2026-10-21T00:00:01.12345678901Z"
        for stamp, accepted in (("2026-10-21T00:00:01.12345678901Z", True),
                                ("2026-10-21T00:00:01.12345678900Z", False)):
            if accepted:
                self.assertEqual(stamp, self.report(m, e, generated_at_utc=stamp)["generated_at_utc"])
            else:
                with self.assertRaises(AggregationBuildError): build(m, e, generated_at_utc=stamp)
        for changes in (dict(current_utc_reliable=False), dict(current_utc=None),
                        dict(generated_at_utc="2026-10-21T00:05:03.00000000001Z"),
                        dict(future_tolerance=timedelta(seconds=-1)),
                        dict(future_tolerance=timedelta(minutes=5, microseconds=1)),
                        dict(future_tolerance=True), dict(future_tolerance=float("nan"))):
            with self.assertRaises(AggregationBuildError): build(m, e, **changes)
        m["finished_at_utc"] = "2026-10-21T00:05:03Z"
        self.report(m, e)
        m["finished_at_utc"] = "2026-10-21T00:05:03.00000000001Z"
        with self.assertRaisesRegex(AggregationBuildError, 'timestamp_in_future'):
            build(m, e)
        m["finished_at_utc"] = "2026-10-21T00:00:01Z"
        self.report(m, e, current_utc=NOW + timedelta(days=30))

    def test_empty_failed_enumeration_and_unaccounted_target_never_become_no_work(self):
        m, e = fixture(enumeration="failed")
        r = self.report(m, e)
        self.assertEqual([], r["periods"])
        self.assertEqual(("failure", None), (r["run_aggregation"]["status"], r["run_aggregation"]["outcome"]))
        m, e = fixture(((9, "verified"),))
        m["files"].clear()
        with self.assertRaises(AggregationBuildError): build(m, e)

    def test_error_scope_identity_and_inventory_digest_are_not_guessed(self):
        m, e = fixture(errors=[error()])
        e["validation"]["errors"][0]["relative_path"] = "different.txt"
        e["integrity"]["digest"] = compute_evidence_digest(e)
        with self.assertRaises(AggregationBuildError): build(m, e)
        m, e = fixture(((9, "verified"),))
        e["enumeration"]["inventory_sha256"] = "c" * 64
        e["integrity"]["digest"] = compute_evidence_digest(e)
        with self.assertRaises(AggregationBuildError): build(m, e)

    def test_remote_schema_resolution_and_unsafe_references_are_rejected_without_io(self):
        m, e = fixture()
        schema = copy.deepcopy(SCHEMAS["report_schema"])
        schema["$ref"] = "https://synthetic.invalid/not-loaded"
        with patch("builtins.open", side_effect=AssertionError("unexpected_io")):
            with self.assertRaises(AggregationBuildError): build(m, e, report_schema=schema)
        for path in ("../outside.json", "/root.json", "C:/dummy.json", "a//b.json", "a\\b.json"):
            with self.subTest(path=path), self.assertRaises(AggregationBuildError):
                build(m, e, manifest_path=path)

    def test_existing_referenced_artifact_validator_accepts_generated_fixture(self):
        for outcomes in ((), ((8, "verified"), (9, "unknown"))):
            m, e = fixture(outcomes)
            with tempfile.TemporaryDirectory(prefix="eo-report-builder-") as directory:
                root = Path(directory)
                (root / "manifests").mkdir()
                (root / "evidence").mkdir()
                (root / "manifests/synthetic.json").write_bytes(encode(m))
                (root / "evidence/synthetic.json").write_bytes(encode(e))
                report = root / "report.json"
                report.write_bytes(build(m, e))
                self.assertEqual("verified", validate_referenced_artifacts(root, report, ROOT / "contracts")["status"])


if __name__ == "__main__":
    unittest.main()
