"""Marker-last publication of a validated artifact set.

This helper composes the single-file no-overwrite primitive. It is not a
filesystem-wide multi-file transaction: a crash can leave a published subset.
The commit marker is published last, and no rollback or cleanup is attempted.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Mapping

from Common import AtomicArtifactPublication as atomic
from Common.ArtifactSetRecovery import is_artifact_transaction_id, is_artifact_basename


class ArtifactSetPublicationError(RuntimeError):
    """Stable, sanitized failure from artifact-set publication."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code



def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_payloads(artifacts: Mapping[str, bytes], marker_name: str) -> dict[str, bytes]:
    if not isinstance(artifacts, Mapping):
        raise ArtifactSetPublicationError("artifact_set_empty_or_invalid")
    try:
        copied = dict(artifacts)
    except Exception:
        raise ArtifactSetPublicationError("artifact_set_empty_or_invalid") from None
    if not copied:
        raise ArtifactSetPublicationError("artifact_set_empty_or_invalid")
    if not is_artifact_basename(marker_name):
        raise ArtifactSetPublicationError("commit_marker_name_invalid")

    for name, payload in copied.items():
        if (
            not is_artifact_basename(name)
            or name == marker_name
        ):
            raise ArtifactSetPublicationError("artifact_name_invalid")
        if not isinstance(payload, bytes):
            raise ArtifactSetPublicationError("artifact_bytes_required")
        if type(payload) is not bytes:
            copied[name] = memoryview(payload).tobytes()
    return copied


def publish_artifact_set_marker_last(
    destination_dir: str,
    artifacts: Mapping[str, bytes],
    *,
    transaction_id: str,
    commit_marker_name: str = "commit-marker.json",
    maximum_artifact_bytes: int | None = None,
    maximum_total_bytes: int | None = None,
) -> dict[str, str]:
    """Publish files without overwrite, then publish a commit marker last.

    Existing identical artifacts are idempotent. Any conflicting destination
    fails closed. A failure leaves already-published artifacts in place for
    later reconciliation; it never rolls them back or removes them.
    Caller-selected byte limits include the generated marker and are checked
    before publishing any file. They do not qualify roots or authorize a run.
    """
    if type(transaction_id) is not str or not is_artifact_transaction_id(transaction_id):
        raise ArtifactSetPublicationError("transaction_id_invalid")
    if any(value is not None and (type(value) is not int or value < 1)
           for value in (maximum_artifact_bytes, maximum_total_bytes)):
        raise ArtifactSetPublicationError("artifact_publish_limit_invalid")

    payloads = _validate_payloads(artifacts, commit_marker_name)
    if maximum_artifact_bytes is not None and any(len(data) > maximum_artifact_bytes for data in payloads.values()):
        raise ArtifactSetPublicationError("artifact_publish_file_limit_exceeded")
    payload_total = sum(len(data) for data in payloads.values())
    if maximum_total_bytes is not None and payload_total > maximum_total_bytes:
        raise ArtifactSetPublicationError("artifact_publish_total_limit_exceeded")
    hashes = {name: _digest(payload) for name, payload in payloads.items()}
    marker_bytes = (
        json.dumps(
            {
                "schema_version": 1,
                "transaction_id": transaction_id,
                "artifact_sha256": hashes,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    if maximum_artifact_bytes is not None and len(marker_bytes) > maximum_artifact_bytes:
        raise ArtifactSetPublicationError("artifact_publish_file_limit_exceeded")
    if maximum_total_bytes is not None and payload_total + len(marker_bytes) > maximum_total_bytes:
        raise ArtifactSetPublicationError("artifact_publish_total_limit_exceeded")

    outcomes: dict[str, str] = {}
    try:
        for name in sorted(payloads):
            outcomes[name] = atomic.publish_bytes_no_overwrite(
                os.path.join(destination_dir, name), payloads[name]
            )
        outcomes[commit_marker_name] = atomic.publish_bytes_no_overwrite(
            os.path.join(destination_dir, commit_marker_name), marker_bytes
        )
    except atomic.ArtifactPublicationError as exc:
        raise ArtifactSetPublicationError(exc.reason_code) from exc
    return outcomes
