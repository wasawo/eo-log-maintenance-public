# Decision Register: C-18–C-32

- Status: Fixed and deferred decisions are recorded here; overall P0 acceptance remains incomplete. The authoritative P0 readiness/acceptance gate is in docs/implementation-workflow.md §4.
- Scope: Initial implementation of ElectronicObserver log maintenance
- Canonical source: GitHub

## Fixed decisions

- **C-18 / C-29 — Retry ownership:** Python performs one API attempt per invocation and returns one result. No Python-level, HTTP-client, or library automatic retries, backoff, or jitter. PowerShell alone classifies retryable results and controls up to four total attempts, with waits of 1, 5, and 15 minutes. Before retrying an upload with an unknown outcome, query Drive state.
- **C-19 / C-22 — Test scope:** Test synchronization, cloud content verification, manifests, archival, IPC, configuration, logging, locks, and retry behavior. Initial runtime has no local-source deletion or Drive deletion code, operation, or setting. Tests must verify that deletion capabilities are absent; passing tests never authorizes adding/enabling deletion.
- **C-20 / C-21 — Documentation/configuration:** Use `SyncLogs.ps1` for sync and PC-A-only `ArchiveLogs.ps1` for archive. `ArchiveAndUploadLogs.ps1` is not an official entry point. Remove `allowDelete`; omit `allowArchive` from PC-B; PC-A's `allowArchive` must be explicitly true to archive. Unknown, missing, malformed, or role-inappropriate config fails before processing. Use canonical `BattleLog` casing.
- **C-23 — OAuth scope (deferred):** Determine the minimum viable scope during Python adapter implementation. Validate list, metadata, upload, and download/hash operations against the actual My Drive folders. Do not widen scope without documenting and reviewing the need. Production authentication is not complete until validated.
- **C-24 — Scheduler times (deferred):** Choose quiet, staggered PC-A/PC-B times before Task Scheduler setup. Run monthly and on first startup in the month if missed; PC-A checks PC-B completion hourly and does not wait indefinitely.
- **C-25 — Filename patterns (resolved):** The complete patterns and real-date validation rules are defined in `docs/filename-and-period-selection.md`. BattleLog: `^(?<Date>\d{8})_\d{8}@.+\.txt$`; ErrorReport: `^(?<Date>\d{8})_\d{8}\.txt$`. Extract the first eight characters, parse strictly as `yyyyMMdd` using invariant culture, and never fall back to LastWriteTime. Unexpected or invalid filenames are validation errors; an unclassifiable filename prevents the run from being reported as fully successful. Manifest status names and transitions remain deferred under C-26.
- **C-26 — Manifest schema (partially resolved under OSD-02):** The maintainer approved required integer `schema_version: 1` and, on 2026-10-21, approved the field specification in `docs/manifest-schema-v1-proposal.md` including run identity/status, per-file results, Drive verification fields, types, enums, nullability, and field-level constraints. Missing/malformed/unsupported versions are rejected safely; existing manifests are not implicitly migrated or rewritten. The candidate transition table is in `docs/manifest-state-transition-v1-proposal.md` and is not yet wholly normative. The verification-result-to-file-state mapping was approved on 2026-10-21: `verified → verified`; `mismatch → failed`; `unavailable`, `ambiguous`, and verification-operation `failed` → `unknown`; `not_checked` leaves the current file state unchanged. The retry-exhaustion rule was approved on 2026-10-21: retry exhaustion alone does not imply failure; use `failed` only with reliable evidence of definitive non-success, and retain `unknown` if cloud outcome is uncertain. Exhaustive allowed/forbidden transitions, outcome/aggregation with OSD-03, freshness/clock-skew policy, crash/concurrency behavior, executable schema/transition tests, and runtime evidence remain pending.
- **C-27 — Distribution release details (deferred):** Before distribution implementation, decide final folder/access model, GitHub Actions authentication, release tags/version/approval, and old package retention. Distribution remains one-way and separate from log maintenance.
- **C-28 — Archive gate:** PC-A requires explicit `allowArchive: true`; missing/invalid values fail closed. PC-B configuration containing `allowArchive` is invalid. Both PCs' relevant manifests and file content must be verified. Archive means copy, verify, and record only; never delete the Drive source.
- **C-30 — Implementation phases:** Phase 0 resolves items required before implementation; Phase 1 establishes shared foundations; Phase 2 syncs, verifies cloud content, and records manifests without local deletion; Phase 3 archives on PC-A, verifies SHA-256, and records results without Drive deletion. Later phases test recovery, distribution, Dry Run, and scheduling. Deletion is not an acceptance criterion.
- **C-31 — Retention and naming:** BattleLog syncs all eligible periods through the previous month; archive eligibility is previous year and older. ErrorReport syncs through the previous year; archive eligibility is two years before the current year and older. In October 2026, BattleLog sync is September 2026 and earlier and archive is December 2025 and earlier; ErrorReport sync is 2025 and earlier and archive is 2024 and earlier. Period selection uses filename date, never LastWriteTime.
- **C-32 — Initial inventory:** Keep inventory/restoration records separate from operational manifests. Compare Drive files against PC-A backups by name, size, and SHA-256. Use Dry Run review before restore. Unmatched, conflicting, or unknown-origin files are held and never automatically restored, archived, or deleted. Inventory completion is not evidence of operational sync success or archive eligibility.

## Deferred items and implementation gates

| Item | Required before | Gate |
|---|---|---|
| Complete filename patterns (SEL-05) | Target-selection implementation | Sample review from PC-A and PC-B; normal and exception cases documented |
| Exact manifest schema | Manifest implementation | Schema and negative tests reviewed |
| OAuth scope (AUTH-17) | Python Drive adapter production validation | Required Drive operations tested with minimum scope |
| Scheduler times (SCH-05) | Task Scheduler setup | Quiet times selected and PC schedules staggered |
| Distribution folder/auth/release/retention | Distribution automation | Access model and release lifecycle reviewed |
| Local source deletion | Any future separate feature | New design, review, tests, and explicit approval; excluded from initial implementation |
| Drive deletion | Any future separate feature | New design, review, tests, and explicit approval; excluded from initial implementation |

