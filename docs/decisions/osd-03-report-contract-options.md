# OSD-03 — Derived aggregation report contract decisions

- Status: R1–R7 approved by maintainer on 2026-10-21; executable schema, runtime implementation, and acceptance evidence remain pending.
- Decision basis: approved OSD-03 aggregation semantics, approved manifest v1 field set, approved B2 run-input evidence direction, A2 inventory digest, exhaustive count reconciliation, and local-authoritative/verified-Drive-copy storage.
- Related: `docs/decisions/osd-03-status-aggregation-options.md`, `docs/design/aggregation-report-v1-proposal.md`, `docs/design/run-input-evidence-v1-proposal.md`, `docs/decisions/aggregation-inventory-integrity-options.md`, OSD-02.
- Boundary: this proposal does not authorize runtime implementation, real log access, Drive writes, archive enablement, or deletion. Recommendations are not decisions until the maintainer explicitly selects them.

## Non-negotiable constraints

1. Do not change the approved manifest v1 field set or add aggregation fields to the manifest.
2. The run manifest remains the authoritative per-file outcome record. The immutable run-input evidence is the authoritative record of completed source enumeration, validation results, and the frozen eligible inventory.
3. The aggregation report is derived evidence, not archive/delete authorization.
4. Never use `LastWriteTime` or mutable source re-enumeration to reconstruct a historical run.
5. Missing, malformed, stale/inconsistent-by-identity, incomplete, or unverifiable required inputs fail closed. A missing report cannot imply success or no-work.
6. Reuse the approved OSD-02 publication and per-PC exclusion safety rules where applicable; do not invent unconditional overwrite or age-only stale-owner detection.
7. Synthetic fixtures and temporary directories only; no runtime acceptance is claimed.

## R1. Per-target detail duplicated in the report

