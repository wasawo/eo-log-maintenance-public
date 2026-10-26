"""Pure classifier for multi-artifact publication/recovery evidence.

This module does not write, publish, remove, or reconcile files. A commit marker
is treated as authoritative only when it exactly binds the expected artifact
set and every published artifact is present with the expected SHA-256.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TX_ID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_RESERVED = {".", ".."}


@dataclass(frozen=True)
class ArtifactSetDecision:
    state: str
    reason_code: str
    may_report_committed: bool = False
    may_publish_next: bool = False
    requires_reconciliation: bool = True
    preserve_existing_artifacts: bool = True


def _blocked(reason: str) -> ArtifactSetDecision:
    return ArtifactSetDecision("blocked", reason)


def is_artifact_transaction_id(value: Any) -> bool:
    """Existing marker grammar: hyphenated UUID, version 1-8, RFC variant."""
    return isinstance(value, str) and _TX_ID.fullmatch(value) is not None


def _copy_mapping(value):
    if not isinstance(value, Mapping):
        return None
    try:
        return dict(value)
    except Exception:
        return None


def _valid_artifact_map(value: Any) -> bool:
    if not isinstance(value, Mapping) or not value:
        return False
    for name, digest in value.items():
        if (
            not isinstance(name, str)
            or not name
            or name in _RESERVED
            or "/" in name
            or "\\" in name
            or "\x00" in name
            or name.startswith(".")
            or not isinstance(digest, str)
            or not _SHA256.fullmatch(digest)
        ):
            return False
    return True


def classify_artifact_set(
    *,
    expected_sha256: Mapping[str, str],
    published_sha256: Mapping[str, str],
    staged_sha256: Mapping[str, str],
    commit_marker: Any = None,
    expected_transaction_id: str | None = None,
) -> ArtifactSetDecision:
    """Classify a synthetic artifact set without performing recovery side effects.

    The caller must supply SHA-256 values computed from observed bytes, not
    metadata or a filename. Unknown/extra published artifacts fail closed.
    Optional expected_transaction_id is an independent exact string binding;
    omitting it does not prove which attempt owns a valid marker.
    """
    if expected_transaction_id is not None and (
            type(expected_transaction_id) is not str or not is_artifact_transaction_id(expected_transaction_id)):
        return _blocked("expected_transaction_id_invalid")
    expected = _copy_mapping(expected_sha256)
    if not _valid_artifact_map(expected):
        return _blocked("expected_artifact_set_invalid")
    published = _copy_mapping(published_sha256)
    if published is None:
        return _blocked("published_artifact_set_invalid")
    staged = _copy_mapping(staged_sha256)
    if staged is None:
        return _blocked("staged_artifact_set_invalid")

    # Every observed artifact entry must be syntactically valid, including extras.
    if published and not _valid_artifact_map(published):
        return _blocked("published_artifact_set_invalid")
    if staged and not _valid_artifact_map(staged):
        return _blocked("staged_artifact_set_invalid")
    if set(published) - set(expected):
        return _blocked("unexpected_published_artifact")
    if set(staged) - set(expected):
        return _blocked("unexpected_staged_artifact")
    if any(expected[name] != digest for name, digest in published.items()):
        return _blocked("published_artifact_digest_mismatch")
    if any(expected[name] != digest for name, digest in staged.items()):
        return _blocked("staged_artifact_digest_mismatch")

    if commit_marker is not None:
        marker = _copy_mapping(commit_marker)
        if marker is None:
            return _blocked("commit_marker_invalid")
        if set(marker) != {"schema_version", "transaction_id", "artifact_sha256"}:
            return _blocked("commit_marker_shape_invalid")
        if type(marker.get("schema_version")) is not int or marker["schema_version"] != 1:
            return _blocked("commit_marker_version_invalid")
        transaction_id = marker.get("transaction_id")
        if not is_artifact_transaction_id(transaction_id):
            return _blocked("commit_marker_transaction_id_invalid")
        if expected_transaction_id is not None and transaction_id != expected_transaction_id:
            return _blocked("commit_marker_transaction_id_mismatch")
        marker_hashes = _copy_mapping(marker.get("artifact_sha256"))
        if not _valid_artifact_map(marker_hashes) or marker_hashes != expected:
            return _blocked("commit_marker_artifact_set_mismatch")
        if published != expected:
            return _blocked("commit_marker_published_set_incomplete")
        return ArtifactSetDecision(
            state="committed",
            reason_code="commit_marker_and_artifacts_verified",
            may_report_committed=True,
            may_publish_next=False,
            requires_reconciliation=False,
            preserve_existing_artifacts=True,
        )

    if published == expected:
        return ArtifactSetDecision(
            state="marker_missing",
            reason_code="all_artifacts_present_without_commit_marker",
            may_report_committed=False,
            may_publish_next=False,
            requires_reconciliation=True,
            preserve_existing_artifacts=True,
        )
    if published:
        return ArtifactSetDecision(
            state="partial_publication",
            reason_code="published_subset_without_commit_marker",
            may_report_committed=False,
            may_publish_next=False,
            requires_reconciliation=True,
            preserve_existing_artifacts=True,
        )
    if staged == expected:
        return ArtifactSetDecision(
            state="ready",
            reason_code="staged_set_matches_expected",
            may_report_committed=False,
            may_publish_next=True,
            requires_reconciliation=False,
            preserve_existing_artifacts=True,
        )
    if staged:
        return ArtifactSetDecision(
            state="staging_incomplete",
            reason_code="staged_subset_without_publication",
            may_report_committed=False,
            may_publish_next=False,
            requires_reconciliation=True,
            preserve_existing_artifacts=True,
        )
    return ArtifactSetDecision(
        state="nothing_published",
        reason_code="no_staged_or_published_artifacts",
        may_report_committed=False,
        may_publish_next=False,
        requires_reconciliation=False,
        preserve_existing_artifacts=True,
    )
