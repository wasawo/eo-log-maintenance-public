# Staging File Lifecycle

> 2026-10-27 compatibility boundary: [Q1–Q10 and flattening](../development/requirements-design-task-review-20261027.md) require per-file movement through source deletion without both-PC period waiting. The existing v1 schema/helper behavior and dated evidence below are unchanged. A v1 `verified`/report/latest-manifest result is not proof of completed movement or permission to delete; both-PC selection/report completeness is not a new archive prerequisite. Deletion-state/IPC/persistence revisions remain detailed-design work. Do not alter old immutable artifacts or infer a schema upgrade from this policy note.

## 1. Purpose and Scope

This document defines the immutable staging-copy lifecycle used before uploading ElectronicObserver log files to Google Drive.

Read-only helper: `SourceInventoryRevalidation.observe_initial_staging_copy` reconstructs an exact frozen initial plan, then checks an explicitly selected existing staging copy's size/hash, single-link regular-file identity and ancestry before/after reading. It never reads source payloads or changes files/state. All permissions stay false; metadata-first history, allocated-copy identity binding, qualified/separate roots and actual Upload payload use remain unimplemented gates. See [observation boundaries](source-inventory-revalidation.md#既存staging-copyの独立読取観測).

Implementation evidence: `tests/test_upload_staging_integration.py` connects a frozen initial plan/B2 and source use-point revalidation to an actual create-new copy in its own synthetic OS-temp root, under a synthetic owned mutex. Explicit sequence numbers preserve the approved basename pattern; an occupied name is retained and only an explicitly requested next sequence is attempted. Reads are bounded by frozen size plus one byte. Flush/fsync/close is followed by regular-file, allocated identity, single-link, size and SHA-256 checks, plus a final source hash comparison. The fixture retains partial/conflicting/changed files and releases ownership on failure; it does not retry automatically.

Both PC/log combinations, empty/multiblock content, changed source, collision, injected partial disk-full, short write, post-close modification and source hardlink replacement are covered. This is tests-only copy evidence: no production copy function, metadata-first writer, ready-state publication, Upload adapter or cleanup is implemented. The returned candidate observation always denies Upload/state changes. No real disk exhaustion, crash/power-loss durability, root/FS qualification, atomic snapshot or protection against later replacement is established. The lifecycle requirements below remain binding for the eventual runtime.

The same lifecycle applies to both PC-A and PC-B and to both `BattleLog` and `ErrorReport` uploads. Only the PC identifier and local paths differ.

This is a specification for the initial implementation. It defines staging creation, verification, upload gating, metadata updates, and normal-flow cleanup. Automatic recovery of leftovers from an interrupted run is deferred. The initial implementation must not delete local source logs or Google Drive source files.

Related specifications:
- `docs/development/implementation-workflow.md`
- `docs/design/powershell-python-contract.md`
- `docs/validation/runtime-safety-test-scenarios.md`

## 2. Runtime Requirements

- PC-A and PC-B must run PowerShell **7.6.7**.
- Windows PowerShell 5.1 compatibility is out of scope.
- Batch entry points must invoke `pwsh.exe`, not `powershell.exe`.
- At startup, validate that the running PowerShell version satisfies the required version. If validation fails, stop before processing files.
- Python remains a Drive API adapter. It performs one API attempt per request and must not implement implicit retries. PowerShell owns retry and recovery decisions.

Example sync invocation (illustrative until the official batch entry point is implemented):

```bat
pwsh.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0SyncLogs.ps1"
```

The exact entry-point script can differ by operation, but all supported batch entry points must use the same PowerShell runtime policy.

## 3. Staging Location and Naming

Staging is local to each PC and must not be synchronized to Google Drive.

Default directory:

```text
%LOCALAPPDATA%\eo-log-maintenance\staging
```

Staging file name:

```text
<run_id>_<sequence>_<original_filename>
```

- `run_id` identifies one execution on one PC and is unique per execution.
- `sequence` distinguishes files within a run and supports alternate names if a collision occurs.
- `original_filename` preserves the source filename.
- Never overwrite an existing staging file.
- Use atomic create-new semantics (for example, .NET `FileMode.CreateNew`) at the time of creation. A pre-check alone is insufficient.
- If a name is occupied, try another sequence number. If a free name cannot be allocated, mark that file `failed` and do not upload it.

