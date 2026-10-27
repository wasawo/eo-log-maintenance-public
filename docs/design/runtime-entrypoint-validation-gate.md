# Runtime Entry-Point Validation Gate

- Status: implementation gate proposal; not a runtime implementation or authorization to archive/delete.
- Last updated: 2026-10-22

2026-10-27 policy revision: [Q1–Q10 and flattening](../requirements/log-move-requirements.md) govern the two move routes. Requirements below are aligned with that policy; the new source-deletion IPC/persistence/verification contracts are not yet specified or implemented. Existing v1 validators remain copy/verification helpers, not proof of completed movement.
- Related: `docs/development/implementation-workflow.md`, `docs/validation/runtime-safety-test-scenarios.md`, `docs/validation/p0-runtime-entrypoint-safety-audit.md`, `docs/design/manifest-state-transition-v1-proposal.md`
- Current validation helpers: `Common/AggregationReportValidation.ps1`, `Common/AggregationReferencedArtifacts.ps1`, `Common/validate_aggregation_artifacts.py`, `Common/RunInputEvidenceIntegrity.py`

## 1. Purpose

Define the minimum fail-closed integration contract before official `scripts/SyncLogs.ps1` and PC-A-only `scripts/ArchiveLogs.ps1` are implemented. The repository currently has validation helpers but no official sync/archive entry-point scripts. Passing helper tests must not be interpreted as runtime integration or production readiness.

## 2. Entry-point separation

- Sync entry point: each PC moves its own eligible local sources to the shared cloud log-type folders, flattening subfolders. Delete only an individually identified local source after destination-content equality and source unchanged since copying are verified. It cannot delete cloud sources.
- Archive entry point: PC-A only. Process current eligible cloud files independently of either PC's period-completion manifests. Verify the archive destination and cloud source unchanged since copying before deleting only that cloud source; late arrivals are processed later.
- PC-B must not receive or expose an archive entry point in its runtime package.
- Package distribution (GitHub to Drive) is a separate workflow and must not be called from either log-maintenance entry point.

## 3. Required pre-side-effect validation sequence

The eventual implementation must perform these gates in order. Any failure, exception, timeout, unsupported schema/version, ambiguous result, or incomplete enumeration blocks the operation that depends on it.

1. Validate the invocation mode, PC identity, log type, configured roots, and configuration schema. Reject unknown modes and unknown fields; never infer PC identity from a path.
2. Acquire an exclusive run lock before mutable run state is created. Record ownership with a unique run identity. A process that cannot prove lock ownership must not release another process's lock.
3. For a new sync run, enumerate the complete configured source scope and record traversal errors. A partial/failed enumeration cannot produce `completed` evidence. Freeze a deterministic inventory before upload/sync decisions.
4. For the existing source/manifest/evidence pipeline, recompute A2 inventory SHA-256 and B2 canonical evidence digest; validate strict schemas and cross-field count/order invariants. Archive needs its own current cloud-target binding; do not impose both PCs' local B2 sets as an archive eligibility prerequisite.
5. Verify that B2 embedded targets exactly match the manifest's frozen file set by relative path, filename, size, and SHA-256. Verify report identity and inventory count/digest against the validated evidence.
6. For every referenced artifact, validate the canonical relative path beneath the explicitly trusted maintenance root, reject reparse/symlink components, read the exact bytes, verify raw-byte SHA-256, and validate the corresponding strict schema. Never use a report-provided absolute path or an untrusted root.
7. Reconcile prior run state conservatively. A crash-left `running` manifest remains incomplete; do not rewrite historical state to manufacture success. Unknown remote outcomes must be reconciled before retry.
8. Before each archive move, query current Drive state, bind the selected cloud source to the destination, and verify actual content; metadata-only identity is insufficient. Validate records needed for that file, without waiting for both PCs' period completion. Prior success is not current verification.
9. Before deleting any source in either route, confirm destination-content equality and source unchanged since copying for that exact source. Failure/uncertainty retains it. Record copy/verification/deletion results separately; a copy-only verified state is not completed movement. Verification methods, deletion response/unknown-outcome handling and persistence contracts require further design. During document review no deletion code/schema or real-data operation is added.

