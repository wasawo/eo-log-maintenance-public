# OSD-03: Run and Period Status Aggregation Options

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

- Status: **Aggregation policy and R1–R7 derived-report contract approved by maintainer on 2026-10-21; executable JSON Schema, runtime implementation, and test evidence pending**
- Related decision: `docs/requirements/p0-open-specification-decisions.md` — OSD-03
- Requirements: EOLM-FIL-004–005, EOLM-MAN-003–006, EOLM-MAN-009–012, EOLM-OPS-003, EOLM-TST-003, EOLM-TST-010
- Scope: run-level and period-level reporting when a run contains verified, failed, unknown, unclassifiable, or zero-work outcomes.

## 1. Rules already fixed by existing specifications

These are not open for reinterpretation in this proposal:

- A relevant unclassifiable or invalid filename is a validation error; `LastWriteTime` is never a fallback.
- An affected run must not be reported as fully successful when a relevant validation error prevents verification.
- A period is not fully successful if a relevant validation error prevents that period from being verified.
- Valid independent files may be processed individually where safe, but processing them does not cancel an error.
- `unknown` is not success. Under `docs/design/staging-file-lifecycle.md` §8, a remaining unknown file leads to `partial_failure` when other files were verified, or `failure` when the overall process did not succeed.
- Run-level states already defined by the lifecycle are `running`, `success`, `partial_failure`, and `failure`. A verified zero-work run uses `status: success` and `outcome: no_work`; do not add a separate `skipped` run status.
- The exact manifest schema and complete state-transition table remain subject to OSD-02. This document does not approve a schema or introduce new status enum values.

## 2. Approved aggregation policy (2026-10-21)

The maintainer approved the combined policy: Option A (continue safe independent work; deny full-success certification when unresolved outcomes exist) with Option C's separation of known-period results from unclassifiable run-scope errors.

### 2.1 Run-level status

| Condition | Run status | Outcome / constraints |
|---|---|---|
| Enumeration and validation succeed; every eligible target is verified | `success` | No extra outcome required by this decision. |
| Enumeration and validation succeed; there are zero eligible targets | `success` | Set `outcome: no_work`. This includes a genuinely empty source or only valid, ineligible files. |
| At least one eligible file is verified and at least one eligible file remains `failed` or `unknown`, or a relevant unclassifiable item exists | `partial_failure` | Never report full success. Preserve per-file and run-scope error details. |
| No eligible file is verified and the run has a confirmed processing/validation failure or cannot establish a valid no-work result | `failure` | Do not use `outcome: no_work`. |
| Enumeration fails or access is denied | `failure` | This is not a zero-work run. |
| Relevant invalid/unclassifiable names exist and no eligible file is verified | `failure` | Invalid names prevent successful no-work classification. |

A run with verified work plus any unresolved relevant failure/unknown/unclassifiable item is `partial_failure`; confirmed failure is not a reason to discard verified independent progress. `unknown` never counts as verified. Do not introduce new status or outcome enum values.

### 2.2 Period-level completion and unclassifiable items

- A known period is complete only when every eligible target assigned to that period is accounted for as `verified`, and no relevant validation or processing error is known to affect that period.
- A `failed` or `unknown` file prevents its assigned period from being considered complete.
- A filename that cannot be reliably classified remains an unassigned run-scope validation error. Never infer its period from `LastWriteTime` or another fallback.
- A run-scope unclassifiable error prevents the overall run from being `success`, but does not by itself invalidate a different known period whose complete target set was independently established and verified.
- Valid independent files may continue where safe; processing them never cancels or hides a validation error.
- The manifest schema currently has no approved period-summary or unassigned-error collection. Do not add fields implicitly. OSD-02 must approve the representation before implementation; until then these are required aggregation semantics, not an approved new manifest shape.

### 2.3 No-work distinction

`success` with `outcome: no_work` is permitted only when enumeration completed successfully, validation found no relevant invalid/unclassifiable items, and there are no eligible targets. Enumeration failure and an input containing only invalid relevant filenames are never no-work.

## 3. Remaining implementation and evidence decisions

1. Specify and validate the approved derived aggregation report for period summaries and run-scope unclassifiable errors, without adding manifest v1 fields.
2. Implement table-driven tests for the aggregation matrix, including mixed verified/failed/unknown outcomes, invalid names, zero-work distinctions, and period-local versus run-scope errors.
3. Prove all-targets-accounted-for using a frozen eligible inventory and test assertions; do not infer completeness from the count of successful files.

## 4. Historical alternatives (superseded by the approval above)

| Option | Aggregation rule | Advantages | Costs / risks |
|---|---|---|---|
| A — Continue safe independent work; fail full-success certification | Process valid independent files where safe. Any unresolved failed, unknown, or unclassifiable relevant item prevents full success. If some files were verified, use the existing `partial_failure` run state; if none were verified and the operation failed, use `failure`. A verified empty workload uses `success` with `outcome: no_work`. Keep unclassifiable items at run scope because no trustworthy period can be assigned. | Closest to the existing statement that valid files may be processed individually; preserves progress while making failures visible; aligns with the existing unknown-file rule. | Needs an approved rule for period-local versus run-level error scope, and for whether confirmed failures follow the same mapping as unknown. A mixed run must not hide unclassifiable items. |
| B — Fail the entire affected log-type run on any validation/processing error | Stop further processing for that log type when a relevant invalid filename or file failure is encountered; report the run as not fully successful. | Simple to reason about; minimizes partial progress after input errors. | More conservative than the current allowance to process independent valid files where safe; may repeatedly block older valid backlog because of one malformed file. Does not remove the need to define period-level results. |
| C — Strict per-period aggregation with separate run summary | Aggregate files into known periods; each period is fully verified only when every relevant file assigned to it is accounted for. Invalid names with no period affect the run summary and are recorded in a separate unassigned-validation-error collection. The overall run cannot be fully successful while such errors remain. | Gives useful per-period diagnostics and supports backlog retry without misattributing invalid files to a period. | Requires manifest/schema support for unassigned validation errors and explicit run-vs-period precedence. OSD-02 must approve the representation before implementation. |

