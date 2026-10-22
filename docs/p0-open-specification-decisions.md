# P0 Open Specification Decisions and Acceptance Blockers

- Status: Open; no deferred policy choice is made by this document.
- Baseline: source repository at PR #25 merge `097e962a1636419ceb428182da2a6a91f6380273`; audit document updates include PR #28 merge `7f879b52d505ba120163528421f2839803d2b582`; the OSD-01–09 backlog was added in PR #29 merge `2cd9eba0dfe7ba7a43dae2e08952dbce576c03c8`.
- Purpose: consolidate unresolved specification choices and identify the requirements/tests they block. This is a decision backlog, not approval and not evidence that runtime behavior exists.
- Rule: do not infer a value from implementation convenience. Each decision requires explicit operator/project approval or a documented not-applicable disposition before dependent runtime work is accepted.

| ID | Decision requiring resolution | Source / existing record | Related requirement IDs | Why it blocks acceptance | Required resolution/evidence | Status |
|---|---|---|---|---|---|
| OSD-01 | Define the trust criteria for attributing a pre-existing, unmarked Drive object to a PC/source file. | `docs/implementation-workflow.md` §2.4–2.5; `docs/staging-file-lifecycle.md` §7; `docs/decision-register-c18-c32.md` C-32; approved by maintainer in this conversation | EOLM-DRV-010, EOLM-SYN-006–009, EOLM-MAN-001–010, EOLM-TST-005, EOLM-TST-010 | Without an agreed trust predicate, an object with no trustworthy origin must not be treated as a verified duplicate or as archive-eligible. | Approved rule recorded below; implement zero/one/multiple/ambiguous/unmarked, incomplete-listing, source-trust, and hash-fallback fixtures with executable reconciliation tests. | Resolved — policy approved; implementation/tests pending |
| OSD-02 | Approve manifest schema/version details and the complete allowed state-transition table, including required fields, per-file results, Drive identity, timestamps, crash/concurrency handling and schema compatibility. | `docs/decision-register-c18-c32.md` C-26; `docs/staging-file-lifecycle.md` §6–8; maintainer approvals on 2026-10-20 and 2026-10-21; `docs/manifest-schema-v1-proposal.md`; `docs/manifest-state-transition-v1-proposal.md`; `docs/osd-02-crash-concurrency-options.md` | EOLM-MAN-001–012, EOLM-REQ-001, EOLM-STG-001–012, EOLM-TST-004–006, EOLM-TST-010 | Version compatibility, field-level schema, timestamp/freshness policy, and the C1–C4 crash/concurrency/latest-manifest policy choices are approved; exhaustive normative transitions, aggregation, runtime implementation, executable tests, and runtime evidence remain incomplete. | Apply approved C1-A/C2-C/C3-B/C4-A in lifecycle/transition/test specifications; explicitly decide remaining transition rows; resolve OSD-03; implement schema/transition/timestamp/concurrency tests and collect evidence before runtime acceptance. Timestamp policy: UTC ISO 8601 `Z`; 5-minute configurable future tolerance; 24-hour configurable freshness threshold for current-execution timestamps only; fail closed if reliable current UTC is unavailable. | Partially resolved — schema/version/timestamp and C1–C4 policy decisions approved; normative transition completeness, OSD-03, implementation/tests, and runtime evidence pending |
| OSD-03 | Define deterministic run-level status aggregation for verified, failed, unknown, unclassifiable, and zero-work outcomes, including period completion. | `docs/filename-and-period-selection.md` §6–7; `docs/staging-file-lifecycle.md` §8; `docs/decision-register-c18-c32.md` C-25/C-26; `docs/osd-03-status-aggregation-options.md`; `docs/aggregation-report-v1-proposal.md`; `contracts/aggregation-report-v1.schema.json` | EOLM-FIL-004–005, EOLM-MAN-003–006, EOLM-MAN-009–012, EOLM-OPS-003, EOLM-TST-003, EOLM-TST-010 | Aggregation policy and R1-B/R2-A/R3-B/R4-A/R5-A/R6-A/R7-A report contract approved. Structural schema and synthetic tests proposed in PR #150; CI evidence pending. Cross-artifact semantic validation, runtime implementation, B2 schema, and runtime acceptance remain pending. | Verify PR #150 CI; then implement strict reader/writer and semantic validators for source hashes, tuple identity, inventory digest/counts, period/error consistency, immutable-input regeneration, publication/recovery, and verified Drive replication. Do not change manifest v1 fields. | Policy approved; schema candidate/tests in PR; runtime implementation/evidence pending |
| OSD-04 | Define exactly which local side effects Dry Run may perform, especially report output, manifest writes, lock state, temporary files and cleanup. | `docs/powershell-python-contract.md` §3; `docs/implementation-workflow.md` Phase 1/7; `docs/decision-register-c18-c32.md` C-30 | EOLM-DRV-016, EOLM-SAF-002, EOLM-SAF-006, EOLM-TST-005, EOLM-TST-007 | The prohibition on Drive mutations and downloaded-content writes is explicit; permitted reporting/manifest side effects are not fully enumerated. | Approve an allowed/forbidden side-effect matrix; use before/after filesystem and mocked Drive snapshots in Dry Run tests. | Blocked — side-effect boundary incomplete |
| OSD-05 | Select and validate the minimum Drive OAuth scope/authentication mechanism against the actual My Drive folder ownership, sharing and quota constraints. | `docs/decision-register-c18-c32.md` C-23/C-27; `docs/powershell-python-contract.md` §2; `docs/distribution-design.md` §8/§11 | EOLM-DRV-007, EOLM-REL-010, EOLM-SEC-001, EOLM-TST-004–005 | A schema or mocked test cannot prove that the chosen identity has the intended least-privilege access to the real folders. | Approve the identity/scope and record a least-privilege access test against the intended folders; keep production upload blocked until validated. | Blocked — authentication not selected/validated |
| OSD-06 | Approve the release authorization and identity policy: protected release event/approval, tag/VERSION/package metadata consistency, source provenance and immutable version publication. | `docs/decision-register-c18-c32.md` C-27; `docs/distribution-design.md` §2–3/§7–8/§11 | EOLM-REL-004, EOLM-REL-006, EOLM-REL-010–014 | Requirement IDs exist, but the release workflow, approval procedure and provenance controls are not implemented or approved. | Approve release/tag policy and protected workflow; test PR/push denial, tag mismatch, existing-version collision, upload/verification failure and previous-pointer preservation. | Blocked — release procedure not approved |
| OSD-07 | Approve release retention duration and whether/when old package cleanup may be enabled. | `docs/decision-register-c18-c32.md` C-27; `docs/distribution-design.md` §3/§11 | EOLM-REL-005, EOLM-REL-007, EOLM-REL-015 | Automated cleanup could remove rollback artifacts without an approved retention rule. | Approve a retention policy and rollback criteria; until then automated release cleanup must remain disabled and previous releases retained. | Blocked — retention policy not approved |
| OSD-08 | Approve quiet/staggered scheduler times and the operational stale-lock/lease recovery policy before Task Scheduler rollout. | `docs/decision-register-c18-c32.md` C-24; `docs/implementation-workflow.md` Phase 8 | EOLM-OPS-001–006, EOLM-LCK-001–004, EOLM-TST-005, EOLM-TST-007–008 | The schedule and recovery policy affect overlap prevention, missed-run handling and safe recovery; no scheduler/lock implementation or tests exist. | Record approved times and lease/stale-lock recovery rules; test overlapping starts, stale locks, missed monthly runs, failure visibility and manual recovery. | Blocked — operational policy deferred |
| OSD-09 | Approve final per-PC package allowlists and deployment/migration behavior, including required versus optional paths and preservation of active config. | `docs/distribution-design.md` §3–6; P0-006/P0-009 | EOLM-CFG-001–007, EOLM-REL-001–003, EOLM-REL-007, EOLM-REL-013, EOLM-TST-006 | Current builder uses a legacy deployability sentinel; official entry points and final PC-A/PC-B allowlists are absent. | Approve role-specific manifests/allowlists and migration procedure; test required/optional paths, forbidden files, PC-B archive exclusion, legacy-only rejection and unchanged active-config hash. | Blocked — final runtime allowlists absent |

