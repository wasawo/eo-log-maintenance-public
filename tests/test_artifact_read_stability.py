"""Synthetic path/handle/read-set changes, never a root/FS qualification."""
import json
import os
from pathlib import Path
import shutil
import subprocess
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


if __name__ == "__main__": unittest.main()