The validators cover parts of steps 4–6. Separate source-inventory, lock, publication and recovery helpers now also exist; they are not an integrated official runtime. Current Drive verification and archive authorization remain absent. See [current inventory](../status/first-release-readiness-20261024.md) for implemented scope and remaining environment qualification.

## 4. Publication and recovery requirements

- Write artifacts to uniquely named temporary files in the destination directory; flush/close before publication and use a platform-supported atomic create/replace primitive whose guarantees are tested.
- Do not overwrite an existing run artifact. A byte-identical retry may be treated as idempotent only after exact identity and digest comparison; conflicting content must fail closed.
- A crash between artifact writes must leave an explicitly incomplete run, not a fabricated complete result. Orphan cleanup must be ownership-based, not age-only.
- Preserve evidence needed to diagnose failure. Do not rewrite prior manifests to reflect later archive-time observations.
- Lock stale-recovery must prove the previous owner is no longer active before takeover. Age alone is insufficient.
- Path checks must be repeated at the point of use; the existing symlink/reparse checks are defense-in-depth and are not a complete defense against hostile concurrent filesystem mutation.

## 5. Failure contract

- Return a stable, sanitized reason code and nonzero process exit for rejected/incomplete operations.
- Never print secrets, file contents, raw exception text, user-specific absolute paths, or untrusted server responses to standard output/error.
- Distinguish confirmed failure from unknown outcome. Timeout, network loss, inaccessible remote state, and exhausted retries without definitive evidence remain unknown.
- Failure to validate a manifest, evidence, report, inventory, lock, or current Drive state blocks the dependent side effect.
- Validation failure must not trigger local-source deletion, Drive deletion, overwrite, archive, or fallback to weaker metadata-only verification.

## 6. Required synthetic acceptance tests before enabling runtime effects

At minimum, tests must cover:

- incomplete source traversal and enumeration errors;
- source changes during enumeration and deterministic frozen inventory;
- manifest/evidence identity and target-set mismatch;
- A2/B2 digest mismatch, duplicate/unsorted targets, count reconciliation failures;
- malformed JSON, duplicate keys, unsupported schema versions, unknown fields, path traversal, symlink/reparse points, and referenced-byte replacement;
- missing/stale/mismatched evidence required for the affected file, and independent current-file archive while PC-B has no successful period manifest;
- Drive object missing, ambiguous, metadata-only match, hash mismatch, inaccessible API, timeout, and transient failure;
- lock contention, stale-lock takeover, owner mismatch, crash at each publication boundary, idempotent retry, and conflicting retry;
- package exclusion of `ArchiveLogs.ps1` from PC-B and absence of active configuration/secrets;
- per-file verification failures retain that source and do not overwrite destinations; independent valid files can complete while a different file fails;
- verified source deletion, changed-source refusal, identical-content reuse, differing-content hold without suffix renaming, and uncertain-outcome reconciliation in isolated synthetic fixtures.

Tests must use synthetic fixtures, temporary directories and mock Drive. Future move tests must check permitted deletion of synthetic sources and refusal outside the two routes/Q5 conditions. No production logs, real credentials, production Drive writes/deletion or deployment is permitted. Existing helper tests are not changed into runtime evidence by this revision.

## 7. Exit criteria for runtime integration

Runtime integration is not complete until:

1. Official entry-point scripts exist and call the validators in the required order.
2. Lock, atomic publication, recovery, and Drive revalidation behavior are implemented and tested.
3. The runtime package allowlist and PC-specific package exclusions are tested against the actual entry points.
4. End-to-end synthetic acceptance tests demonstrate correct per-source completion, retention on failed/unknown verification, normal rerun, and no operation outside the permitted routes/roles. Failure of one file does not prohibit completion of another independent verified file.
5. CI passes on the exact PR head and post-merge main commit.
6. Operator-facing configuration, deployment, recovery, and rollback instructions are updated.

Until then, P0 remains open and no release is deployable for real log maintenance.