## Approved decision record — OSD-01

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-20).
- **Chosen rule:** A file is a same-content comparison candidate only when its name, size, and SHA-256 match the trusted comparison source and exactly one matching candidate exists in the fully enumerated target Drive folder. Candidate identification and archive authorization are separate decisions.
- **Additional mandatory conditions:**
  1. The comparison source must be a confirmed, trusted PC-A backup/source record. If its integrity or provenance is not established, hold the item; a matching hash does not establish the source's provenance by itself.
  2. Drive candidate enumeration must complete successfully, including all pages and the intended target folder. API errors, incomplete pagination, insufficient access, or uncertain scope must not be interpreted as zero/one candidate; hold and fail closed.
  3. A match establishes only a same-content comparison candidate. It does not by itself authorize restore, declare synchronization successful, prove trusted origin, or permit archive.
  4. If a trustworthy Drive SHA-256 is unavailable, download the candidate through the Drive API and compute SHA-256 locally. Metadata-only name/size matching is insufficient. Download/hash failure or size/hash mismatch means hold and fail closed.
- **Fail-closed outcomes:** zero matches, multiple matches, ambiguous identity, untrusted comparison source, incomplete/failed listing, inaccessible target, hash acquisition/verification failure, or any mismatch must not trigger automatic restore, sync-success classification, archive, overwrite, or deletion. Record the conflict/incomplete result and preserve originals.
- **Rationale:** separates content identity from provenance and operational authorization; prevents incomplete searches or untrusted reference data from being treated as proof.
- **Affected requirements:** EOLM-DRV-010, EOLM-SYN-006–009, EOLM-MAN-001–010, EOLM-ARC-001–005, EOLM-TST-005, EOLM-TST-010; implementation workflow §2.4–2.5.
- **Disposition:** policy decision resolved. Runtime implementation, executable tests, and objective runtime evidence remain pending; this approval does not close P0-010 or mark affected requirements verified.

