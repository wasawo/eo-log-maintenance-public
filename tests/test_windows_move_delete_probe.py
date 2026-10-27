"""Real Win32 checks restricted to constructor-created synthetic temp files."""
import json
import os
import unittest

from windows_move_delete_probe import DisposableMoveDeleteProbe, MoveDeleteProbeError


@unittest.skipUnless(os.name == "nt", "real Windows file APIs required")
class WindowsMoveDeleteProbeTests(unittest.TestCase):
    def probe(self, data=b"synthetic log"):
        probe = DisposableMoveDeleteProbe(data)
        self.addCleanup(probe.close)
        return probe

    def test_same_handle_delete_after_verified_copy_and_prepared_record(self):
        for data in (b"synthetic log", b"", b"x" * 131073):
            with self.subTest(size=len(data)):
                probe = self.probe(data)
                result = probe.run()
                self.assertEqual("completed", result["status"])
                self.assertEqual("delete_confirmed", result["reason"])
                self.assertTrue(result["write_open_blocked"])
                self.assertTrue(result["delete_open_blocked"])
                self.assertFalse((probe._root / "source.bin").exists())
                self.assertEqual(data, probe._path("destination.bin").read_bytes())
                prepared = json.loads(probe._path("prepared.json").read_bytes())
                self.assertEqual(probe._source_id, tuple(prepared["source_id"]))
                self.assertEqual(probe._destination_id, tuple(prepared["destination_id"]))
                self.assertEqual(len(data), prepared["size"])
                self.assertEqual(result, json.loads(probe._path("result.json").read_bytes()))

    def test_changed_source_or_destination_and_same_bytes_replacement_are_retained(self):
        for fault in ("source_changed", "source_replaced", "destination_changed", "destination_replaced", "record_failed"):
            with self.subTest(fault=fault):
                probe = self.probe()
                result = probe.run(fault=fault)
                self.assertEqual("retained", result["status"])
                self.assertTrue(probe._path("source.bin").is_file())
                self.assertFalse((probe._root / "result.json").exists())

    def test_other_read_handle_delays_removal_and_does_not_mean_completion(self):
        probe = self.probe()
        first = probe.run(keep_reader=True)
        self.assertEqual({"status": "unknown", "reason": "delete_pending",
                          "write_open_blocked": True, "delete_open_blocked": True}, first)
        self.assertEqual("unknown", probe.reconcile()["status"])
        probe.release_reader()
        result = probe.reconcile()
        self.assertEqual({"status": "completed", "reason": "reconciled_completion"}, result)
        self.assertEqual(first, json.loads(probe._path("result.json").read_bytes()))
        prior = probe._path("reconciled.json").read_bytes()
        self.assertEqual(result, probe.reconcile())
        self.assertEqual(prior, probe._path("reconciled.json").read_bytes())

    def test_missing_result_can_reconcile_without_repeating_delete(self):
        probe = self.probe()
        result = probe.run(fault="result_record_failed")
        self.assertEqual("unknown", result["status"])
        self.assertFalse((probe._root / "source.bin").exists())
        self.assertFalse((probe._root / "result.json").exists())
        self.assertEqual("reconciled_completion", probe.reconcile()["reason"])

    def test_reconciliation_requires_valid_binding_and_current_destination(self):
        for problem in ("record_corrupt", "record_missing", "destination_corrupt", "source_recreated"):
            with self.subTest(problem=problem):
                probe = self.probe()
                probe.run(fault="result_record_failed")
                if problem == "record_corrupt":
                    probe._path("prepared.json").write_bytes(b"{}")
                elif problem == "record_missing":
                    probe._path("prepared.json").unlink()
                elif problem == "destination_corrupt":
                    probe._path("destination.bin").write_bytes(b"bad")
                else:
                    probe._path("source.bin", existing=False).write_bytes(b"synthetic log")
                self.assertEqual("unknown", probe.reconcile()["status"])
                self.assertFalse((probe._root / "reconciled.json").exists())

    def test_hardlink_or_changed_owner_marker_blocks_mutation(self):
        probe = self.probe()
        os.link(probe._path("source.bin"), probe._root / "synthetic-alias")
        with self.assertRaisesRegex(MoveDeleteProbeError, "probe_file_changed"):
            probe.run()
        marker = probe._root / ".probe-owner"
        marker.write_bytes(b"changed")
        try:
            with self.assertRaisesRegex(MoveDeleteProbeError, "probe_root_changed"):
                probe.run()
        finally:
            marker.write_bytes(probe._nonce)
        self.assertEqual(b"synthetic log", (probe._root / "source.bin").read_bytes())

    def test_no_caller_selected_path_or_unknown_fault(self):
        probe = self.probe()
        for name in ("../outside", "C:\\outside", "folder/source.bin", "unknown.bin"):
            with self.assertRaisesRegex(MoveDeleteProbeError, "probe_name_invalid"):
                probe._path(name)
        with self.assertRaisesRegex(MoveDeleteProbeError, "probe_fault_invalid"):
            probe.run(fault="unknown")
        self.assertEqual(b"synthetic log", probe._path("source.bin").read_bytes())

    def test_actual_create_only_record_failures_preserve_source_or_unknown_result(self):
        probe = self.probe()
        probe._path("prepared.json", existing=False).write_bytes(b"existing")
        self.assertEqual({"status": "retained", "reason": "record_failed"}, probe.run())
        self.assertEqual(b"synthetic log", probe._path("source.bin").read_bytes())
        self.assertEqual(b"existing", probe._path("prepared.json").read_bytes())
        probe = self.probe()
        probe._path("result.json", existing=False).write_bytes(b"existing")
        self.assertEqual({"status": "unknown", "reason": "result_record_failed"}, probe.run())
        self.assertFalse((probe._root / "source.bin").exists())
        self.assertEqual(b"existing", probe._path("result.json").read_bytes())
        self.assertEqual("reconciled_completion", probe.reconcile()["reason"])

    def test_existing_writer_prevents_delete_guard_acquisition(self):
        for name in ("source.bin", "destination.bin"):
            with self.subTest(writer=name):
                probe = self.probe()
                with probe._handle(name, access=0x40000000, share=7):
                    with self.assertRaisesRegex(MoveDeleteProbeError, "probe_open_failed"):
                        probe.run()
                self.assertEqual(b"synthetic log", probe._path("source.bin").read_bytes())
                self.assertFalse((probe._root / "prepared.json").exists())


if __name__ == "__main__":
    unittest.main()
