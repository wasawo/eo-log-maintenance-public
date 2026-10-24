"""JSON Schema contract tests for the PowerShell/Python Drive adapter."""

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FORMAT_CHECKER = FormatChecker()


def load_schema(filename: str) -> dict:
    with (CONTRACTS / filename).open(encoding="utf-8") as stream:
        return json.load(stream)


REQUEST_SCHEMA = load_schema("drive-request.schema.json")
RESPONSE_SCHEMA = load_schema("drive-response.schema.json")
REQUEST_VALIDATOR = Draft202012Validator(REQUEST_SCHEMA, format_checker=FORMAT_CHECKER)
RESPONSE_VALIDATOR = Draft202012Validator(RESPONSE_SCHEMA, format_checker=FORMAT_CHECKER)


def request(operation: str, parameters: dict, *, dry_run: bool = True) -> dict:
    return {
        "schema_version": "1.0",
        "request_id": "8c7e5db8-08f4-4c9e-a6b2-5b45c1aaf031",
        "operation": operation,
        "dry_run": dry_run,
        "parameters": parameters,
    }


class SchemaDefinitionTests(unittest.TestCase):
    def test_request_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(REQUEST_SCHEMA)

    def test_response_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(RESPONSE_SCHEMA)


class RequestContractTests(unittest.TestCase):
    def assert_request_valid(self, instance: dict) -> None:
        errors = list(REQUEST_VALIDATOR.iter_errors(instance))
        self.assertEqual([], errors, msg="; ".join(error.message for error in errors))

    def assert_request_invalid(self, instance: dict) -> None:
        self.assertTrue(
            list(REQUEST_VALIDATOR.iter_errors(instance)),
            msg=f"Expected request to be rejected: {instance!r}",
        )

    def test_all_four_supported_operations_accept_valid_requests(self) -> None:
        cases = [
            request("list_files", {"parent_id": "folder-123"}),
            request("get_file_metadata", {"file_id": "file-123"}),
            request(
                "upload_file",
                {
                    "local_path": r"C:\logs\example.log",
                    "parent_id": "folder-123",
                    "file_name": "example.log",
                    "expected_sha256": "a" * 64,
                },
            ),
            request(
                "download_file",
                {
                    "file_id": "file-123",
                    "staging_path": r"C:\staging\example.log",
                },
            ),
        ]
        for instance in cases:
            with self.subTest(operation=instance["operation"]):
                self.assert_request_valid(instance)

    def test_dry_run_must_be_boolean_and_explicit(self) -> None:
        missing = request("get_file_metadata", {"file_id": "file-123"})
        del missing["dry_run"]
        self.assert_request_invalid(missing)
        self.assert_request_invalid(
            request("get_file_metadata", {"file_id": "file-123"}, dry_run="true")
        )

    def test_invalid_uuid_is_rejected(self) -> None:
        instance = request("get_file_metadata", {"file_id": "file-123"})
        instance["request_id"] = "not-a-uuid"
        self.assert_request_invalid(instance)

    def test_unknown_operation_including_delete_is_rejected(self) -> None:
        for operation in ("delete_file", "delete", "unknown_operation"):
            with self.subTest(operation=operation):
                self.assert_request_invalid(request(operation, {}))

    def test_operation_specific_required_parameters_are_enforced(self) -> None:
        cases = [
            request("list_files", {}),
            request("get_file_metadata", {}),
            request("upload_file", {"parent_id": "folder-123"}),
            request("download_file", {"file_id": "file-123"}),
        ]
        for instance in cases:
            with self.subTest(operation=instance["operation"]):
                self.assert_request_invalid(instance)

    def test_unknown_top_level_and_operation_parameters_are_rejected(self) -> None:
        top_level = request("get_file_metadata", {"file_id": "file-123"})
        top_level["unexpected"] = True
        self.assert_request_invalid(top_level)
        self.assert_request_invalid(
            request("get_file_metadata", {"file_id": "file-123", "overwrite": True})
        )

    def test_invalid_sha256_is_rejected(self) -> None:
        self.assert_request_invalid(
            request(
                "upload_file",
                {
                    "local_path": r"C:\logs\example.log",
                    "parent_id": "folder-123",
                    "file_name": "example.log",
                    "expected_sha256": "not-a-sha256",
                },
            )
        )


