# Implementation Workflow: ElectronicObserver Log Maintenance

Historical implementation inventory and dependency order: [2026-10-24 readiness review](../status/first-release-readiness-20261024.md). The current scope/order proposal follows the 2026-10-27 review below. This plan does not itself establish completion or production authorization.

2026-10-27: [初回ログ移動の受け入れ条件・実装順案](initial-move-delivery-plan-20261027.md)にQ1〜Q10と平坦化の合意を整理した。本書の役割/保持/削除/phase/受け入れ条件を合意へ整合した。現行の作業順案は同計画T0〜T5で、以下のphaseは分野別作業の参照。初回完成は両経路の元削除まで。具体的な削除・記録・IPC等の詳細契約と実装再開指示は未完。

2026-10-27から[要件・設計・タスクを再確認中](requirements-design-task-review-20261027.md)。AGENTSの該当境界は利用者の明示承認を受け限定改訂済み。本書は要件の整合であり、実装/実データ操作の開始指示ではない。


- Status: Proposed implementation plan
- Repository: `wasawo/eo-log-maintenance-public`
- Canonical source: GitHub
- Runtime deployment: Manual download/review on each PC
- Last updated: 2026-10-18

## 1. Purpose

Implement safe synchronization, verification, retention, and archival for ElectronicObserver BattleLog and ErrorReport files on PC-A and PC-B. This workflow covers both the initial catch-up of existing Drive data and ongoing manual/scheduled operation. Initial inventory/restoration is a separate, non-operational workflow; it is not treated as a successful sync or archive eligibility proof.

## 2. Fixed requirements

### 2.1 Roles

- **PC-A**: Moves its own eligible logs to the cloud, and moves eligible cloud logs to its archive. Each route includes destination-content verification, source-unchanged verification immediately before deletion, and deletion of only the verified source. Records and failure handling remain required; implementation is pending.
- **PC-B**: Moves its own eligible logs to the cloud, including deletion of only its verified local sources under Q5. It must never archive or delete cloud sources. Do not package or install an archive entry point for PC-B.
- **Google Drive for desktop shared log location**: Common destination for both PCs' logs and shared maintenance manifests.
- **GitHub**: Canonical source for scripts and documentation.
- **Google Drive distribution folder**: Approved release package destination, separate from the log collection folder. Distribution is one-way from GitHub to Drive. PC updates remain manual.

### 2.2 Paths

Both PC configurations require maintenanceLocal for that PC's authoritative local maintenance artifacts. Keep it disjoint from runtime, source, Drive and archive roots. See configuration-local-root.md for the approved field and template/runtime evidence boundary.

All paths and distribution folder URLs below are non-operational public examples. Keep actual values in private operator configuration. The distribution-folder placeholder is not a usable folder ID.

Installation requirement: deployment creates the target PC's active `Config/PC-A.json` or `Config/PC-B.json` from its example only when absent; the operator manually enters actual paths without copying or renaming files. Preserve existing active configuration on updates. Role fields and safe capability defaults remain template-defined. This installer/configuration flow is not implemented yet; it does not authorize runtime deployment or alter release approval gates.

PC-A local sources:
- BattleLog: `C:\\Example\\PCA\\Source\\BattleLog`
- ErrorReport: `C:\\Example\\PCA\\Source\\ErrorReport`
- Runtime root: `C:\\Example\\PCA\\Runtime\\`
- BattleLog archive: `C:\\Example\\PCA\\Archive\\BattleLog`
- ErrorReport archive: `C:\\Example\\PCA\\Archive\\ErrorReport`

PC-B local sources:
- BattleLog: `C:\\Example\\PCB\\Source\\BattleLog`
- ErrorReport: `C:\\Example\\PCB\\Source\\ErrorReport`
- Runtime root: `C:\\Example\\PCB\\Runtime\\`

Shared log destinations:
- BattleLog: `G:\\ExampleDrive\\SharedLogs\\BattleLog`
- ErrorReport: `G:\\ExampleDrive\\SharedLogs\\ErrorReport`
- Manifests/state: `G:\\ExampleDrive\\SharedLogs\\_maintenance\\`