A JSON metadata file is stored alongside each staging file. It records at least:

- `run_id`
- original relative path
- original filename
- size in bytes
- SHA-256
- status
- staging path

Metadata must be written through a temporary file, re-read and validated as JSON, and then replace the official metadata file. Do not assume this local atomic-replacement guarantee applies to Google Drive.

## 4. Target Inventory Freeze

After the per-PC global maintenance lock has been acquired and residual staging inspection has completed, freeze the eligible upload target list for the run. Record the target list in the run manifest.

Each target entry contains:

- filename
- relative path
- size in bytes
- SHA-256

Files added after the target list is frozen are deferred to the next run. A file that disappears after target-list creation is marked `failed`; processing may continue for other frozen targets. Files that were not part of the frozen list are not failures for the current run.

Before staging each target, recompute the source file's size and SHA-256. If either differs from the frozen inventory, mark the file `failed` and do not upload it.

## 5. Capacity Checks

Check available staging capacity:
1. Once at the start, using the total size of the frozen target list.
2. Again immediately before creating each staging copy.
3. Handle a copy failure caused by capacity changing after a check.

The initial safety reserve is:

```text
required_free_bytes = remaining_target_bytes + ceil(remaining_target_bytes * 0.10) + 100000000
```

The fixed reserve is exactly **100,000,000 bytes** (decimal MB, not 100 MiB). All internal calculations use bytes. Human-readable logs may additionally show decimal MB.

If capacity is insufficient, mark the affected file `failed`, do not upload it, and continue processing other files where safe. If a copy fails, attempt to delete only the incomplete staging file created by the current operation. If that cleanup fails, retain the file and emit a warning.

## 6. Per-File State Machine

Allowed staging/upload states:

- `staging`: metadata has been written before the staging copy is created.
- `ready`: staging copy exists and its size and SHA-256 match the frozen target.
- `pending`: upload has not been confirmed as started/successful.
- `uploaded`: the upload API reported success, but cloud content verification is not yet complete.
- `verified`: the cloud object has been verified to contain the expected bytes.
- `failed`: a failure is confirmed.
- `unknown`: upload outcome cannot be determined reliably.

The metadata-first sequence is mandatory. The run manifest initially records each frozen target as `pending` to mean “registered for processing; staging has not begun.” When processing that target begins, the per-file state transitions to `staging` before the staging copy is created. After staging verification, `ready` means the copy is prepared; immediately before an upload attempt, transition `ready → pending` again. These two `pending` states are distinguished by their preceding state and recorded transition history; `pending` alone never proves that upload was attempted or succeeded.

1. Write staging metadata with status `staging`.
2. Create the staging copy without overwriting any existing file.
3. Verify the copy's size and SHA-256 against the frozen target inventory.
4. Update metadata to `ready`.
5. Upload only the verified staging copy. Once ready, do not read the original source file for upload.
6. Update the run manifest as the upload progresses and after cloud verification.
7. Remove the staging copy and its metadata only after upload success, cloud content verification, and the required manifest update have all been confirmed.

If creation or verification fails, do not upload the copy. Attempt to remove only the incomplete staging file created by that operation; if deletion fails, retain it and warn.

## 7. Cloud Verification and Unknown Outcomes

A successful upload API response is not by itself proof that cloud content is correct. Verify the Drive object using the strongest available method:
- If Drive provides a trustworthy SHA-256, compare it to the expected hash.
- Otherwise download the cloud object through the API and calculate SHA-256 locally.
- Metadata-only retrieval is not content verification.

If upload communication fails or times out and the result is uncertain, set the file state to `unknown`. Do not treat it as success or convert it to `failed` merely because the retry limit was reached. Set `failed` only when reliable evidence confirms that the operation did not succeed and the failure is definitive (for example, an explicit non-retryable rejection that guarantees no object was created, or a confirmed content mismatch). A timeout, communication failure, incomplete Drive enumeration, or exhausted retry budget alone is not enough. For verification results, use the approved mapping: `mismatch → failed`; `unavailable`, `ambiguous`, or verification-operation `failed` → `unknown`; `not_checked` leaves the current file state unchanged. A verification operation failure is not proof of a content mismatch.