class ResponseContractTests(unittest.TestCase):
    def assert_response_valid(self, instance: dict) -> None:
        errors = list(RESPONSE_VALIDATOR.iter_errors(instance))
        self.assertEqual([], errors, msg="; ".join(error.message for error in errors))

    def assert_response_invalid(self, instance: dict) -> None:
        self.assertTrue(
            list(RESPONSE_VALIDATOR.iter_errors(instance)),
            msg=f"Expected response to be rejected: {instance!r}",
        )

    def test_success_response_is_valid(self) -> None:
        self.assert_response_valid(
            {
                "schema_version": "1.0",
                "request_id": "8c7e5db8-08f4-4c9e-a6b2-5b45c1aaf031",
                "operation": "get_file_metadata",
                "success": True,
                "result": {"file_id": "file-123"},
                "error": None,
            }
        )

    def test_failure_response_is_valid(self) -> None:
        self.assert_response_valid(
            {
                "schema_version": "1.0",
                "request_id": "8c7e5db8-08f4-4c9e-a6b2-5b45c1aaf031",
                "operation": "get_file_metadata",
                "success": False,
                "result": None,
                "error": {
                    "code": "DRIVE_PERMISSION_DENIED",
                    "message": "アクセスが拒否されました。",
                    "retryable": False,
                },
            }
        )

    def test_success_and_error_fields_must_be_consistent(self) -> None:
        self.assert_response_invalid(
            {
                "schema_version": "1.0",
                "request_id": "8c7e5db8-08f4-4c9e-a6b2-5b45c1aaf031",
                "operation": "get_file_metadata",
                "success": True,
                "result": {"file_id": "file-123"},
                "error": {
                    "code": "DRIVE_PERMISSION_DENIED",
                    "message": "アクセスが拒否されました。",
                    "retryable": False,
                },
            }
        )

    def test_fixed_error_codes_require_the_approved_retryable_value(self) -> None:
        # Independent approval table: only transient failures carry true.
        policy = {
            "INVALID_REQUEST": False,
            "AUTHENTICATION_FAILED": False,
            "DRIVE_PERMISSION_DENIED": False,
            "DRIVE_RESOURCE_NOT_FOUND": False,
            "DRIVE_TRANSIENT_FAILURE": True,
            "VERIFICATION_FAILED": False,
            "INTERNAL_ERROR": False,
            "OPERATION_TIMEOUT": False,
            "CONFLICT_OR_AMBIGUOUS": False,
        }
        for operation in ("list_files", "get_file_metadata", "upload_file", "download_file"):
            for code, flag in policy.items():
                with self.subTest(operation=operation, code=code):
                    instance = {
                        "schema_version": "1.0",
                        "request_id": "8c7e5db8-08f4-4c9e-a6b2-5b45c1aaf031",
                        "operation": operation,
                        "success": False,
                        "result": None,
                        "error": {"code": code, "message": "synthetic failure", "retryable": flag},
                    }
                    self.assert_response_valid(instance)
                    for invalid in (not flag, None, "true", "false", 0, 1, [], {}):
                        with self.subTest(retryable=invalid):
                            instance["error"]["retryable"] = invalid
                            self.assert_response_invalid(instance)
                    del instance["error"]["retryable"]
                    self.assert_response_invalid(instance)

    def test_unknown_error_code_and_extra_fields_are_rejected(self) -> None:
        invalid = {
            "schema_version": "1.0",
            "request_id": "8c7e5db8-08f4-4c9e-a6b2-5b45c1aaf031",
            "operation": "get_file_metadata",
            "success": False,
            "result": None,
            "error": {
                "code": "SOME_NEW_ERROR",
                "message": "失敗",
                "retryable": False,
            },
        }
        self.assert_response_invalid(invalid)
        invalid["error"]["code"] = "INTERNAL_ERROR"
        invalid["extra"] = "not allowed"
        self.assert_response_invalid(invalid)

    def test_invalid_uuid_and_unknown_operation_are_rejected(self) -> None:
        self.assert_response_invalid(
            {
                "schema_version": "1.0",
                "request_id": "not-a-uuid",
                "operation": "delete_file",
                "success": True,
                "result": {},
                "error": None,
            }
        )


REPORT_SCHEMA = load_schema("aggregation-report-v1.schema.json")
REPORT_VALIDATOR = Draft202012Validator(REPORT_SCHEMA, format_checker=FORMAT_CHECKER)


