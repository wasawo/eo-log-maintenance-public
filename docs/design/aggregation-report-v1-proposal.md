# Derived Aggregation Report v1 Proposal

- Status: derived-report representation and R1–R7 report-contract policy approved on 2026-10-21; structural JSON Schema v1 merged in PR #150; report-local consistency checks merged in PR #151; exact-byte reference helper merged in PR #152; B2 schema merged in PR #153; manifest schema merged in PR #154. PR #155 adds an independently callable schema/identity validator for report-referenced artifacts; PR #156 adds a validation-only A2/B2 digest and count-reconciliation helper. Production entry-point integration and full acceptance remain pending.
- Decision basis: C-33 and the OSD-02/OSD-03 representation decision dated 2026-10-21.
- Scope: persist run/period aggregation results and run-scope validation errors without changing the approved manifest v1 field set.
- Non-goal: this document does not claim runtime implementation or executable test evidence.
- Decision support: see [Aggregation Inventory Integrity — Decision Options](../decisions/aggregation-inventory-integrity-options.md) for remaining inventory hashing and completeness-evidence decisions.
- Enumeration/validation evidence schema draft: [Run Input Evidence v1 Proposal](run-input-evidence-v1-proposal.md). B2 representation, count reconciliation, source-entry universe, canonicalization, traversal completion rule (C-41), best-effort concurrent source mutation detection (C-42), enumeration status semantics (C-43), and distinct-event enumeration error counting (C-44) are approved; executable schema and synthetic contract tests are introduced in PR #153; cross-artifact runtime implementation remains pending.
- Approved storage direction (2026-10-21): local authoritative report/evidence artifacts with verified Google Drive copies for access from both PCs. A Drive copy is not authoritative/available to consumers until identity and content verification succeeds; publication must follow the approved OSD-02 atomic create-if-absent and lock ownership controls; implementation remains pending.
- G1 generated-UTC derivation approved 2026-10-24: use the later original finish-UTC string from exact manifest/B2 inputs, choosing the manifest spelling for equal instants. The [selected-policy record](../decisions/selected-policy-decisions-20261024.md#3-g1の確定規則) is authoritative; builder follow-up and regeneration acceptance remain unimplemented.
- Approved inventory digest direction (2026-10-21): A2 versioned length-prefixed records; exact contract and reference vectors are recorded in `docs/decisions/aggregation-inventory-integrity-options.md`. B2 immutable run-input evidence, embedded inventory, exhaustive count reconciliation, and canonical evidence digest rules are approved and specified in `docs/design/run-input-evidence-v1-proposal.md` and `docs/decisions/aggregation-inventory-integrity-options.md`.

## 1. Design principles

1. Preserve the approved manifest v1 field set and its strict validation rules. Do not add period-summary or unassigned-error fields to that manifest.
2. Produce one derived aggregation report per maintenance run, linked to the originating manifest by `run_id` and manifest identity.
3. Derive file outcomes from the originating run manifest and period eligibility from the frozen filename-based inventory. Never use `LastWriteTime` as a period fallback.
4. Record unclassifiable relevant filenames as run-scope validation errors. Do not invent a period for them.
5. A report may certify a period complete only when report identity, inventory, file outcomes, and relevant error scope can all be validated.
6. Missing, malformed, stale, or inconsistent evidence must fail closed. It must never be interpreted as a complete period.
7. This report is derived evidence, not a replacement for the run manifest and not authorization to archive or delete any source.

## 2. Storage and identity

Proposed local authoritative directory:

```text
<local-maintenance-root>/_maintenance/aggregation-reports/<PC-ID>/
```

Publish a verified copy to the configured Google Drive maintenance root using the existing verified-upload discipline. The canonical local root and Drive destination mapping must be configuration-defined, not guessed from the current working directory. Local report creation and Drive replication are separate states: replication failure must leave the validated local artifact intact and must not claim cross-PC availability. The report identity is exactly (pc_id, log_type, run_id, report_schema_version); no separate report_id is stored.

Canonical filename derived from the identity tuple:

```text
<PC-ID>_<LogType>_<run_id>_v<report_schema_version>.aggregation.json
```

The PC ID, log type, and run ID in the filename must exactly match the corresponding report fields and the referenced manifest identity. The report must reference the manifest by its canonical relative path or exact manifest filename; implementations must not discover a manifest by guessing from timestamps.

One report is produced for one run. It may contain summaries for multiple periods and run-scope errors that cannot be assigned to a period.

## 3. Proposed JSON schema shape

The approved structural contract is implemented as a Draft 2020-12 schema in `contracts/aggregation-report-v1.schema.json` (PR #150); PR-head and post-merge CI passed. A bounded report-local consistency validator in `Common/AggregationReportValidation.ps1` merged in PR #151 and passed CI. A separate exact-byte reference helper in `Common/AggregationArtifactReference.ps1` was merged in PR #152. Neither replaces schema validation and cross-artifact semantic checks. Full acceptance remains pending.

```json
{
  "report_schema_version": 1,
  "run_id": "<originating run id>",
  "pc_id": "PC-A",
  "log_type": "BattleLog",
  "manifest_ref": {
    "path": "_maintenance/manifests/PC-A/PC-A_BattleLog_2026-09_<run_id>.json",
    "schema_version": 1,
    "sha256": "<lowercase SHA-256 of exact validated manifest bytes>"
  },
  "evidence_ref": {
    "path": "_maintenance/run-input-evidence/PC-A/PC-A_BattleLog_<run_id>.evidence.json",
    "schema_version": 1,
    "sha256": "<lowercase SHA-256 of exact validated evidence bytes>"
  },
  "generated_at_utc": "2026-10-21T00:00:00Z",
  "inventory_ref": {
    "kind": "b2_run_input_evidence_inventory",
    "eligible_target_count": 12,
    "inventory_sha256": "<digest of canonical frozen eligible inventory>"
  },
  "run_aggregation": {
    "status": "partial_failure",
    "outcome": null,
    "verified_count": 10,
    "failed_count": 1,
    "unknown_count": 1,
    "run_scope_error_count": 0,
    "enumeration_complete": true,
    "validation_complete": true
  },
  "periods": [
    {
      "period": "2026-09",
      "completion": "incomplete",
      "eligible_count": 12,
      "verified_count": 10,
      "failed_count": 1,
      "unknown_count": 1,
      "relevant_error_count": 0
    }
  ],
  "run_scope_errors": [
    {
      "error_id": "VAL-0001",
      "code": "unclassifiable_relevant_filename",
      "filename": "unexpected-name.txt",
      "relative_path": "unexpected-name.txt",
      "period": null,
      "affects_run": true,
      "affects_periods": [],
      "message": "Filename did not match the approved period classification rule."
    }
  ]
}
```

Illustrative values only; the sample counts and values are not test evidence. The report should avoid secrets, OAuth data, file contents, and unsanitized exception text.

### 3.1 Field intent

| Field | Purpose / validation |
|---|---|
| `report_schema_version` | Required integer; reject missing, malformed, or unsupported versions. No implicit migration. |
| Identity | The tuple (pc_id, log_type, run_id, report_schema_version) is the unique report identity; no report_id field is stored. |
| `run_id`, `pc_id`, `log_type` | Must match the originating manifest identity. |
| `manifest_ref` | Canonical relative path, schema version, and SHA-256 of exact validated manifest bytes; referenced manifest must be parsed and validated. |
| `generated_at_utc` | Approved G1: compare exact manifest.finished_at_utc and B2.enumeration.finished_at_utc as UTC instants without rounding; preserve the later original string, or the manifest's original spelling for equal instants. An immutable-input anchor, not actual report-write time, freshness or cloud-observation proof. |
| `evidence_ref` | Canonical relative path, schema version, and SHA-256 of exact validated B2 run-input evidence bytes. |
| `inventory_ref` | Identifies the exact frozen eligible inventory; count and digest must match the validated manifest target list and B2 evidence. |
| `run_aggregation` | Summary must be reproducible from validated file outcomes, enumeration/validation results, and run-scope errors. |
| `periods` | One summary-only entry per period; eligible targets are resolved from manifest and B2 evidence, not duplicated in the report. Completion is complete, incomplete, or indeterminate. |
| `run_scope_errors` | Errors that cannot be assigned to one period; period must be null and they must not be silently dropped. |

The inventory digest contract A2 (versioned length-prefixed records) and immutable B2 run-input evidence direction are approved and specified in `docs/decisions/aggregation-inventory-integrity-options.md` and `docs/design/run-input-evidence-v1-proposal.md`. The storage direction C3 (local authoritative artifacts plus verified Drive copies) is also approved. The report structural schema candidate is in PR #150; B2's executable schema, reference-vector tests, cross-artifact runtime validation, report publication/recovery, and Drive replication remain pending.

## 4. Aggregation semantics

Implementation slice: `Common/AggregationReportBuilder.py` currently derives report bytes from explicit exact manifest/B2 bytes and caller-supplied trusted static schemas, canonical references, generated UTC, reliable current UTC and future tolerance (default/maximum five minutes, configurable down to zero). It reuses A2/B2 and manifest-inventory checks, validates terminal verification outcomes, and performs no source scan, filesystem/Drive/lock/publication or status mutation. T-01–12 synthetic tests cover both log types; report periods use filename-derived months, including ErrorReport, independently of the manifest's annual target_period. All supplied relevant errors remain accounted for as period counts or unassigned run-scope records. A completed validation with exhaustive accounting can preserve an independently complete known period despite an unclassifiable error. Incomplete validation is not promoted by matching counts; unaffected periods remain indeterminate without the required coverage evidence. B2 V1's completed/error-independent meaning and report G1's exact-input time source are now selected, but the source helper still emits incomplete for validation errors and the report builder still takes caller-supplied generated UTC. Producer/consumer follow-up, G1 derivation/mismatch rejection and formal regeneration acceptance remain unimplemented. This slice does not approve the full transition table, runtime acceptance, cloud verification or authorization. See the [V1/G1 comparison history](../decisions/b2-validation-coverage-report-time-options.md) and [selection record](../decisions/selected-policy-decisions-20261024.md).

Use the approved OSD-03 policy in `docs/decisions/osd-03-status-aggregation-options.md`:

- Run-level `success`: all eligible targets are `verified` and there are no relevant validation/processing errors.
- A validated zero-work run is `success` with `outcome: no_work` only when enumeration and validation completed successfully and no eligible targets exist.
- Run-level `partial_failure`: at least one eligible target is verified and either (a) at least one eligible target is `failed`/`unknown`, or (b) a relevant unclassifiable run-scope error exists.
- Run-level `failure`: no eligible target is verified and a processing/validation failure or relevant unclassifiable run-scope error exists, or a valid no-work result cannot be established.
- Period completion is `complete` only when every eligible target assigned to that period is `verified` and no relevant validation/processing error affects it; use `incomplete` for known failed/unknown targets or relevant errors, and `indeterminate` when required evidence is missing, malformed, conflicting, or unverifiable. These are report-only values, not manifest enums.
- An unclassifiable relevant filename blocks run-level success but does not automatically invalidate an independently complete known period whose inventory and relevant error scope are established.
- `unknown` never counts as verified. Do not add run-status or outcome enum values.

The report's run status/outcome must agree with the originating manifest. If the manifest does not contain an outcome for a non-zero-work run, the report must not invent a new manifest value; it records the computed aggregation and validation must follow the approved manifest contract.

### Approved G1 generated UTC (2026-10-24)

Use only `finished_at_utc` from the exact immutable manifest and `enumeration.finished_at_utc` from the exact immutable B2 evidence. Compare valid UTC instants at the existing supported precision without rounding or truncation. Choose the later input's original string for `generated_at_utc`; if they represent the same instant, choose the manifest's original string. This defines the immutable-input anchor, not the wall-clock time when bytes were written. It is an explicit approved derivation, not an implicit finish-time substitution by the current implementation.

Missing/invalid required values or contradictions with the existing time checks stop derivation; do not fill them from a real clock, guessed value or another stored artifact. Preserve exact-input identity/digest validation, reliable current UTC, the existing maximum five-minute future tolerance, start/finish ordering and historical-age rules. Do not expire immutable historical evidence solely by age. R5-A remains exact manifest plus B2 only, with the same report identity, identical-byte idempotence and different-byte conflict; G2/G3 are not adopted. Do not rewrite previous reports into G1 form. The caller-time builder has not yet implemented this derivation or rejection of a mismatching supplied time.

## 5. Inventory and per-period integrity

1. Read and validate the exact manifest referenced by manifest_ref and the exact immutable B2 evidence referenced by evidence_ref. Verify each referenced artifact's SHA-256 against its exact bytes and validate internal identity.
2. Reconstruct the frozen eligible-target set from the B2 run-input evidence. Cross-check its identity and eligible target outcomes against the originating manifest; do not re-enumerate mutable source directories to retroactively redefine the run's inventory.
3. Validate eligible-target count and the A2 inventory digest against the canonical frozen inventory in B2 evidence and the report's inventory_ref. Reject any disagreement.
4. For each eligible target, validate identity, expected hash, and per-file status against the originating manifest. Reject duplicate, missing, extra, or conflicting target entries.
5. Derive each target's period from the approved filename rule only. Reject period assignment based on filesystem timestamps or Drive metadata.
6. Recompute every period summary and run summary from the validated evidence and manifest. Each eligible target must be assigned exactly once to a period; reject missing/duplicate period rows or count disagreement.
7. A relevant error may affect a period only when the approved rules establish that relationship. Unassigned/run-scope errors remain visible at run scope and must not be guessed into a period.
8. If the report cannot establish that the inventory and error set are complete, period completion is indeterminate and must not be reported as complete.

The frozen eligible target list in the manifest does not, by itself, prove that initial directory enumeration completed or that all invalid/unclassifiable names were recorded. The approved B2 direction requires separate immutable run-input evidence; its proposal is `docs/design/run-input-evidence-v1-proposal.md`. Until that evidence has an approved executable schema and validated runtime implementation, the report must not certify a period complete where completeness depends on missing evidence.

## 6. Publication, crash behavior, and regeneration

Proposed safe publication contract:

1. Build the report in a temporary file in the same filesystem/directory as the final report.
2. Serialize deterministically; flush/close the temporary file; re-read and validate it.
3. Validate its source manifest and inventory references before publication.
4. Publish the local authoritative report with a same-filesystem atomic create operation that does not expose a partially written final report. Never assume local filesystem atomicity applies to Drive.
5. Replicate the validated report and its referenced immutable evidence to the configured Drive destination using a separately specified upload/verification procedure. Treat the Drive copy as published only after exact identity and content verification. Record sanitized replication failure diagnostics without deleting or corrupting the local authoritative artifact.
6. If a final report for the same report identity already exists, do not overwrite it blindly. Compare validated content and either treat an identical report as idempotent or fail safely on conflict.
7. A crash before publication leaves a temporary artifact that is not authoritative. Do not treat it as a final report or period-completion evidence.
8. A missing final report may be regenerated only from the same immutable manifest and a trustworthy preserved inventory/validation record. Do not re-scan current mutable source state and claim it is the original run.
9. If required inputs are unavailable, conflicting, or cannot prove the original run's complete inventory, retain the run as unresolved; do not fabricate a replacement report.
10. Report-write or validation failure must be visible operationally and must never turn a failed/partial run into success.

Open details before implementation: locking interaction with the global per-PC maintenance lock, temp-file cleanup policy, report collision behavior, exact atomic replace primitive, and stale/incomplete report recovery.

## 7. Freshness and consistency

- `generated_at_utc` is the G1 immutable-input anchor, not actual write time or a freshness proof.
- A report is valid only for its exact referenced manifest and frozen inventory.
- If the referenced manifest is missing, malformed, mismatched, or has a different `run_id`/PC/log type, reject the report.
- A newer run must not silently cause an older report to be relabeled as current. Reports are immutable per run identity.
- Latest-run selection and timestamp tie-breaking remain governed by the OSD-02 latest-manifest policy; this report does not override it.
- A valid report does not independently authorize archive, overwrite, restore, or deletion. Current Drive state must still be independently re-queried and verified where required.

## 8. Acceptance tests required

Use synthetic fixtures and temporary directories only. At minimum, add table-driven tests for:

- valid schema and rejection of missing/unsupported `report_schema_version`
- filename/report/manifest identity mismatch
- missing or malformed source manifest
- inventory count/digest mismatch
- missing, extra, duplicate, or conflicting eligible-target entries
- per-period count mismatch and duplicate period assignment
- run aggregation mismatch against file outcomes and run-scope errors
- zero-work versus enumeration failure versus only-invalid filenames
- unclassifiable filename with verified work and without verified work
- independently complete known period plus unrelated run-scope error
- failed/unknown eligible target blocks its period
- `LastWriteTime` conflicts with filename-derived period and is ignored
- report missing, truncated, malformed, or inconsistent after simulated crash
- safe idempotent regeneration from immutable inputs versus refusal when inputs are incomplete
- concurrent report publication / existing report conflict
- report-write failure never yields a false success
- no source-file mutation, Drive mutation, or deletion side effects

## 9. Implementation and acceptance status

R1–R7 are approved; no report-contract policy decision remains open in this document. The first executable structural-schema slice is proposed in PR #150 at `contracts/aggregation-report-v1.schema.json`, with synthetic structural tests added to `tests/test_contract_schemas.py`. The CI result for those tests is pending until the current PR's exact latest HEAD completes validation.

Still pending after this slice: executable B2 evidence schema; cross-artifact identity/path/hash verification; A2 inventory digest and count reconciliation in runtime code; aggregation recomputation; period/error-scope consistency; deterministic regeneration from immutable inputs; OSD-02 atomic publication and lock integration; local-vs-Drive replication verification; runtime acceptance evidence. This schema does not change manifest v1 and does not authorize runtime side effects. OSD-02, OSD-03 implementation acceptance, P0-008, P0-010, and P0-012 remain open as applicable.

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


## OSD-03 executable schema implementation slice — PR #150 (2026-10-21)

- Added `contracts/aggregation-report-v1.schema.json` as a strict Draft 2020-12 structural schema candidate for the approved R1–R7 report shape. It rejects unknown properties, `report_id`, unsupported/non-integer report schema versions, invalid enums/count types, non-UTC-Z timestamps, malformed lowercase SHA-256 values, and non-canonical relative paths.
- Added schema-definition and synthetic structural-contract tests in `tests/test_contract_schemas.py`. They cover partial-failure and zero-work examples, all three period completion values, strict versioning, unknown fields, reference path/hash validation, timestamp form, enums/counts, and run-scope error shape.
- These tests are authored but **not yet executed/evidenced** in this PR. CI must pass on the exact latest PR HEAD before merge. No runtime report reader/writer, cross-artifact digest verification, tuple/path binding, count recomputation, deterministic regeneration, atomic publication, lock integration, or Drive replication implementation is included in this slice.
- The JSON Schema validates structure only. Cross-field and cross-artifact invariants remain mandatory fail-closed runtime checks; schema acceptance alone is not proof of report correctness or authorization for any side effect.
- No manifest v1 fields, B2 evidence contract, A2 digest contract, or OSD-02 safety boundaries are changed. No real logs, credentials, production paths, Drive writes, archive enablement, or deletion.


## Runtime reference validation slice (PR #155)

The new `Common/AggregationReferencedArtifacts.ps1` wrapper invokes `Common/validate_aggregation_artifacts.py` to validate the derived report against `aggregation-report-v1.schema.json`, then validates the exact referenced manifest and B2 evidence bytes against their respective Draft 2020-12 schemas. It verifies each reference SHA-256 over the raw bytes and binds `run_id`, `pc_id`, and `log_type` across the report and both artifacts. Duplicate JSON keys, malformed/non-object JSON, unsafe paths, missing artifacts, schema errors, digest mismatches, and identity mismatches fail closed with stable reason codes; artifact contents and exception/path details are not returned.

This is a standalone validation entry point, not yet wired into official sync/archive entry points. It does not calculate or reconcile B2 inventory/evidence digests, implement A2 digest generation, prove complete source enumeration, apply timestamp freshness/transition policy, coordinate locks, revalidate live Drive state, or authorize archive. Runtime packaging includes the validator, schemas, and its declared Python dependency. Synthetic tests do not constitute production acceptance.


## Cross-artifact inventory validation update (2026-10-22)

PR #157 connects the report-referenced artifact verifier to B2 canonical digest/count validation and exact manifest-to-evidence frozen-target reconciliation. The report inventory count/digest is also checked against the evidence inventory. This is still validation-only helper behavior: it does not create the artifacts, prove the source traversal was complete, publish atomically, replicate to Drive, or authorize archive/deletion. Confirm exact-head CI before claiming this validation slice is verified.
