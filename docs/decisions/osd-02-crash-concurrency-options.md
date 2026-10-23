# OSD-02 — Crash, concurrency, and latest-manifest options

- Status: C1–C4 policy approved by maintainer on 2026-10-21; runtime implementation and executable acceptance remain pending.
- Related records: `docs/requirements/p0-open-specification-decisions.md`, `docs/design/manifest-state-transition-v1-proposal.md`, `docs/design/manifest-schema-v1-proposal.md`, `docs/design/staging-file-lifecycle.md`.
- Scope: local manifest publication, concurrent writers on one PC, crash-left `running` manifests, and selection of the current manifest for a PC/log type/period.
- Safety boundary: synthetic/design-only. This proposal does not authorize real log access, Google Drive operations, archive enablement, deletion, or runtime implementation.

## 1. Invariants

1. Validate each candidate's schema and exact agreement between filename identity and JSON identity (`pc_id`, `log_type`, `target_period`, `run_id`).
2. Historical manifests are immutable. A later run uses a new `run_id`.
3. A crash-left `running` manifest remains `running`; never rewrite it automatically to `failure` or `success`.
4. A newer unresolved/running/partial/failed run never permits fallback to an older `success` for an operation requiring current completion.
5. Ties and ambiguous candidates are not resolved by filesystem order, `LastWriteTime`, or unapproved lexical tie-breaks.
6. Stale reads must not overwrite newer state. Re-read and revalidate before commit, or fail closed.
7. Lock, atomicity, identity, read, or enumeration failure blocks dependent operations.
8. The approved 5-minute future tolerance and 24-hour freshness threshold are not lock leases, crash-detection windows, or retry authorization.

## 2. C1 — manifest publication (approved A)

Write to a unique temporary file in the destination directory; flush and close it; re-read and validate the complete bytes; then publish atomically. First publication uses create-if-absent. Updates compare the expected prior identity/version and re-read immediately before atomic replacement. If the filesystem/API cannot guarantee atomicity or compare-before-write, stop without publishing. Direct writes to the final path and unconditional replacement are rejected.

## 3. C2 — same-PC writer exclusion (approved C)

Require both a per-PC/per-maintenance-scope OS named mutex and an exclusive lock record. The record carries a unique ownership token and sanitized process/run identity. Acquire the mutex before creating the record. Release the record only if the token still matches; never delete another owner's lock. A stale record blocks work until explicit recovery verifies the previous owner is gone and records a sanitized disposition. PID alone or age alone is insufficient proof. Lock acquisition failure blocks processing before manifest/source mutation.

## 4. C3 — crash-left running manifest (approved B)

Keep the old `running` manifest immutable and incomplete. After verifying that no previous process/lock owner remains, record recovery disposition separately and start a new run with a new `run_id`. Re-enumerate and rebuild the inventory. Reconcile any uncertain remote upload before retry. Do not convert the old manifest to a terminal state. No timeout automatically changes status or authorizes retry.

## 5. C4 — latest-manifest resolution (approved A)

Resolve candidates within the exact `(pc_id, log_type, target_period)` tuple. Validate every candidate and filename/payload identity agreement. Select only a unique maximum validated `started_at_utc`. A tie at the maximum, malformed/conflicting candidate, incomplete enumeration, or read error is ambiguous and blocks the operation. Do not use `run_id`, filesystem enumeration order, creation time, or `LastWriteTime` as a tie-break. If the unique latest manifest is not acceptable for the requested operation, never fall back to an older success.

## 6. Required synthetic acceptance tests — pending execution

1. Crash before temp creation, during write, after flush, after validation, before publish, and after publish. A failed pre-publish operation leaves an existing authoritative manifest byte-identical; temp files are never authoritative.
2. Concurrent first publication: exactly one create-if-absent succeeds; the other reports conflict without overwrite.
3. Concurrent update: a stale expected version cannot replace newer content.
4. Unsupported atomic primitive: fail closed without publishing.
5. Mutex contention/acquisition failure, abnormal termination, and ownership-token mismatch: no processing or mutation without required locks; one owner cannot release another's lock.
6. Stale-lock recovery: age/PID alone cannot authorize removal; live/ambiguous owner or unknown state blocks.
7. Crash-left `running`: old manifest remains byte-identical; recovery uses a new `run_id` and freshly enumerated inventory.
8. Uncertain upload outcome: reconcile remote state before retry; age/timeout alone never authorizes retry.
9. Resolver cases: no candidate, one candidate, unique latest, equal maximum timestamps, malformed filename, filename/payload mismatch, unreadable candidate, incomplete enumeration, and mismatched scope.
10. Latest `running`, `partial_failure`, `failure`, or incomplete state blocks current-completion-dependent operations and never falls back to older `success`.
11. Malformed timestamps fail closed; filesystem timestamps and lexical run IDs are never tie-breakers.
12. All tests use synthetic fixtures and temporary directories only. No real logs, credentials, production paths, Drive operations, archive enablement, or deletion.

Evidence status: **not run / not yet evidenced**. Documentation approval is not executable acceptance.

## 7. Acceptance boundary

This document records approved design choices, not implementation, executable test results, or operational evidence. The complete transition table remains non-normative where other decisions remain open. OSD-02 runtime enforcement, OSD-03, P0-008, P0-010, and P0-012 remain open as applicable.

## C4 selection implementation slice (2026-10-23)

[Latest selection core](../design/latest-manifest-selection.md) implements the existing EOLM-MAN-002 basename parser, strict candidate/identity checks and unique latest started_at_utc selection over supplied observations. Thirty-two synthetic tests cover ambiguity, malformed/read uncertainty, no fallback and run-time boundaries. Runtime directory enumeration/read binding, actual clock reliability, full semantic/Drive validation, recovery and P0 acceptance remain pending. This implements only the documented C4 subset; it does not close the full acceptance matrix above.
