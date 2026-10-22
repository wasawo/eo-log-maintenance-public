# Runtime Entry-Point Validation Gate

- Status: implementation gate proposal; not a runtime implementation or authorization to archive/delete.
- Last updated: 2026-10-22
- Related: `docs/implementation-workflow.md`, `docs/runtime-safety-test-scenarios.md`, `docs/p0-runtime-entrypoint-safety-audit.md`, `docs/manifest-state-transition-v1-proposal.md`
- Current validation helpers: `Common/AggregationReportValidation.ps1`, `Common/AggregationReferencedArtifacts.ps1`, `Common/validate_aggregation_artifacts.py`, `Common/RunInputEvidenceIntegrity.py`

## 1. Purpose

Define the minimum fail-closed integration contract before official `scripts/SyncLogs.ps1` and PC-A-only `scripts/ArchiveLogs.ps1` are implemented. The repository currently has validation helpers but no official sync/archive entry-point scripts. Passing helper tests must not be interpreted as runtime integration or production readiness.

## 2. Entry-point separation

- Sync entry point: may enumerate a configured local source, freeze the target inventory, sync/verify permitted Drive objects, and write run artifacts according to approved manifest/evidence contracts. It must not delete local source files or Drive files.
- Archive entry point: PC-A only. It must independently read and validate both PC-A and PC-B completion manifests and the corresponding frozen inventories, then re-query and re-verify current Drive content immediately before any archive action.
- PC-B must not receive or expose an archive entry point in its runtime package.
- Package distribution (GitHub to Drive) is a separate workflow and must not be called from either log-maintenance entry point.

## 3. Required pre-side-effect validation sequence

The eventual implementation must perform these gates in order. Any failure, exception, timeout, unsupported schema/version, ambiguous result, or incomplete enumeration blocks the operation that depends on it.

1. Validate the invocation mode, PC identity, log type, configured roots, and configuration schema. Reject unknown modes and unknown fields; never infer PC identity from a path.
2. Acquire an exclusive run lock before mutable run state is created. Record ownership with a unique run identity. A process that cannot prove lock ownership must not release another process's lock.
3. For a new sync run, enumerate the complete configured source scope and record traversal errors. A partial/failed enumeration cannot produce `completed` evidence. Freeze a deterministic inventory before upload/sync decisions.
4. Recompute A2 inventory SHA-256 and B2 canonical evidence digest; validate the strict manifest/evidence schemas and all cross-field count/order invariants.
5. Verify that B2 embedded targets exactly match the manifest's frozen file set by relative path, filename, size, and SHA-256. Verify report identity and inventory count/digest against the validated evidence.
6. For every referenced artifact, validate the canonical relative path beneath the explicitly trusted maintenance root, reject reparse/symlink components, read the exact bytes, verify raw-byte SHA-256, and validate the corresponding strict schema. Never use a report-provided absolute path or an untrusted root.
7. Reconcile prior run state conservatively. A crash-left `running` manifest remains incomplete; do not rewrite historical state to manufacture success. Unknown remote outcomes must be reconciled before retry.
8. Before archive, independently validate both PCs' manifests and evidence. Then re-query current Drive state and verify content by trusted Drive SHA-256 or download-and-local-hash; metadata-only identity is insufficient. A stale manifest or prior successful run is not current archive authorization.
9. Only after all required checks succeed may the implementation enter a separately approved archive transaction. Archive/delete capabilities remain disabled until their own explicit policy, tests, and approval are complete.

The current validator helpers cover only parts of steps 4–6. They do not perform source enumeration, lock/recovery, current Drive verification, or archive authorization.

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
- missing/stale/mismatched PC-A or PC-B manifest/evidence;
- Drive object missing, ambiguous, metadata-only match, hash mismatch, inaccessible API, timeout, and transient failure;
- lock contention, stale-lock takeover, owner mismatch, crash at each publication boundary, idempotent retry, and conflicting retry;
- package exclusion of `ArchiveLogs.ps1` from PC-B and absence of active configuration/secrets;
- assertion that all failure cases perform no archive/delete/overwrite operation.

Tests must use synthetic fixtures and temporary directories. No production logs, real credentials, Drive writes, archive enablement, or deletion is permitted as part of these acceptance tests.

## 7. Exit criteria for runtime integration

Runtime integration is not complete until:

1. Official entry-point scripts exist and call the validators in the required order.
2. Lock, atomic publication, recovery, and Drive revalidation behavior are implemented and tested.
3. The runtime package allowlist and PC-specific package exclusions are tested against the actual entry points.
4. End-to-end synthetic acceptance tests demonstrate no destructive side effect under every failure condition.
5. CI passes on the exact PR head and post-merge main commit.
6. Operator-facing configuration, deployment, recovery, and rollback instructions are updated.

Until then, P0 remains open and no release is deployable for real log maintenance.
