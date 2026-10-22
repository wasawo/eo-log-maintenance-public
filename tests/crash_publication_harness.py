"""Synthetic process-crash evidence; never an operational recovery tool.

Only a newly created, explicitly acknowledged child of the OS temporary directory
is accepted. Test artifacts are retained, never cleaned up or repaired here.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from unittest.mock import patch

# Support both unittest discovery and direct, explicitly opted-in invocation.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Common import AtomicArtifactPublication as atomic
from Common.ArtifactSetDirectoryVerification import verify_published_artifact_set
from Common.ArtifactSetPublication import publish_artifact_set_marker_last

PAYLOADS = {"manifest.json": b'{"synthetic":true}\n', "report.json": b'{"items":2}\n'}
TRANSACTION_ID = "123e4567-e89b-42d3-a456-426614174000"
MARKER = "commit-marker.json"
TIMEOUT_SECONDS = 20


class HarnessError(RuntimeError):
    """A fixed reason code, without paths or exception text."""


def create_disposable_root(root: str | Path, *, acknowledged: bool = False) -> Path:
    """Accept only a fresh UUID-named direct child of the local OS temp root.

    This first slice deliberately does not accept operator-selected volumes.
    It is Tier A synthetic evidence, not Tier B qualification.
    """
    if acknowledged is not True:
        raise HarnessError("disposable_acknowledgement_required")
    candidate = Path(root)
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise HarnessError("disposable_root_invalid")
    if not re.fullmatch(r"eo-crash-harness-[0-9a-f]{32}", candidate.name):
        raise HarnessError("disposable_root_name_invalid")
    try:
        temp = Path(tempfile.gettempdir()).resolve(strict=True)
        if candidate.parent != temp:
            raise HarnessError("disposable_root_not_local_temp_child")
        for component in (temp, *temp.parents):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or (
                getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise HarnessError("disposable_root_reparse_component")
        if os.name == "nt":
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
            kernel.GetDriveTypeW.restype = ctypes.c_uint
            if kernel.GetDriveTypeW(temp.anchor) != 3:  # DRIVE_FIXED
                raise HarnessError("disposable_root_not_fixed_local_volume")
        # Existing folders, links and dangling links must never be adopted.
        candidate.mkdir(exist_ok=False)
    except HarnessError:
        raise
    except FileExistsError as exc:
        raise HarnessError("disposable_root_already_exists") from exc
    except OSError as exc:
        raise HarnessError("disposable_root_unavailable") from exc
    return candidate


def _hashes() -> dict[str, str]:
    return {name: hashlib.sha256(data).hexdigest() for name, data in PAYLOADS.items()}


def _publisher(directory: str, connection) -> None:
    real_publish = atomic.publish_bytes_no_overwrite
    completed = 0

    def checkpoint():
        connection.send(("boundary", completed))
        if connection.recv() != "continue":
            raise HarnessError("checkpoint_protocol_invalid")

    def publish(destination, data):
        nonlocal completed
        outcome = real_publish(destination, data)
        completed += 1
        checkpoint()
        return outcome

    try:
        checkpoint()  # Before the first artifact.
        with patch.object(atomic, "publish_bytes_no_overwrite", side_effect=publish):
            publish_artifact_set_marker_last(
                directory, PAYLOADS, transaction_id=TRANSACTION_ID,
            )
    except Exception:
        # No exception messages, absolute paths, tokens or hostnames cross IPC.
        connection.send(("error", "publisher_failed"))
    finally:
        connection.close()


def _observer(directory: str, connection, retry: bool) -> None:
    try:
        root = Path(directory)
        before = {p.name: p.read_bytes() for p in root.iterdir()}
        initial = verify_published_artifact_set(root, _hashes())
        if retry:
            publish_artifact_set_marker_last(
                directory, PAYLOADS, transaction_id=TRANSACTION_ID,
            )
        final = verify_published_artifact_set(root, _hashes())
        after = {p.name: p.read_bytes() for p in root.iterdir()}
        connection.send({
            "initial_committed": initial.may_report_committed,
            "final_committed": final.may_report_committed,
            "preserved": all(after.get(name) == data for name, data in before.items()),
            "names": sorted(after),
            "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in after.items()},
        })
    except Exception:
        connection.send({"error": "observer_failed"})
    finally:
        connection.close()


def _receive(connection):
    if not connection.poll(TIMEOUT_SECONDS):
        raise HarnessError("worker_timeout")
    try:
        return connection.recv()
    except EOFError as exc:
        raise HarnessError("worker_exited_without_result") from exc


def _stop(process) -> None:
    if process.is_alive():
        process.terminate()
    process.join(timeout=5)
    if process.is_alive():
        process.kill()
        process.join(timeout=5)
    if process.is_alive():
        raise HarnessError("worker_stop_failed")


def observe_fresh(directory: Path, *, retry: bool = False) -> dict:
    """Read-only inspection or exact-byte retry in a fresh spawned interpreter.

    Internal harness helper: caller must supply a harness-owned scenario.
    """
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(target=_observer, args=(str(directory), child, retry))
    try:
        process.start()
        child.close()
        result = _receive(parent)
        process.join(timeout=5)
        if process.is_alive() or process.exitcode != 0 or "error" in result:
            raise HarnessError("observer_failed")
        return result
    finally:
        if process.pid is not None:
            _stop(process)
        parent.close()
        child.close()


def run_crash_matrix(root: str | Path, *, acknowledged: bool = False) -> dict:
    """Terminate only this harness's own children at each completed-file boundary."""
    destination = create_disposable_root(root, acknowledged=acknowledged)
    context = multiprocessing.get_context("spawn")
    outcomes = []
    names = sorted(PAYLOADS) + [MARKER]
    for boundary in range(len(names) + 1):
        scenario = destination / ("boundary-" + str(boundary))
        scenario.mkdir()
        parent, child = context.Pipe()
        process = context.Process(target=_publisher, args=(str(scenario), child))
        try:
            process.start()
            child.close()
            for completed in range(boundary + 1):
                if _receive(parent) != ("boundary", completed):
                    raise HarnessError("checkpoint_protocol_invalid")
                if completed < boundary:
                    parent.send("continue")
            _stop(process)  # Actual termination; no publisher finally/rollback.
            if process.exitcode in (None, 0):
                raise HarnessError("publisher_not_terminated")
            observed = observe_fresh(scenario)
            expected_names = sorted(names[:boundary])
            committed = boundary == len(names)
            if observed["names"] != expected_names:
                raise HarnessError("published_subset_mismatch")
            if observed["initial_committed"] != committed:
                raise HarnessError("crash_classification_mismatch")
            if any(observed["sha256"].get(name) != _hashes()[name]
                   for name in PAYLOADS if name in observed["names"]):
                raise HarnessError("published_bytes_mismatch")
            retried = observe_fresh(scenario, retry=True)
            if not retried["final_committed"] or not retried["preserved"]:
                raise HarnessError("idempotent_retry_failed")
            outcomes.append({
                "boundary": boundary,
                "publisher_exit_code": process.exitcode,
                "committed_before_retry": committed,
                "committed_after_retry": retried["final_committed"],
                "published_bytes_preserved": retried["preserved"],
            })
        finally:
            if process.pid is not None:
                _stop(process)
            parent.close()
            child.close()
    return {"evidence_tier": "synthetic-local-temp", "scenarios": outcomes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disposable-root", required=True)
    parser.add_argument("--acknowledge-disposable", action="store_true")
    args = parser.parse_args()
    # Only explicitly supplied local paths are displayed for operator review.
    # This line must not be copied into public evidence or CI logs.
    print("Requested disposable root: " + str(Path(args.disposable_root).absolute()),
          file=sys.stderr, flush=True)
    try:
        result = run_crash_matrix(
            args.disposable_root, acknowledged=args.acknowledge_disposable,
        )
    except (HarnessError, OSError, EOFError):
        print(json.dumps({"error": "synthetic_harness_failed"}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