## Current implementation status

The repository currently has JSON Schema contract tests, but runtime scripts and runtime safety tests remain incomplete. This register records decisions; it does not claim the implementation or tests have passed.


## C-26 — OSD-02 verification-result mapping approval — 2026-10-21

The maintainer approved this mapping for a file's verification result to its per-file status:

- `verified` → `verified`
- `mismatch` → `failed`
- `unavailable` → `unknown`
- `ambiguous` → `unknown`
- verification-operation `failed` → `unknown`
- `not_checked` → leave the current file status unchanged

A known content mismatch is a confirmed failure. Unavailable, ambiguous, or failed verification does not establish the cloud object's content/state and must remain `unknown`; none may authorize success or archive. This approval is limited to the mapping and does not approve verification method/time/hash combinations, retry exhaustion, terminal-state rules, OSD-03 aggregation, freshness, crash/concurrency, or the full transition table. OSD-02 and P0-010 remain open.


## C-26 — OSD-02 retry-exhaustion decision — 2026-10-21

The maintainer approved that exhausting the retry budget does not by itself determine file status. Set `failed` only when reliable evidence establishes definitive non-success (for example, an explicit non-retryable rejection that guarantees no object was created, or a confirmed content mismatch). If the cloud upload outcome remains uncertain, retain `unknown`. Timeout, communication failure, incomplete Drive enumeration, and retry exhaustion alone must not be converted to `failed`. Verification `unavailable`, `ambiguous`, or verification-operation `failed` remains `unknown`; confirmed `mismatch` maps to `failed`. This resolves retry-exhaustion classification only; OSD-02/P0-010 remain open.


## C-26 — OSD-02 retry-exhaustion exception-case approval — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- **Approved artifact:** exception cases EX-01–EX-10 and cross-cutting rules in `docs/manifest-state-transition-v1-proposal.md` §6.
- **Chosen policy:** file status is based on reliable evidence, not retry count alone. A definitive rejection maps to `failed` only when the operation contract establishes that no remote object was created. Timeouts, communication failures, incomplete/uncertain Drive listing, ambiguous candidates, and verification-operation failures map to or remain `unknown` when cloud state cannot be established. A confirmed content mismatch maps to `failed`.
- **Reconciliation:** `unknown → pending` requires complete, trustworthy enumeration proving target absence and a retry permitted by policy. A unique same-content candidate can map to `verified` only after OSD-01 trust and actual content-verification requirements are met.
- **Archive safety:** previous verification does not authorize archive by itself; archive must re-query and verify current Drive content. If current verification is mismatch, archive is blocked; if unavailable/ambiguous/verification failed, state remains unknown and archive is blocked.
- **Scope boundary:** this approval does not close OSD-02 or P0-010. Post-verification/terminal-state transitions, cross-field verification constraints, OSD-03 aggregation, timestamp freshness/clock-skew, crash/concurrency/latest-manifest resolution, executable tests, and runtime evidence remain pending. No runtime implementation or test pass is claimed.


## C-26 — OSD-02 terminal file-state policy — 2026-10-21

- **Approving authority:** project maintainer (explicit selection of option A in conversation on 2026-10-21).
- **Chosen rule:** within a single `run_id`, `verified` and `failed` are terminal file states. No transition out of either state is permitted within that run; a later run must use a new `run_id` and a new manifest.
- **Archive-time re-verification:** archive must independently re-query and verify the current Drive object. If the current check finds a mismatch, is unavailable/ambiguous, or the verifier fails, block archive and record sanitized operational diagnostics. Do not rewrite the historical manifest or change the file's terminal state in the prior run.
- **Rationale:** preserve run history and avoid retroactively mutating an execution record, while ensuring stored `verified` evidence never bypasses current archive checks.
- **Scope boundary:** this resolves file-level terminal-state immutability only. Run-level transitions, OSD-03 aggregation, verification method/time/hash combinations, timestamp freshness/clock-skew, crash/concurrency/latest-manifest resolution, executable tests, and runtime evidence remain open. OSD-02 and P0-010 remain open.

## C-26 — OSD-02 verification object method/time/hash consistency — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of option A in conversation on 2026-10-21).
- **Chosen rule:** `verification.method` describes the method actually used to obtain `observed_sha256`, not a method merely attempted.
- **Allowed combinations:**
  - `not_checked` → `not_performed`, `checked_at_utc: null`, `observed_sha256: null`.
  - `verified` or `mismatch` → `drive_sha256` or `download_sha256`, non-null `checked_at_utc`, and a valid observed SHA-256. `mismatch` requires an observed hash different from the expected source hash.
  - `unavailable`, `ambiguous`, or verification-operation `failed` when no observed hash was obtained → `not_performed`, non-null `checked_at_utc` representing the attempt time, and `observed_sha256: null`.
- **Diagnostics:** attempted method, sanitized error details, and retry-by-retry details are recorded in sanitized operational logs, not added to the approved manifest schema. Do not store an arbitrary candidate hash when identity is ambiguous.
- **Invalid combinations:** every status/method/time/hash combination outside the approved table in `docs/manifest-state-transition-v1-proposal.md` §4 must be rejected.
- **Rationale:** separates an attempted operation from successful hash acquisition, preserves the approved field set, and avoids claiming evidence that was not obtained.
- **Scope boundary:** this resolves verification-object field consistency only. Run-level status/time consistency, OSD-03 aggregation, timestamp freshness/clock-skew, crash/concurrency/latest-manifest selection, executable validation tests, and runtime evidence remain open. OSD-02 and P0-010 remain open.

