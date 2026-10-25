"""All-or-none explicit staging allocation observations with bounded reads."""
import json
import unittest
from unittest.mock import patch

from Common import SourceInventoryRevalidation as check
import test_initial_source_integration as fixture


class InitialStagingBatchTests(unittest.TestCase):
    setUp = fixture.InitialSourceIntegrationTests.setUp
    cleanup = fixture.InitialSourceIntegrationTests.cleanup
    build = fixture.InitialSourceIntegrationTests.build
    plan_context = fixture.InitialSourceIntegrationTests.plan_context

    def seed(self, pc="PC-A", log="BattleLog"):
        name = "20260901_01020304@synthetic.txt" if log == "BattleLog" else "20250901_01020304.txt"
        for directory, payload in (("left", b"first"), ("right", b"second")):
            parent = self.source / directory
            parent.mkdir()
            (parent / name).write_bytes(payload)
        _, self.plan = self.build(pc=pc, log=log)
        self.context = self.plan_context(pc, log)
        self.allocations = tuple((item["relative_path"], sequence) for sequence, item in
            enumerate(json.loads(self.plan.proposed_bytes)["files"], 1))
        self.destinations = tuple(self.candidate / f"{self.run}_{seq}_{name}"
                                  for _, seq in self.allocations)
        for destination, payload in zip(self.destinations, (b"first", b"second")):
            destination.write_bytes(payload)

    def observe(self, allocations=None):
        return check.observe_initial_staging_copies(self.candidate, self.plan,
            allocations=self.allocations if allocations is None else allocations, **self.context)

    def test_explicit_order_exact_binding_and_once_only_plan_reconstruction(self):
        self.seed(pc="PC-B", log="ErrorReport")
        with patch.object(check, "prepare_initial_manifest", wraps=check.prepare_initial_manifest) as prepare:
            results = self.observe(self.allocations[::-1])
        prepare.assert_called_once()
        self.assertEqual(tuple(path for path, _ in self.allocations[::-1]), tuple(r.relative_path for r in results))
        self.assertEqual((6, 5), tuple(r.size_bytes for r in results))
        for result in results:
            self.assertIs(self.plan.evidence_bytes, result.evidence_bytes)
            self.assertFalse(result.may_upload or result.may_change_state or result.may_cleanup or result.may_archive)

    def test_allocation_validation_precedes_all_filesystem_reads(self):
        self.seed()
        first, second = self.allocations
        variants = ([first], (list(first),), (first, ("../escape", 2)), (first, (second[0], True)),
                    (first, ("missing.txt", 2)), (first, first), (first, (first[0], 99)),
                    (first, (second[0], first[1])), (first, (second[0],)))
        for allocations in variants:
            with self.subTest(allocations=allocations), patch.object(check, "_source_chain") as chain:
                with self.assertRaises(check.SourceRevalidationError): self.observe(allocations)
                chain.assert_not_called()

    def test_later_missing_or_wrong_size_stops_before_any_hash(self):
        self.seed()
        self.destinations[1].unlink()
        for payload in (None, b"s"):
            if payload is not None: self.destinations[1].write_bytes(payload)
            with patch.object(check, "_hash_stable_file") as read:
                with self.assertRaises(check.SourceRevalidationError): self.observe()
                read.assert_not_called()
        self.assertEqual(b"first", self.destinations[0].read_bytes())

    def test_same_size_wrong_later_content_returns_no_partial_tuple(self):
        self.seed()
        self.destinations[1].write_bytes(b"WRONG!")
        with self.assertRaisesRegex(check.SourceRevalidationError, "staging_copy_content_mismatch"):
            self.observe()
        self.assertEqual(b"WRONG!", self.destinations[1].read_bytes())

    def test_earlier_file_changed_during_later_read_is_rejected_at_batch_end(self):
        self.seed()
        real_hash = check._hash_stable_file
        def changed(path, **options):
            result = real_hash(path, **options)
            if path == self.destinations[1]: self.destinations[0].write_bytes(b"changed first")
            return result
        with patch.object(check, "_hash_stable_file", side_effect=changed):
            with self.assertRaisesRegex(check.SourceRevalidationError, "staging_copy_observation_changed"):
                self.observe()
        self.assertEqual(b"changed first", self.destinations[0].read_bytes())

    def test_growth_after_batch_stat_is_refused_before_open(self):
        self.seed()
        real_hash = check._hash_stable_file
        def grow(path, **options):
            path.write_bytes(b"grown beyond frozen size")
            with patch.object(type(path), "open", side_effect=AssertionError("payload must not open")) as opened:
                try:
                    return real_hash(path, **options)
                finally:
                    opened.assert_not_called()
        with patch.object(check, "_hash_stable_file", side_effect=grow):
            with self.assertRaisesRegex(check.SourceRevalidationError, "staging_copy_observation_unavailable"):
                self.observe()
        self.assertEqual(b"grown beyond frozen size", self.destinations[0].read_bytes())

    def test_empty_selection_still_checks_root_and_is_not_no_work_or_upload_permission(self):
        self.seed()
        with patch.object(check, "_source_chain", wraps=check._source_chain) as chain:
            self.assertEqual((), self.observe(()))
        self.assertEqual(2, chain.call_count)
        with patch.object(check, "_source_chain", side_effect=OSError("synthetic")):
            with self.assertRaises(check.SourceRevalidationError): self.observe(())

    def test_repeated_batch_reobserves_and_retains_corrupted_file(self):
        self.seed()
        self.observe()
        self.destinations[0].write_bytes(b"WRONG")
        with self.assertRaises(check.SourceRevalidationError): self.observe()
        self.assertEqual(b"WRONG", self.destinations[0].read_bytes())


if __name__ == "__main__":
    unittest.main()
