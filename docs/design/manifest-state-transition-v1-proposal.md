# Maintenance Manifest v1 — State-Transition Table Proposal

- Status: transition tables adopted by the maintainer on 2026-10-24, subject to existing approved aggregation, crash/concurrency, terminal-state and immutable-history rules. Unlisted transitions are rejected. Persistence details, implementation, tests and runtime acceptance remain incomplete. See [selection record](../decisions/selected-policy-decisions-20261024.md).
- Related decision: OSD-02 / C-26.
- Approved field contract: `docs/design/manifest-schema-v1-proposal.md`.
- Related aggregation decision: `docs/decisions/osd-03-status-aggregation-options.md`.
- Scope: candidate transitions for per-file lifecycle state, Drive verification result, and run status. This document does not authorize runtime implementation.

## 1. Rules already established by approved specifications

- Run status enum: `running`, `success`, `partial_failure`, `failure`.
- File status enum: `staging`, `ready`, `pending`, `uploaded`, `verified`, `failed`, `unknown`.
- Verification status enum: `not_checked`, `verified`, `mismatch`, `unavailable`, `ambiguous`, `failed`.
- Verification method enum: `not_performed`, `drive_sha256`, `download_sha256`.
- A verified verification result requires actual content verification; metadata-only lookup is insufficient.
- **Approved verification-object combinations (2026-10-21):** `not_checked` pairs with `not_performed` and null time/hash; `verified` and `mismatch` require an actually used hash method (`drive_sha256` or `download_sha256`), a non-null timestamp, and a valid observed hash; `unavailable`, `ambiguous`, or verification-operation `failed` with no observed hash pair with `not_performed`, a non-null attempt timestamp, and null hash. `method` describes the method that actually obtained the hash, not merely an attempted method. Detailed attempted-method/error/retry diagnostics belong in sanitized operational logs.
- A cloud object ID does not establish content equality or provenance. Archive must independently re-query/re-verify current Drive state.
- **Approved terminal-state rule (2026-10-21):** `verified` and `failed` are terminal within a run. Later archive-time verification may block archive and emit sanitized operational diagnostics, but must not rewrite the historical manifest or transition that file state. A later run uses a new `run_id`.
- **Approved retry-exhaustion rule:** reaching the retry limit is not by itself evidence of success or failure. Use file `failed` only when reliable evidence establishes that the operation did not succeed and the failure is definitive (such as an explicit non-retryable rejection that guarantees no object was created, or a confirmed content mismatch). If the remote upload outcome cannot be established, retain `unknown`; verification `unavailable`, `ambiguous`, or verification-operation `failed` also maps to `unknown`.
- A crash-left `running` manifest remains incomplete and must not be automatically rewritten to `failure`. A new execution gets a new `run_id`.
- Existing source/staging rules require upload only from a verified staging copy, unknown upload outcomes to be reconciled before retry, and preservation of staging artifacts when success cannot be established.
- An uncertain file is never success. Run-level aggregation remains subject to OSD-03.
- This table must not add status or outcome enum values without explicit approval.

## 2. Adopted per-file state transitions (2026-10-24)

The maintainer adopted the following rows with the conditions recorded above. Any transition not explicitly listed must be rejected unless a later explicit decision approves an additional row. This does not permit implementation to introduce new enum values or rewrite historical records.