Before retrying an upload with an unknown outcome, PowerShell must inspect the current Drive state:
- Object exists and content hash matches: transition to `verified`.
- Object is confirmed absent: re-upload may proceed.
- Object exists with a different hash, or its state/content cannot be confirmed: retain `unknown` and stop processing that file.

Python performs one API attempt per request. PowerShell owns retry policy, with at most four total attempts and waits of 1, 5, and 15 minutes between attempts. Before a retry when the previous upload outcome is uncertain, inspect Drive state first. Reaching four attempts does not itself classify the file as `failed`: use `failed` only when reliable evidence establishes definitive non-success; otherwise retain `unknown`.

If a staging file is `unknown`, cloud content is unverified/mismatched, or the required manifest update fails, retain the staging file and metadata. Do not delete them.

If staging deletion fails after the upload, cloud verification, and manifest update have succeeded, log a warning and continue. Do not change the successful upload outcome to `failed`; retain the remaining staging artifacts.

## 8. Manifest and Run Status

### 8.1 Schema version and compatibility

- Every operational maintenance manifest must include a required integer `schema_version` field. The initial schema version is `1`.
- Reject a manifest when `schema_version` is missing, malformed, or unsupported. Stop the affected processing safely; never interpret the manifest as successful or archive-eligible.
- Do not implicitly migrate, rewrite, or convert existing manifests. Any future schema migration requires an explicitly approved, versioned migration design and tests.
- The field names, types, enums, nullability, verification object, and listed field-level constraints in `docs/design/manifest-schema-v1-proposal.md` were approved on 2026-10-21. Implementations must not infer missing fields or silently default invalid values.
- The verification-result-to-file-state mapping was approved on 2026-10-21: `verified → verified`; `mismatch → failed`; `unavailable`, `ambiguous`, and verification-operation `failed` → `unknown`; `not_checked` leaves the current file status unchanged. The retry-exhaustion rule was also approved on 2026-10-21: retry exhaustion alone does not imply failure; `failed` requires reliable evidence of definitive non-success, otherwise retain `unknown`. These approvals do not settle every verification method/time/hash combination.
- The exhaustive allowed/forbidden transition table is still pending OSD-02. `docs/design/manifest-state-transition-v1-proposal.md` remains a discussion proposal for all unapproved rows and rules; it is not wholly normative.
- Run/period aggregation remains subject to OSD-03; timestamp freshness/clock skew remains subject to EOLM-MAN-011; crash/concurrency and latest-manifest tie-breaking remain unresolved. Approval of fields does not authorize runtime implementation or establish runtime evidence.

Each maintenance execution creates a new manifest with a unique `run_id`. A run manifest is first written with status `running` after lock acquisition and before file processing, then updated to its final status using the same `run_id`.

Run status values are:
- `running`
- `success`
- `partial_failure`
- `failure`

A zero-work run uses `status: success` and `outcome: no_work`; do not add a separate `skipped` run status.

File-level states are recorded separately from run status. If any file remains `unknown` after retry/reconciliation, the run is `partial_failure` when other files were verified, or `failure` when the overall process did not succeed. An uncertain file must never be counted as a success.

A new run uses a new `run_id` and fresh per-file states beginning at `pending` (target registered, staging not yet started); do not copy forward prior file states. On beginning staging for a target, transition `pending → staging`, then `staging → ready` after copy verification, and `ready → pending` immediately before upload. Older manifests remain unchanged. The latest run for a given PC, period, and log type takes precedence: if it is `running`, hold; if it is `partial_failure` or `failure`, do not fall back to an older success. Even with a successful latest manifest, archive decisions must re-verify the current Drive state.

Manifest location:

```text
_maintenance/manifests/PC-A/
_maintenance/manifests/PC-B/
```

Manifest file naming:

```text
<PC-ID>_<LogType>_<TargetPeriod>_<run_id>.json
```

Example: `PC-A_BattleLog_2026-09_<run_id>.json`