## C-26 — OSD-02 run status and finish-time consistency — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of option A in conversation on 2026-10-21).
- **Chosen rule:** `started_at_utc` is required for all run statuses; `running` requires `finished_at_utc: null`; terminal statuses `success`, `partial_failure`, and `failure` require a non-null `finished_at_utc`.
- **Validation:** reject manifests whose status/finish-time combination violates this rule.
- **Boundary:** this does not establish chronological ordering, freshness, future-time, or clock-skew constraints, nor crash recovery or OSD-03 aggregation. A crash-left `running` manifest is not automatically rewritten to `failure`.
- **Scope boundary:** this resolves run status/finish-time consistency only. OSD-03 aggregation, timestamp ordering/freshness/clock-skew, crash/concurrency/latest-manifest selection, executable tests, and runtime evidence remain open. OSD-02 and P0-010 remain open.

## C-26 — OSD-02 timestamp validation policy shape — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of option A in conversation on 2026-10-21).
- **Chosen rule:** timestamp fields use UTC ISO 8601 with a `Z` designator; invalid/unparseable values are rejected without normalization or repair.
- **Ordering:** when both timestamps exist, reject `finished_at_utc` earlier than `started_at_utc`.
- **Future time and freshness:** use configuration-driven future-time/clock-skew tolerance and context-appropriate freshness thresholds. Reject timestamps beyond the configured future tolerance; do not hard-code unapproved numeric values or silently rewrite timestamps.
- **Still open:** actual numeric values, exact contexts where freshness is enforced, and clock synchronization/monitoring expectations under EOLM-MAN-011.
- **Scope boundary:** this approves policy shape only. OSD-03 aggregation, crash/concurrency/latest-manifest resolution, executable tests, runtime evidence, and the specific timestamp configuration remain open. OSD-02 and P0-010 remain open.

## C-26 — OSD-02 crash/concurrency/latest-manifest policy shape — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of option A in conversation on 2026-10-21).
- **Manifest eligibility:** validate structure and cross-check filename identity with the identity recorded inside the manifest before considering it a current-state candidate.
- **Latest selection:** do not use timestamp alone to resolve ties. If candidates remain ambiguous, stop the dependent operation rather than selecting arbitrarily.
- **Concurrent updates:** do not allow stale reads to overwrite newer state; re-read and re-validate or fail safely when a conflict is detected.
- **Crash behavior:** a crash-left `running` manifest remains unfinished; do not silently rewrite it to `success` or `failure`.
- **Archive/deletion gate:** block destructive actions until current remote state is re-established and verified.
- **Still open:** atomicity/locking implementation, exact identity fields and filename convention, stale-run recovery procedure, and executable tests. OSD-02 and P0-010 remain open; no runtime support is claimed.


## C-25 / OSD-03 — Run and period aggregation policy approval — 2026-10-21

- **Approving authority:** project maintainer (explicit approval of combined Option A + Option C in conversation on 2026-10-21).
- **Run status:** all eligible files verified with no relevant errors => `success`; successful enumeration/validation with zero eligible targets => `success` plus `outcome: no_work`; verified work plus any eligible-file `failed`/`unknown` or unclassifiable run-scope error => `partial_failure`; no verified eligible work with a processing/validation failure or inability to prove no-work => `failure`.
- **Period completion:** every eligible file assigned to the period must be `verified`, with no known relevant error affecting that period. `failed`/`unknown` blocks that period.
- **Unclassifiable names:** remain run-scope errors and cannot be assigned by timestamp fallback. They block run-level success, but do not automatically invalidate independently complete known periods.
- **Safe progress:** process independent valid files where safe; successful sub-work never erases or hides an error.
- **Still open:** OSD-02 must determine manifest representation for period summaries and run-scope errors, or explicitly use a derived report without new manifest fields. Implementation, table-driven tests, and runtime evidence remain pending. OSD-03 and P0-008/P0-010 are not closed by this policy approval alone.


## C-33 — OSD-02 / OSD-03 derived aggregation report representation — 2026-10-21

- **Approving authority:** project maintainer (explicit approval in conversation on 2026-10-21).
- **Decision:** formally adopt Option A. Preserve the approved manifest v1 field set; do not add fields for period summaries or unassigned run-scope validation errors.
- **Representation:** write those results to a separate durable derived aggregation report associated with the originating manifest/run through `run_id`.
- **Required safeguards:** validate report identity and contents against the originating run and frozen eligible inventory. Missing, malformed, stale, or inconsistent report data cannot certify period completion. Unclassifiable filenames remain run-scope errors and must never be assigned to periods using `LastWriteTime`.
- **Rationale:** avoids changing the approved v1 schema while retaining explicit period-level outcomes and run-scope validation evidence.
- **Affected requirements:** EOLM-MAN-003–006, EOLM-MAN-009–012, EOLM-OPS-003, EOLM-TST-003, EOLM-TST-010; OSD-02, OSD-03, P0-008, P0-010.
- **Still open:** report schema/version, canonical path/name, publication/atomicity, crash/recovery behavior, freshness and consistency checks, runtime implementation, and executable tests.
- **Disposition:** representation choice approved; dependent design and implementation evidence remain open.

## C-34 — Aggregation artifact storage direction — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21; both PCs need access to aggregation reports and evidence.
- **Chosen option:** C3 — local authoritative artifacts plus verified Google Drive copies.
- **Required behavior:** create and validate immutable report/evidence artifacts locally first. Replicate to the configured Drive maintenance destination only after local validation. A Drive copy is available to the other PC only after exact identity and content verification succeeds.
- **Failure handling:** Drive replication failure leaves the validated local artifact intact and must not be represented as cross-PC availability. If upload outcome is uncertain, reconcile current Drive state before retrying.
- **Scope boundary:** this selects the storage direction only. Inventory digest framing/field set, path normalization, enumeration-completeness evidence schema, exact local root and Drive mapping, upload/verification implementation, locking, crash recovery, and executable tests remain open. OSD-02, OSD-03, P0-008, and P0-010 remain open; no runtime implementation or evidence is claimed.