| From | To | Trigger / required evidence | Prohibitions / notes |
|---|---|---|---|
| `pending` | `staging` | Staging metadata is durably written before creating the staging copy. | Do not overwrite an existing staging file; do not upload yet. |
| `staging` | `ready` | Staging copy exists and its size and SHA-256 match the frozen inventory. | No upload if copy creation or verification fails. |
| `staging` | `failed` | A confirmed staging/copy/verification failure is recorded. | Cleanup is limited to incomplete artifacts created by the current operation; failed cleanup retains artifacts and warns. |
| `ready` | `pending` | Upload is about to be attempted and the attempt is recorded. | Upload input must be the verified staging copy, not a mutable source file. |
| `pending` | `uploaded` | Upload API explicitly reports success. | This is not cloud-content verification and is not archive authorization. |
| `pending` | `unknown` | Upload outcome cannot reliably be determined. | Must inspect Drive state before retry; do not assume absence or success. |
| `pending` | `failed` | Evidence confirms the upload did not succeed (for example, an explicit non-retryable rejection that means no object was created), and the error is classified as non-retryable or retry policy is exhausted. | Retry exhaustion alone is insufficient. If the remote outcome is uncertain, use `unknown`. |
| `uploaded` | `verified` | Cloud content is verified by trustworthy Drive SHA-256 or by download-and-local-hash comparison. | Metadata-only matching is insufficient. |
| `uploaded` | `unknown` | Verification cannot establish current content or upload outcome remains uncertain. | Preserve staging artifacts; no success/archive. |
| `uploaded` | `failed` | Content verification establishes a mismatch between expected and observed bytes. | Only `mismatch → failed`. Verification unavailable/ambiguous/operation failure maps to `unknown`, not `failed`. |
| `unknown` | `verified` | Reconciliation finds exactly one trusted same-content candidate and verifies its content under OSD-01. | Must not bypass full enumeration, source trust, or hash requirements. |
| `unknown` | `pending` | Reconciliation confirms the upload target is absent and a retry is permitted by the retry policy. | Retry only after the absence determination is complete and trustworthy. |
| `unknown` | `failed` | Reconciliation establishes with reliable evidence that the upload did not succeed and the failure is confirmed (for example, a definitive rejection plus confirmed target absence). | Retry exhaustion alone, incomplete enumeration, timeout, or uncertain cloud state must remain `unknown`. |

### Open transition questions

1. **Initial per-file state — decided:** the maintainer selected option A on 2026-10-21. A new run begins with `pending` as a planning/target-registered state; before creating a staging copy, metadata-first processing transitions `pending → staging → ready`; immediately before upload attempt, it transitions `ready → pending`. The two `pending` occurrences represent distinct lifecycle points, disambiguated by the preceding state and event history. This decision resolves only the initial-state ambiguity; at that individual approval point the full table was not normative; later conditional adoption is recorded in §5.
2. **Verification result mapping — mapping approved:** `verified → verified`; `mismatch → failed`; `unavailable → unknown`; `ambiguous → unknown`; `failed → unknown`; `not_checked` leaves the current file state unchanged. This mapping does not approve every method/time/hash combination or the full transition table.
3. **Retry exhaustion — policy approved:** exhausting the retry budget does not itself determine file state. Use `failed` only when evidence confirms the operation did not succeed and the failure is definitive; use `unknown` whenever the cloud outcome remains uncertain. A verification result of `unavailable`, `ambiguous`, or verification-operation `failed` maps to `unknown`; a confirmed content `mismatch` maps to file `failed`.
4. **Post-verification state — decided 2026-10-21:** `verified` and `failed` are terminal file states within one run. A later archive-time verification does not rewrite that run's file status or historical manifest. If current verification fails, is unavailable, or is ambiguous, block the archive and record the current result in sanitized operational logs (or other separately approved operational diagnostics). A later execution uses a new `run_id` and its own manifest.
5. **Terminal file states — decided 2026-10-21:** no transition out of `verified` or `failed` is permitted within the same run. This does not make a stored `verified` status a permanent archive authorization; archive must independently re-query and verify current Drive content.
6. **Run-level status/time constraint — decided 2026-10-21:** `started_at_utc` is required for every status; `running` requires null `finished_at_utc`; terminal statuses (`success`, `partial_failure`, `failure`) require non-null `finished_at_utc`. Ordering/freshness/clock-skew and crash recovery remain separate.
7. **Verification object combinations — decided 2026-10-21:** approve and enforce the exhaustive combinations in §4; `method` means the method that actually obtained the observed hash. Failed attempts with no hash use `not_performed`, an attempt timestamp, and null hash; detailed attempt diagnostics go to sanitized operational logs.
7. **Aggregation boundary:** Use the approved OSD-03 file-to-run/period aggregation and outcome rules, including zero-work and unclassifiable filenames. Adoption of this table does not replace those conditions.

## 3. Adopted run-level transitions (2026-10-24)