- **A — duplicate target rows in each period summary (proposal's current example):** each period contains an `eligible_targets` list with path/name/size/hash/status.
  - Advantage: the report is self-describing.
  - Risk: duplicates the immutable inventory in run-input evidence and per-file outcomes in the manifest; consistency requires cross-validating three copies.
- **B — summaries only; reference the immutable source artifacts (recommended):** each period stores counts and completion state only. The report references the exact manifest and run-input evidence, including their SHA-256 digests, and validates each eligible target against those artifacts when reading the report.
  - Advantage: one authoritative copy for inventory and one for per-file outcomes; fewer divergent copies.
  - Cost: readers must load and validate both referenced artifacts before trusting completion.
- **C — embed inventory in report, omit it from evidence:** rejected because it reopens the approved B2 evidence decision and weakens preservation of initial enumeration/validation facts.

## R2. Report identity and `report_id`

- **A — identity tuple only (recommended):** the unique report identity is exactly `(pc_id, log_type, run_id, report_schema_version)`. Omit the redundant `report_id`; derive the canonical filename from the tuple.
- **B — deterministic `report_id`:** retain the field, defined as a versioned deterministic encoding/hash of the exact identity tuple. Requires a byte-level canonicalization contract and reference vectors.
- **C — random UUID:** easy to generate but permits multiple report IDs for the same run unless a separate uniqueness/collision rule is added; not recommended.

## R3. Referenced source identity

- **A — path plus identity fields:** canonical relative paths and exact identity tuple, but no source-content digest.
- **B — canonical relative path plus SHA-256 of exact bytes (recommended):** `manifest_ref` and `evidence_ref` each contain canonical relative path, schema version, and lowercase 64-character SHA-256 of the validated artifact bytes. The referenced artifact's internal identity must match the report tuple. This detects replacement at a stable path.
- Absolute paths, path guessing, and timestamp-only discovery are rejected.

## R4. Local publication, locking, and temp-file cleanup

- **A — reuse OSD-02 controls (recommended):** publish locally using unique same-directory temporary files, flush/close, read-back validation, and atomic create-if-absent. Reuse the already-held per-PC maintenance lock during normal run publication. Regeneration/recovery must acquire the same mutex plus ownership-token lock record. Existing report identity with identical validated bytes is idempotent; differing bytes are a conflict and are never overwritten.
  - Temp cleanup: a process may remove only its own temp file after confirming its ownership token. Orphan temp files are non-authoritative; retain them for explicit disposition unless owner absence and safe cleanup can be proven without relying on age alone.
- **B — report-specific independent lock:** separate mutex/lock namespace and lifecycle. Rejected as unnecessary coordination complexity and risk of lock-order deadlocks unless an implementation constraint proves shared locking impossible.
- **C — direct final-path writes or unconditional replacement:** rejected.

## R5. Missing report and regeneration

- **A — deterministic regeneration from immutable inputs (recommended):** regenerate only from the exact validated manifest plus immutable B2 evidence. Do not rescan mutable source directories. Validate identity, inventory digest, all counts, and error scope. If inputs are incomplete/unavailable, leave the report unresolved. Existing same-identity identical output is idempotent; any different content is a conflict.
- **B — no regeneration:** a missing report always remains unresolved and requires a new maintenance run. Strongly limits recovery but avoids reconstruction complexity.
- Neither choice permits modifying the old manifest or fabricating enumeration facts.

## R6. Period completion and consistency

- **A — three-state completion (recommended):** `complete`, `incomplete`, `indeterminate`. `complete` only when evidence proves every eligible target for the period is verified and no relevant error affects it. `incomplete` when known failed/unknown targets or known relevant errors prevent completion. `indeterminate` when required inventory/enumeration/validation evidence is missing, malformed, conflicting, or unverifiable. Never map indeterminate to complete.
- **B — binary complete/incomplete:** any uncertain case is collapsed to incomplete. Safer than optimistic behavior but loses the distinction between known failure and insufficient evidence.
- Do not add these values to the manifest's run-status enum. Run status remains governed by the approved existing manifest contract and OSD-03 policy.
- Report summary counts must be recomputed from the referenced manifest and evidence. Reject disagreement, duplicate/missing period rows, a target assigned to multiple periods, inventory digest/count mismatch, or report/manifest/evidence identity mismatch.
- Validate `generated_at_utc` as UTC ISO 8601 uppercase `Z` and apply the approved future-time rule at generation. Historical report age alone must not invalidate immutable evidence.

## R7. Local authoritative artifact and Drive replication

- **A — separate states (recommended):** local validated publication is authoritative; Drive replication is a separate verified step. Report local publication success even if replication fails, but explicitly record sanitized replication failure and never claim cross-PC availability until the Drive copy's identity and exact content are verified.
- **B — coupled success:** treat the overall report as unavailable until local and Drive publication both succeed. This is conservative for cross-PC consumers but risks conflating a valid local artifact with replication failure.
- In either case, never delete or corrupt a valid local report because Drive replication failed. The approved storage direction already requires local authority plus verified Drive copies; this choice clarifies reporting semantics only.

## R8. Acceptance evidence

Regardless of selected options, require synthetic table-driven tests for:
- required fields, nullability, enum and unsupported schema-version rejection;
- identity/path/content-digest mismatch for report, manifest, and evidence;
- inventory count/digest mismatch, missing/extra/duplicate target accounting, count mismatch and duplicate period;
- all approved run aggregation cases, zero-work versus enumeration failure versus only-invalid filenames, and known-period completion plus unrelated run-scope errors;
- report publication crash points, concurrent create, identical idempotent retry, conflicting retry, and unsupported atomic primitive;
- missing/corrupt report regeneration from complete immutable inputs and refusal when evidence is incomplete;
- local success plus Drive replication failure, verified replication, and no cross-PC availability claim before verification;
- no source mutation, Drive deletion, archive action, or deletion side effect.

Evidence status: **tests not yet executed**. This options document is not schema approval and does not close OSD-03, P0-008, or P0-010.


## Maintainer-approved OSD-03 report contract (2026-10-21)

The maintainer explicitly approved **R1-B, R2-A, R3-B, R4-A, R5-A, R6-A, R7-A**. This settles the report-contract options but does not constitute an executable JSON Schema, runtime implementation, or test evidence.

- **R1-B — summaries only:** period entries contain counts and completion state, not duplicated per-target rows. Validate the eligible inventory and per-file outcomes against immutable run-input evidence and the originating manifest.
- **R2-A — tuple identity:** report identity is exactly (pc_id, log_type, run_id, report_schema_version). Omit report_id; derive the canonical filename from that tuple. Do not add fields to manifest v1.
- **R3-B — content-bound references:** manifest_ref and evidence_ref each include canonical relative path, schema version, and lowercase 64-character SHA-256 of exact validated bytes. Validate referenced artifact identity against the report tuple. Reject absolute paths, traversal, identity mismatch, malformed digest, or changed bytes.
- **R4-A — reuse OSD-02 controls:** use unique same-directory temp files, flush/close, read-back validation, and atomic create-if-absent; reuse the existing per-PC maintenance lock during normal publication. Regeneration/recovery must acquire the same named mutex plus ownership-token lock record. Existing same-identity identical bytes are idempotent; different bytes are a conflict and are never overwritten. Remove a temp file only when ownership is proven; orphan temp files are non-authoritative and must not be removed based on age alone.
- **R5-A — deterministic regeneration:** regenerate only from the exact validated manifest plus immutable B2 run-input evidence. Never re-scan mutable source directories to reconstruct historical inventory. Validate identity, inventory digest, all counts, and error scope. If inputs are incomplete/unavailable, remain unresolved. Identical output is idempotent; different content for the same identity is a conflict.
- **R6-A — three-state period completion:** complete only if all eligible targets for the period are verified and no relevant error affects it; incomplete for known failed/unknown targets or known relevant errors; indeterminate if required evidence is missing, malformed, conflicting, or unverifiable. Never map indeterminate to complete. These are report-only values and must not be added to manifest run-status enums.
- **R7-A — separate local/Drive states:** local validated publication is authoritative. Drive replication is a separate verified step; replication failure does not invalidate/delete the local artifact. Do not claim cross-PC availability until the Drive copy's identity and exact content are verified.
- Recompute all summary counts from the referenced manifest and B2 evidence. Reject missing/duplicate period rows, target accounting mismatch, inventory digest/count mismatch, report/manifest/evidence identity mismatch, and inconsistent error scope. generated_at_utc uses UTC ISO 8601 uppercase Z and approved future-time validation; report age alone does not invalidate immutable historical evidence.
- Required synthetic acceptance tests are specified but **not yet executed/evidenced**. Runtime implementation, executable schema, and operational evidence remain pending. No P0 item is closed by this documentation change.


## OSD-03 report-contract acceptance tests — approved design, execution pending

1. Required fields, strict integer schema version, unsupported versions, no implicit migration, and absence of report_id.
2. Canonical report identity tuple and filename agreement for PC/log type/run/schema version.
3. Canonical relative manifest_ref and evidence_ref; exact bytes SHA-256; malformed digest, absolute/traversal path, identity mismatch, and stable-path content replacement all fail closed.
4. R1-B: report period rows contain summaries only; counts recompute from the referenced manifest and B2 evidence; no duplicated per-target inventory is trusted from the report.
5. Inventory digest/count mismatch; missing, extra, duplicate, or multiply assigned target; missing/duplicate period row; report/manifest/evidence identity mismatch; inconsistent error scope.
6. R6-A: complete, incomplete, and indeterminate boundaries; indeterminate never becomes complete and these values never enter manifest v1 run-status enums.
7. R4-A publication crash points, concurrent create, identical idempotent retry, conflicting retry, unsupported atomic primitive, mutex/lock ownership, and temp-file ownership cleanup. Orphan cleanup cannot rely on age alone.
8. R5-A regeneration only from exact immutable manifest and B2 evidence; refuse if evidence is missing, corrupt, incomplete, or inconsistent; never rescan mutable source.
9. R7-A local publication succeeds independently of Drive replication; replication failure preserves local report; cross-PC use is blocked until identity and content verification succeeds.
10. UTC timestamp format/future tolerance, historical age, zero-work versus failed enumeration versus only-invalid filenames, known-period completion with unrelated run-scope errors, and all approved OSD-03 aggregation cases.
11. Synthetic fixtures and temporary directories only. No real logs, credentials, production paths, Drive writes, archive enablement, or deletion. Evidence status: **not run / not yet evidenced**.