## Approved decision record — OSD-02 version compatibility

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-20).
- **Chosen rule:** the maintenance manifest must carry a required schema-version field; the initial schema version is integer `1`.
- **Invalid or unsupported input:** a missing, malformed, or unsupported schema version causes the manifest to be rejected and processing to stop safely. It must never be interpreted as success.
- **Compatibility:** no implicit migration, rewrite, or in-place conversion of existing manifests. Any future migration requires an explicit versioned migration design and tests.
- **State transitions:** allowed and forbidden transitions must be specified in a normative table and enforced by tests. This approval does not yet approve the transition table or all field-level schema details.
- **Rationale:** explicit versioning prevents ambiguous interpretation of historical manifests and prevents silent data mutation.
- **Affected requirements:** EOLM-MAN-001–009, EOLM-MAN-012, EOLM-REQ-001, EOLM-STG-001–012, EOLM-TST-004–006, EOLM-TST-010.
- **Disposition:** version/compatibility policy approved; OSD-02 remains partially open pending field-level schema, transition, timestamp/freshness and crash/concurrency decisions, implementation, executable tests, and runtime evidence.

## Resolved rule that must not be reopened implicitly

- Period eligibility is based on the date parsed from the filename only; `LastWriteTime` and verified metadata must not replace or override filename-derived eligibility. See C-25 and the implementation-workflow crosswalk. The remaining filename-date/metadata disagreement item is a test-coverage gap, not a request to change this rule.

## Acceptance and change-control rule

1. A decision is resolved only when the approving authority, chosen value/rule, rationale, and affected requirement IDs are recorded in the decision register or authoritative specification.
2. Update traceability, implementation, tests and handoff together when a decision is approved.
3. Do not mark a requirement `verified` based on this backlog or on documentation/schema CI alone.
4. No local source-log deletion or Google Drive deletion may be introduced in P0–P2. PC-B must not gain an archive entry point.
5. P0-010 remains open until every source clause is mapped or explicitly dispositioned and the required implementation/test/evidence status is accurate.


## OSD-02 field specification approval — 2026-10-21

- The maintainer approved the contents of `docs/manifest-schema-v1-proposal.md`: the required field set, names, types, enums, nullability, verification object, and field-level constraints. The document is now the approved field specification, but it is not an executable schema or runtime implementation.
- The approved design keeps run identity/status, target files, and Drive content-verification evidence in one manifest. The approved version rule remains integer `schema_version: 1`; unsupported/malformed versions are rejected and no implicit migration is permitted.
- Next review artifact: `docs/manifest-state-transition-v1-proposal.md`. Its transition rows are candidates for discussion, not approved normative behavior.
- Still requiring decisions: exhaustive file/run transition rules and cross-field consistency; outcome and run/period aggregation with OSD-03; crash/concurrency and latest-manifest tie-breaking; crash/concurrency and latest-manifest tie-breaking.
- No runtime implementation, executable schema validation, transition enforcement, or operational evidence is claimed.