Distribution folder supplied by the operator:
- `https://drive.google.com/drive/folders/<EXAMPLE_DISTRIBUTION_FOLDER_ID>`
- This folder is for script packages, not operational log files.

### 2.3 Retention and eligible periods

Period selection is based on the date encoded in the filename. `LastWriteTime` must never be used as a fallback. Verified metadata may corroborate Drive identity/content, but it must not override filename-derived period eligibility.

- BattleLog synchronization: all eligible periods **up to and including the previous month**.
- ErrorReport synchronization: all eligible periods **up to and including the previous year**.
- PC-A BattleLog archive: periods **in the previous year and earlier**.
- PC-A ErrorReport archive: periods **up to and including two years before the current year**.
- Current-month BattleLog and current-year ErrorReport remain on the source PC.
- Steady state: Drive retains the current year's BattleLog before the current month and the previous year's ErrorReport; PC-A archive retains older eligible periods.
- A failed/leftover older period must be eligible for retry on the next run. Do not process only one month/year and leave older backlog stranded.

Example for a run in October 2026:
- Sync BattleLog dated September 2026 and earlier.
- Sync ErrorReport from 2025 and earlier.
- Archive BattleLog from December 2025 and earlier.
- Archive ErrorReport from 2024 and earlier.

If no eligible files exist, report a successful skip for that category/period. A verification failure is an error, not a skip.

### 2.4 Collision and duplicate handling

