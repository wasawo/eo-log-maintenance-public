"""Scoped latest selection plus exact report binding; synthetic temp only."""
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from Common import ManifestDirectoryReader as reader
from Common.LatestManifestSelection import LatestManifestSelectionError
from Common.AggregationReportBuilder import build_aggregation_report
from Common.RunInputEvidenceIntegrity import compute_evidence_digest
from Common.validate_aggregation_artifacts import validate_referenced_artifacts
from test_aggregation_report_builder import fixture, encode, SCHEMAS, NOW, ROOT


class ManifestReportSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eolm-manifest-report-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def install(self, *, pc_id="PC-A", log_type="BattleLog", offset=0, outcomes=((9, "verified"),)):
        m, e = fixture(outcomes, log_type=log_type)
        run_id = str(uuid4())
        m["pc_id"] = e["pc_id"] = pc_id
        m["run_id"] = e["run_id"] = run_id
        for value in (m, e["enumeration"]):
            for field in ("started_at_utc", "finished_at_utc"):
                stamp = datetime.fromisoformat(value[field].replace("Z", "+00:00")) + timedelta(seconds=offset)
                value[field] = stamp.isoformat().replace("+00:00", "Z")
        for file in m["files"]:
            if file["verification"]["checked_at_utc"] is not None:
                file["verification"]["checked_at_utc"] = m["finished_at_utc"]
        e["integrity"]["digest"] = compute_evidence_digest(e)
        basename = f'{pc_id}_{log_type}_{m["target_period"]}_{run_id}.json'
        relative = f"_maintenance/manifests/{pc_id}/{basename}"
        evidence_relative = f"_maintenance/evidence/{run_id}.json"
        manifest_path, evidence_path = self.root / relative, self.root / evidence_relative
        report_path = self.root / "_maintenance/reports" / (run_id + ".json")
        for path in (manifest_path, evidence_path, report_path): path.parent.mkdir(parents=True, exist_ok=True)
        raw_m, raw_e = encode(m), encode(e)
        report = build_aggregation_report(raw_m, raw_e, manifest_path=relative, evidence_path=evidence_relative,
            current_utc=NOW, current_utc_reliable=True, **SCHEMAS)
        manifest_path.write_bytes(raw_m); evidence_path.write_bytes(raw_e); report_path.write_bytes(report)
        return SimpleNamespace(manifest=m, evidence=e, manifest_path=manifest_path,
            report_path=report_path, relative=relative, content=raw_m)

    def read(self, source, **changes):
        options = dict(expected_pc_id=source.manifest["pc_id"], expected_log_type=source.manifest["log_type"],
            expected_target_period=source.manifest["target_period"], current_utc=NOW, current_utc_reliable=True)
        options.update(changes)
        return reader.read_latest_manifest_with_report(self.root, source.report_path, ROOT / "contracts", **options)

    def add_unreported(self, source, status, *, tie=False):
        changed = deepcopy(source.manifest)
        changed.update(run_id=str(uuid4()), status=status, outcome=None, files=[],
            started_at_utc=source.manifest["started_at_utc"] if tie else "2026-10-21T00:00:02Z",
            finished_at_utc=None if status == "running" else "2026-10-21T00:00:03Z")
        path = source.manifest_path.parent / f'{changed["pc_id"]}_{changed["log_type"]}_{changed["target_period"]}_{changed["run_id"]}.json'
        path.write_bytes(encode(changed))

    def test_both_pcs_and_log_types_bind_exact_latest_bytes_without_writes(self):
        for pc_id in ("PC-A", "PC-B"):
            for log_type in ("BattleLog", "ErrorReport"):
                with self.subTest(pc_id=pc_id, log_type=log_type):
                    source = self.install(pc_id=pc_id, log_type=log_type)
                    before = {p: p.read_bytes() for p in self.root.rglob("*.json")}
                    selected = self.read(source)
                    self.assertEqual(source.content, selected.content)
                    self.assertEqual(source.manifest_path.name, selected.filename)
                    self.assertEqual(hashlib.sha256(source.content).hexdigest(), selected.sha256)
                    self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*.json")})

    def test_artifact_byte_limit_reaches_report_validator(self):
        source = self.install()
        with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "^selected_manifest_report_invalid$"):
            self.read(source, maximum_artifact_bytes=1)
        maximum = max([source.report_path.stat().st_size,
            *(p.stat().st_size for p in self.root.rglob("*.json")),
            *((ROOT/"contracts"/name).stat().st_size for name in (
                "aggregation-report-v1.schema.json", "manifest-v1.schema.json", "run-input-evidence-v1.schema.json"))])
        self.assertEqual(source.content, self.read(source, maximum_artifact_bytes=maximum).content)

    def test_invalid_artifact_limit_rejects_before_manifest_io(self):
        source = self.install()
        for value in (True, False, 0, -1, 1.5, "4096"):
            with self.subTest(value=value), patch.object(reader, "read_latest_manifest") as observe:
                with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "^manifest_read_limit_invalid$"):
                    self.read(source, maximum_artifact_bytes=value)
                observe.assert_not_called()

    def test_newer_success_does_not_reuse_old_report(self):
        source = self.install()
        self.install(offset=1)
        with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "selected_manifest_report_invalid"):
            self.read(source)

    def test_latest_incomplete_never_falls_back_or_validates_old_report(self):
        for status in ("running", "partial_failure", "failure"):
            with self.subTest(status=status):
                source = self.install(pc_id="PC-B" if status == "failure" else "PC-A",
                    log_type="ErrorReport" if status == "partial_failure" else "BattleLog")
                self.add_unreported(source, status)
                with patch.object(reader, "validate_referenced_artifacts") as validate:
                    with self.assertRaises(LatestManifestSelectionError): self.read(source)
                    validate.assert_not_called()

    def test_report_from_copied_equal_bytes_at_a_different_path_is_rejected(self):
        source = self.install()
        alias = self.root / "copied.json"
        alias.write_bytes(source.content)
        report = json.loads(source.report_path.read_bytes())
        report["manifest_ref"]["path"] = alias.name
        source.report_path.write_bytes(encode(report))
        self.assertEqual("verified", validate_referenced_artifacts(self.root, source.report_path, ROOT / "contracts")["status"])
        with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "selected_manifest_report_invalid"):
            self.read(source)

    def test_selected_content_cannot_change_even_if_report_hash_is_updated(self):
        source = self.install()
        real = reader.validate_referenced_artifacts
        def changed(*args, **kwargs):
            raw = source.content + b"\n"
            source.manifest_path.write_bytes(raw)
            report = json.loads(source.report_path.read_bytes())
            report["manifest_ref"]["sha256"] = hashlib.sha256(raw).hexdigest()
            source.report_path.write_bytes(encode(report))
            return real(*args, **kwargs)
        with patch.object(reader, "validate_referenced_artifacts", side_effect=changed):
            with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "selected_manifest_report_invalid"):
                self.read(source)

    def test_reselection_blocks_newer_success_or_running_after_report_validation(self):
        for status in ("success", "running"):
            with self.subTest(status=status):
                source = self.install(pc_id="PC-A" if status == "success" else "PC-B")
                real = reader.validate_referenced_artifacts
                def changed(*args, **kwargs):
                    result = real(*args, **kwargs)
                    self.assertEqual("verified", result["status"])
                    if status == "success": self.install(offset=1)
                    else: self.add_unreported(source, "running")
                    return result
                with patch.object(reader, "validate_referenced_artifacts", side_effect=changed):
                    with self.assertRaises((reader.ManifestDirectoryReadError, LatestManifestSelectionError)):
                        self.read(source)

    def test_declared_success_with_wrong_aggregation_is_not_accepted(self):
        source = self.install(outcomes=((9, "unknown"),))
        changed = deepcopy(source.manifest)
        changed["status"] = "success"
        raw = encode(changed)
        source.manifest_path.write_bytes(raw)
        report = json.loads(source.report_path.read_bytes())
        report["manifest_ref"]["sha256"] = hashlib.sha256(raw).hexdigest()
        source.report_path.write_bytes(encode(report))
        with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "selected_manifest_report_invalid"):
            self.read(source)

    def test_inspection_can_read_terminal_failure_but_never_promotes_running(self):
        source = self.install(outcomes=((9, "unknown"),))
        self.assertEqual("failure", self.read(source, require_current_success=False).status)
        self.add_unreported(source, "running")
        with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "selected_manifest_report_invalid"):
            self.read(source, require_current_success=False)

    def test_partial_or_wrong_typed_expected_binding_is_rejected(self):
        source = self.install()
        for options in ({"expected_manifest_bytes": source.content}, {"expected_manifest_path": source.relative},
                        {"expected_manifest_bytes": bytearray(source.content), "expected_manifest_path": source.relative}):
            result = validate_referenced_artifacts(self.root, source.report_path, ROOT / "contracts", **options)
            self.assertEqual("expected_manifest_binding_invalid", result["reason_code"])

    def test_missing_report_is_not_generated_and_untrusted_clock_blocks_before_validation(self):
        source = self.install()
        with patch.object(reader, "validate_referenced_artifacts") as validate:
            with self.assertRaises(LatestManifestSelectionError): self.read(source, current_utc_reliable=False)
            validate.assert_not_called()
        source.report_path.unlink()
        with self.assertRaisesRegex(reader.ManifestDirectoryReadError, "selected_manifest_report_invalid"):
            self.read(source)
        self.assertFalse(source.report_path.exists())
        self.assertEqual(source.content, source.manifest_path.read_bytes())


if __name__ == "__main__": unittest.main()