Validate that the filename identity matches the internal JSON identity. Keep manifests indefinitely in the initial implementation; no automatic retention/deletion is permitted.

For local manifest updates, write to a temporary file, re-read and validate the JSON, then replace the official manifest. If a crash leaves a manifest in `running`, leave it incomplete; do not automatically rewrite it to `failure`. The next execution uses a new `run_id`.

## 9. Residual Staging Artifacts

At every maintenance-run startup, after acquiring the global per-PC maintenance lock and before beginning uploads, inspect the staging directory.

If even one residual artifact exists, emit a warning. The initial implementation must not automatically upload, recover, or delete residual artifacts.

Cases that require warning and retention:
- staging file without metadata
- metadata without staging file
- malformed JSON metadata
- inconsistent metadata or file state
- leftovers from an interrupted run

For malformed metadata, log the path and issue, and include `run_id` only if it can be parsed safely. Do not process affected artifacts automatically.

Merely detecting residual artifacts is warning-only and does not by itself change the run status. If residual inspection cannot complete (for example, access denied or enumeration failure), do not start uploads; set run status to `failure` and preserve existing files and metadata.

Automatic recovery of leftovers is deferred to a later phase. No time-based cleanup is allowed in the initial implementation.

## 10. Locking and Concurrency

One global lock serializes all maintenance operations on each PC. PC-A and PC-B use independent locks.

Lock acquisition waits/retries for up to 60 seconds. If the lock remains unavailable, log that another process is running and exit; do not force-kill or steal the lock. This contention exit is not a business failure. If an abandoned mutex is detected after a process crash, log it and verify the prior state before continuing.

## 11. Explicit Non-Goals for the Initial Implementation

The initial implementation must not:
- delete local source logs
- delete Google Drive source files
- overwrite existing staging files
- automatically recover, upload, or delete residual staging artifacts
- automatically clean up staging artifacts based on age
- treat metadata-only cloud retrieval as content verification
- upload directly from a mutable source file instead of the verified staging copy
- implement implicit retries in Python

## 12. Acceptance Test Perspectives

Use `docs/validation/runtime-safety-test-scenarios.md` for the shared test catalog and add/trace test coverage for at least:

- PowerShell version mismatch blocks processing before any file operation.
- Both PC-A and PC-B use `pwsh.exe` entry points.
- Frozen inventory records filename, relative path, size, and SHA-256.
- Source mutation after inventory freeze blocks upload.
- Staging metadata is written before the copy and transitions from `staging` to `ready` only after size/hash verification.
- A staging-name collision never overwrites an existing file and tries another sequence.
- Insufficient capacity at initial or per-file checks prevents that file's upload.
- Capacity loss during copy attempts cleanup only for the incomplete file created by the current operation.
- Only the verified staging copy is used as upload input.
- Unknown upload outcome triggers Drive-state inspection before retry.
- Cloud verification or manifest-update failure retains staging file and metadata.
- Normal successful flow removes staging file only after upload, cloud verification, and manifest update are confirmed.
- Failed staging deletion after otherwise successful flow produces a warning without changing the upload result.
- Any residual artifact triggers a warning and is retained.
- Residual inspection failure blocks uploads and produces run status `failure`.
- No local-source or Drive-source deletion path is introduced.

This document specifies behavior and acceptance perspectives; test implementation should reference the shared runtime test catalog rather than duplicate its full scenario descriptions.


## 13. OSD-03 aggregation policy approved — 2026-10-21