def aggregation_report() -> dict:
    return {
        "report_schema_version": 1,
        "run_id": "8c7e5db8-08f4-4c9e-a6b2-5b45c1aaf031",
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "manifest_ref": {
            "path": "_maintenance/manifests/PC-A/PC-A_BattleLog_run.json",
            "schema_version": 1,
            "sha256": "a" * 64,
        },
        "evidence_ref": {
            "path": "_maintenance/run-input-evidence/PC-A/run.evidence.json",
            "schema_version": 1,
            "sha256": "b" * 64,
        },
        "generated_at_utc": "2026-10-21T00:00:00Z",
        "inventory_ref": {
            "kind": "b2_run_input_evidence_inventory",
            "eligible_target_count": 2,
            "inventory_sha256": "c" * 64,
        },
        "run_aggregation": {
            "status": "partial_failure",
            "outcome": None,
            "verified_count": 1,
            "failed_count": 1,
            "unknown_count": 0,
            "run_scope_error_count": 0,
            "enumeration_complete": True,
            "validation_complete": True,
        },
        "periods": [
            {
                "period": "2026-09",
                "completion": "incomplete",
                "eligible_count": 2,
                "verified_count": 1,
                "failed_count": 1,
                "unknown_count": 0,
                "relevant_error_count": 0,
            }
        ],
        "run_scope_errors": [],
    }


class AggregationReportSchemaDefinitionTests(unittest.TestCase):
    def test_aggregation_report_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(REPORT_SCHEMA)


class AggregationReportContractTests(unittest.TestCase):
    def assert_report_valid(self, instance: dict) -> None:
        errors = list(REPORT_VALIDATOR.iter_errors(instance))
        self.assertEqual([], errors, msg="; ".join(error.message for error in errors))

    def assert_report_invalid(self, instance: dict) -> None:
        self.assertTrue(
            list(REPORT_VALIDATOR.iter_errors(instance)),
            msg=f"Expected aggregation report to be rejected: {instance!r}",
        )

    def test_valid_partial_failure_report_is_accepted(self) -> None:
        self.assert_report_valid(aggregation_report())

    def test_valid_zero_work_report_is_accepted(self) -> None:
        report = aggregation_report()
        report["inventory_ref"]["eligible_target_count"] = 0
        report["run_aggregation"].update(
            status="success",
            outcome="no_work",
            verified_count=0,
            failed_count=0,
            unknown_count=0,
        )
        report["periods"] = []
        self.assert_report_valid(report)

    def test_three_period_completion_states_are_accepted(self) -> None:
        report = aggregation_report()
        base = report["periods"][0]
        report["periods"] = [
            {**base, "period": "2026-07", "completion": "complete"},
            {**base, "period": "2026-08", "completion": "incomplete"},
            {**base, "period": "2026-09", "completion": "indeterminate"},
        ]
        self.assert_report_valid(report)

    def test_schema_version_must_be_integer_one(self) -> None:
        for value in ("1", 2, True):
            with self.subTest(value=value):
                report = aggregation_report()
                report["report_schema_version"] = value
                self.assert_report_invalid(report)

    def test_unknown_fields_and_report_id_are_rejected(self) -> None:
        for field in ("report_id", "unexpected"):
            with self.subTest(field=field):
                report = aggregation_report()
                report[field] = "not allowed"
                self.assert_report_invalid(report)

    def test_artifact_references_require_lowercase_sha256_and_safe_relative_path(self) -> None:
        invalid_cases = [
            ("sha256", "A" * 64),
            ("path", "/absolute/path.json"),
            ("path", "../outside.json"),
            ("path", "_maintenance/../outside.json"),
            ("path", r"_maintenance\outside.json"),
            ("path", "C:/absolute/path.json"),
        ]
        for field, value in invalid_cases:
            with self.subTest(field=field, value=value):
                report = aggregation_report()
                report["manifest_ref"][field] = value
                self.assert_report_invalid(report)

    def test_generated_timestamp_must_be_utc_z(self) -> None:
        for value in ("2026-10-21T00:00:00+00:00", "2026-10-21T00:00:00", "not-a-date"):
            with self.subTest(value=value):
                report = aggregation_report()
                report["generated_at_utc"] = value
                self.assert_report_invalid(report)

    def test_period_and_completion_enums_are_strict(self) -> None:
        report = aggregation_report()
        report["periods"][0]["period"] = "2026-13"
        self.assert_report_invalid(report)
        report = aggregation_report()
        report["periods"][0]["completion"] = "success"
        self.assert_report_invalid(report)

    def test_negative_counts_and_unknown_run_status_are_rejected(self) -> None:
        report = aggregation_report()
        report["run_aggregation"]["verified_count"] = -1
        self.assert_report_invalid(report)
        report = aggregation_report()
        report["run_aggregation"]["status"] = "indeterminate"
        self.assert_report_invalid(report)

    def test_run_scope_error_requires_explicit_scope_and_sanitized_shape(self) -> None:
        report = aggregation_report()
        report["run_scope_errors"] = [
            {
                "error_id": "VAL-0001",
                "code": "unclassifiable_relevant_filename",
                "filename": "unexpected-name.txt",
                "relative_path": "unexpected-name.txt",
                "period": None,
                "affects_run": True,
                "affects_periods": [],
                "message": "Filename did not match the approved period classification rule.",
            }
        ]
        self.assert_report_valid(report)
        report["run_scope_errors"][0]["extra"] = "not allowed"
        self.assert_report_invalid(report)