## Approved decision record — OSD-02 manifest v1 field specification

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- **Approved artifact:** `docs/manifest-schema-v1-proposal.md`, including the run-level fields, per-file fields, verification object, types, enums, nullability, and stated field-level validation constraints.
- **Scope boundary:** approval fixes the field specification only. It does not approve the complete allowed/forbidden state-transition table, run/period aggregation under OSD-03, timestamp freshness/clock-skew policy under EOLM-MAN-011, crash/concurrency semantics, executable schema, runtime implementation, or operational evidence.
- **Next step:** review `docs/manifest-state-transition-v1-proposal.md` and decide the proposed transition rules explicitly.
- **Disposition:** field specification approved; OSD-02 remains partially open and P0-010 remains open.


## OSD-02 transition clarification — initial per-file state

- **Approving authority:** project maintainer (explicit selection of option A on 2026-10-21).
- **Chosen rule:** new run target entries begin in `pending` to mean registered for processing before staging. When staging begins, transition `pending → staging → ready`; immediately before upload, transition `ready → pending` to record that upload has not yet been confirmed as started/successful.
- **Disambiguation:** the same `pending` enum is used at two distinct lifecycle points. Its meaning is determined by the preceding state and event history; `pending` by itself is never evidence of upload attempt or success. The manifest schema has no separate event-history field in the approved field set, so the implementation must validate transition sequence using available run processing context and persisted state changes without inventing new fields.
- **Scope:** this resolves the initial-state ambiguity only. The verification-result mapping and retry-exhaustion rule are approved. Terminal file states, run aggregation, timestamps/freshness, and crash/concurrency policy remain open. The transition table is still a proposal, not a fully approved normative table.


## OSD-02 transition clarification — verification-result mapping

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- **Chosen mapping:** verification status `verified` maps to file status `verified`; `mismatch` maps to `failed`; `unavailable`, `ambiguous`, and verification-operation `failed` map to `unknown`; `not_checked` leaves the current file status unchanged.
- **Safety interpretation:** `mismatch` is evidence of a known content mismatch and is therefore a confirmed file failure. `unavailable`, `ambiguous`, or a failed verification operation do not establish the cloud object's content/state, so the file remains `unknown`; these states must not authorize success, archive, overwrite, or deletion. `not_checked` is not a state transition and must not overwrite the existing file status.
- **Scope boundary:** this approves only the verification-result-to-file-status mapping. It does not approve all verification method/time/hash combinations, retry-exhaustion behavior, terminal-state rules, run/period aggregation under OSD-03, freshness/clock-skew, crash/concurrency, or the complete normative transition table. OSD-02 and P0-010 remain open.


## OSD-02 transition clarification — retry exhaustion — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- **Chosen rule:** exhausting the retry budget does not itself determine the per-file state. Set file status to `failed` only when reliable evidence confirms the operation did not succeed and the failure is definitive (for example, an explicit non-retryable rejection that guarantees no object was created, or a confirmed content mismatch). If the remote upload outcome remains uncertain, retain `unknown`.
- **Verification failures:** `mismatch → failed`; `unavailable`, `ambiguous`, and verification-operation `failed` → `unknown`. An inability to verify is not evidence of content mismatch.
- **Safety boundary:** a timeout, communication failure, incomplete Drive enumeration, or retry exhaustion alone must never be converted to `failed`. A retry after an uncertain upload requires complete, trustworthy reconciliation of Drive state first.
- **Scope boundary:** this resolves retry-exhaustion classification only. It does not approve terminal-state immutability, verification method/time/hash combinations, run/period aggregation under OSD-03, freshness, crash/concurrency, or the full transition table. OSD-02 and P0-010 remain open.