- Keep the existing shared folder layout; do not add PC-A/PC-B subfolders to the log destination.
- Use SHA-256 to compare file contents.
- 2026-10-27 Q8: [confirmed collision policy](requirements-design-task-review-20261027.md#27-同名ファイルの扱いq8回答2026-10-27) applies to both move routes, including collisions caused by flattening source subfolders. These requirements do not authorize implementation resumption or production operations.
- If a same-name destination file has verified identical content, reuse that destination and avoid unnecessary re-copying. Verify both Q5 deletion conditions for each individual source before deleting it; matching a destination is not by itself a completed move.
- If same-name files have different contents, leave the existing destination unchanged, preserve the source, and report a conflict for that file. Continue unrelated files where safe. Do not automatically add `_PCA`/`_PCB`, rename existing files, overwrite, or merge contents. This replaces the earlier automatic suffix policy for initial completion.
- If content equality or destination identity cannot be established, preserve the source and report the unresolved reason. Manual conflict resolution and simultaneous-publication details remain to be designed.
- For inventory/reconciliation, a same-content comparison candidate requires matching name, size, and SHA-256 against a trusted comparison source, with exactly one candidate in a completely enumerated target Drive folder. A match is not proof of provenance and does not itself authorize restore, sync-success classification, or archive; see the approved OSD-01 decision in `docs/requirements/p0-open-specification-decisions.md`.
- Existing suffixed files are not automatically renamed or removed under this revision.
- Verify copied files with SHA-256 and record source name, final name, source PC, size, checksum, period, and result in the manifest.
- 2026-10-27 Q9: after ordinary per-file failures or source-deletion failures, the operator reruns the same move operation; a separate retry command is not required. Re-evaluate current sources and destinations, reuse verified identical content, and verify both Q5 conditions per source before deletion. Keep conflicts and unverifiable items unresolved in the results. Unknown outcomes require reconciliation; crash-left locks and ownership records remain subject to the separate explicit-recovery design. See [rerun policy](requirements-design-task-review-20261027.md). Result reconciliation and deletion API details remain to be designed; this is not implementation or production authorization.
- 2026-10-27 Q10: initial conflict support consists of an on-screen summary, a local detailed report identifying the comparison targets and reasons, operator judgment, and the ordinary move rerun after resolution. Dedicated comparison/resolution tooling is a later candidate; automatic conflict resolution is excluded. See [confirmed support scope](requirements-design-task-review-20261027.md). Report format, retention, status mapping, and manual preservation procedures remain detailed-design work; this scope decision does not establish implementation or production readiness.
- 2026-10-27 Q11: an unknown deletion outcome may become reconciled move completion only with valid source/destination/content binding records, confirmed absence of that source, and current matching destination content. Do not claim the prior deletion request succeeded, blindly retry deletion, treat access failure as absence, or rewrite old history. See the [record/reconciliation design proposal](../design/move-source-destination-verification.md). Record format, absence evidence, state/IPC and cross-route reconciliation remain to be specified; no implementation or real-data operation is authorized.

### 2.5 Deletion and cloud confirmation

- Q1/Q2/Q5: initial completion includes local-source deletion after both destination-content equality and source unchanged since copying are verified. Otherwise preserve that source. This requirement is not implementation-resumption or production-operation authorization.
- A file's presence in the Google Drive for desktop local folder alone is not proof of completed cloud upload.
- Preferred approach: Google Drive API query of the actual cloud file listing and metadata/checksum where available; compare the cloud file identity/name, size, and SHA-256 with the local source.
- If a cloud SHA-256 is unavailable, download the file through the Drive API and compute SHA-256 locally. Metadata-only name/size matching is insufficient. If API download/verification fails, identity is ambiguous, or size/hash mismatches, fail closed and retain the source; mark the period incomplete.
- Candidate enumeration must cover the intended target folder and complete all pagination successfully. API errors, incomplete pagination, insufficient access, or uncertain query scope must never be interpreted as confirmed zero/one candidates; hold and fail closed.
- For the separate initial-inventory workflow, the comparison source must be a confirmed, trusted PC-A backup/source record. Operational moves require their own current source/destination binding; do not impose a PC-A-only comparison source on PC-B's own transfer. Candidate identity and move completion are separate facts.
- API authentication, scopes, and the ability to access the supplied My Drive folder must be configured and tested before production validation.
- Q3/Q4: PC-A processes eligible files currently in the cloud without waiting for both PCs' period-completion manifests. Late arrivals are handled on a later run. Verify each current cloud source and archive destination independently.
- Q2/Q5: archive completion includes deleting only the verified cloud source after archive-content equality and source unchanged since copying are confirmed. Unknown, changed, or mismatched items retain their sources. Exact verification/deletion APIs and persistence contracts remain to be designed.
- Deletion is limited to these two move routes and per-source Q5 conditions. Generic or unconditional deletion is not adopted. During this document review no deletion code/schema is added; real-data deletion requires a separate concrete instruction under AGENTS.
- 2026-10-27 Q12: both routes directly delete only the verified eligible source file without moving it to a recycle bin/trash. Trash placement or disappearance from the source folder alone is not completed source deletion, including Q11 reconciliation. Do not empty trash, recursively delete folders or clean unrelated data. This confirms policy only; API/FS identity binding, response/absence contracts and implementation resumption remain pending.

### 2.6 Invocation

- Manual and scheduled runs use the same processing code; no separate initial-migration code path.
- Manual sync and manual archive entry points are provided where allowed.
- Scheduled tasks call the same entry points or script functions with equivalent parameters.
- The run computes all eligible backlog periods automatically.
- PC-B has no archive entry point or cloud-source deletion capability; only its own eligible local sources may be deleted as part of a verified move.
- Scripts run from each PC's local runtime root, not directly from Drive.
- GitHub changes are reviewed and tested, a release package is synchronized to the separate Drive distribution folder, then each PC is updated manually.

## 3. Runtime layout

PC-A:
```text
C:\\Example\\PCA\\Runtime\\
├── VERSION
├── Config\\PC-A.json
├── Common\\LogFunctions.ps1
├── SyncLogs.ps1
├── ArchiveLogs.ps1
├── Run_Log_Sync.bat
├── Run_Log_Archive.bat
└── logs\\
```

PC-B:
```text
C:\\Example\\PCB\\Runtime\\
├── VERSION
├── Config\\PC-B.json
├── Common\\LogFunctions.ps1
├── SyncLogs.ps1
├── Run_Log_Sync.bat
└── logs\\
```

## 4. P0 readiness and acceptance gate

The implementation phases below are a proposed delivery sequence, not evidence that implementation may proceed or that a phase has been accepted. Before declaring Phase 1 ready to exit or beginning operational rollout, the maintainer must review `docs/requirements/p0-gap-register.md`, `docs/requirements/p0-open-specification-decisions.md`, `docs/validation/requirements-source-audit.md`, and `docs/validation/p0-source-test-inventory.md` together.

P0 is **not accepted** while any P0 item is open, any required design decision is blocked/unapproved, or required runtime evidence is absent. The acceptance review must record each P0-001–P0-012 item as `complete`, `blocked` (with decision/prerequisite), or `incomplete` (with evidence gap); a documentation-only change cannot satisfy a runtime acceptance criterion. At minimum, the review must verify:

1. Source clauses are mapped to stable requirement IDs, implementation targets, executable tests, and exact CI/runtime evidence; unmapped or partial clauses have an explicit disposition (P0-010).
2. PowerShell 7.6.7 is enforced on every official entry point before file processing; official entry points and launch methods are identified (P0-001–003).
3. PowerShell/Python contract decisions are approved and contract/schema/semantic tests cover the agreed behavior (P0-005).
4. Release-package readiness and PC-specific allowlists match the approved official entry points; the legacy prototype alone cannot make a package deployable (P0-006, P0-009).
5. Existing helper/schema/package tests are not counted as end-to-end runtime evidence. Sync, cloud verification, manifest, archive, IPC, recovery, and Dry Run claims require executable tests at the relevant boundary (P0-004, P0-007–008).
6. P0 acceptance criteria are consistent across this workflow, `README.md`, the decision register, and the P0 gap register (P0-011).
7. Both move routes complete only after destination equality and source unchanged since copying are verified and that exact source is deleted. Tests prove retention on uncertainty, PC-B cloud-delete/archive refusal, and rejection of unrelated/period-ineligible sources across code/config/contracts/package/runtime (P0-012). Existing no-delete schema/package tests remain evidence of their current interfaces only.
8. All unresolved OSD items remain explicit blockers for the phase/function they govern. A proposal or static audit does not constitute operator approval.

**Gate result for the current repository:** not accepted. The maintainer selected the policy directions recorded in the [2026-10-24 decision ledger](../decisions/selected-policy-decisions-20261024.md), including OSD-02/03/04, but detailed C-02 result fields, credential/provider and distribution controls remain open. Official sync/archive entry points and runtime orchestration are absent. This checklist is a future acceptance gate, not a claim that P0 has passed. Do not use real credentials, real logs, production paths, or real Google Drive operations to fill evidence gaps without a separately approved test plan. Current dependency order is in the [first-release readiness inventory](../status/first-release-readiness-20261024.md).

## 5. Implementation phases

### Phase 0 — Baseline and decisions

1. Keep this plan and the README aligned with the fixed requirements.
2. Inspect the existing prototype only as a behavior reference; do not transplant it as a finished design.
3. Confirm actual filename patterns for BattleLog and ErrorReport, including date parsing, extensions, and any filename exceptions.
4. Retain the selected OAuth/principal/scope direction. The current four-operation interface does not support cloud-source deletion. Design and separately qualify the additional role-limited operation, required scope/provider behavior and cross-PC visibility; do not widen scope automatically.
5. Define manifest schema/version and rules for proving the origin of a pre-existing unmarked file.
6. Confirm whether the Drive API returns SHA-256 checksums for the relevant file types; define a fail-closed fallback when not available.

Exit criteria: filename/period rules and role-limited move contracts are coherent with Q1–Q10. New deletion/verification/result fields, persistence and provider/credential details are closed before their dependent implementation. Existing manifest transitions do not express deletion completion. Scheduler setup is later work, not a prerequisite for manual movement.

### Phase 1 — Common functions and configuration

Implement `Common/LogFunctions.ps1` and validate configuration:
- Load and validate the active PC configuration and role.
- Parse log dates/periods and select all eligible backlog files.
- Calculate SHA-256, compare files, and verify copied content.
- Create/read/version-check manifests and reject malformed or mismatched manifests.
- Produce structured logs and consistent exit codes.
- Provide safe path construction and prevent path traversal or accidental source/destination overlap.
- Add Dry Run that performs no upload, final download placement, archive placement, local-source deletion, or Drive deletion. Normal execution is subject to the two-route/Q5 source-deletion conditions; Dry Run never grants those effects.

Exit criteria: unit tests cover period boundaries, filename exceptions, configuration validation, manifest validation, hashing, and error handling.

### Phase 2 — Synchronization implementation

Implement `scripts/SyncLogs.ps1` and `Run_Log_Sync.bat`:
1. Identify the machine from validated configuration.
2. Enumerate all eligible BattleLog and ErrorReport files, including older backlog.
3. Flatten eligible files into the shared log-type destination by basename. Reuse verified identical content; preserve and report differing/ambiguous items without automatic renaming.
4. Copy to a temporary/staging destination where practical, verify the copied content, and then finalize without overwriting unrelated files.
5. Query Google Drive API to confirm the actual cloud-side file and its content metadata/checksum.
6. Confirm the exact local source is unchanged since copying immediately before deletion, and delete only that source after destination-content equality is confirmed. Retain changed/mismatched/unverifiable sources; deletion failure is not completed movement.
7. Write a manifest with per-file status and period-level completion status.
8. Treat no eligible files as a successful skip; treat failed checks as errors and preserve source files.

PC-B build/runtime must not contain or expose archive or cloud-source deletion; it may delete only its own eligible verified move sources.

Exit criteria: automated tests cover normal copy, already-present identical file with per-source verification, conflicting same-name file preservation without automatic renaming, ambiguous destination, partial copy, cloud API failure, checksum mismatch, retry after failure, and no eligible files.

### Phase 3 — Archive implementation (PC-A only)

Implement `scripts/ArchiveLogs.ps1` and `Run_Log_Archive.bat`:
1. Enumerate all eligible Drive backlog periods for archival.
2. Bind each current cloud source to its intended archive destination and validate the records required for that file.
3. Re-query and verify current cloud identity/content. Do not wait for either PC's period-completion manifest; late arrivals are handled on a subsequent run.
4. Copy eligible Drive files to the configured PC-A archive destination without overwriting different content.
5. Verify archive content with SHA-256 and ensure all files for the selected operation are accounted for.
6. Verify the cloud source is unchanged since copying immediately before deletion, then delete only that source after archive-content equality is confirmed. Retain unknown/mismatched/changed sources and record deletion failures separately.
7. Record archive outcome and verification results in an archive status manifest.
8. If evidence needed for that file is invalid, source identity is ambiguous, API access is unavailable, or verification fails, preserve the affected source and destination and report the reason. Independent files may complete; another PC's failed/missing period record alone is not a blocker.

Exit criteria: PC-A archive moves complete through cloud-source deletion, failure cases retain their sources, B absence/late arrivals and normal rerun are tested, and PC-B cannot execute archive/cloud-source deletion.

### Phase 4 — Recovery and idempotency tests

Test the same scripts against a seeded test directory and mock Drive API responses:
- Initial catch-up of the currently uploaded historical logs.
- Multiple old periods left behind after earlier failures.
- Re-running after partial completion.
- Identical files and differing same-name files from both PCs.
- Existing unmarked Drive files with and without trustworthy source manifests.
- Missing/invalid manifests and stale API metadata.
- Process interruption between copy, verification, deletion and result update; rerun must reconcile state, then delete only a source satisfying current Q5 conditions. Crash-left ownership problems require explicit recovery.
- Drive API quota, network, permission, and transient failures.
- Boundary dates around month/year rollover and leap day where relevant.

Exit criteria: re-running is safe and does not duplicate, overwrite, or delete unverified data.

### Phase 5 — Packaging and repository CI

Update the release allowlist and tests:
- Include `SyncLogs.ps1`, `ArchiveLogs.ps1`, `Common/LogFunctions.ps1`, runtime BAT files, safe example configs, VERSION, README, and CHANGELOG.
- Do not package active PC-specific configurations, secrets, operational logs, runtime manifests, tests, or repository-only automation.
- Require PowerShell parsing/static analysis and behavioral tests in CI.
- Correct `docs/release/distribution-design.md`: the usable entry point is `SyncLogs.ps1` plus PC-A-only `ArchiveLogs.ps1`, not the old `ArchiveAndUploadLogs.ps1` prototype.
- Keep package publication separate from log synchronization and deletion.

Exit criteria: a release package passes allowlist/exclusion tests and contains all required runtime files, with no deployable marker or secrets.

### Phase 6 — Google Drive distribution

Use the separate distribution folder:
`https://drive.google.com/drive/folders/<EXAMPLE_DISTRIBUTION_FOLDER_ID>`

1. Build a versioned package from a reviewed GitHub release.
2. Verify package SHA-256 before upload.
3. Upload package and checksum; confirm the cloud-side artifacts.
4. Update `latest.json` only after successful upload and verification.
5. Keep PC deployment manual: download, verify, inspect diff, preserve active config, then apply by operator approval.
6. Never let distribution failure trigger or bypass log deletion.

Exit criteria: release can be uploaded and retrieved without exposing credentials, and a failed upload leaves the previous release pointer unchanged.

### Phase 7 — Dry-run and controlled rollout

1. Install the same reviewed package manually on PC-A and PC-B, preserving their active configs.
2. Run sync dry-run on both PCs and inspect candidate periods, names, hashes, manifests, and proposed actions.
3. Run synthetic/isolated movement tests and verify cloud-side API behavior only under a separately approved limited environment plan.
4. Confirm each move's required records can be read and validated without treating report availability as deletion authority.
5. Run PC-A archive Dry Run; verify PC-B cannot archive and that B's missing period manifest alone does not block current eligible files.
6. Review initial catch-up scope, including existing Drive files from September 2026 and earlier BattleLog and 2025 and earlier ErrorReport.
7. Confirm source deletion is limited to the two routes/Q5/roles, unknown items retain sources, and Dry Run has no effects. Real-data deletion/deployment requires a separate concrete instruction; synthetic acceptance is not production permission.

Exit criteria: operator signs off on dry-run reports, recovery tests, and archive safety gates.

### Phase 8 — Scheduled operation

After controlled rollout:
- Configure PC-A and PC-B scheduled sync runs.
- Configure PC-A scheduled archive runs only.
- Use the same code path as manual execution.
- Prevent overlapping runs with a lock/lease and stale-lock recovery policy.
- Log each run and surface failures; do not silently treat errors as skips.
- Review retention and failures periodically.
- Keep a documented manual run path for recovery and troubleshooting.

Exit criteria: repeated scheduled runs complete safely, retries recover prior failures, and failures remain visible.

## 6. Required deliverables

- Updated `README.md`, `docs/release/distribution-design.md`, and this workflow.
- `Common/LogFunctions.ps1`.
- `scripts/SyncLogs.ps1` and `scripts/ArchiveLogs.ps1`.
- PC-specific manual entry points and safe example configs.
- Manifest schema and sample non-operational fixtures.
- Automated tests for all safety gates and failure cases.
- Release-package CI updates.
- Google Drive API authentication and cloud verification documentation.
- PC installation, manual operation, scheduling, recovery, and rollback instructions.

## 7. Non-negotiable safety gates

- Fail closed on uncertain cloud status, missing or invalid manifests, checksum mismatch, ambiguous source attribution, or incomplete archive verification.
- Never overwrite a different file to resolve a collision.
- Never delete source or Drive data merely because a local Drive sync folder lists a file.
- PC-B never archives or deletes cloud sources. Each PC deletes only its own verified eligible local sources; only PC-A deletes cloud sources after verified archive placement.
- Manual and scheduled execution share the same logic and safety checks.
- Initial catch-up is handled by normal manual execution over all eligible backlog periods.
- Require both destination-content equality and source unchanged since copying immediately before any move-source deletion. Preserve failed/unknown items; retain independent file completion. Detailed contracts and an implementation-resumption instruction are still required before coding; production operations require their own concrete instruction.