- `success` requires every eligible target to be verified and no relevant validation/processing errors.
- A zero-work run is `success` with `outcome: no_work` only when enumeration and validation completed successfully and there are no eligible targets. Enumeration failure/access denial or only-invalid relevant names must not be classified as no-work.
- When verified work coexists with an eligible file in `failed`/`unknown` or a relevant unclassifiable filename, use `partial_failure`. If no eligible work is verified and a processing/validation failure exists, or valid no-work cannot be established, use `failure`.
- Period completion requires every eligible file assigned to that period to be `verified`, with no relevant error affecting that period. A `failed` or `unknown` file blocks its period's completion.
- Unclassifiable names remain run-scope validation errors; never infer a period from `LastWriteTime`. They block run-level success but do not automatically invalidate a separately complete known period with an established inventory.
- Continue safe processing of independent valid files, but do not hide errors or count `unknown` as success. Do not add run status or outcome enum values.
- **Representation approved on 2026-10-21:** keep the approved manifest v1 field set unchanged. Store period summaries and unassigned run-scope validation errors in a separate durable derived aggregation report linked by `run_id`. The report must be validated against the frozen eligible inventory; missing, malformed, stale, or inconsistent report data must not certify period completion. Review/approval of `docs/design/aggregation-report-v1-proposal.md`, publication/recovery rules, implementation, and table-driven test evidence remain required.


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

## Pure upload-staging capacity observation (2026-10-25)

`Get-EoStagingCapacityObservation` in [LogFunctions.ps1](../../Common/LogFunctions.ps1) implements section 5 arithmetic from supplied remaining-target bytes, available-free bytes and an explicit reliable observation flag. The two byte values accept nonnegative PowerShell Int32, Int64 or BigInteger only; null, bool, float/decimal, strings and negative values are rejected without conversion. The required value is BigInteger: `remaining + ceil(remaining / 10) + 100000000`, using integer division, never floating-point arithmetic. The fixed reserve is decimal bytes and also applies when remaining is zero; zero input is not a no-work decision.

Invalid numeric inputs return `rejected` with a fixed reason and null RequiredFreeBytes. Valid numbers with unconfirmed free space return `held`; confirmed insufficient space also returns `held`. A sufficient supplied observation returns `requires_runtime_evidence`. Every output has MayCreateStaging=false and MayUpload=false. The helper reads no volume metadata, creates no file, performs no reservation/wait/cleanup and never authenticates root, space, clock or provider.

The eventual uploader still needs an independently qualified initial observation and a fresh per-file observation, plus safe handling if capacity changes after a check. Reusing an earlier result is not a capacity reservation or write authorization. This implements the approved upload-staging formula only; it does not adopt a capacity policy for API downloads or qualify the download test fixture.

[Tests](../../tests/Test-StagingCapacity.ps1) cover ceil boundaries, exact threshold and one-byte deficit, zero, numbers beyond Int64/IEEE-754 precision, type/reliability rejection, changing supplied capacity and non-authorizing flags. Formal staging/copy/runtime integration, real filesystem free-space observations and capacity-change failure acceptance remain pending.

## Explicit remaining-target size aggregation (2026-10-25)

`Get-EoStagingCapacityFromSizes` accepts a one-dimensional array snapshot of explicitly selected remaining target sizes, validates every member as a nonnegative Int32/Int64/BigInteger, sums in BigInteger and calls the capacity observation helper. It preserves the input and returns RemainingTargetBytes/TargetCount plus the existing required-space observation. One invalid member rejects the entire set with no partial total. Scalar/string/null, nested members and multidimensional arrays are not coerced into size snapshots.

Selection is external: the helper does not inspect manifest states, subtract uploaded/unknown files, authenticate frozen inventory or decide which targets remain. Empty arrays yield total zero but still require the fixed reserve; they are not evidence of no work. Valid totals remain available for diagnostics when an independent free-space observation is invalid/unconfirmed, but every result retains MayCreateStaging=false and MayUpload=false. Fresh initial/per-file space, source/inventory qualification, safe copy and mid-copy capacity loss handling remain runtime gates.

The same [capacity test](../../tests/Test-StagingCapacity.ps1) covers empty/typed/mixed arrays, totals beyond Int64, ceil after summation, invalid members without partial totals, input preservation and independently supplied start/per-file selections. This does not set a download capacity policy or mark EOLM-STG-009 fully verified.

## Explicit sizes bound to exact manifest/B2 (2026-10-25)

`inspect_staging_target_sizes` in [ManifestTransitionInspection.py](../../Common/ManifestTransitionInspection.py) projects an explicit tuple of canonical relative paths from exact running-manifest/B2 bytes. It checks independent PC/log/target-period/run identity, strict schemas, B2 digest/counts/inventory equality, complete enumeration/classification coverage and `manifest start <= enumeration start <= finish <= reliable current UTC + 5 minutes`. Missing/duplicate/noncanonical selections and invalid selected filenames are rejected. Both PCs are supported without archive capabilities.

