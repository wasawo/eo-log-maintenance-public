# Implementation Workflow: ElectronicObserver Log Maintenance

- Status: Proposed implementation plan
- Repository: `wasawo/eo-log-maintenance-public`
- Canonical source: GitHub
- Runtime deployment: Manual download/review on each PC
- Last updated: 2026-10-18

## 1. Purpose

Implement safe synchronization, verification, retention, and archival for ElectronicObserver BattleLog and ErrorReport files on PC-A and PC-B. This workflow covers both the initial catch-up of existing Drive data and ongoing manual/scheduled operation. Initial inventory/restoration is a separate, non-operational workflow; it is not treated as a successful sync or archive eligibility proof.

## 2. Fixed requirements

### 2.1 Roles

- **PC-A**: Synchronizes its own logs; writes its manifest; archives eligible Drive logs to the PC-A archive destinations by copying, verifying, and recording results only. Initial implementation has no local-source deletion or Drive deletion capability.
- **PC-B**: Synchronizes its own logs and writes its manifest. It must never archive or delete source/Drive logs. Do not package or install an archive entry point for PC-B.
- **Google Drive for desktop shared log location**: Common destination for both PCs' logs and shared maintenance manifests.
- **GitHub**: Canonical source for scripts and documentation.
- **Google Drive distribution folder**: Approved release package destination, separate from the log collection folder. Distribution is one-way from GitHub to Drive. PC updates remain manual.

### 2.2 Paths

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
- Steady state: Drive retains the previous month of BattleLog and previous year of ErrorReport; PC-A archive retains older eligible periods.
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
- If a same-name destination file has the same SHA-256, treat it as a duplicate and avoid unnecessary re-copying.
- If same-name files have different contents, preserve both and add `_PCA` or `_PCB` immediately before the extension (for example, `20261001_log_PCA.txt`).
- If an existing unmarked file must be renamed, determine its source from a trusted manifest/record before assigning its source suffix. If its source cannot be established, do not guess, overwrite, or delete it; record a conflict requiring safe resolution.
- For inventory/reconciliation, a same-content comparison candidate requires matching name, size, and SHA-256 against a trusted comparison source, with exactly one candidate in a completely enumerated target Drive folder. A match is not proof of provenance and does not itself authorize restore, sync-success classification, or archive; see the approved OSD-01 decision in `docs/p0-open-specification-decisions.md`.
- If the suffixed target also exists with different content, never overwrite it; report an error and leave originals untouched.
- Verify copied files with SHA-256 and record source name, final name, source PC, size, checksum, period, and result in the manifest.

### 2.5 Deletion and cloud confirmation

- Initial implementation never deletes local source files. Keep each source file after sync and cloud verification.
- A file's presence in the Google Drive for desktop local folder alone is not proof of completed cloud upload.
- Preferred approach: Google Drive API query of the actual cloud file listing and metadata/checksum where available; compare the cloud file identity/name, size, and SHA-256 with the local source.
- If a cloud SHA-256 is unavailable, download the file through the Drive API and compute SHA-256 locally. Metadata-only name/size matching is insufficient. If API download/verification fails, identity is ambiguous, or size/hash mismatches, fail closed and retain the source; mark the period incomplete.
- Candidate enumeration must cover the intended target folder and complete all pagination successfully. API errors, incomplete pagination, insufficient access, or uncertain query scope must never be interpreted as confirmed zero/one candidates; hold and fail closed.
- The comparison source must be a confirmed, trusted PC-A backup/source record. If source integrity or provenance is unconfirmed, hold the item even if a content hash matches. Candidate identity and archive eligibility are separate gates.
- API authentication, scopes, and the ability to access the supplied My Drive folder must be configured and tested before production validation.
- PC-A archives only after both PC-A and PC-B manifests indicate successful synchronization and verification for the relevant periods.
- Initial implementation never deletes Drive files. Archive only after verifying the archive destination against Drive source with SHA-256 and confirming required manifests/checks.
- Local-source deletion and Drive deletion are excluded from the initial implementation: do not include deletion code, operations, or configuration settings. Any future deletion feature requires a separate design, review, tests, and explicit approval.

### 2.6 Invocation