## 5. Historical recommendation (superseded by the approval above)

Use Option A as the baseline for safe independent processing, combined with Option C's explicit distinction between known-period results and unclassifiable errors. This preserves the existing rule that valid independent files may proceed where safe while ensuring an unclassifiable filename cannot be silently assigned to a period or hidden by successful files.

This recommendation does **not** settle whether an invalid item blocks one period, all periods for a log type, or only run-level full-success certification. That scope must be explicitly selected by the operator/maintainer before implementation. The schema representation also depends on OSD-02.

## 6. Aggregation test matrix

The expected outcomes below are normative policy expectations. Tests must also assert that no invalid/unknown file is counted as verified and that independent safe work does not erase recorded errors.

| Case | Enumeration / inventory | Eligible file outcomes | Relevant unclassifiable names | Expected run status | Period expectation |
|---|---|---|---|---|---|
| T-01 | Success; no eligible targets | None | None | `success`, `outcome: no_work` | No eligible period work; no period may be inferred |
| T-02 | Failure or access denied | Not trustworthy | Any / unknown | `failure`; never `no_work` | No period may be certified from incomplete enumeration |
| T-03 | Success; frozen inventory complete | All eligible files `verified` | None | `success` | Every period whose full eligible inventory is verified is complete |
| T-04 | Success; frozen inventory complete | At least one `verified`, plus `failed` in a known period | None | `partial_failure` | Period containing `failed` is incomplete; independently complete periods may remain complete |
| T-05 | Success; frozen inventory complete | At least one `verified`, plus `unknown` in a known period | None | `partial_failure` | Period containing `unknown` is incomplete |
| T-06 | Success; frozen inventory complete | At least one `verified` | One or more | `partial_failure` | Known periods may be complete only if their inventory is independently established and no error affects them |
| T-07 | Success; frozen inventory complete | No verified eligible file | One or more | `failure` | No period completion may be claimed for unverified eligible targets |
| T-08 | Success; frozen inventory complete | No verified eligible file; processing/validation failure | None | `failure` | Any affected period is incomplete |
| T-09 | Success; only valid but ineligible files | None | None | `success`, `outcome: no_work` | Ineligible files do not enter the eligible-target denominator |
| T-10 | Success; only invalid relevant names | None | One or more | `failure`; never `no_work` | No period assignment via timestamp fallback |
| T-11 | Success; eligible targets across periods | One period all `verified`; another has `failed`/`unknown` | None | `partial_failure` | First period may be complete; second is incomplete |
| T-12 | Success; one eligible target `verified`; all other eligible targets accounted for as `verified` | All verified | None | `success` only if no other relevant error exists | Completeness must be proved from the frozen inventory, not by counting successful outcomes alone |

A relevant unclassifiable name with at least one verified eligible file yields `partial_failure`, not `success`; with no verified eligible file it yields `failure`. A period is complete only if every eligible file assigned to it is verified and no relevant error affects that period. A run-scope unclassifiable error does not automatically invalidate an independently complete known period, but must remain visible in the run result.

## 7. Required test evidence

- Table-driven tests for every approved row and cross-product of relevant file outcomes.
- A mixed fixture with at least one verified eligible file and one invalid/unclassifiable file.
- A fixture where filename date and `LastWriteTime` imply opposite eligibility outcomes.
- Distinction between an empty source, only-ineligible valid files, only-invalid relevant files, and an enumeration/access failure.
- Assertions for run status, period completion, manifest contents, source-file existence/hash preservation, and no delete operations.
- Synthetic files and temporary directories only; no real ElectronicObserver logs, production paths, or real Drive data.
- Runtime tests remain blocked until the official target-enumeration/orchestration entry point and approved manifest representation exist.

## 8. Approval and acceptance gate

The aggregation policy and derived-report representation are approved, but OSD-03 is not fully closed: `docs/design/reference/aggregation-report-v1-proposal.md` must be reviewed and approved, then implemented and covered by table-driven consistency tests. Do not mark P0-008/P0-010 complete based on this document alone.

## OSD-03 approved report-contract compatibility note (2026-10-21)

R1-B/R2-A/R3-B/R4-A/R5-A/R6-A/R7-A are approved. The report contains period summaries only and references the exact manifest and B2 evidence by canonical relative path, schema version, and SHA-256 of exact bytes. Report identity is (pc_id, log_type, run_id, report_schema_version), with no report_id field. Deterministic regeneration uses only immutable validated inputs; it must not re-enumerate mutable source directories. Period completion is complete/incomplete/indeterminate and remains report-only, not a manifest v1 enum. Local publication is authoritative; Drive replication is separate and must be content-verified before cross-PC use. These decisions do not alter manifest v1, B2 evidence structure, A2 inventory digest, or exhaustive count reconciliation. Executable schema, runtime implementation, and tests remain pending.