## C-35 — Frozen inventory digest framing — 2026-10-21

- **Approving authority:** project maintainer, explicit approval in conversation on 2026-10-21.
- **Chosen option:** A2 — versioned length-prefixed records.
- **Approved contract:** fixed ASCII domain/version prefix; unsigned 64-bit big-endian record count; records sorted by unsigned lexicographic UTF-8 bytes of validated canonical relative path; fields ordered as relative path, filename, canonical decimal size, and lowercase SHA-256; each field encoded as unsigned 32-bit big-endian byte length followed by UTF-8 bytes.
- **Path and value rules:** forward-slash relative paths after source-separator conversion; reject absolute/drive/UNC paths, empty, dot, or dot-dot segments, NUL, backslash, filename/path disagreement, and duplicate canonical paths. Do not Unicode-normalize or case-fold. Size must be a non-negative integer encoded as canonical decimal ASCII; expected SHA-256 must be 64 lowercase hexadecimal ASCII characters.
- **Empty inventory:** hash the fixed prefix plus an unsigned 64-bit zero record count; absent evidence is not equivalent to an empty inventory.
- **Reference vectors:** the proposal document includes empty-inventory and one-record vectors for independent cross-runtime tests. These are specification vectors, not production test evidence.
- **Scope boundary:** implementation, executable schema, cross-runtime tests, evidence artifact shape, and publication/recovery behavior remain open. OSD-02, OSD-03, P0-008, and P0-010 remain open.


## C-36 — Immutable enumeration/validation evidence artifact — 2026-10-21

- **Approving authority:** project maintainer, explicit approval on 2026-10-21.
- **Chosen option:** B2 — a separate immutable run-input evidence artifact.
- **Required behavior:** preserve initial enumeration and filename-validation outcomes independently from the manifest and derived aggregation report. Evidence must distinguish completed enumeration/validation from failed or incomplete work; a missing artifact, missing count, or missing error list must not be interpreted as zero errors or a successful empty inventory.
- **Identity and immutability:** evidence identity must match the originating run ID, PC ID, and log type. A conflicting artifact for the same run identity must be reconciled, never silently overwritten.
- **Storage:** create and validate the local authoritative artifact first; replicate to the configured Google Drive destination only after local validation. Cross-PC consumers may use the remote copy only after identity and content verification.
- **Scope boundary:** this approves the separate-artifact direction, not the full JSON schema, embedded versus referenced inventory, count reconciliation rules, evidence digest canonicalization, exact paths, locking, Drive verification implementation, or recovery behavior. Those remain open; no runtime implementation or test evidence is claimed.


## C-37 — Embedded inventory in B2 evidence — 2026-10-21

- **Approving authority:** project maintainer, explicit approval on 2026-10-21.
- **Chosen option:** A — embed the complete frozen eligible-target inventory in the immutable run-input evidence artifact.
- **Rationale:** the evidence is self-contained and recovery does not depend on a separate inventory file being present. Duplication with manifest target records is intentional.
- **Required validation:** embedded targets must match the originating manifest's frozen target set and approved A2 inventory digest. Any count, path, size, filename, hash, or digest mismatch is an integrity failure; never repair by silently choosing one copy.
- **Compatibility:** do not change manifest v1 fields. The evidence schema remains a separate versioned artifact.
- **Scope boundary:** exact count reconciliation across all enumerated entry categories, evidence digest canonicalization, path/root configuration, atomic local publication, Drive verification, locking/recovery, and executable tests remain open. No runtime implementation or test evidence is claimed.


## C-38 — Exhaustive B2 enumeration classification and count reconciliation — 2026-10-21

- **Approving authority:** project maintainer, explicit approval on 2026-10-21.
- **Chosen option:** A — exhaustive mutually exclusive classification and count reconciliation.
- **Required invariant:** each entry returned by a completed enumeration belongs to exactly one of `eligible_targets`, `valid_ineligible`, `invalid_relevant`, or explicitly contract-authorized `ignored_entries`. Their counts must sum exactly to `entries_observed`; no entry may be omitted or counted twice.
- **Error treatment:** `enumeration_errors` is a separate diagnostic count, not part of the category sum. Any enumeration error prevents enumeration status `completed`; partial enumeration must not be interpreted as an empty or complete inventory.
- **Follow-up:** source-entry universe and link handling are specified by C-40; the completion/error-detection rule is specified by C-41. Executable enumeration tests remain open. This decision does not claim implementation or test evidence.


## C-39 — Canonical integrity digest for B2 evidence — 2026-10-21

- **Approving authority:** project maintainer, explicit approval on 2026-10-21.
- **Chosen option:** A — hash a fixed canonical representation, excluding only `integrity.digest` from its own input.
- **Canonical bytes:** normative rules are in `docs/run-input-evidence-v1-proposal.md` §5. UTF-8 JSON without BOM, insignificant whitespace, or trailing newline; object keys sorted by unsigned UTF-8 byte order at every level; `inventory.targets` sorted by canonical relative-path UTF-8 bytes; `validation.errors` sorted by relative path, code, filename, and error ID; deterministic string escaping; canonical integer notation only; floating-point values prohibited.
- **Validation before hashing:** reject duplicate object keys, invalid UTF-8, unknown schema versions, missing fields, invalid types, and values outside constraints; no silent coercion or repair.
- **Digest:** SHA-256 represented as exactly 64 lowercase hexadecimal ASCII characters. `integrity.algorithm` and `integrity.canonicalization` remain in the hashed object; only `integrity.digest` is omitted.
- **Versioning:** changes to canonicalization rules require a new canonicalization identifier or evidence schema version.
- **Scope boundary:** executable schema, duplicate-key-safe parser, independent cross-runtime canonical-byte/digest vectors, source-entry universe and pagination semantics, publication/root configuration, Drive verification, locking, and recovery remain open. Any future array requires a specified ordering before implementation. No runtime implementation or test evidence is claimed.