- Manual and scheduled runs use the same processing code; no separate initial-migration code path.
- Manual sync and manual archive entry points are provided where allowed.
- Scheduled tasks call the same entry points or script functions with equivalent parameters.
- The run computes all eligible backlog periods automatically.
- PC-B has no archive entry point and no callable archive/delete capability.
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

The implementation phases below are a proposed delivery sequence, not evidence that implementation may proceed or that a phase has been accepted. Before declaring Phase 1 ready to exit or beginning operational rollout, the maintainer must review `docs/p0-gap-register.md`, `docs/p0-open-specification-decisions.md`, `docs/requirements-source-audit.md`, and `docs/p0-source-test-inventory.md` together.

P0 is **not accepted** while any P0 item is open, any required design decision is blocked/unapproved, or required runtime evidence is absent. The acceptance review must record each P0-001–P0-012 item as `complete`, `blocked` (with decision/prerequisite), or `incomplete` (with evidence gap); a documentation-only change cannot satisfy a runtime acceptance criterion. At minimum, the review must verify:

1. Source clauses are mapped to stable requirement IDs, implementation targets, executable tests, and exact CI/runtime evidence; unmapped or partial clauses have an explicit disposition (P0-010).
2. PowerShell 7.6.7 is enforced on every official entry point before file processing; official entry points and launch methods are identified (P0-001–003).
3. PowerShell/Python contract decisions are approved and contract/schema/semantic tests cover the agreed behavior (P0-005).
4. Release-package readiness and PC-specific allowlists match the approved official entry points; the legacy prototype alone cannot make a package deployable (P0-006, P0-009).
5. Existing helper/schema/package tests are not counted as end-to-end runtime evidence. Sync, cloud verification, manifest, archive, IPC, recovery, and Dry Run claims require executable tests at the relevant boundary (P0-004, P0-007–008).
6. P0 acceptance criteria are consistent across this workflow, `README.md`, the decision register, and the P0 gap register (P0-011).
7. Local source deletion and Drive deletion remain absent from initial implementation code, configuration, entry points, and deployable packages; evidence limits are explicitly stated until runtime exists (P0-012).
8. All unresolved OSD items remain explicit blockers for the phase/function they govern. A proposal or static audit does not constitute operator approval.

**Gate result for the current repository:** not accepted. Official sync/archive entry points and runtime orchestration are absent; OSD-02/03 and other decisions remain unresolved; therefore the checklist above is a future acceptance gate, not a claim that P0 has passed. Do not use real credentials, real logs, production paths, or real Google Drive operations to fill evidence gaps without a separately approved test plan.

## 5. Implementation phases

### Phase 0 — Baseline and decisions

1. Keep this plan and the README aligned with the fixed requirements.
2. Inspect the existing prototype only as a behavior reference; do not transplant it as a finished design.
3. Confirm actual filename patterns for BattleLog and ErrorReport, including date parsing, extensions, and any filename exceptions.
4. Defer the exact OAuth scope until Python adapter implementation; then validate the minimum scope against the actual My Drive folders and required operations. Do not widen scope without documenting and reviewing the need.
5. Define manifest schema/version and rules for proving the origin of a pre-existing unmarked file.
6. Confirm whether the Drive API returns SHA-256 checksums for the relevant file types; define a fail-closed fallback when not available.

Exit criteria: filename patterns, manifest schema, and pre-existing-file origin rules are specified before their respective implementation begins. OAuth scope and scheduler times remain gated until their stated implementation steps.

### Phase 1 — Common functions and configuration

Implement `Common/LogFunctions.ps1` and validate configuration:
- Load and validate the active PC configuration and role.
- Parse log dates/periods and select all eligible backlog files.
- Calculate SHA-256, compare files, and verify copied content.
- Create/read/version-check manifests and reject malformed or mismatched manifests.
- Produce structured logs and consistent exit codes.
- Provide safe path construction and prevent path traversal or accidental source/destination overlap.
- Add Dry Run that performs no upload, final download placement, archive placement, local-source deletion, or Drive deletion. The initial implementation contains no deletion operations or deletion settings.

Exit criteria: unit tests cover period boundaries, filename exceptions, configuration validation, manifest validation, hashing, and error handling.

### Phase 2 — Synchronization implementation

