# P0 Runtime Entrypoint and Deletion-Surface Audit

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

> 2026-10-27追記: 以下の監査結果は記載された当時の対象/基準の証拠として保持する。[現行要件台帳](../../requirements/requirements-traceability.md)はQ1〜Q10と平坦化を反映済みで、全面削除禁止・両PC期間待ち・自動suffixの旧基準を現在へ復活させない。新しい移動契約に対するsource→要件→実装→試験→証拠の再照合は未完で、本履歴だけでは受け入れを満たさない。

- Audit type: static tracked-file inspection
- Repository baseline: `main` at `7f293686a340d84a2c64023f3722805dda49bf3f` (PR #92 merge, 2026-10-20; static review refreshed after PRs #91–#92)
- Scope: tracked file inventory, operational entry-point presence, PowerShell launch references, and deletion-related commands in PowerShell scripts, schemas, config examples, tests, and CI workflows
- Limitation: this is not a runtime test, package-content test for a production release, or proof about untracked files on operator machines.

## 1. Entrypoint inventory

The current tracked tree contains no `.bat` or `.cmd` files and no operational `scripts/SyncLogs.ps1` or `scripts/ArchiveLogs.ps1` entry point. `scripts/README.md` describes future maintenance utilities only. The package builder now requires the official entry-point paths for a deployable role package (both `SyncLogs.ps1` and `ArchiveLogs.ps1` for PC-A; `SyncLogs.ps1` only for PC-B) and excludes the legacy `scripts/ArchiveAndUploadLogs.ps1` from deployable content. The legacy file is absent from the tracked tree; package tests use a fixture with that name to verify legacy-only packages are rejected.

CI workflows invoke PowerShell through the GitHub Actions PowerShell 7.6.7 executable. A static scan of tracked executable/config/schema/test/workflow files at this baseline found no `powershell.exe` references. This does not prove how a future Task Scheduler job or locally created batch file will launch the scripts.

## 2. Deletion-related command inspection

Tracked paths inspected for this refresh (PR #92 merge baseline):

- `Common/LogFunctions.ps1`
- `.github/scripts/Build-ReleasePackage.ps1`
- `tests/Test-LogFunctions.ps1`
- `tests/Test-ReleasePackage.ps1`
- `.github/workflows/validate.yml`
- `.github/workflows/package-validation.yml`
- `contracts/drive-request.schema.json`
- `contracts/drive-response.schema.json`
- `Config/PC-A.example.json`
- `Config/PC-B.example.json`

The file-level review also confirmed that the tracked tree contains no operational PowerShell entry points or Python Drive adapter. This is a bounded static review of the listed paths, not a repository-wide proof over future/untracked files.

Findings:

- `Common/LogFunctions.ps1` and `tests/Test-LogFunctions.ps1` contain no `Remove-Item` command and no Drive delete operation.
- `.github/scripts/Build-ReleasePackage.ps1` uses `Remove-Item` only for the prior generated ZIP at the configured output path and for its own temporary staging directory in `finally`. It does not target log-source roots or invoke a Drive deletion API.
- `tests/Test-ReleasePackage.ps1` uses `Remove-Item` to clean up test fixtures created under a unique temporary test directory, including an active-config fixture and the legacy runtime-script fixture.
- The request schema allows only `list_files`, `get_file_metadata`, `upload_file`, and `download_file`; delete operations are not in its enum. Schema tests explicitly reject `delete_file`, `delete`, and unknown operations.
- The tracked tree at the PR #92 baseline contains `tests/test_contract_schemas.py` but no Python Drive adapter implementation, so runtime behavior of any future adapter cannot yet be audited. PR #78 adds package-builder negative tests rejecting `allowDelete` in both example configs, plus PC-A/PC-B role-specific template checks; these validate templates during package building, not an active-config runtime loader or a complete source/config/package/runtime negative-capability proof. The tracked-tree inventory contains no `.bat`/`.cmd` launchers and no official `SyncLogs.ps1` or `ArchiveLogs.ps1` entry points.

## 3. P0 disposition

- Baseline refresh for this audit: PR #92 merge commit `7f293686a340d84a2c64023f3722805dda49bf3f`; source-clause baseline remains PR #25 merge `097e962a1636419ceb428182da2a6a91f6380273`. PRs #91–#92 changed documentation/traceability only; the bounded operational-source/config/schema/test paths below were rechecked.
- The tracked tree at PR #92 still contains no `.bat`/`.cmd`, official `scripts/SyncLogs.ps1` or `scripts/ArchiveLogs.ps1`, or Python Drive adapter.
- Static scan results: `Remove-Item` is used by the package builder to remove its generated ZIP and temporary staging directory, and by package tests to clean temporary fixtures. These are build/test cleanup paths; no operational source-log or Drive-log deletion implementation was found in the inspected tracked files.
- The request schema allows only `list_files`, `get_file_metadata`, `upload_file`, and `download_file`; schema tests reject delete operations. This is not proof about future runtime code.

| Gap | Static audit result | Status after this audit |
|---|---|---|
| P0-001 | Shared module guard exists, but formal runtime entry points do not exist, so the guard cannot yet be proven on all operational paths. | Open |
| P0-003 | No tracked `.bat`/`.cmd` launchers exist to validate; no tracked `powershell.exe` reference was found in the inspected executable/config files. | Open; re-audit when launchers are added |
| P0-006 / P0-009 | The package builder now requires the official role-specific entry-point paths (`SyncLogs.ps1`; PC-A also requires `ArchiveLogs.ps1`, PC-B excludes it), but the official runtime files are still absent from the tracked tree and the final role allowlists/deployment decisions remain open. | Open |
| P0-012 | No source-log deletion or Drive deletion path was found in the inspected tracked runtime-related source. Build/test cleanup commands are limited to generated output/staging/test fixtures. | Partial static evidence only; runtime/package acceptance remains open |

## 4. Required follow-up controls

1. Do not add a batch launcher until the final entry-point names, runtime guard, and command-line flags are agreed.
2. When launchers are added, add CI assertions that all `.bat`/`.cmd` files use `pwsh.exe -NoLogo -NoProfile -NonInteractive` and cannot continue after version-guard failure.
3. When the Python adapter is implemented, add an allowlist test for its operation names and a source scan/test proving that no Drive deletion API is called.
4. Keep package-builder cleanup separate from operational log lifecycle code. Add tests asserting that cleanup paths remain inside generated output/staging/test roots.
5. Re-run this audit against the exact source and package artifacts before any deployable release is approved.

## 5. Current evidence boundary (PR #92 baseline)

- `.github/scripts/Build-ReleasePackage.ps1` uses `Remove-Item` only to replace the generated ZIP at the configured package output path and to remove its own temporary staging directory in `finally`; these are package-generation outputs, not log-source or Drive objects.
- `tests/Test-ReleasePackage.ps1` removes only temporary test fixtures created by the test. This includes fixture copies and the active-config fixture; it is test cleanup, not runtime log cleanup.
- `contracts/drive-request.schema.json` exposes only `list_files`, `get_file_metadata`, `upload_file`, and `download_file`; `tests/test_contract_schemas.py` explicitly rejects `delete_file`, `delete`, and unknown operations. This limits the declared adapter contract, but cannot constrain an adapter that does not yet exist.
- The package builder rejects `allowDelete` in both example configuration templates and validates role semantics for the example configs. The PC-A example has `allowArchive: false`; the PC-B example omits `allowArchive`. PR #91's archive-gate crosswalk and PR #92's P0 traceability refresh document these same boundaries; they do not add runtime enforcement. These remain package-build checks on example files, not active configuration enforcement.
- PRs #91–#92 update the C-28 archive-gate evidence matrix, P0 gap register, source/test inventory, and traceability register; they do not add runtime code or expand the audited executable paths. This audit did not execute operational scripts or generated packages and did not inspect untracked files on operator machines. It therefore supports only a partial static disposition for P0-012.

## 6. Safety statement

This audit does not certify the system as deployable or operationally safe. It records only the static evidence available in the current tracked repository. No local source-log deletion or Google Drive deletion capability is added by this change.

## OSD-03 approved report-contract compatibility note (2026-10-21)

R1-B/R2-A/R3-B/R4-A/R5-A/R6-A/R7-A are approved. The report contains period summaries only and references the exact manifest and B2 evidence by canonical relative path, schema version, and SHA-256 of exact bytes. Report identity is (pc_id, log_type, run_id, report_schema_version), with no report_id field. Deterministic regeneration uses only immutable validated inputs; it must not re-enumerate mutable source directories. Period completion is complete/incomplete/indeterminate and remains report-only, not a manifest v1 enum. Local publication is authoritative; Drive replication is separate and must be content-verified before cross-PC use. These decisions do not alter manifest v1, B2 evidence structure, A2 inventory digest, or exhaustive count reconciliation. Executable schema, runtime implementation, and tests remain pending.

No runtime entrypoint was implemented or executed as part of this documentation decision. No deletion capability or production operation is authorized.


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

## Supplemental review — referenced-artifact validator (PR #155, 2026-10-22)

The new `Common/AggregationReferencedArtifacts.ps1` and `Common/validate_aggregation_artifacts.py` are validation-only helpers. They read the report and its referenced JSON artifacts, calculate SHA-256 over raw artifact bytes, apply strict JSON Schema contracts, and compare run identity. They contain no source/Drive deletion, upload, archive, or Drive API operation. The Python helper rejects absolute/traversal/backslash paths and symlink components under the explicitly supplied trusted root, suppresses exception text and artifact contents, and returns stable rejection codes. These checks are defense-in-depth, not a race-free guarantee against concurrent hostile filesystem mutation. The helper is not yet connected to official runtime entry points, and this supplemental review does not supersede a future full entry-point audit or production acceptance test.


## Supplemental review — A2/B2 integrity helper (PR #156, 2026-10-22)

`Common/RunInputEvidenceIntegrity.py` is a pure validation helper for already-constructed B2 evidence. It recomputes the versioned length-prefixed A2 inventory digest and the B2 canonical JSON digest, applies the strict evidence schema, checks embedded inventory/count invariants, rejects completed enumeration with enumeration errors, and enforces canonical ordering for inventory targets and validation errors. It performs no source enumeration, file writes, Drive calls, upload, archive, or deletion. Digest validation does not prove the evidence was honestly or completely generated; source traversal, frozen inventory-to-manifest reconciliation, immutable publication, runtime entry-point integration, lock/recovery, and live Drive verification remain separate requirements. Exact-head CI must pass before this slice is considered verified.


## Supplemental review — manifest/B2 inventory binding (PR #157, 2026-10-22)

The referenced-artifact verifier now calls the A2/B2 integrity validator and compares the embedded evidence inventory with the originating manifest's frozen `files` records using relative path, filename, size, and SHA-256. It also compares the report's inventory count/digest to the evidence. The tests use synthetic JSON and temporary directories. This rejects cross-artifact divergence but does not prove that either artifact was generated from a complete source traversal; official runtime entry-point integration, immutable publication, locking/recovery, and Drive revalidation remain unimplemented.


## Entry-point integration gate — PR #158 (2026-10-22)

The repository inventory confirms that official `scripts/SyncLogs.ps1` and `scripts/ArchiveLogs.ps1` are not yet present. Existing aggregation and evidence helpers validate supplied artifacts but do not enumerate sources, publish evidence, acquire locks, recover interrupted runs, revalidate live Drive content, or authorize archive/deletion. `docs/design/runtime-entrypoint-validation-gate.md` defines the required pre-side-effect validation sequence and synthetic acceptance conditions. This is a design gate only; it does not close the runtime safety audit. PR #157 is merged and exact-head CI passed; post-merge main CI must be confirmed independently.


## Supplemental review — source inventory builder (PR #159, 2026-10-22)

`Common/SourceInventoryEvidenceBuilder.py` is a read-only helper that enumerates a supplied source root, hashes eligible files, and constructs an in-memory B2 evidence object. It does not publish artifacts, mutate source files, call Drive, or perform archive/delete operations. Enumeration/read/hash uncertainty produces an incomplete enumeration state; the serializer validates evidence contracts and returns deterministic JSON bytes without filesystem writes. Synthetic tests are added to CI, but their exact-head result must be verified before merge. This helper is not connected to official runtime entry points and does not itself provide atomic publication, lock/recovery, or a race-free guarantee against concurrent source mutation. P0 remains open.


## Supplemental review — atomic artifact publication (PR #160, 2026-10-22)

The new helper publishes one byte sequence by creating a temporary file in the resolved destination parent, flushing and fsyncing the file, and using same-filesystem hard-link creation as an atomic no-overwrite publication primitive. Existing identical bytes are accepted as an idempotent retry; conflicting content or unsupported atomic-link behavior is rejected. The helper never replaces an existing artifact. Its limits are explicit: no lock ownership, multi-file commit protocol, stale recovery, guaranteed directory metadata durability, or protection from hostile concurrent parent-directory changes. Do not connect it to official runtime entry points until those remaining controls and their acceptance tests are complete.


## Supplemental review — lock ownership and crash-recovery gate (PR #161, 2026-10-22)

The new acceptance gate makes the approved OSD-02 safety constraints testable without claiming implementation. It explicitly prohibits stale-lock removal based only on age/PID, requires ownership-token matching before lock-record mutation, preserves crash-left `running` manifests, and blocks retry when Drive reconciliation is incomplete or ambiguous. The test matrix is synthetic and pending execution. No official entry-point integration, live Drive operation, archive, or deletion is authorized. P0 remains open.


## Supplemental review — isolated owned-run lock primitive (PR #162; pending CI, 2026-10-22)

`Common/OwnedRunLock.py` introduces an isolated Windows named-mutex adapter and an exclusive create-only lock record containing a per-acquisition token and minimal identity fields. It caps waiting at 60 seconds, rejects malformed/mismatched records, and cleans up only when the current token still matches. Abandoned mutexes deliberately fail closed without adopting or removing an existing record; recovery remains unimplemented. Synthetic tests are authored and wired to Validate but have not yet been CI-verified. No manifest/source mutation, Drive calls, archive, deletion, or official entry-point integration is included. P0 remains open.


## Supplemental review — crash-recovery decision gate (PR #163; pending CI, 2026-10-22)

The pure recovery decision helper fails closed for non-abandoned mutexes, invalid/mismatched lock records, unconfirmed owner termination, non-unique latest candidates, invalid/non-running/schema-invalid manifests, identity mismatch, incomplete/ambiguous Drive reconciliation, or unresolved uploads. An eligible result requires a new run and fresh inventory while preserving the prior manifest. The helper performs no recovery mutation, manifest write, source enumeration, Drive call, archive, deletion, or official entry-point integration. Synthetic tests are authored but pending CI; P0 remains open.


## Supplemental review — artifact-set recovery classifier (PR #164; pending CI, 2026-10-22)

The pure classifier treats a transaction as committed only when a schema-versioned marker with a valid transaction ID binds the exact expected SHA-256 map and every published artifact matches. Partial or marker-missing states are explicitly non-committed and require reconciliation; the classifier never authorizes overwriting or cleanup. Synthetic tests are authored but pending CI. This does not implement the multi-artifact protocol or perform file/Drive/archive/delete side effects. P0 remains open.


## Supplemental review — marker-last artifact-set publication (PR #165; pending CI, 2026-10-22)

The isolated helper composes per-file atomic no-overwrite publication and publishes a commit marker last. A crash may leave a published subset; the absence of a marker prevents that subset from being treated as committed. Existing conflicting bytes fail closed, and no rollback/deletion is performed. This does not provide a filesystem-wide transaction or prove durability across every filesystem. Synthetic filesystem tests are pending CI. No official entry-point or Drive/archive/delete integration is included.


## PR #166 note — isolated artifact-set directory verification (2026-10-22)

The new `Common/ArtifactSetDirectoryVerification.py` module performs read-only hashing and marker validation for one directory snapshot. It rejects duplicate marker JSON keys, unexpected entries, symlinks/non-regular files, invalid directories, and unreadable or malformed marker data. It neither modifies files nor invokes Drive. This does not change the audit finding that official `scripts/SyncLogs.ps1` and PC-A-only `scripts/ArchiveLogs.ps1` entry points are absent; no runtime deletion capability is added. Point-in-time verification is not a substitute for locking, revalidation at use, crash/concurrency acceptance, or end-to-end runtime evidence. P0 remains open.


## Cross-process publication test boundary (PR #167; 2026-10-22)

The new synthetic test races two spawned publishers against a temporary directory with conflicting content for one artifact. Its intended assertion is one valid committed winner and one conflict, with marker hashes matching the observed winner. It does not test official entry points, Google Drive/network storage, power-loss recovery, lock ownership integration, or any archive/delete path. P0 remains open.


## Target-filesystem acceptance boundary (2026-10-22)

PR #167 post-merge Validate (`39702034526`) and Package Validation (`39702034521`) succeeded on `f979a5200d48a7ccccfed6ad31de07529bd340df`. This is hosted Windows CI evidence for synthetic temporary-directory behavior only. `docs/validation/target-filesystem-acceptance.md` separates CI, disposable local-volume qualification on PC-A/PC-B, and synchronized/network target qualification. Tier B and Tier C are not run; Google Drive/network semantics, remote visibility, power-loss durability, and verification-to-use stability remain unverified. This does not alter the finding that official sync/archive entrypoints are absent and does not authorize production logs, Drive operations, archive, or deletion. P0 remains open.


## Owned publication/recovery integration evidence (2026-10-23)

`tests/test_owned_publication_integration.py` uses real Windows machine-wide
named mutexes and spawned processes in a fresh harness-owned temp root. It
verifies competing-publisher timeout without artifact changes, normal token
cleanup plus exact-byte retry, actual abandoned-mutex fail-closed behavior,
ownership-token mismatch preservation, and revalidation after an external writer
changes previously verified bytes. A parent handle keeps the mutex object alive
so the abandonment assertion does not accidentally test a newly created mutex.

A schema-valid synthetic crash-left running manifest and actual surviving lock
record are supplied to the pure recovery classifier. Missing termination proof,
ambiguous latest candidate, incomplete reconciliation, unresolved uploads and
record-identity mismatch all block. A positive result still requires fresh
inventory/new run identity and does not authorize stale-record deletion/adoption.
The tests preserve that manifest, lock record and published bytes; operational
recovery and lock-protected use of real source/Drive data remain unimplemented.
This is hosted/local synthetic evidence, not Tier B/C or complete runtime
integration. P0-010/P0-012 remain open.


## Windows junction rejection regression (2026-10-23)

The directory verifier now checks lstat-based symlink/reparse attributes on the
requested directory, every lexical ancestor, and each observed entry before
reading artifact bytes. This closes a reproduced Windows junction-root/ancestor
gap where is_symlink alone did not detect junctions. Reparse uncertainty fails
closed with sanitized reasons; no files are changed by verification.
Checks are point-in-time defense-in-depth, not race-free path containment.

The regression suite creates real junctions only inside fresh owned synthetic
roots, asserts that root/ancestor rejection occurs before artifact read, rejects
a junction under an expected artifact name, and injects a sanitized read failure
without modifying existing bytes. CI runs this Windows suite; local-volume
evidence now includes it. P0 and remaining Tier B/C gates stay open.