## C-40 — B2 source-entry universe and link handling — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen scope:** recursively enumerate the configured source scope; directory entries are traversal nodes and are excluded from `entries_observed`; each encountered non-directory entry is counted once.
- **Regular files:** classify each by the filename/eligibility validation rules. Only eligible regular files appear in the frozen target inventory.
- **Symbolic links and reparse points:** never follow them. Count the link/reparse-point entry itself once as `ignored_entries`, explicitly authorized by this source contract. Never traverse a link target, including a target inside the source root.
- **Unsupported/inaccessible entries:** any unsupported non-regular entry type or inability to enumerate a directory prevents `enumeration.status = completed`; do not silently omit the entry or subtree.
- **Scope boundary:** C-41 specifies traversal completion/error detection; concurrent source mutation semantics and executable enumeration tests remain open. No runtime implementation or test evidence is claimed.


## C-41 — B2 enumeration completion determination — 2026-10-21

- **Approving authority:** project maintainer (explicit selection of option A on 2026-10-21).
- **Chosen option:** A — completion requires successful, exhaustive traversal of every directory in the configured source scope.
- **Completion rule:** the root and every reached directory must be enumerated to normal exhaustion. Directory-enumerator creation, iteration/advancement, entry inspection needed for classification, and enumerator cleanup/disposal failures count as enumeration errors when they prevent proving exhaustive traversal. Lazy exceptions raised during iteration must be caught and treated as errors; successful enumerator creation alone is not proof of completion.
- **Failure behavior:** on the first enumeration/access/I/O error, stop traversal and set enumeration status to `failed` or `incomplete` (the runtime must use the schema-defined status distinction consistently). Record a sanitized diagnostic and increment the separate `enumeration_errors` count. Do not claim count reconciliation, complete inventory, no-work, or period completion from a failed/incomplete enumeration. Never silently skip the affected directory or subtree.
- **Scope boundary:** C-42 defines best-effort mutation detection but does not provide an atomic snapshot guarantee. Executable enumeration/change-detection tests remain open. No runtime implementation or test evidence is claimed.


## C-42 — B2 source mutation detection during enumeration — 2026-10-21

- **Approving authority:** project maintainer (explicit selection of option A on 2026-10-21).
- **Chosen option:** A — best-effort change detection with fail-closed handling; do not claim a filesystem snapshot.
- **Detection contract:** record each traversed directory's observed entry-name/type set and relevant metadata for each observed regular file. After initial enumeration and eligible-target hash collection, enumerate the directories again and compare entry sets; re-check the relevant metadata for every observed regular file and eligible target. Relevant metadata includes entry type, size, and last-write timestamp at the precision exposed by the supported API. Eligible-target content hashes must be calculated from the actual bytes frozen into the inventory; if metadata changes across the read, reject the scan. If a target's bytes cannot be read and hashed consistently, the scan is not complete.
- **Change response:** any detected addition, deletion, rename, type change, size change, timestamp change, or mismatch between the frozen target set and the re-check invalidates the evidence. Mark enumeration failed/incomplete, preserve sanitized diagnostics, and do not publish or use it as completed evidence. Errors during the second pass are also enumeration errors under C-41.
- **Limitations:** this is best-effort detection, not an atomic snapshot. A change that occurs and reverts between checks, or a content change that preserves all checked metadata and is not reflected in the computed target hash, may evade detection. The implementation must not claim detection of all concurrent mutations.
- **Scope boundary:** executable tests for add/remove/rename, type/size/timestamp changes, read/hash races, second-pass errors, and limitations remain required. No runtime implementation or test evidence is claimed.


## C-43 — Enumeration status semantics — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** A — define status by observed outcome, with distinct meanings for `completed`, `failed`, and `incomplete`.
- **`completed`:** the root and every reached directory reached normal exhaustion, and all required C-42 consistency/change-detection checks completed successfully.
- **`failed`:** an explicit failure or invalidating condition was observed, including enumeration/access/I/O or entry-inspection error, unsupported non-regular entry type, detected source mutation, or inconsistent metadata/hash read.
- **`incomplete`:** the run ended before completion without an observed failure cause, such as cancellation, timeout, interruption, or process termination, where a durable evidence record can still be finalized. If termination prevents finalization, missing/unfinalized evidence is invalid; do not synthesize an evidence artifact.
- **Safety invariant:** only `completed` can support no-work or completeness certification. Both `failed` and `incomplete` are non-complete and must fail closed.
- **Follow-up:** C-44 defines `enumeration_errors` as distinct error-event count with duplicate propagation deduplicated. Executable status-transition and interruption tests remain required. No runtime implementation or test evidence is claimed.


## C-44 — `enumeration_errors` counting semantics — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** A — count distinct underlying error events, not catch/log invocations or affected entries.
- **Counting invariant:** `enumeration_errors` equals the number of distinct enumeration-error events represented by unique sanitized diagnostic records for the run. Each event has one stable `error_id`; the count is not added to the mutually exclusive entry-classification totals.
- **Deduplication:** if the same underlying failure propagates through traversal, validation, cleanup, or logging layers, retain one diagnostic event and count it once. Do not increment the counter again merely because another layer observes or reports that same failure.
- **Multiple failures:** independently observed failure events are counted separately, even if they occur in the same directory or affect the same entry. Do not collapse separate failures solely because their error codes or paths match. When implementation cannot reliably establish that two observations are the same event, it must use a documented deterministic correlation rule and test it; it must not silently discard a possibly distinct failure.
- **Failure invariant:** any enumeration-error event prevents `enumeration.status = completed`. Sanitized diagnostic records must not expose secrets or unsanitized exception text.
- **Follow-up:** C-45 defines identity at first observation and propagates the same event ID across layers. Executable tests for same-exception propagation, multiple independent failures, diagnostic/count equality, and fail-closed status remain required. No runtime implementation or test evidence is claimed.