## OSD-02 retry-exhaustion exception-case clarification — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- **Approved rule:** EX-01–EX-10 and cross-cutting retry/reconciliation rules are recorded in `docs/manifest-state-transition-v1-proposal.md` §6 and `docs/decision-register-c18-c32.md`.
- **Core classification:** `failed` requires reliable evidence of definitive non-success, including a confirmed content mismatch or a rejection whose operation contract guarantees that no remote object was created. If remote state is uncertain, use `unknown`. Retry exhaustion, timeout, communication loss, incomplete Drive enumeration, ambiguous candidates, and verification-operation failure do not by themselves establish definitive failure.
- **Retry gate:** `unknown → pending` requires complete and trustworthy reconciliation proving target absence plus retry-policy permission. Incomplete pagination, insufficient access, or uncertain query scope blocks retry. A same-content candidate may become `verified` only after OSD-01 trust, uniqueness, and actual content verification are satisfied.
- **Archive gate:** archive must independently re-query and re-verify current Drive state; prior `verified` evidence alone is insufficient. Current mismatch blocks archive; unavailable/ambiguous/verification-operation failure remains `unknown` and blocks archive.
- **Scope boundary:** this resolves the retry exception-case policy only. It does not approve the full normative transition table or close OSD-02/P0-010. Terminal-state behavior, verification method/time/hash combinations, OSD-03 aggregation, freshness/clock-skew, crash/concurrency/latest-manifest resolution, executable tests, and runtime evidence remain open.


## OSD-02 transition clarification — terminal file states — 2026-10-21

- **Approving authority:** project maintainer (explicit selection of option A in conversation on 2026-10-21).
- **Chosen rule:** `verified` and `failed` are terminal file states within one `run_id`; no transition out of either state is permitted in that run. A later run uses a new `run_id` and a new manifest rather than rewriting historical results.
- **Archive gate:** archive must independently re-query and re-verify the current Drive object. A current mismatch, unavailable/ambiguous result, or verification-operation failure blocks archive and must be recorded in sanitized operational diagnostics. It does not mutate the prior manifest or transition the prior run's file state.
- **Scope boundary:** this resolves post-verification and terminal file-state semantics only. Run-level terminal transitions and OSD-03 aggregation, verification method/time/hash combinations, timestamp freshness/clock-skew, crash/concurrency/latest-manifest selection, executable tests, and runtime evidence remain open. OSD-02 remains partially resolved and P0-010 remains open.

## OSD-02 transition clarification — verification object method/time/hash consistency — 2026-10-21

- **Approving authority:** project maintainer (explicit selection of option A in conversation on 2026-10-21).
- **Chosen rule:** `verification.method` states the method actually used to obtain an observed content hash, not merely a method attempted.
- **Allowed combinations:** `not_checked` uses `not_performed` with null timestamp and null hash; `verified`/`mismatch` require an actual hash method, non-null timestamp, and observed hash; `unavailable`/`ambiguous`/verification-operation `failed` without an observed hash use `not_performed`, a non-null attempt timestamp, and null hash.
- **Diagnostics:** detailed attempted method, sanitized error, and retry history belong in sanitized operational logs. An arbitrary candidate hash must not be recorded where candidate identity is ambiguous. `mismatch` requires an observed hash that differs from the expected source hash.
- **Invalid combinations:** reject any combination outside the approved table in `docs/manifest-state-transition-v1-proposal.md` §4.
- **Scope boundary:** this resolves verification-object field consistency only. Run-level status/time consistency, OSD-03 aggregation, timestamp freshness/clock-skew, crash/concurrency/latest-manifest selection, executable validation tests, and runtime evidence remain open. OSD-02 and P0-010 remain open.

## OSD-02 transition clarification — run status and finish-time consistency — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of option A in conversation on 2026-10-21).
- **Chosen rule:** `started_at_utc` is required in every run state. `running` requires `finished_at_utc: null`; `success`, `partial_failure`, and `failure` require non-null `finished_at_utc`.
- **Validation:** reject status/finish-time combinations outside this rule.
- **Boundary:** timestamp ordering, freshness, future-time and clock-skew rules remain open and separate. A crash-left `running` manifest is not automatically converted to `failure`; crash/concurrency policy remains open.
- **Scope boundary:** this resolves run status/finish-time consistency only. OSD-03 aggregation, timestamp ordering/freshness/clock-skew, crash/concurrency/latest-manifest selection, executable tests, and runtime evidence remain open. OSD-02 and P0-010 remain open.