| From | To | Trigger / required evidence | Prohibitions / notes |
|---|---|---|---|
| (new manifest) | `running` | Lock acquired; manifest written and validated before file processing. | Must have unique `run_id`; no processing before the running manifest is safely recorded. |
| `running` | `success` | All required work is accounted for, all required file outcomes are verified, no relevant validation/processing error remains, and final manifest validates. | Exact aggregation and `outcome` must follow the approved OSD-03 rules. |
| `running` | `partial_failure` | Some work was verified but at least one relevant item remains unresolved or failed under the approved aggregation rule. | Exact mapping must follow the approved OSD-03 rules. |
| `running` | `failure` | Run cannot safely complete or no verified work exists after a confirmed overall failure, as determined by the approved aggregation rule. | Exact mapping must follow the approved OSD-03 rules. |
| `running` | `running` | Same run is continuing and its manifest is updated atomically after validation. | Do not change `run_id`; enforce the approved status/time consistency and crash/concurrency/single-owner rules. Persistence and writer integration remain unimplemented. |
| terminal status | any different status | **Forbidden by default.** | A later execution must create a new manifest with a new `run_id`; older manifests are not rewritten to represent a later run. |

Crash recovery is not a transition: if the process crashes, leave the last valid manifest as `running`; do not automatically rewrite it to a terminal state.

## 5. Approved run status and finish-time consistency — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21; option A).
- `started_at_utc` is required for every run status.
- `status: running` requires `finished_at_utc: null`.
- Terminal run statuses `success`, `partial_failure`, and `failure` each require a non-null `finished_at_utc`.
- Any status/time combination outside these rules is invalid and must be rejected by manifest validation.
- This decision does not define whether finish time is chronologically after start time, acceptable future timestamps, timestamp freshness, clock-skew tolerances, crash recovery, or run/period aggregation under OSD-03.
- A crash-left `running` manifest is not automatically rewritten to `failure`; recovery behavior remains governed by the approved crash/concurrency policy and its independent qualification gates.

## 4. Approved verification object combinations — 2026-10-21

The maintainer selected option A. These combinations are normative policy decisions for the v1 verification object; every combination not listed below is invalid and must be rejected by the validator.

| `verification.status` | `verification.method` | `checked_at_utc` | `observed_sha256` | Required interpretation |
|---|---|---|---|---|
| `not_checked` | `not_performed` | null | null | No verification attempt recorded |
| `verified` | `drive_sha256` or `download_sha256` | non-null UTC timestamp | valid 64-hex hash | Actual observed hash matches expected source hash |
| `mismatch` | `drive_sha256` or `download_sha256` | non-null UTC timestamp | valid 64-hex hash | Actual observed hash differs from expected source hash |
| `unavailable`, `ambiguous`, or `failed` when no observed hash was obtained | `not_performed` | non-null UTC attempt timestamp | null | Attempt occurred, but no observed content hash was obtained |

- `method` records the method that actually obtained an observed hash, not a method merely attempted. If an attempted verification fails before obtaining a hash, use `not_performed`.
- For `unavailable`, `ambiguous`, or verification-operation `failed` without a hash, `checked_at_utc` records when the attempt occurred. Record the attempted method, sanitized error details, and retry history in sanitized operational logs.
- If multiple candidates make identity ambiguous, do not place an arbitrary candidate's hash in the single `observed_sha256` field. Without one established observed hash, use `not_performed` and null hash.
- `mismatch` requires an actual observed hash that differs from the expected hash; no hash means the result cannot be `mismatch`.
- The verification-result-to-file-status mapping remains: `verified → verified`; `mismatch → failed`; `unavailable`, `ambiguous`, or verification-operation `failed` → `unknown`; `not_checked` leaves the current file status unchanged.
- These field-combination rules do not decide run-level aggregation, archive authorization, timestamp freshness/clock skew, or crash/concurrency behavior. Archive must independently re-query and re-verify current Drive content.
## 5. Table adoption and remaining implementation work (2026-10-24)