## C-45 — Error-event identity and deduplication — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** A — assign an error-event ID at first observation and propagate it through all layers.
- **Identity rule:** the layer that first converts an underlying enumeration failure into a diagnostic event assigns one `error_id`. Wrappers and downstream traversal, validation, cleanup, and logging layers preserve and propagate that ID; they do not mint a new ID for the same failure.
- **Deduplication:** retain one canonical diagnostic per `error_id`. Repeat observations with that ID do not create another event or increment `enumeration_errors`. Conflicting core attributes for one ID are an internal consistency error, not silently merged.
- **Independent events:** separately observed failures receive separate IDs, even if they share a path or error code. Do not infer identity from path, code, or time alone.
- **Scope:** IDs must be unique within the run/evidence artifact. Exact encoding and collision handling remain open. No runtime implementation or test evidence is claimed.
- **Follow-up:** C-46 defines `error_id` encoding and uniqueness/collision policy; executable propagation and deduplication tests remain required.


## C-46 — `error_id` format and collision handling — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** A — per-run monotonic sequence, formatted `ERR-000001`, `ERR-000002`, etc.
- **Allocation:** allocate the next sequence value exactly once when a distinct event is first created. Propagation layers preserve the assigned ID and never allocate a replacement for the same event.
- **Uniqueness scope:** IDs must not be reused within one run/evidence artifact. Cross-run identification uses the run identifier plus `error_id`; the ID alone is not a global identifier.
- **Exhaustion:** if the supported sequence range is exhausted, fail closed. Do not wrap, reuse, or truncate IDs.
- **Follow-up:** executable tests for sequence formatting, uniqueness, propagation, exhaustion, and duplicate counting remain required. No runtime implementation or test evidence is claimed.


## C-47 — Diagnostic fields, nullability, and sanitization — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** A — fixed required schema with field-specific nullability and sanitization.
- **Required keys:** `error_id`, `error_code`, `phase`, `operation`, `target_relative_path`, and `message`. All keys are present; nullable values are explicit JSON `null`.
- **Nullability:** `error_id`, `error_code`, `phase`, and `operation` are non-null. `target_relative_path` and `message` may be null when no safe value can be produced.
- **Sanitization:** `error_id` follows C-46; codes/phases/operations use bounded documented enums; paths are relative, normalized, traversal-safe, and redacted; messages are short, bounded, and scrub secrets, personal data, absolute paths, and control characters. Raw exception text, exception objects, stack traces, environment variables, request/response bodies, and arbitrary metadata are prohibited.
- **Failure behavior:** if optional text/path cannot be safely sanitized, emit null. If a non-null required field cannot be validly populated, do not emit a malformed diagnostic; fail evidence finalization closed and report evidence unavailable/failed through the outer status channel.
- **Determinism:** sanitization and serialization must be deterministic. Field maximum lengths and exact allowlists must be fixed in the schema before implementation.
- **Follow-up:** C-48 defines diagnostic schema versioning and compatibility policy; C-49 will define controlled vocabularies for `error_code`, `phase`, and `operation`. Runtime implementation and executable sanitization/schema tests remain pending.


## C-48 — Diagnostic schema versioning and compatibility — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** A — explicit positive integer `schema_version` on every diagnostic record; strict, version-specific validation.
- **Validation:** reject missing, malformed, non-integer, non-positive, or unsupported versions. Reject unknown fields and validate all required keys, types, nullability, field constraints, and sanitization rules against the selected version.
- **Compatibility:** each released version's structure and semantics are immutable. Any incompatible change requires a new integer version; adding a field also requires a new version because unknown fields are rejected.
- **Historical evidence:** no implicit migration, repair, rewrite, or relabeling. An older version may be read only while an explicit validator for that version remains implemented; validation must not mutate the record.
- **Version scope:** diagnostic `schema_version` is independent of the enclosing artifact's `evidence_schema_version`.
- **Required tests:** valid supported version; missing/null/string/fractional/zero/negative/unsupported version; unknown and missing fields; type/nullability checks; version-specific validation; no mutation during validation; historical-version acceptance only with an explicit validator.
- **Follow-up:** C-49 fixes the initial allowlists; C-50 will define detailed mapping from concrete failure conditions to `error_code`. Runtime implementation and executable tests remain pending.


## C-49 — Diagnostic controlled vocabularies — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** fixed, case-sensitive allowlists for `error_code`, `phase`, and `operation`.
- **Unknown handling:** unrecognized failure types map to reserved `unknown_error`; genuinely unidentifiable phase/operation map to reserved `unknown`. Raw exception class names/messages are never enum values.
- **Initial allowlists:** `error_code`: `enumeration_failed`, `invalid_filename`, `file_access_denied`, `file_read_failed`, `file_metadata_failed`, `hash_failed`, `source_mutation_detected`, `manifest_invalid`, `evidence_invalid`, `validation_failed`, `serialization_failed`, `aggregation_failed`, `publication_failed`, `unknown_error`. `phase`: `enumeration`, `classification`, `metadata`, `content_read`, `hashing`, `manifest_validation`, `evidence_validation`, `evidence_finalization`, `aggregation`, `report_serialization`, `report_publication`, `unknown`. `operation`: `enumerate_entries`, `classify_target`, `read_metadata`, `read_content`, `compute_hash`, `detect_source_mutation`, `validate_manifest`, `validate_evidence`, `finalize_evidence`, `aggregate_results`, `serialize_report`, `publish_report`, `unknown`.
- **Validation:** reject unlisted values, case variants, empty strings, and nulls. No aliases or dynamic enum extension. Any allowlist change requires a reviewed contract update and tests; schema-incompatible changes follow C-48.
- **Required tests:** accept all allowlisted values; reject invalid values; deterministic known-failure mappings; fallback behavior for unmapped failures; no exception-data leakage.
- **Follow-up:** C-50 defines detailed failure-condition-to-`error_code` mappings. Runtime implementation and executable tests remain pending.