Implement `scripts/SyncLogs.ps1` and `Run_Log_Sync.bat`:
1. Identify the machine from validated configuration.
2. Enumerate all eligible BattleLog and ErrorReport files, including older backlog.
3. Determine destination names using SHA-256 duplicate/collision rules.
4. Copy to a temporary/staging destination where practical, verify the copied content, and then finalize without overwriting unrelated files.
5. Query Google Drive API to confirm the actual cloud-side file and its content metadata/checksum.
6. Retain local source files; initial implementation contains no source-deletion operation or setting.
7. Write a manifest with per-file status and period-level completion status.
8. Treat no eligible files as a successful skip; treat failed checks as errors and preserve source files.

PC-B build/runtime must not contain or expose archive/delete functionality.

Exit criteria: automated tests cover normal copy, already-present identical file, conflicting same-name file, suffix collision, partial copy, cloud API failure, checksum mismatch, retry after failure, and no eligible files.

### Phase 3 — Archive implementation (PC-A only)

Implement `scripts/ArchiveLogs.ps1` and `Run_Log_Archive.bat`:
1. Enumerate all eligible Drive backlog periods for archival.
2. Load and validate both PC-A and PC-B manifests for every relevant period.
3. Confirm that both PCs completed synchronization and verification and that cloud-side confirmation is current and applicable to the files being archived.
4. Copy eligible Drive files to the configured PC-A archive destination without overwriting different content.
5. Verify archive content with SHA-256 and ensure all files for the selected operation are accounted for.
6. Do not delete the Drive copy. Record archive verification and results only.
7. Record archive outcome and verification results in an archive status manifest.
8. If a manifest is absent/stale/invalid, source origin is ambiguous, the API is unavailable, or any hash/verification fails, preserve Drive and archive data and report the error.

Exit criteria: PC-A archive tests pass, and tests prove PC-B cannot execute the archive path.

### Phase 4 — Recovery and idempotency tests

Test the same scripts against a seeded test directory and mock Drive API responses:
- Initial catch-up of the currently uploaded historical logs.
- Multiple old periods left behind after earlier failures.
- Re-running after partial completion.
- Identical files and differing same-name files from both PCs.
- Existing unmarked Drive files with and without trustworthy source manifests.
- Missing/invalid manifests and stale API metadata.
- Process interruption between copy, verification, and manifest update; restart must recheck state without deleting source data.
- Drive API quota, network, permission, and transient failures.
- Boundary dates around month/year rollover and leap day where relevant.

Exit criteria: re-running is safe and does not duplicate, overwrite, or delete unverified data.

### Phase 5 — Packaging and repository CI

Update the release allowlist and tests:
- Include `SyncLogs.ps1`, `ArchiveLogs.ps1`, `Common/LogFunctions.ps1`, runtime BAT files, safe example configs, VERSION, README, and CHANGELOG.
- Do not package active PC-specific configurations, secrets, operational logs, runtime manifests, tests, or repository-only automation.
- Require PowerShell parsing/static analysis and behavioral tests in CI.
- Correct `docs/distribution-design.md`: the usable entry point is `SyncLogs.ps1` plus PC-A-only `ArchiveLogs.ps1`, not the old `ArchiveAndUploadLogs.ps1` prototype.
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
3. Run non-destructive sync tests and verify cloud-side API behavior.
4. Confirm both manifests can be read and validated from the shared maintenance location.
5. Run PC-A archive Dry Run; verify that PC-B cannot archive and missing PC-B manifests block archival.
6. Review initial catch-up scope, including existing Drive files from September 2026 and earlier BattleLog and 2025 and earlier ErrorReport.
7. Confirm the initial runtime has no local-source or Drive deletion code, operations, or settings. Test acceptance does not authorize deletion capability.

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

- Updated `README.md`, `docs/distribution-design.md`, and this workflow.
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
- PC-B never archives. Initial implementation on either PC has no local-source or Drive deletion capability.
- Manual and scheduled execution share the same logic and safety checks.
- Initial catch-up is handled by normal manual execution over all eligible backlog periods.
- Do not implement local-source deletion or Drive deletion in the initial version. Future deletion requires a separate design, review, tests, and explicit approval.