The maintainer adopted the candidate tables subject to the already-approved conditions and rejection of unlisted transitions. Keep the historical individual decisions below within their original scope; this later adoption does not add new enum values, permit historical rewrites, or prove implementation. Remaining work includes lifecycle/traceability alignment, persistence/source contracts, executable transition tests and independent runtime evidence.

No runtime implementation, executable transition tests, or operational evidence is claimed by this proposal.


## 6. Approved retry-exhaustion exception cases — 2026-10-21

The maintainer approved the exception-case policy in conversation on 2026-10-21. These rules clarify retry and reconciliation behavior; they do **not** make the full transition table normative or authorize runtime implementation.

| ID | Exception case | Required disposition | Guard / rationale |
|---|---|---|---|
| EX-01 | Explicit HTTP 4xx or other rejection | failed only if the operation contract reliably guarantees that no remote object was created; otherwise unknown when outcome remains uncertain | HTTP status alone is insufficient; classify using operation semantics and evidence |
| EX-02 | HTTP 5xx, timeout, or communication loss during upload | unknown unless independent reliable evidence establishes definitive non-success | The remote operation may have completed despite the lost response |
| EX-03 | Retry budget exhausted and target is not found by Drive search | Keep unknown until target absence is established by complete, trustworthy reconciliation; only then may retry policy permit unknown → pending | Retry exhaustion and an unproven absence do not establish failure |
| EX-04 | Drive listing pagination fails, access is insufficient, or query scope is uncertain | unknown; do not interpret the result as zero or one candidate | Incomplete enumeration cannot prove target absence or uniqueness |
| EX-05 | Multiple same-name or otherwise ambiguous candidates | unknown; hold for safe reconciliation | Do not choose arbitrarily, overwrite, or declare success |
| EX-06 | Upload API reports success but content verification follows | mismatch → failed; unavailable, ambiguous, or verification-operation failed → unknown | Upload acknowledgement is not content verification |
| EX-07 | A previously verified object fails a later verification | Block archive based on the current failed verification; record sanitized operational diagnostics without rewriting the historical manifest | Archive must independently re-query and verify current Drive state; `verified` remains terminal within the original run, per the approved 2026-10-21 decision |
| EX-08 | Process crashes while a manifest is running | Leave the last valid manifest running; do not automatically rewrite it to failure | A new execution uses a new run_id; crash recovery/concurrency policy remains an open OSD-02 item |
| EX-09 | Reconciliation after an unknown upload finds one same-content candidate | Transition to verified only after OSD-01 trust, complete enumeration, uniqueness, and actual content verification requirements are met | Matching metadata or object ID alone is insufficient |
| EX-10 | Verification operation throws, returns malformed data, or cannot produce a reliable result | unknown; no success or archive authorization | Failure of the verifier is not proof of remote content mismatch |

### Cross-cutting rules

1. HTTP status codes alone do not determine file status. failed requires reliable evidence of definitive non-success; when remote state remains uncertain, use unknown.
2. unknown → pending is allowed only after complete, trustworthy reconciliation establishes target absence and the retry policy permits another attempt. Incomplete listing, pagination failure, insufficient access, or uncertain scope blocks the retry.
3. A previous verified result does not independently authorize a later archive. Archive must re-query and re-verify the current Drive object. If that later check fails, is unavailable, or is ambiguous, block archive and record sanitized diagnostics; do not rewrite the historical manifest or change the terminal file status within that run.
4. Preserve staging artifacts whenever success cannot be established. Do not overwrite or delete source/Drive objects as a recovery shortcut.
5. Keep detailed attempt/error diagnostics in sanitized operational logs. Do not add manifest fields or enum values without explicit approval.
6. These exception cases are approved policy clarifications, not runtime evidence. Executable schema/transition tests and runtime reconciliation tests remain required.

### Remaining decisions unaffected by this approval

Historical open-items statement: these choices were unresolved at that earlier approval point. Later OSD-03, timestamp and crash/concurrency decisions apply, and table adoption is recorded in §5. Their runtime implementation and acceptance remain incomplete.