## C-50 — Deterministic diagnostic `error_code` mapping — 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** A — explicit failure-condition mapping table with deterministic precedence and `unknown_error` fallback.
- **Contract:** every distinct diagnostic event receives exactly one primary `error_code`; propagated observations preserve the original `error_id` and code. Independent failures receive independent event IDs and are classified separately.
- **Mapping:** use the normative priority-ordered table in `docs/aggregation-inventory-integrity-options.md`, C-50. The table maps invalid readable manifest to `manifest_invalid`; invalid readable evidence to `evidence_invalid`; observed source inconsistency to `source_mutation_detected`; naming violations to `invalid_filename`; explicit access-denied signals to `file_access_denied`; directory traversal failures to `enumeration_failed`; metadata/content-read/hash failures to their respective codes; general contract validation to `validation_failed`; serialization, aggregation, and publication failures to their respective codes; and unmatched conditions to `unknown_error`.
- **Precedence and evidence:** evaluate explicit conditions in priority order; rely on structured operation context and stable platform error categories, never free-form exception text or localization. Do not treat unreadable artifacts as invalid content. Do not infer source mutation without an observed mismatch. Never reclassify the same propagated event at a later layer.
- **Allowlist/versioning:** emitted codes must be members of the C-49 diagnostic schema-v1 allowlist. This decision adds no new code or field and does not change the schema version. Any later allowlist or semantic contract change requires review under C-48.
- **Required tests:** each mapping row; precedence collisions; access-denied versus generic I/O; read versus hash; invalid readable manifest/evidence versus unreadable artifact; mutation versus ordinary read failure; serialization versus publication; propagation and deduplication; independent events; unknown fallback; no message-text parsing; no raw exception-data leakage.
- **Runtime input model:** approved Option A — one required, case-sensitive scalar Condition token selected by the trusted producer. Exact tokens, structured prerequisites, and invalid-input behavior are normative in docs/aggregation-inventory-integrity-options.md, C-50. Unknown/malformed tokens reject with a fixed non-disclosing error; only unmatched_failure maps to unknown_error.
- **Implementation boundary:** Resolve-DiagnosticErrorCode maps one token to the existing C-49 allowlist and does not infer from exception data, allocate event IDs, select phase/operation, or implement producer-side precedence. Propagation layers preserve the original classification.
- **Follow-up:** runtime producer integration and tests for precedence selection, propagation/deduplication, and end-to-end evidence remain required. Helper tests do not establish P0 acceptance.


## C-51 — Deterministic diagnostic phase/operation mapping — approved 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** explicit processing-context mapping table with deterministic `unknown/unknown` fallback, defined normatively in `docs/aggregation-inventory-integrity-options.md`, section “Deterministic phase and operation mapping — C-51”.
- **Contract:** assign `phase` and `operation` together when the distinct diagnostic event is first created, from trusted structured context describing the failed action. Wrappers, retries, cleanup, and logging preserve the original pair. Do not infer from exception text or substitute the later observer's context.
- **Fallback:** use `unknown/unknown` only when trusted structured state genuinely cannot identify the pair; missing instrumentation or an unimplemented mapping must be exposed rather than hidden. Reject semantically undefined pairs.
- **Compatibility:** no fields or allowlist values are added; schema v1 remains unchanged.
- **Required tests:** every mapping row, invalid pair rejection, event propagation invariance, failed action versus observer context, read versus validation failure, genuine unknown fallback, missing instrumentation, deterministic repeated results, and no exception-text parsing.
- **Follow-up:** C-52 defines diagnostic message templates and sanitization behavior. Runtime implementation and executable tests remain pending.


## C-52 — Deterministic diagnostic message templates — approved 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** fixed, deterministic message templates selected by validated `error_code`; the normative code-to-template table is in `docs/aggregation-inventory-integrity-options.md`, section “Diagnostic message templates and sanitization — C-52”.
- **Data policy:** schema-v1 templates contain no dynamic parameters. Do not include raw exception text/class, stack traces, OS-provided error text, environment variables, request/response bodies, credentials, tokens, connection strings, absolute paths, or other uncontrolled data. Safe target context, if needed, is represented only by the separately validated `target_relative_path` field.
- **Fallback and validation:** every C-49 allowlisted `error_code` has one exact template, including `unknown_error`. Missing/invalid codes reject diagnostic finalization; do not infer a message from exception text. A valid code produces a non-null message of at most 512 Unicode characters.
- **Determinism/versioning:** templates are fixed English ASCII strings in schema v1. Any future interpolation or template semantics change requires explicit contract review and tests; parameters, if later approved, must be defined from trusted structured state with a field-specific allowlist and sanitization contract.
- **Required tests:** exact message fixture per code, invalid-code rejection, unknown fallback, byte-for-byte determinism, no interpolation, length and encoding constraints, secret/path/exception/stack-trace non-disclosure, and proof that messages do not affect classification, event identity, deduplication, or aggregation.
- **Follow-up:** C-53 will address diagnostic sanitization mechanics for path and other structured fields, including exact normalization/redaction order. Runtime implementation and executable tests remain pending.