if __name__ == "__main__":
    unittest.main(verbosity=2)


EVIDENCE_SCHEMA = load_schema("run-input-evidence-v1.schema.json")
EVIDENCE_VALIDATOR = Draft202012Validator(EVIDENCE_SCHEMA, format_checker=FORMAT_CHECKER)


def valid_evidence() -> dict:
    digest = "a" * 64
    return {
        "evidence_schema_version": 1,
        "evidence_id": "PC-A_BattleLog_run-001",
        "run_id": "run-001",
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "source_scope": {"root_id": "battlelog-source", "relative_scope": "."},
        "enumeration": {
            "status": "completed", "started_at_utc": "2026-10-21T00:00:00Z",
            "finished_at_utc": "2026-10-21T00:00:02Z", "entries_observed": 1,
            "eligible_target_count": 1, "inventory_sha256": digest, "enumeration_errors": 0,
        },
        "validation": {
            "status": "completed", "valid_eligible_count": 1, "valid_ineligible_count": 0,
            "invalid_relevant_count": 0, "ignored_entries_count": 0, "errors": [],
        },
        "inventory": {
            "kind": "embedded",
            "targets": [{"filename": "20260930_example.txt", "relative_path": "2026/09/20260930_example.txt",
                         "size_bytes": 1234, "expected_sha256": digest}],
        },
        "integrity": {"algorithm": "sha256",
                      "canonicalization": "EO-LOG-MAINTENANCE-RUN-INPUT-EVIDENCE-V1", "digest": digest},
    }


class RunInputEvidenceSchemaTests(unittest.TestCase):
    def test_evidence_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(EVIDENCE_SCHEMA)

    def test_minimal_synthetic_evidence_shape_is_valid(self) -> None:
        errors = list(EVIDENCE_VALIDATOR.iter_errors(valid_evidence()))
        self.assertEqual([], errors, msg="; ".join(error.message for error in errors))

    def test_unknown_fields_and_unsupported_versions_are_rejected(self) -> None:
        instance = valid_evidence()
        instance["unexpected"] = True
        self.assertTrue(list(EVIDENCE_VALIDATOR.iter_errors(instance)))
        instance = valid_evidence()
        instance["evidence_schema_version"] = 2
        self.assertTrue(list(EVIDENCE_VALIDATOR.iter_errors(instance)))

    def test_uppercase_digest_and_unsafe_relative_paths_are_rejected(self) -> None:
        instance = valid_evidence()
        instance["integrity"]["digest"] = "A" * 64
        self.assertTrue(list(EVIDENCE_VALIDATOR.iter_errors(instance)))
        instance = valid_evidence()
        instance["inventory"]["targets"][0]["relative_path"] = "../outside.txt"
        self.assertTrue(list(EVIDENCE_VALIDATOR.iter_errors(instance)))

    def test_inventory_records_reject_unknown_fields(self) -> None:
        instance = valid_evidence()
        instance["inventory"]["targets"][0]["extra"] = "not allowed"
        self.assertTrue(list(EVIDENCE_VALIDATOR.iter_errors(instance)))


MANIFEST_SCHEMA = load_schema("manifest-v1.schema.json")
MANIFEST_VALIDATOR = Draft202012Validator(MANIFEST_SCHEMA, format_checker=FORMAT_CHECKER)


def valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "run_id": "8c7e5db8-08f4-4c9e-a6b2-5b45c1aaf031",
        "pc_id": "PC-A",
        "log_type": "BattleLog",
        "target_period": "2026-09",
        "status": "success",
        "outcome": None,
        "started_at_utc": "2026-10-21T00:00:00Z",
        "finished_at_utc": "2026-10-21T00:00:02Z",
        "files": [
            {
                "relative_path": "2026/09/20260930_example.txt",
                "filename": "20260930_example.txt",
                "size_bytes": 1234,
                "sha256": "a" * 64,
                "status": "verified",
                "drive_file_id": "drive-object-123",
                "verification": {
                    "status": "verified",
                    "method": "download_sha256",
                    "checked_at_utc": "2026-10-21T00:00:03Z",
                    "observed_sha256": "a" * 64,
                },
            }
        ],
    }