## OSD-02 transition clarification — timestamp validation policy shape — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of option A in conversation on 2026-10-21).
- **Chosen rule:** require UTC ISO 8601 timestamps with a `Z` designator; reject malformed/unparseable values and finish times earlier than start times without silently correcting them.
- **Future time and freshness:** use configuration-driven future-time/clock-skew tolerance and context-appropriate freshness thresholds; reject values beyond configured future tolerance.
- **Still open:** numeric configuration values, exact contexts in which freshness applies, and clock synchronization/monitoring expectations under EOLM-MAN-011.
- **Scope boundary:** this approves the timestamp policy shape only. OSD-03 aggregation, crash/concurrency/latest-manifest selection, executable tests, runtime evidence, and numeric timestamp configuration remain open. OSD-02 and P0-010 remain open.

## OSD-02 transition clarification — crash, concurrency, and latest-manifest policy shape — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of option A in conversation on 2026-10-21).
- **Manifest eligibility:** validate structure and cross-check filename identity with the identity recorded in the JSON.
- **Latest selection:** timestamp collisions or otherwise indistinguishable candidates are ambiguous; stop the dependent operation rather than choose arbitrarily.
- **Concurrent updates:** prevent stale reads from overwriting newer state; re-read/re-validate or fail safely on conflict.
- **Crash behavior:** a crash-left `running` manifest remains unfinished and is not automatically rewritten to `success` or `failure`.
- **Destructive-action gate:** do not archive or delete until current remote state has been re-established and verified.
- **Still open:** concrete atomicity/locking strategy, exact identity fields and filename convention, stale-run recovery, and executable tests.
- **Scope boundary:** this approves policy shape only. OSD-03 aggregation, numeric timestamp configuration, runtime implementation/evidence, and P0-010 closure remain open.


## OSD-03 aggregation policy approval — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of the combined Option A + Option C policy in conversation on 2026-10-21).
- **Run aggregation:** all eligible targets verified and no relevant errors => `success`; verified zero-work only after successful enumeration and validation => `success` with `outcome: no_work`; verified work plus any unresolved eligible-file `failed`/`unknown` or run-scope unclassifiable error => `partial_failure`; no verified eligible work and a processing/validation failure or inability to establish valid no-work => `failure`.
- **Period aggregation:** a period is complete only when every eligible target assigned to it is verified and no relevant error affects that period. `failed` or `unknown` blocks completion of its period.
- **Unclassifiable filenames:** retain as run-scope validation errors; never infer period from `LastWriteTime`. They block run-level `success` but do not automatically invalidate an independently complete known period whose target inventory is established.
- **Safe independent work:** continue processing independent valid files where safe; progress never cancels or hides errors.
- **No-work distinction:** enumeration/access failure and only-invalid relevant filenames are not no-work.
- **Still open:** OSD-02 must settle whether period summaries and unassigned validation errors are stored in the manifest or provided by a supported derived report. No new fields or enum values are implicitly approved. Executable tests and runtime evidence remain pending; OSD-03/P0-008/P0-010 are not closed by policy approval alone.


## OSD-02 / OSD-03 representation decision — derived aggregation report — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- **Chosen option:** Option A. Keep the approved manifest v1 field set unchanged. Do not add period-summary or unassigned-error fields to the manifest.
- **Required representation:** store period-level aggregation results and unclassifiable run-scope validation errors in a separate, durable derived aggregation report linked to the source run by `run_id`.
- **Integrity requirements:** report results must be checked against the frozen eligible inventory and originating run. Missing, malformed, stale, or inconsistent report data must not certify period completion. The report must preserve run-scope errors without assigning an inferred period; `LastWriteTime` is never a fallback.
- **Scope boundary:** report schema, publication/atomicity, crash recovery, freshness/consistency validation, implementation, and executable tests remain pending. This decision does not close OSD-02, OSD-03, P0-008, or P0-010 and does not claim runtime support.