## C-53 — Structured-field sanitization and path safety — approved 2026-10-21

- **Approving authority:** project maintainer, explicit selection of option A on 2026-10-21.
- **Chosen option:** validate structured values and emit only values proven safe; if an optional target path is unsafe, emit JSON `null` for the entire path field rather than partially redacting it. Normative processing order is defined in `docs/aggregation-inventory-integrity-options.md`, section “Structured-field sanitization and path safety — C-53”.
- **Path handling:** normalize separator direction only for validation; reject absolute, drive-qualified, UNC/device, NUL/control-containing, colon-containing, empty-segment, dot-segment, traversal-segment, or otherwise invalid relative paths. Do not collapse or resolve unsafe segments. Check the candidate against a sensitive-path policy before emission. Do not partially mask a path.
- **Other fields:** required enum/identity fields must pass schema and allowlist validation or diagnostic finalization fails. Messages use exact C-52 templates with no interpolation. JSON escaping does not replace validation.
- **Determinism:** no filesystem, symlink, current-working-directory, locale, or machine-specific path-resolution dependency. Sanitization must not change event identity, classification, aggregation, or source artifacts.
- **Required tests:** malformed and hostile path cases, sensitive match at every segment position, no partial redaction, valid canonical relative path, deterministic cross-platform behavior, serializer escaping, invalid required fields, and preservation of event identity/classification when an optional path becomes null.
- **Follow-up:** C-54 defines the concrete sensitive-path pattern/segment policy and matching precedence. Runtime implementation and executable tests remain pending.


## C-54 — Concrete sensitive-path secret-format grammars — approved 2026-10-21

- **Approval:** maintainer explicitly selected A for P1, P2, P3, P4, P5, and P6.
- **Normative source:** `docs/decision-record-c54-sensitive-path-detection.md`, section “C-54 approved secret-format grammars — P1–P6”.
- **Decision:** approve the URI user-info regex and character restrictions (P1); case-insensitive Bearer scheme with the specified non-empty ASCII token alphabet and optional trailing equals padding (P2); case-sensitive `ghp_` and `github_pat_` prefixes with their distinct ASCII suffix alphabets and minimum length 20 (P3); exactly uppercase `AKIA` plus 16 uppercase ASCII alphanumeric characters, with other AWS access-key prefixes out of scope (P4); the five fixed, case-sensitive PEM private-key markers listed in the decision record (P5); and the exact ASCII boundaries/case rules embedded in those patterns (P6).
- **Change control:** do not broaden patterns, infer other provider prefixes, add PEM labels, apply Unicode normalization, or substitute generic substring/entropy matching without explicit approval and tests.
- **Tests/evidence:** `tests/Test-C54PatternContract.ps1` checks synthetic positive, negative, boundary, and case fixtures and runs in Validate CI. This only validates the approved pattern grammar; it does not prove the runtime C-53/C-54 sanitizer, whole-field nulling, or diagnostic non-disclosure. Those remain pending.
- **P0 boundary:** runtime sanitization is not implemented/verified by this decision. P0-010 and P0-012 remain open.


## OSD-02 — Timestamp, freshness, and clock policy — 2026-10-21

- **Approving authority:** project maintainer, explicit approval in conversation on 2026-10-21.
- **Decision:** require parseable UTC ISO 8601 timestamps with uppercase `Z`; reject malformed, offset-form, timezone-less, and unparseable values.
- **Ordering:** reject `finished_at_utc < started_at_utc`; never repair timestamp values.
- **Future tolerance:** 5 minutes from runtime UTC now, configurable; reject values beyond this bound.
- **Freshness:** 24-hour configurable threshold, applied only to timestamps generated/updated in the current execution (run start/finish and verification-attempt timestamps). Do not invalidate historical manifests solely due to age.
- **Clock synchronization:** host OS time synchronization is assumed to be configured. Detect unavailable/clearly invalid clock readings where exposed; if current UTC cannot be obtained reliably, fail closed for time-dependent operations. Separate external monitoring/alerting is not required.
- **Configuration validation:** reject invalid, negative, non-finite, or unparseable tolerance/threshold values; no silent fallback.
- **Required evidence:** fixed-clock boundary tests, malformed format and ordering tests, invalid configuration tests, clock-unavailable fail-closed tests, and historical-manifest age tests.
- **Affected requirements:** EOLM-MAN-011, EOLM-MAN-001–010, EOLM-TST-004–006, EOLM-TST-010 and dependent archive freshness gates.
- **Boundary:** this resolves the numeric timestamp/freshness/clock-sync question only. Crash/concurrency/latest-manifest decisions, OSD-03 aggregation, complete transition enforcement, runtime implementation, executable tests, and operational evidence remain open. No runtime support is claimed.


## OSD-02 approved crash/concurrency/latest-manifest policy (2026-10-21)

Maintainer approved C1-A/C2-C/C3-B/C4-A. C1-A requires validated same-directory temporary writes, atomic create-if-absent, compare-before-replace, and fail-closed behavior when guarantees are unavailable. C2-C requires a per-scope OS named mutex plus exclusive ownership-token lock record; stale lock recovery is explicit and must verify the owner is gone. C3-B preserves crash-left `running` history and creates a new `run_id` only after recovery checks, with a fresh inventory and reconciliation of uncertain uploads. C4-A selects only a unique maximum validated `started_at_utc` for the exact PC/log-type/period scope; ties, malformed/conflicting candidates, read errors, or incomplete enumeration block operation, and there is no fallback to an older success. Timestamp freshness/future tolerance are not lock or retry timeouts.

Synthetic tests for crash points, concurrent create/update, lock ownership/recovery, interrupted runs, uncertain uploads, and resolver ambiguity are required but **not yet executed/evidenced**. These decisions do not claim runtime implementation or close P0-008/P0-010/P0-012.


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