## 6. Approved timestamp validation policy shape — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21; option A).
- Timestamp fields must use UTC ISO 8601 representation with a `Z` UTC designator. Invalid format or an unparseable value is rejected; the validator must not silently normalize or repair it.
- Where both `started_at_utc` and `finished_at_utc` are present, reject the manifest if `finished_at_utc` is earlier than `started_at_utc`.
- Future-time validation must account for an explicitly configured tolerance for clock skew. Reject timestamps beyond that configured tolerance; do not silently rewrite them.
- Timestamp freshness thresholds must be configuration-driven and applied in the relevant operational context. Do not hard-code an unapproved numeric threshold or treat every historical manifest as invalid merely because it is old.
- **Still open:** numeric tolerance/freshness values, the exact operational contexts in which freshness applies, and clock synchronization/monitoring expectations. These are configuration/operations decisions under EOLM-MAN-011, not part of this policy-shape approval.
- If timestamp validation fails, fail closed: reject the manifest for the operation that depends on it; do not repair timestamps or treat invalid metadata as valid.
## 7. Approved terminal file-state policy — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21; option A).
- **Chosen rule:** `verified` and `failed` are terminal file states within a single `run_id`; no transition out of either state is permitted in that run.
- **Later archive-time verification:** archive must still independently re-query and verify the current Drive object. If that check reports mismatch, unavailable, ambiguous, or verifier failure, block archive and write sanitized operational diagnostics. Do not rewrite the prior manifest or alter that run's terminal file status to reflect the later check.
- **Run separation:** a subsequent processing attempt or new evidence requiring a new lifecycle record must use a new `run_id` and a new manifest; it must not mutate the historical run's result.
- **Scope boundary:** this decision resolves terminal file-state and post-verification mutation semantics only. It does not decide run-level terminal status transitions, OSD-03 aggregation, verification method/time/hash combinations, timestamp freshness/clock-skew, crash/concurrency/latest-manifest selection, or implementation/test evidence. At the time of that individual decision the complete table was not normative; later adoption is recorded in §5.

## 8. Approved crash, concurrency, and latest-manifest policy shape — 2026-10-21

- **Manifest eligibility:** validate the manifest and cross-check its filename identity against the identity encoded in the JSON before treating it as a candidate for current state.
- **Ambiguous latest selection:** timestamps alone do not break ties. If candidates cannot be uniquely ordered using approved identity/ordering rules, mark the selection ambiguous and stop the dependent operation; never choose arbitrarily.
- **Concurrent updates:** detect conflicting updates for the same target. A stale read must not overwrite newer state; re-read and re-validate or fail safely.
- **Crash handling:** preserve a crash-left `running` manifest as unfinished. Do not silently convert it to `success` or `failure`.
- **Destructive-action gate:** do not archive or delete until current remote state has been re-established and verified.
- **Still open:** concrete locking/atomic-write strategy, the exact identity fields and filename convention, stale-run recovery, and executable concurrency/crash/ambiguity tests. This decision does not assert implementation or test evidence.


## 9. Approved OSD-03 run/period aggregation policy — 2026-10-21

- **Run-level `success`:** every eligible target is `verified`, with no relevant validation/processing error. A successful enumeration and validation with zero eligible targets is `success` and `outcome: no_work`.
- **Run-level `partial_failure`:** at least one eligible target is verified and at least one relevant eligible target remains `failed` or `unknown`, or an unclassifiable run-scope validation error exists. Verified independent progress does not erase errors.
- **Run-level `failure`:** no eligible target is verified and a processing/validation failure exists, or the system cannot establish a valid no-work result. Enumeration/access failure is not no-work.
- **Period completion:** every eligible target assigned to that period must be `verified`, and no relevant validation/processing error may affect the period. Any `failed` or `unknown` assigned to the period prevents completion.
- **Unclassifiable filename:** retain as run-scope error; never infer a period from `LastWriteTime`. It prevents run-level success but does not automatically invalidate an independently complete known period whose inventory is established.
- **No enum expansion:** use existing run statuses and `outcome: no_work`; do not introduce `skipped` or other values.
- **Approved representation (2026-10-21):** keep the approved manifest v1 field set unchanged. Store period summaries and unassigned run-scope validation errors in a separate durable derived aggregation report linked to the run by `run_id`. The report must be checked against the frozen eligible inventory; missing, malformed, stale, or inconsistent report data cannot certify period completion. Report schema, atomic publication/recovery rules, runtime implementation, and executable aggregation tests remain pending.