## Approved OSD-02 timestamp and freshness policy — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- **Timestamp format:** all manifest timestamps must be valid, parseable UTC ISO 8601 strings with an explicit uppercase `Z` suffix. Offset forms, missing timezone, malformed values, and unparseable values are rejected.
- **Ordering:** `finished_at_utc` must not precede `started_at_utc`. Invalid ordering is rejected; timestamps are never silently repaired.
- **Future-time tolerance:** maximum accepted future skew is 5 minutes relative to the runtime's current UTC clock. Any timestamp more than 5 minutes in the future is rejected for the dependent operation.
- **Freshness threshold:** 24 hours, configuration-driven. Freshness checks apply only to timestamps generated or updated during the current execution, including run start/finish and verification-attempt timestamps. Historical manifests are retained as history and are not invalidated solely because they are older than 24 hours.
- **Clock synchronization:** assume the host OS time synchronization service is configured; at runtime, detect unavailable or clearly invalid clock readings where the platform exposes that information. If the current time cannot be obtained or parsed reliably, fail closed for time-dependent operations. A timestamp outside the configured future tolerance is rejected. This decision does not require a separate external monitoring/alerting service.
- **Configuration contract:** the 5-minute future tolerance and 24-hour freshness threshold are initial approved defaults and must be configurable; invalid, negative, non-finite, or unparseable configuration values must be rejected rather than silently defaulted. Configuration validation and fixed-clock tests are required.
- **Scope boundary:** this policy does not define crash recovery, concurrent writers, latest-manifest tie-breaking, OSD-03 aggregation, or archive authorization. Archive still independently re-queries and verifies current Drive state. Policy approval is not runtime implementation or test evidence.
- **Affected requirements:** EOLM-MAN-011, EOLM-MAN-001–010, EOLM-TST-004–006, EOLM-TST-010, and applicable archive freshness gates.
- **Disposition:** numeric timestamp/freshness policy resolved; OSD-02 remains partially open for crash/concurrency/latest-manifest decisions, transition completeness, executable schema/transition tests, and runtime evidence. OSD-03, P0-008, P0-010, and P0-012 remain open.


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


## OSD-03 executable schema implementation slice — PR #150 (2026-10-21)

- Added `contracts/aggregation-report-v1.schema.json` as a strict Draft 2020-12 structural schema candidate for the approved R1–R7 report shape. It rejects unknown properties, `report_id`, unsupported/non-integer report schema versions, invalid enums/count types, non-UTC-Z timestamps, malformed lowercase SHA-256 values, and non-canonical relative paths.
- Added schema-definition and synthetic structural-contract tests in `tests/test_contract_schemas.py`. They cover partial-failure and zero-work examples, all three period completion values, strict versioning, unknown fields, reference path/hash validation, timestamp form, enums/counts, and run-scope error shape.
- These tests are authored but **not yet executed/evidenced** in this PR. CI must pass on the exact latest PR HEAD before merge. No runtime report reader/writer, cross-artifact digest verification, tuple/path binding, count recomputation, deterministic regeneration, atomic publication, lock integration, or Drive replication implementation is included in this slice.
- The JSON Schema validates structure only. Cross-field and cross-artifact invariants remain mandatory fail-closed runtime checks; schema acceptance alone is not proof of report correctness or authorization for any side effect.
- No manifest v1 fields, B2 evidence contract, A2 digest contract, or OSD-02 safety boundaries are changed. No real logs, credentials, production paths, Drive writes, archive enablement, or deletion.


## PR #151 status note — OSD-03 internal consistency slice (2026-10-22)

PR #150 merged the structural aggregation-report v1 JSON Schema and its synthetic schema tests; PR-head and post-merge CI passed. PR #151 adds a report-local PowerShell consistency validator and synthetic tests for period uniqueness, safe reference paths/digest shape, summary count reconciliation, completion consistency, run-scope error count, and zero-work/success consistency. Until PR #151 CI passes on its exact latest HEAD, these tests are authored but not yet verified. This slice does not validate exact referenced manifest/evidence bytes, B2/A2 integrity, full target-set completeness, cross-artifact identity, deterministic regeneration, atomic publication, lock ownership, or Drive replication. P0 acceptance remains open.

## OSD-03 status correction — 2026-10-22

PR #151 is merged at `e93f0ea552496831c69efb1e8dd2818ac86f4e5b`. Validate and Package Validation passed on exact PR HEAD `846cfdbb1ce76f3ec1363460c4f0576b7c10a2b6` (runs `39635268289`, `39635268115`) and on the post-merge commit (runs `39636402422`, `39636402408`). The report-local consistency validator is now implemented and CI-verified within its stated scope. PR #152 adds a narrow exact-byte reference verifier; its tests are not yet CI-verified. Neither PR implements full manifest/B2 schema validation, identity binding, A2 digest recomputation, exhaustive target/count reconciliation, deterministic report regeneration, atomic publication, lock recovery, or Drive replication. P0 acceptance remains open.