class ManifestSchemaDefinitionTests(unittest.TestCase):
    def test_manifest_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(MANIFEST_SCHEMA)


class ManifestContractTests(unittest.TestCase):
    def assert_manifest_valid(self, instance: dict) -> None:
        errors = list(MANIFEST_VALIDATOR.iter_errors(instance))
        self.assertEqual([], errors, msg="; ".join(error.message for error in errors))

    def assert_manifest_invalid(self, instance: dict) -> None:
        self.assertTrue(
            list(MANIFEST_VALIDATOR.iter_errors(instance)),
            msg=f"Expected manifest to be rejected: {instance!r}",
        )

    def test_valid_terminal_manifest_is_accepted(self) -> None:
        self.assert_manifest_valid(valid_manifest())

    def test_running_manifest_requires_null_finish_and_terminal_requires_timestamp(self) -> None:
        manifest = valid_manifest()
        manifest["status"] = "running"
        manifest["finished_at_utc"] = None
        self.assert_manifest_valid(manifest)
        manifest["finished_at_utc"] = "2026-10-21T00:00:02Z"
        self.assert_manifest_invalid(manifest)
        manifest = valid_manifest()
        manifest["finished_at_utc"] = None
        self.assert_manifest_invalid(manifest)

    def test_period_shape_is_bound_to_log_type(self) -> None:
        manifest = valid_manifest()
        manifest["target_period"] = "2026"
        self.assert_manifest_invalid(manifest)
        manifest = valid_manifest()
        manifest["log_type"] = "ErrorReport"
        manifest["target_period"] = "2026"
        self.assert_manifest_valid(manifest)
        manifest["target_period"] = "2026-09"
        self.assert_manifest_invalid(manifest)

    def test_no_work_requires_success_and_empty_file_inventory(self) -> None:
        manifest = valid_manifest()
        manifest["outcome"] = "no_work"
        manifest["files"] = []
        self.assert_manifest_valid(manifest)
        manifest["status"] = "failure"
        self.assert_manifest_invalid(manifest)
        manifest = valid_manifest()
        manifest["outcome"] = "no_work"
        self.assert_manifest_invalid(manifest)

    def test_verification_status_method_time_hash_combinations_are_strict(self) -> None:
        manifest = valid_manifest()
        verification = manifest["files"][0]["verification"]
        verification.update(
            status="not_checked", method="not_performed",
            checked_at_utc=None, observed_sha256=None,
        )
        self.assert_manifest_valid(manifest)
        verification["method"] = "download_sha256"
        self.assert_manifest_invalid(manifest)
        manifest = valid_manifest()
        verification = manifest["files"][0]["verification"]
        verification.update(
            status="unavailable", method="not_performed",
            checked_at_utc="2026-10-21T00:00:03Z", observed_sha256=None,
        )
        self.assert_manifest_valid(manifest)
        verification["observed_sha256"] = "a" * 64
        self.assert_manifest_invalid(manifest)

    def test_unknown_fields_unsupported_versions_and_unsafe_paths_are_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["unexpected"] = True
        self.assert_manifest_invalid(manifest)
        manifest = valid_manifest()
        manifest["schema_version"] = 2
        self.assert_manifest_invalid(manifest)
        manifest = valid_manifest()
        manifest["files"][0]["relative_path"] = "../outside.txt"
        self.assert_manifest_invalid(manifest)
        manifest = valid_manifest()
        manifest["files"][0]["filename"] = "folder/file.txt"
        self.assert_manifest_invalid(manifest)

    def test_invalid_timestamp_hash_and_run_id_are_rejected(self) -> None:
        for field, value in (
            ("started_at_utc", "2026-10-21T00:00:00+00:00"),
            ("finished_at_utc", "not-a-date"),
            ("run_id", "not-a-uuid"),
        ):
            with self.subTest(field=field):
                manifest = valid_manifest()
                manifest[field] = value
                self.assert_manifest_invalid(manifest)
        manifest = valid_manifest()
        manifest["files"][0]["sha256"] = "A" * 64
        self.assert_manifest_invalid(manifest)
