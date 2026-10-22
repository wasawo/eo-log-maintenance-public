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
from uuid import UUID

from Common import AtomicArtifactPublication as atomic


class ArtifactSetPublicationError(RuntimeError):
    """Stable, sanitized failure from artifact-set publication."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code



def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_payloads(artifacts: Mapping[str, bytes], marker_name: str) -> dict[str, bytes]:
    if not isinstance(artifacts, Mapping) or not artifacts:
        raise ArtifactSetPublicationError("artifact_set_empty_or_invalid")
    if not isinstance(marker_name, str) or not marker_name or marker_name.startswith("."):
        raise ArtifactSetPublicationError("commit_marker_name_invalid")
    if marker_name in {".", ".."} or "/" in marker_name or "\\" in marker_name or "\x00" in marker_name:
        raise ArtifactSetPublicationError("commit_marker_name_invalid")

    copied: dict[str, bytes] = {}
    for name, payload in artifacts.items():
        if (
            not isinstance(name, str)
            or not name
            or name.startswith(".")
            or name in {".", ".."}
            or "/" in name
            or "\\" in name
            or "\x00" in name
            or name == marker_name
        ):
            raise ArtifactSetPublicationError("artifact_name_invalid")
        if not isinstance(payload, bytes):
            raise ArtifactSetPublicationError("artifact_bytes_required")
        copied[name] = payload
    return copied


def publish_artifact_set_marker_last(
    destination_dir: str,
    artifacts: Mapping[str, bytes],
    *,
    transaction_id: str,
    commit_marker_name: str = "commit-marker.json",
) -> dict[str, str]:
    """Publish files without overwrite, then publish a commit marker last.

    Existing identical artifacts are idempotent. Any conflicting destination
    fails closed. A failure leaves already-published artifacts in place for
    later reconciliation; it never rolls them back or removes them.
    """
    try:
        parsed_id = UUID(transaction_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ArtifactSetPublicationError("transaction_id_invalid") from exc
    if str(parsed_id) != transaction_id.lower():
        raise ArtifactSetPublicationError("transaction_id_invalid")

    payloads = _validate_payloads(artifacts, commit_marker_name)
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
