"""Synthetic path/handle/read-set changes, never a root/FS qualification."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import Common.validate_aggregation_artifacts as validator
from Common import AtomicArtifactPublication, ArtifactSetDirectoryVerification, ManifestDirectoryReader
import test_aggregation_referenced_artifacts as referenced_fixture


def stat_copy(info, **changes):
    values = {name: getattr(info, name) for name in (
        "st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")}
    values["st_file_attributes"] = getattr(info, "st_file_attributes", 0)
    return SimpleNamespace(**{**values, **changes})


class ArtifactReadStabilityTests(unittest.TestCase):
    def test_windows_birthtime_is_compared_instead_of_incompatible_ctime(self):
        values = dict(st_dev=1, st_ino=2, st_size=3, st_mtime_ns=4, st_nlink=1, st_birthtime_ns=5)
        path_info = SimpleNamespace(**values, st_ctime_ns=5)
        handle_info = SimpleNamespace(**values, st_ctime_ns=999)
        for module in (validator, AtomicArtifactPublication, ArtifactSetDirectoryVerification, ManifestDirectoryReader):
            with self.subTest(module=module.__name__), patch.object(module.os, "name", "nt"):
                self.assertEqual(module._signature(path_info), module._signature(handle_info))
                for field in ("st_ino", "st_size", "st_mtime_ns", "st_birthtime_ns"):
                    changed = SimpleNamespace(**{**values, field: 1000}, st_ctime_ns=999)
                    self.assertNotEqual(module._signature(path_info), module._signature(changed))
            with patch.object(module.os, "name", "posix"):
                self.assertNotEqual(module._signature(path_info), module._signature(handle_info))

    write_report = referenced_fixture.ReferencedArtifactValidationTests.write_report

    def setUp(self):
        referenced_fixture.ReferencedArtifactValidationTests.setUp(self)
        self.contracts = Path(self.temp.name) / "contracts"
        self.contracts.mkdir()
        for name in ("aggregation-report-v1.schema.json", "manifest-v1.schema.json", "run-input-evidence-v1.schema.json"):
            shutil.copyfile(referenced_fixture.CONTRACTS / name, self.contracts / name)

    def validate(self):
        return validator.validate_referenced_artifacts(self.root, self.report_path, self.contracts)

    def assert_rejected(self, result, reason):
        self.assertEqual("rejected", result["status"])
        self.assertEqual(reason, result["reason_code"])
        self.assertEqual({}, result["artifacts"])
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_late_change_to_each_read_input_blocks_success(self):
        targets = [self.report_path, self.root / "_maintenance/manifests/PC-A/manifest.json",
            self.root / "_maintenance/run-input-evidence/PC-A/evidence.json",
            *sorted(self.contracts.glob("*.json"))]
        real = validator.derive_aggregation_report
        for target in targets:
            with self.subTest(target=target.name):
                original = target.read_bytes()
                def changed(*args, **kwargs):
                    result = real(*args, **kwargs)
                    target.write_bytes(original + b"\n")
                    return result
                with patch.object(validator, "derive_aggregation_report", side_effect=changed):
                    self.assert_rejected(self.validate(), "artifact_read_set_changed")
                target.write_bytes(original)

    def test_opened_handle_must_match_the_inspected_file(self):
        real = os.fstat
        def replaced(fd):
            info = real(fd)
            return stat_copy(info, st_ino=info.st_ino + 1)
        with patch.object(validator.os, "fstat", side_effect=replaced):
            self.assert_rejected(self.validate(), "artifact_changed_during_read")

    def test_change_during_stream_read_is_rejected(self):
        real = os.fstat
        calls = 0
        def changed(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.report_path.write_bytes(self.report_path.read_bytes() + b"\n")
            return real(fd)
        with patch.object(validator.os, "fstat", side_effect=changed):
            self.assert_rejected(self.validate(), "artifact_changed_during_read")

    def test_parent_chain_identity_change_is_rejected(self):
        real = validator._directory_chain
        calls = 0
        def changed(directory):
            nonlocal calls
            result = real(directory)
            if directory == self.report_path.parent:
                calls += 1
                if calls == 2:
                    return ((result[0][0], result[0][1] + 1), *result[1:])
            return result
        with patch.object(validator, "_directory_chain", side_effect=changed):
            self.assert_rejected(self.validate(), "artifact_changed_during_read")

    def test_reparse_attributes_are_rejected_before_resolution_or_read(self):
        real = Path.lstat
        for target in (self.root, self.report_path, self.root / "_maintenance",
                self.root / "_maintenance/manifests/PC-A/manifest.json",
                self.contracts, self.contracts / "aggregation-report-v1.schema.json"):
            def changed(path, *args, **kwargs):
                info = real(path, *args, **kwargs)
                return stat_copy(info, st_file_attributes=0x400) if path == target else info
            with self.subTest(target=target.name), patch.object(Path, "lstat", changed):
                self.assert_rejected(self.validate(), "reparse_point_not_allowed")

    def test_external_broken_and_invalid_schemas_do_not_fetch_or_echo(self):
        path = self.contracts / "aggregation-report-v1.schema.json"
        for schema in ({"$ref": "https://synthetic.invalid/private-detail"},
                       {"$ref": "#/$defs/missing"}, {"type": "synthetic-invalid"}):
            path.write_text(json.dumps(schema), encoding="utf-8")
            with patch("socket.socket", side_effect=AssertionError("unexpected_network")) as network:
                self.assert_rejected(self.validate(), "schema_unavailable:report")
                network.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows junction fixture required")
    def test_actual_junction_root_is_rejected_without_traversing_it(self):
        alias = Path(self.temp.name) / "junction"
        # Both link and target are inside this fixture's own temp directory.
        self.assertEqual(Path(self.temp.name).resolve(), alias.parent.resolve())
        result = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(alias), str(self.root)],
                                capture_output=True, check=False)
        self.assertEqual(0, result.returncode, "synthetic junction creation failed")
        try:
            self.assert_rejected(validator.validate_referenced_artifacts(alias, self.report_path, self.contracts),
                                 "reparse_point_not_allowed")
        finally:
            os.rmdir(alias)  # Remove only the link; never recurse through it.


class ArtifactReadBoundsTests(unittest.TestCase):
    def test_excessive_json_nesting_in_any_read_input_returns_fixed_rejection(self):
        paths = self.seed()
        malformed = b'{"nested":'+b"["*2048+b"0"+b"]"*2048+b"}"
        for path in paths:
            original = path.read_bytes()
            path.write_bytes(malformed)
            with self.subTest(path=path.name):
                self.assert_rejected(self.validate(), "malformed_json")
                self.assertEqual(malformed, path.read_bytes())
            path.write_bytes(original)

    def test_nonfinite_json_numbers_in_all_artifacts_and_schemas_are_rejected(self):
        paths = self.seed()
        for path in paths:
            original = path.read_bytes()
            for number in (b"1e999", b"-1e999", b"NaN", b"Infinity", b"-Infinity"):
                content = b'{"nested":{"number":'+number+b"}}"
                path.write_bytes(content)
                with self.subTest(path=path.name, number=number):
                    self.assert_rejected(self.validate(), "invalid_json_constant")
                    self.assertEqual(content, path.read_bytes())
            path.write_bytes(original)

    def test_finite_json_float_tokens_preserve_original_bytes_and_values(self):
        for number, expected in ((b"1.25", 1.25), (b"1e-3", 0.001), (b"1.0", 1.0)):
            raw = b'{"number":'+number+b"}"
            self.report_path.write_bytes(raw)
            with self.subTest(number=number):
                observed, value = validator._read_json_bytes(self.report_path)
                self.assertEqual(raw, observed)
                self.assertIs(type(value["number"]), float)
                self.assertEqual(expected, value["number"])

    def test_cli_malformed_nested_json_returns_json_exit_two_without_traceback(self):
        self.seed()
        self.report_path.write_bytes(b'{"nested":'+b"["*2048+b"0"+b"]"*2048+b"}")
        result = subprocess.run([sys.executable, "-B", str(Path(validator.__file__)),
            "--root", str(self.root), "--report", str(self.report_path), "--contracts", str(self.contracts)],
            capture_output=True, text=True, check=False)
        self.assertEqual(2, result.returncode)
        self.assert_rejected(json.loads(result.stdout), "malformed_json")
        self.assertEqual("", result.stderr)

    setUp = ArtifactReadStabilityTests.setUp
    write_report = ArtifactReadStabilityTests.write_report
    install_terminal_plan = referenced_fixture.ReferencedArtifactValidationTests.install_terminal_plan
    assert_rejected = ArtifactReadStabilityTests.assert_rejected

    def seed(self):
        self.install_terminal_plan(())
        return [self.report_path, self.root/"_maintenance/manifests/PC-A/manifest.json",
            self.root/"_maintenance/run-input-evidence/PC-A/evidence.json",
            *sorted(self.contracts.glob("*.json"))]

    def validate(self, **changes):
        return validator.validate_referenced_artifacts(self.root, self.report_path, self.contracts, **changes)

    def test_exact_maximum_accepts_all_artifacts_and_schemas_without_mutation(self):
        paths = self.seed()
        originals = {path: path.read_bytes() for path in paths}
        expected = self.validate()
        self.assertEqual("verified", expected["status"])
        self.assertEqual(expected, self.validate(maximum_artifact_bytes=max(map(len, originals.values()))))
        self.assertEqual(originals, {path: path.read_bytes() for path in paths})

    def test_invalid_limits_reject_before_root_io(self):
        for key in ("maximum_artifact_bytes", "maximum_total_artifact_bytes"):
            for value in (True, False, 0, -1, 1.5, "4096"):
                with self.subTest(key=key, value=value), patch.object(validator, "_directory_chain") as chain:
                    self.assert_rejected(self.validate(**{key: value}), "artifact_read_limit_invalid")
                    chain.assert_not_called()

    def test_total_exact_boundary_includes_initial_and_final_reads(self):
        paths = self.seed()
        total = 2*sum(path.stat().st_size for path in paths)
        self.assertEqual("verified", self.validate(maximum_total_artifact_bytes=total)["status"])
        self.assert_rejected(self.validate(maximum_total_artifact_bytes=total-1), "artifact_total_read_limit_exceeded")

    def test_total_budget_does_not_reset_before_final_report_read(self):
        paths = self.seed()
        total = sum(path.stat().st_size for path in paths)
        real_open = Path.open
        report_opens = []
        def guarded(path, *args, **kwargs):
            if path == self.report_path:
                report_opens.append(path)
                if len(report_opens) > 1:
                    raise AssertionError("final read must fail before open")
            return real_open(path, *args, **kwargs)
        with patch.object(Path, "open", guarded):
            self.assert_rejected(self.validate(maximum_total_artifact_bytes=total), "artifact_total_read_limit_exceeded")
        self.assertEqual([self.report_path], report_opens)

    def test_total_budget_counts_schema_and_rejects_before_open(self):
        self.seed()
        schema = self.contracts/"aggregation-report-v1.schema.json"
        total = self.report_path.stat().st_size + schema.stat().st_size - 1
        real_open = Path.open
        def guarded(path, *args, **kwargs):
            if path == schema:
                raise AssertionError("schema must fail before open")
            return real_open(path, *args, **kwargs)
        with patch.object(Path, "open", guarded):
            self.assert_rejected(self.validate(maximum_total_artifact_bytes=total), "artifact_total_read_limit_exceeded")

    def test_total_budget_is_local_to_each_invocation_after_success_or_rejection(self):
        paths = self.seed()
        total = 2*sum(path.stat().st_size for path in paths)
        for ceiling in (total, 1, total, total):
            result = self.validate(maximum_total_artifact_bytes=ceiling)
            self.assertEqual("rejected" if ceiling == 1 else "verified", result["status"])

    def test_total_and_per_file_limits_are_both_enforced(self):
        paths = self.seed()
        maximum = max(path.stat().st_size for path in paths)
        total = 2*sum(path.stat().st_size for path in paths)
        self.assertEqual("verified", self.validate(maximum_artifact_bytes=maximum,
            maximum_total_artifact_bytes=total)["status"])
        self.assert_rejected(self.validate(maximum_artifact_bytes=maximum-1,
            maximum_total_artifact_bytes=total), "artifact_read_limit_exceeded")
        self.assert_rejected(self.validate(maximum_artifact_bytes=maximum,
            maximum_total_artifact_bytes=total-1), "artifact_total_read_limit_exceeded")

    def test_each_oversized_input_rejects_before_its_payload_open(self):
        paths = self.seed()
        ceiling = max(path.stat().st_size for path in paths)
        real_open = Path.open
        for target in paths:
            original = target.read_bytes()
            target.write_bytes(original + b" "*(ceiling+1-len(original)))
            def guarded(path, *args, **kwargs):
                if path == target:
                    raise AssertionError("oversize payload must not open")
                return real_open(path, *args, **kwargs)
            with self.subTest(target=target.name), patch.object(Path, "open", guarded):
                self.assert_rejected(self.validate(maximum_artifact_bytes=ceiling), "artifact_read_limit_exceeded")
            self.assertEqual(ceiling+1, target.stat().st_size)
            target.write_bytes(original)

    def test_final_read_set_recheck_enforces_the_same_limit(self):
        paths = self.seed()
        ceiling = max(path.stat().st_size for path in paths)
        real_derive = validator.derive_aggregation_report
        def grow(*args, **kwargs):
            result = real_derive(*args, **kwargs)
            original = self.report_path.read_bytes()
            self.report_path.write_bytes(original+b" "*(ceiling+1-len(original)))
            return result
        with patch.object(validator, "derive_aggregation_report", side_effect=grow):
            self.assert_rejected(self.validate(maximum_artifact_bytes=ceiling), "artifact_read_limit_exceeded")
        self.assertEqual(ceiling+1, self.report_path.stat().st_size)

    def test_growth_during_stream_read_stops_at_initial_size_plus_one(self):
        self.report_path.write_bytes(b"x"*70000)
        real_open = Path.open
        consumed, requests = [], []
        class Stream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, size):
                requests.append(size)
                block = self.stream.read(size)
                consumed.append(len(block))
                if len(requests) == 1:
                    with real_open(self_path, "ab") as writer: writer.write(b"y"*70000)
                return block
        self_path = self.report_path
        def opened(path, *args, **kwargs): return Stream(real_open(path, *args, **kwargs))
        with patch.object(Path, "open", opened):
            with self.assertRaisesRegex(validator.ArtifactValidationError, "^artifact_changed_during_read$"):
                validator._stable_bytes(self.report_path, 70000)
        self.assertEqual(70001, sum(consumed))
        self.assertTrue(all(0 < size <= 65536 for size in requests))
        self.assertEqual(140000, self.report_path.stat().st_size)

    def test_growth_before_open_rejects_handle_without_reading(self):
        self.seed()
        real_open = Path.open
        target = self.report_path
        class Stream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, *_): raise AssertionError("changed handle cannot read")
        def opened(path, *args, **kwargs):
            if path == target:
                with real_open(path, "ab") as writer: writer.write(b" ")
                return Stream(real_open(path, *args, **kwargs))
            return real_open(path, *args, **kwargs)
        with patch.object(Path, "open", opened):
            self.assert_rejected(self.validate(), "artifact_changed_during_read")

    def test_default_reads_are_chunked_and_preserve_exact_bytes(self):
        payload = b"x"*131073
        self.report_path.write_bytes(payload)
        real_open = Path.open
        requests = []
        class Stream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, size):
                requests.append(size)
                return self.stream.read(size)
        def opened(path, *args, **kwargs): return Stream(real_open(path, *args, **kwargs))
        with patch.object(Path, "open", opened):
            self.assertEqual(payload, validator._stable_bytes(self.report_path)[0])
        self.assertTrue(all(0 < size <= 65536 for size in requests))
        self.assertGreater(len(requests), 2)

    def test_cli_limit_returns_fixed_rejection_and_exit_two(self):
        self.seed()
        for option, reason in (("--maximum-artifact-bytes", "artifact_read_limit_exceeded"),
                ("--maximum-total-artifact-bytes", "artifact_total_read_limit_exceeded")):
            with self.subTest(option=option):
                result = subprocess.run([sys.executable, "-B", str(Path(validator.__file__)),
                    "--root", str(self.root), "--report", str(self.report_path), "--contracts", str(self.contracts),
                    option, "1"], capture_output=True, text=True, check=False)
                self.assertEqual(2, result.returncode)
                self.assert_rejected(json.loads(result.stdout), reason)
                self.assertEqual("", result.stderr)


if __name__ == "__main__": unittest.main()