The immutable StagingSizeObservation binds the original bytes, explicit path order, integer target sizes and exact integer sum. Empty selection still validates the whole pair and yields zero without declaring no_work. Known validation errors remain in the original B2. Terminal manifests are not accepted as current planning inputs, but a running snapshot alone does not prove an active/new/fresh run, ownership or safe continuation.

The helper never determines remaining targets from pending/ready/other file states. In particular, pending occurs both before staging and before upload; only trusted event history can distinguish the lifecycle point. An explicitly selected ready/pending file's size is a numeric observation, not permission to recopy it. All may_create_staging/may_upload/may_archive flags are false, and the helper performs no I/O, state transition, publication or copy.

These are internal Python observations, not a new IPC schema or implemented PS transport. Passing the size snapshot into the existing PS integer-capacity helpers, qualifying source/root/free space and enforcing event prerequisites at the actual use point remain runtime integration gates. [Tests](../../tests/test_staging_size_observation.py) cover both PCs/logs, order/huge integers/exact bytes, no implicit state selection, empty selection, invalid scope/clock/pair/coverage and preserved errors.

## Isolated Python-to-PowerShell capacity bridge (tests only, 2026-10-25)

[Python integration tests](../../tests/test_staging_capacity_bridge.py) project explicit sizes from synthetic exact manifest/B2 and pass only size arrays, synthetic free bytes and reliability through stdin to a [fixed test driver](../../tests/staging_capacity_bridge.ps1). The driver loads the existing PS helper, enforces exact PowerShell 7.6.7 via its runtime guard, and returns numeric observations through stdout. No input is evaluated as code, no caller directory/destination is accepted, and no operational artifacts, capacity query or network calls are made.

Tests cover both PCs/log types at exact threshold/one-byte deficit, values beyond Int64/IEEE-754 exact integers through JSON, empty selection/fixed reserve, unconfirmed space and invalid member types. Returned totals/reserves must remain JSON integers and all permission flags remain false. The test reports the actual PS version; local execution may select an executable with EOLM_TEST_PWSH, otherwise CI uses the pinned pwsh on PATH.

This demonstrates numeric interoperability of the supplied synthetic data only. The stdin shape is not a runtime IPC/schema decision, does not qualify duplicate-key/encoding/timeout/security handling for a production transport, and does not adopt C-02 fields. Formal PS transport, trusted input provenance, target/event-history selection, real free-space/root/FS qualification and staging/copy integration remain unimplemented. Passing tests does not make a deployable runtime or weaken Dry Run A.

## Windows caller-available space metadata observation (2026-10-25)

`Get-EoStagingFreeSpaceObservation` in [MachineConfigurationRootInspection.ps1](../../Common/MachineConfigurationRootInspection.ps1) observes an existing drive-rooted directory only. It rejects reparse components through the existing canonical directory inspector, obtains canonical volume/path observations before/after the query, and rejects detectable change or failure. The native [GetDiskFreeSpaceExW contract](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdiskfreespaceexw) distinguishes caller-available space from total volume free space (including per-user quota effects); this helper selects the caller-available UInt64 result and preserves it as BigInteger.

Success returns requires_runtime_evidence and AvailableFreeBytes only, with FreeSpaceReliable=false and MayCreateStaging/MayUpload=false. Failure returns held, a fixed reason and null bytes, without path/canonical name/raw exception output. No directory/file is created, repaired or cleaned by the helper. Dot-sourcing does not query space; calling it may initialize the existing Add-Type native metadata type. Dry Run A qualification of that initialization and runtime invocation remain absent.

The query does not authenticate the intended configured root, effective token/ACL, local/non-synced filesystem, metadata freshness, stable namespace across observations or capacity reservation. Canonical strings alone do not prove OS identity; the additional identity observations below remain non-authorizing and do not prove atomicity or ABA exclusion. Native/mapped/remote filesystem provider behavior and real operational roots are unqualified. Passing the result directly to the capacity helper with its false reliability flag must remain held. No external filesystem qualification is inferred from an API success.