## 9. Approved timestamp, future-skew, freshness, and clock policy — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- Every timestamp field must be a parseable UTC ISO 8601 timestamp ending in uppercase `Z`. Reject offset-form timestamps, timezone-less timestamps, malformed strings, and unparseable values.
- `finished_at_utc` must be greater than or equal to `started_at_utc`; reject any terminal manifest with an earlier finish time. Do not rewrite or repair invalid timestamps.
- Maximum future-time tolerance is 5 minutes relative to the runtime's current UTC clock. Reject timestamps more than 5 minutes ahead for the operation that depends on them.
- Freshness threshold is 24 hours, configurable. Apply freshness checks only to timestamps generated or updated during the current execution (run start/finish and verification-attempt timestamps). Do not reject historical manifests solely because they are older than 24 hours.
- Assume host OS time synchronization is configured. Detect unavailable or clearly invalid clock readings when the platform exposes this information. If current UTC time cannot be obtained reliably, fail closed for time-dependent operations. No separate external monitoring/alerting service is required by this decision.
- The 5-minute and 24-hour values are approved initial defaults and must remain configurable. Reject invalid, negative, non-finite, or unparseable configuration values; do not silently fall back to defaults.
- Required tests: fixed-clock boundaries at exactly 5 minutes and just beyond; fresh timestamp at exactly 24 hours and just beyond; malformed/offset/timezone-less timestamp rejection; end-before-start rejection; invalid configuration rejection; unavailable clock fail-closed; historical-manifest age alone does not invalidate history.
- **Scope boundary:** this approval does not resolve crash recovery, concurrency, latest-manifest tie-breaking, OSD-03 aggregation, or runtime archive authorization. Archive must independently re-query and verify current Drive state. At the time of that individual approval the full table was not normative; later adoption is recorded in §5; no runtime implementation or passing executable tests are claimed.


## OSD-02 approved crash/concurrency/latest-manifest policy (2026-10-21)

Maintainer approved C1-A/C2-C/C3-B/C4-A. C1-A requires validated same-directory temporary writes, atomic create-if-absent, compare-before-replace, and fail-closed behavior when guarantees are unavailable. C2-C requires a per-scope OS named mutex plus exclusive ownership-token lock record; stale lock recovery is explicit and must verify the owner is gone. C3-B preserves crash-left `running` history and creates a new `run_id` only after recovery checks, with a fresh inventory and reconciliation of uncertain uploads. C4-A selects only a unique maximum validated `started_at_utc` for the exact PC/log-type/period scope; ties, malformed/conflicting candidates, read errors, or incomplete enumeration block operation, and there is no fallback to an older success. Timestamp freshness/future tolerance are not lock or retry timeouts.

Synthetic tests for crash points, concurrent create/update, lock ownership/recovery, interrupted runs, uncertain uploads, and resolver ambiguity are required but **not yet executed/evidenced**. These decisions do not claim runtime implementation or close P0-008/P0-010/P0-012.


## OSD-02 crash/concurrency test requirements — pending execution

- Inject crashes before/during temporary write, after flush/validation, before publication, and after publication; prove incomplete temp files are never authoritative and failed publication leaves prior content unchanged.
- Race concurrent first publishers and concurrent updates; prove create-if-absent and compare-before-replace prevent overwrite.
- Test named-mutex contention/failure, process termination, lock ownership-token mismatch, and stale-lock recovery. Age/PID alone must not authorize lock removal.
- Preserve crash-left `running` manifest byte-for-byte; after verified owner recovery, create a new `run_id` with a fresh inventory; reconcile uncertain uploads before retry.
- Test unique latest timestamp, equal maxima, malformed or identity-mismatched candidates, read/enumeration failure, and latest non-success blocking fallback to older success.
- Use synthetic fixtures and temporary directories only. Evidence status: **not run / not yet evidenced**; no runtime acceptance is implied.
