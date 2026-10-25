"""TEST ONLY: exact Python manifest/B2 size projection -> PS 7.6.7 arithmetic."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from Common.RunInputEvidenceIntegrity import compute_evidence_digest, compute_inventory_digest
import test_staging_size_observation as sizes_fixture
from test_aggregation_report_builder import encode


ROOT = Path(__file__).resolve().parents[1]
PWSH = os.environ.get("EOLM_TEST_PWSH") or shutil.which("pwsh")


@unittest.skipUnless(PWSH, "PowerShell 7.6.7 executable required")
class StagingCapacityBridgeTests(unittest.TestCase):
    def bridge(self, cases):
        result = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-File",
            str(ROOT/"tests/staging_capacity_bridge.ps1")], input=json.dumps(cases),
            capture_output=True, text=True, encoding="utf-8", timeout=30, cwd=ROOT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.assertEqual(0, result.returncode, "test capacity bridge failed")
        self.assertEqual("", result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual("7.6.7", value["PowerShellVersion"])
        self.assertEqual(len(cases), len(value["Observations"]))
        return value["Observations"]

    def assert_observation(self, result, total, count, required, reason):
        self.assertIs(int, type(result["RemainingTargetBytes"]))
        self.assertIs(int, type(result["RequiredFreeBytes"]))
        self.assertEqual((total, count, required, reason), (result["RemainingTargetBytes"],
            result["TargetCount"], result["RequiredFreeBytes"], result["ReasonCode"]))
        self.assertIs(False, result["MayCreateStaging"])
        self.assertIs(False, result["MayUpload"])

    def test_both_pc_log_projections_cross_stdin_without_numeric_or_order_loss(self):
        cases, expected = [], []
        for pc in ("PC-A", "PC-B"):
            for log in ("BattleLog", "ErrorReport"):
                manifest, evidence = sizes_fixture.seed(pc, log)
                paths = tuple(file["relative_path"] for file in json.loads(manifest)["files"])[::-1]
                projected = sizes_fixture.inspect(manifest, evidence, paths)
                total = projected.remaining_target_bytes
                required = (total*11+9)//10 + 100000000
                for available in (required, required-1):
                    cases.append(dict(target_sizes=projected.target_sizes,
                        available_free_bytes=available, free_space_reliable=True))
                    expected.append((total, len(paths), required,
                        "staging_capacity_observed_sufficient" if available == required else "staging_capacity_insufficient"))
                self.assertEqual(manifest, projected.manifest_bytes)
                self.assertEqual(evidence, projected.evidence_bytes)
        for result, wanted in zip(self.bridge(cases), expected): self.assert_observation(result, *wanted)

    def test_huge_manifest_sizes_and_json_roundtrip_remain_exact(self):
        manifest, evidence = sizes_fixture.seed()
        m, e = json.loads(manifest), json.loads(evidence)
        sizes = (10**60+1, 10**60+2)
        for file, target, size in zip(m["files"], e["inventory"]["targets"], sizes):
            file["size_bytes"] = target["size_bytes"] = size
        e["enumeration"]["inventory_sha256"] = compute_inventory_digest(e["inventory"]["targets"])
        e["integrity"]["digest"] = compute_evidence_digest(e)
        projected = sizes_fixture.inspect(encode(m), encode(e), tuple(file["relative_path"] for file in m["files"]))
        required = (projected.remaining_target_bytes*11+9)//10 + 100000000
        result, = self.bridge([dict(target_sizes=projected.target_sizes,
            available_free_bytes=required, free_space_reliable=True)])
        self.assert_observation(result, 2*10**60+3, 2, required, "staging_capacity_observed_sufficient")

    def test_empty_projection_and_unconfirmed_space_do_not_bypass_reserve(self):
        manifest, evidence = sizes_fixture.seed()
        projected = sizes_fixture.inspect(manifest, evidence, ())
        results = self.bridge([dict(target_sizes=projected.target_sizes, available_free_bytes=99999999,
                                   free_space_reliable=True),
                               dict(target_sizes=projected.target_sizes, available_free_bytes=100000000,
                                   free_space_reliable=False)])
        self.assert_observation(results[0], 0, 0, 100000000, "staging_capacity_insufficient")
        self.assert_observation(results[1], 0, 0, 100000000, "staging_capacity_unconfirmed")

    def test_wrong_member_types_remain_rejected_across_json(self):
        results = self.bridge([dict(target_sizes=[10, bad], available_free_bytes=200000000,
                                   free_space_reliable=True) for bad in (True, None, "1", 1.5, -1)])
        for result in results:
            self.assertEqual(("rejected", "staging_target_sizes_invalid", None, None),
                (result["Status"], result["ReasonCode"], result["RemainingTargetBytes"], result["RequiredFreeBytes"]))
            self.assertIs(False, result["MayCreateStaging"])
            self.assertIs(False, result["MayUpload"])


if __name__ == "__main__": unittest.main()