[Tests](../../tests/Test-StagingFreeSpace.ps1) use only a self-created marked OS-temp directory. They verify native metadata, exact mocked UInt64 maximum, missing/file/reparse/invalid paths, query failure/type mismatch, changed canonical observations, sanitized output, original bytes and unqualified-capacity hold. The existing root inspector regression remains applicable. This is a read observation, not accepted staging/copy/runtime integration or a download capacity policy.

## Handle-derived directory identity checks (2026-10-25)

The native root inspector now obtains canonical path plus volume serial and file-index high/low from the same opened directory handle. Its old CanonicalDirectory API delegates to the new observation and preserves its string result. The free-space wrapper compares all of these fields before/after the path-based query, rejecting a detected identity change even when the canonical name is unchanged. Identity/canonical metadata stays internal and is not added to the public capacity result or logs.

The [GetFileInformationByHandle documentation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfileinformationbyhandle) describes comparison of volume serial/file index. The [structure contract](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-by_handle_file_information) also warns of filesystem-specific support, file-ID reuse and non-unique 64-bit IDs on ReFS. These checks detect supplied/observable changes only: they do not select or qualify a filesystem, guarantee uniqueness/currentness, pin the directory throughout GetDiskFreeSpaceExW, exclude ABA, or prove an approved root. FreeSpaceReliable and all permission flags remain false.

The free-space test adds changed serial/high/low with the same canonical string and actual same-path directory replacement during the query callback. Both move endpoints are verified inside its own synthetic OS-temp root; the original directory/bytes are preserved. Existing root canonical/alias/reparse regression remains unchanged. Formal root/provider/FS/token/Dry Run A and runtime acceptance remain open.

## Extended file identity for free-space observations (2026-10-25)

The free-space path now requires [GetFileInformationByHandleEx / FileIdInfo (0x12)](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyhandleex) from the same opened directory handle. [FILE_ID_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info) contains a 64-bit volume serial and 128 opaque file-ID bits. The internal immutable observation preserves the full volume value and both UInt64-sized ID portions; no float conversion, ID normalization or public-field serialization is performed.

Both before/after observations must contain the extended identity, and every identity portion must match. Failure/unavailability or a legacy-only observation is held, with no fallback to 64-bit-only checks. A missing pre-query identity stops before reading free space. The old canonical-string/legacy observer APIs retain their existing behavior and do not require this extra provider capability; no configuration schema or owner-v2 identity format changes.

Tests add native extended-identity acquisition, changes in all three UInt64 fields including adjacent values near UInt64 maximum, and missing pre/post identity/query failures. The native capability is demonstrated only on the synthetic test filesystem; this does not establish support or acceptance for other filesystems/providers. Wider IDs do not prevent reuse/ABA, pin the path through the space query, authenticate an intended root, or change FreeSpaceReliable/permission flags from false. Formal FS/token/root/runtime qualification remains open.

## Ancestor-chain identity observations (2026-10-25)

The free-space wrapper now collects ordered directory observations from the selected leaf through its drive root, before and after the query. Each component is opened for the existing metadata-only canonical/extended-ID observation, with reparse-component checks around chain collection. Missing/empty/legacy identity observations, chain-length changes or any per-position canonical/identity difference cause held/null bytes. Component IDs and paths remain internal; the capacity output and all false permission/reliability flags are unchanged.

This extends detection beyond replacement of the leaf itself. The synthetic test also moves a parent aside, creates a replacement under the old name, and moves the original leaf into it. It verifies that the leaf ID and bytes are unchanged, the parent ID changed, and the free-space wrapper holds. Both endpoints of each directory move are verified under its own marked OS-temp root. Synthetic empty/length-changed/parent-only-changed chains are also rejected.

Collection is a sequence of metadata reads, not one atomic ancestry snapshot. Handles are closed before the path-based space query. It does not prevent changes during collection, ID reuse/ABA or later replacement, authenticate configured roots/ACL/token/FS, or reserve space. Formal operational root/provider and Dry Run A/runtime qualification remain pending. Existing canonical-string APIs and native metadata layout are unchanged.
