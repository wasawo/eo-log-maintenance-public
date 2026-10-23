# P0 Source / Specification / Test Inventory

- Status: Partial static inventory reconciliation in progress. Latest merged tracked-tree baseline: PR #123 merge `6b543930f9a9805f50693bd6333a8278c416fe05` (2026-10-21). PR #117–#123 are documentation-only changes and add no runtime implementation or runtime acceptance evidence. Clause-by-clause source/requirement/test disposition remains open. Operational manifest schema/reader/writer, staging, enumeration, archive gate, retry orchestration, IPC, security logging, and status evidence remain absent; package-builder, Drive adapter-schema, helper, and documentation CI do not establish runtime acceptance.
- Repository: wasawo/eo-log-maintenance-public
- Specification/source-clause baseline commit: `097e962a1636419ceb428182da2a6a91f6380273` (PR #25 merge; preserved for source-clause traceability).
- Latest merged tracked-tree baseline: PR #123 merge `6b543930f9a9805f50693bd6333a8278c416fe05`. PR #123 is documentation-only and adds no runtime implementation or runtime acceptance evidence. PR #122 is documentation-only and adds no runtime implementation or runtime acceptance evidence. PR #117–#123 are documentation-only and do not alter runtime implementation/test coverage. The Drive response schema is not a maintenance manifest schema; no operational manifest schema/reader/writer exists. C-29 retry/unknown-upload evidence, C-25 test-plan status, and C-26 manifest crosswalk remain documentation/traceability only; RETRY-01–06 and SEL-RT-01–10 remain not implemented/not run.
- Related records: docs/requirements/p0-gap-register.md; docs/requirements/requirements-traceability.md; docs/validation/requirements-source-audit.md; docs/validation/p0-runtime-entrypoint-safety-audit.md; docs/validation/p0-contract-review-findings.md; docs/validation/sel-rt-fixture-traceability.md
- Scope: repository file inventory and current specification-to-implementation-to-test relationships.
- Limitation: static repository review only. It does not prove runtime behavior or imply incomplete runtime scripts are implemented.

## 1. Current source artifact inventory

| Area | Current artifacts | Role / evidence available | Coverage state |
|---|---|---|---|
| Shared PowerShell functions | Common/LogFunctions.ps1, Common/README.md | Filename/date parsing and period-selection helpers; exact PowerShell 7.6.7 guard; README also describes functions not yet implemented | Partial implementation; map each function to requirement and test |
| Operational PowerShell entry points | `scripts/SyncLogs.ps1` exists as a sentinel only; `scripts/ArchiveLogs.ps1` and operational batch entry points are absent | No operational sync/archive execution path is available to verify; SyncLogs contains no sync implementation | Unimplemented; not runtime-safe or deployable |
| Package builder | .github/scripts/Build-ReleasePackage.ps1 | Builds review artifacts under an allowlist; sources shared functions and enforces version guard | Packaging utility exists; PC-A/PC-B release acceptance incomplete |
| PowerShell tests | tests/Test-LogFunctions.ps1, tests/Test-ReleasePackage.ps1 | Helper functions, version-guard decisions, package-builder behavior | CI executes these tests; cannot prove absent operational entry-point safety |
| Python/schema tests | tests/test_contract_schemas.py, requirements-test.txt | Validates request/response JSON Schema and contract examples, including unknown-operation rejection | Schema tests run in Validate; PR #49's IPC audit confirms they do not cover raw stdout/stderr, process exit codes, request correlation, timeout, secret redaction, or live Drive adapter behavior |
| Request/response schemas | contracts/drive-request.schema.json, contracts/drive-response.schema.json | Machine-readable PowerShell/Python boundary contract | Artifacts exist; contract approval and runtime integration open |
| Example configuration | Config/PC-A.example.json, Config/PC-B.example.json | Example per-PC paths and role settings | Package-builder tests validate template semantics and reject known unsafe variants; active-config runtime loader, approved-root containment, role-bound authorization, and PC-A positive archive authorization remain unimplemented |
| CI validation | .github/workflows/validate.yml, .github/workflows/package-validation.yml | Installs PowerShell 7.6.7, verifies archive hash and runtime version, runs available tests and static analysis | Evidence covers current helper/package tests only |
| Distribution documentation | docs/release/distribution-design.md, README.md, VERSION, CHANGELOG.md | Distribution constraints, project status, release metadata | Must be reconciled with future official entry points and per-PC allowlists |
| Runtime design and safety | docs/development/implementation-workflow.md, docs/design/powershell-python-contract.md, docs/design/staging-file-lifecycle.md, docs/validation/runtime-safety-test-scenarios.md | Proposed behavior for sync, cloud verification, manifests, archive eligibility, retries, and safety | Design exists; some requirements remain proposed or unapproved |
| Filename/period rules | `docs/design/filename-and-period-selection.md`, `docs/validation/filename-period-test-plan.md`, `Common/LogFunctions.ps1`, `tests/Test-LogFunctions.ps1` | §2 filename patterns/date parsing, §§3–4 sync/archive cutoff rules, §§6–7 invalid-name/run-status rules | FIL-001–004 and FIL-007–009 helper-level assertions are clause-mapped to `Test-LogFunctions.ps1` and Validate #44; FIL-005/006/010 remain runtime-unimplemented (mixed-error aggregation, full backlog enumeration, zero-target manifest/run status). Timestamp disagreement and enumeration are not covered by helper CI. |
| Requirement records | docs/requirements/requirements-traceability.md, docs/validation/requirements-source-audit.md, docs/decisions/decision-register-c18-c32.md, docs/requirements/p0-gap-register.md | Requirement IDs, source coverage, decisions, prioritized gaps | Baseline and disposition of partial/unmapped sections need reconciliation |
| Future maintenance utilities | scripts/README.md | Describes planned documentation/update helpers | Utilities are not implemented and do not count as source/test coverage |

## 2. Traceability rules

For every normative requirement, the traceability register should identify:
1. Stable requirement ID and exact source path/section.
2. Implementation artifact, or explicit Not implemented state.
3. Verification artifact and CI/local command, or explicit No executable test yet state.
4. Evidence (successful CI run, test output, or review decision), separate from planned verification.
5. Dependencies on unresolved decisions or contract review.

A document link, schema file, or test plan is not runtime evidence. Schema/helper tests do not establish that a future operational entry point is safe.

## 3. Current CI evidence

| Evidence | Conclusion | Does not establish |
|---|---|---|
| Validate run 39372725014: https://github.com/wasawo/eo-log-maintenance/actions/runs/39372725014 | Successful on PR #25 head; installs/verifies PowerShell 7.6.7, validates JSON schemas/configs, runs `tests/Test-LogFunctions.ps1`, and runs PSScriptAnalyzer. | End-to-end sync, Drive verification, manifest lifecycle, archive eligibility, all-entrypoint startup guard, or runtime no-delete proof. |
| Package Validation run 39372724979: https://github.com/wasawo/eo-log-maintenance/actions/runs/39372724979 | Successful on PR #25 head; installs/verifies PowerShell 7.6.7 and runs package-builder tests. | Deployable PC-A/PC-B package with final official runtime entry points. |
| Validate run 39372313204: https://github.com/wasawo/eo-log-maintenance/actions/runs/39372313204 | Successful on PR #24 head; retained as historical evidence. | Runtime integration and cloud behavior. |
| Package Validation run 39372313187: https://github.com/wasawo/eo-log-maintenance/actions/runs/39372313187 | Successful on PR #24 head; retained as historical evidence. | Production release packaging or deployment. |
| Validate run 39373621988: https://github.com/wasawo/eo-log-maintenance/actions/runs/39373621988 | Successful on PR #26 head; refreshes artifact inventory and static safety audit. | Runtime integration or operational deletion safety. |
| Package Validation run 39373622016: https://github.com/wasawo/eo-log-maintenance/actions/runs/39373622016 | Successful on PR #26 head; package-builder tests passed. | Deployable production package or cloud release workflow. |
| Validate run 39373986586: https://github.com/wasawo/eo-log-maintenance/actions/runs/39373986586 | Successful on PR #27 head; source matrix/crosswalk documentation validated. | Runtime integration or operational release readiness. |
| Package Validation run 39373986582: https://github.com/wasawo/eo-log-maintenance/actions/runs/39373986582 | Successful on PR #27 head; package-builder tests passed. | Deployable production package or cloud release workflow. |
| Validate run 39374352642: https://github.com/wasawo/eo-log-maintenance/actions/runs/39374352642 | Successful on PR #28 head; phase crosswalk documentation validated. | Runtime phase acceptance or operational readiness. |
| Package Validation run 39374352675: https://github.com/wasawo/eo-log-maintenance/actions/runs/39374352675 | Successful on PR #28 head; package-builder tests passed. | Deployable production package or cloud release workflow. |
| Validate run 39374829187: https://github.com/wasawo/eo-log-maintenance/actions/runs/39374829187 | Successful on PR #29 head; decision backlog and crosswalk links validated. | Resolution of any deferred policy or runtime acceptance. |
| Package Validation run 39374829183: https://github.com/wasawo/eo-log-maintenance/actions/runs/39374829183 | Successful on PR #29 head; package-builder tests passed. | Deployable production package or cloud release workflow. |
| Validate run 39379247675: https://github.com/wasawo/eo-log-maintenance/actions/runs/39379247675 | Successful on PR #38 head; validates documentation/schema/code checks with SEL-RT-01–10 explicitly labelled design-only. | Executed runtime enumeration, timestamp non-fallback, mixed-input aggregation, or no-mutation proof. |
| Package Validation run 39379247689: https://github.com/wasawo/eo-log-maintenance/actions/runs/39379247689 | Successful on PR #38 head; package-builder tests passed. | Deployable production package or cloud release workflow. |
| Validate run 39379961951: https://github.com/wasawo/eo-log-maintenance/actions/runs/39379961951 | Successful on PR #40 head; validates the non-normative OSD-03 options proposal and linked decision records. | Approval/resolution of OSD-03 or OSD-02, or runtime status aggregation. |
| Package Validation run 39379961909: https://github.com/wasawo/eo-log-maintenance/actions/runs/39379961909 | Successful on PR #40 head; package-builder tests passed. | Deployable production package or cloud release workflow. |
| Validate run 39384288557: https://github.com/wasawo/eo-log-maintenance/actions/runs/39384288557 | Successful on PR #42 head; validates handoff recording PR #41 and preserves approval gates. | Runtime integration or policy approval. |
| Package Validation run 39384288385: https://github.com/wasawo/eo-log-maintenance/actions/runs/39384288385 | Successful on PR #42 head; package-builder tests passed. | Deployable production package or cloud release workflow. |
| Validate run 39395439176: https://github.com/wasawo/eo-log-maintenance/actions/runs/39395439176 | Successful on PR #50 head `dda840b8f3d943cc6e6ae299460ccf50ada092ca`; validates the current documentation/schema/helper/static-analysis checks. | Runtime enumeration, process-boundary IPC, sync/archive orchestration, real Drive behavior, or destructive-operation safety. |
| Package Validation run 39395439152: https://github.com/wasawo/eo-log-maintenance/actions/runs/39395439152 | Successful on PR #50 head `dda840b8f3d943cc6e6ae299460ccf50ada092ca`; package-builder validation passed. | Deployable operational package or runtime sync/archive acceptance. |

## 4. Remaining P0-010 work

- Continue clause-by-clause reconciliation between `docs/validation/requirements-source-audit.md`, `docs/requirements/requirements-traceability.md`, current tracked artifacts, named executable tests, and objective CI evidence. The baseline and latest PR #50 CI evidence are now refreshed, but this does not mean every row is reconciled.
- Keep IPC-01–06 marked not implemented/not run until a process-boundary harness exists; schema validation and successful documentation CI are not runtime proof.

- Reconcile every source-section row in docs/validation/requirements-source-audit.md with stable IDs in docs/requirements/requirements-traceability.md; disposition each Partial and Unmapped row.
- Exact assertion-to-requirement mappings for the existing PowerShell filename/date/cutoff helper tests are recorded in `docs/validation/requirements-source-audit.md` §3.11. PR #20 reconciled scenario IDs between §3.1 and §3.10. README and C-18–C-32 rows are now being dispositioned against existing IDs; runtime test gaps remain. PR #38 adds design-only SEL-RT-01–10 runtime fixture matrix; no runtime enumeration entrypoint exists, so these are not passed evidence. Filename-date vs LastWriteTime disagreement, mixed-directory enumeration and run-status remain runtime gaps. The test plan requires synthetic fixtures and isolated temporary paths; no automated guard currently proves that the suite cannot access real logs/production paths. Planned runtime scenarios must remain labelled not implemented, not passed.
- Keep source audit rows linked to the OSD IDs and ensure every deferred decision remains blocked until explicitly approved. Do not infer trusted-manifest, mixed run-status, MAN-011 freshness, Dry Run side-effect, Drive auth, release retention or scheduler policy.
- Resolve duplicate or conflicting normative statements in README, implementation workflow, contract, distribution design, and decision register.
- Record the final inventory and audit result in the gap register only after all rows are reconciled.

## 5. Safety constraints

- No local source-log deletion or Google Drive deletion in P0-P2.
- PC-B must not receive an archive entry point.
- A successful package-builder test is not proof that a production package is deployable.
- Do not close P0-010 until partial/unmapped source sections are dispositioned and requirement-to-test links are reviewed.

## SEL-RT fixture traceability cross-reference

- Detailed fixture-to-requirement/evidence disposition: [`docs/validation/sel-rt-fixture-traceability.md`](sel-rt-fixture-traceability.md).
- SEL-RT-01–10 remain design-only and not executed. Helper-level tests do not prove runtime enumeration, timestamp non-fallback, mixed-input status aggregation, empty-vs-failed enumeration, or source no-mutation.
- Operational runtime behavior and runtime acceptance tests remain absent; `scripts/SyncLogs.ps1` is only a sentinel, while `scripts/ArchiveLogs.ps1` and operational launchers are absent. P0-010 remains open. OSD-02/03 and EOLM-MAN-011 numeric freshness/future-time tolerances and applicability remain unresolved.


## 6. Latest review baseline update (PR #53)

- Tracked-tree baseline: `1a54cafb2e444cc4d778a64dca0bd1439dfeff6d` (PR #53 merge).
- PR #51 inventory/evidence refresh: Validate https://github.com/wasawo/eo-log-maintenance/actions/runs/39395744201; Package Validation https://github.com/wasawo/eo-log-maintenance/actions/runs/39395744306.
- PR #52 source-audit/test-plan crosswalk: Validate https://github.com/wasawo/eo-log-maintenance/actions/runs/39396308946; Package Validation https://github.com/wasawo/eo-log-maintenance/actions/runs/39396308916.
- PR #53 config-example audit correction: Validate https://github.com/wasawo/eo-log-maintenance/actions/runs/39396579155; Package Validation https://github.com/wasawo/eo-log-maintenance/actions/runs/39396579172.
- These CI runs validated documentation, schema/helper tests, and package-builder checks at their respective PR heads. They do not constitute runtime acceptance evidence and are not interchangeable across HEAD SHAs.
- Current config finding: `Config/PC-A.example.json` intentionally has `allowArchive: false`; `Config/PC-B.example.json` omits `allowArchive`. Validate parses example JSON but does not enforce semantic PC-role/capability constraints. No runtime config loader or operational entry-point implementation is present in the tracked tree; `scripts/SyncLogs.ps1` is a sentinel only, and `scripts/ArchiveLogs.ps1` is absent.
- P0-010 remains open. Clause-level source-to-requirement-to-implementation-to-executable-test-to-objective-evidence reconciliation is incomplete; SEL-RT-01–10 and IPC-01–06 remain not implemented/not run. Schema tests validate contract shape/examples only and are not process-boundary evidence. OSD-02, OSD-03, and EOLM-MAN-011 remain blocked.


## Latest tracked-tree disposition update (PR #69 merge baseline)

- Review baseline: `13df2952fe8e13ca114ddcf21532d840dfa8264e`.
- The source audit currently has no source-section row in §2.1 marked Unmapped; the remaining work is not a wholesale missing-ID problem. Partial rows primarily represent (a) helper-only tests without runtime enumeration/orchestration, (b) schema-only IPC evidence, (c) package-builder/static checks without operational entry-point logic or active-config runtime semantic PC-role enforcement, and (d) mapped requirements blocked by unresolved OSD decisions.
- Existing CI remains evidence only for the exact tests it executes. PR #69's CI validated the documentation change at its PR head; it did not execute sync/archive/runtime scenarios.
- P0-010 remains open until each applicable clause is linked to its requirement ID, implementation or explicit not-implemented state, executable test or explicit not-run/blocked state, and objective evidence. P0-012 remains open until deletion-capability absence is demonstrated across source/config/contracts/packages and runtime mutation boundaries.
- Safety boundary unchanged: no real credentials, Google Drive operations, real logs, production paths, or deletion behavior. SEL-RT-01–10 and IPC-01–06 remain not implemented/not run.


## 7. Latest review baseline update (PR #80)

- Tracked-tree baseline: `4c9f16caf2c464bcc5720b98acb6656d5d95060a` (PR #80 merge, 2026-10-20).
- PR #78 verifies example-config semantics during package building; PR #80 corrects traceability for the PC-A archive-entry requirement and PC-B package archive exclusion. Neither proves runtime role enforcement or runtime capability absence.
- Official runtime entry points, manifest schema, orchestration, and process-boundary IPC harness remain absent. SEL-RT-01–10 and IPC-01–06 remain design/mapping evidence only, not implemented runtime tests.
- P0-010 remains open for clause-level source-to-requirement-to-implementation-to-executable-test-to-objective-evidence reconciliation. P0-012 remains open for complete deletion-capability absence proof across source, config, contracts, package, and runtime boundaries.
- OSD-02/03 and EOLM-MAN-011 remain blocked; other distribution/Dry Run decisions remain blocked as recorded in the open-decision register. Do not infer policy values or authorize release/runtime execution from passing documentation/package CI.


## 7. Latest review baseline update (PR #84)

- Tracked-tree baseline: `176fe194c1511204e409a8217920372a0022e31e` (PR #84 merge, 2026-10-20).
- IPC-01–06 are mapped in `docs/validation/requirements-source-audit.md`; schema-shape evidence is distinguished from child-process exit/output/timeout/redaction tests, which remain not implemented/not run.
- MAN-01–10 and EOLM-MAN-011/012 are mapped in `docs/validation/requirements-source-audit.md`; no maintenance manifest schema, reader/writer, orchestration, or runtime archive gate exists. OSD-02/03 and EOLM-MAN-011 remain blocking.
- `docs/validation/p0-runtime-entrypoint-safety-audit.md` records a bounded static review of named tracked paths. Build/test cleanup and the four-operation adapter schema provide only partial evidence; they do not prove absence of deletion capability in future runtime code or generated deployable packages.
- P0-010 and P0-012 remain open. Passing Validate / Package Validation means only that current checks succeeded; neither is runtime acceptance evidence.


## 8. Latest review baseline update (PR #91)

- Tracked-tree baseline: `0fe7ac0428e4596afc77464f8caa4461dd19c5b5` (PR #91 merge, 2026-10-20).
- The C-28 audit now distinguishes PR #78's example-config/package-builder semantic checks from active-config runtime authorization. Runtime archive gate, two-PC manifest/freshness checks, cloud-content verification, copy/verify/record ordering, and interruption recovery remain not implemented/not run or blocked.
- PR #84 remains bounded static deletion-surface evidence only. PR #91 does not add deletion guards or prove full source/config/contract/package/runtime negative capability.
- P0-010 and P0-012 remain open. Passing documentation/package CI is not runtime acceptance evidence.


## C-29 retry and unknown-upload evidence slice (PR #95)

- Source: docs/decisions/decision-register-c18-c32.md C-18/C-29 and docs/design/powershell-python-contract.md §§6–8.
- Requirement IDs: EOLM-DRV-001/002/003/006/008/009/010; related evidence requirements EOLM-TST-004/005.
- Scenario IDs: RETRY-01–06 in docs/validation/runtime-safety-test-scenarios.md.
- Current artifacts: decision/contract prose and JSON request/response schema tests only. There is no Python Drive adapter, retry orchestrator, Drive pagination/reconciliation implementation, or executable retry test.
- Important distinction: complete successful query proving no candidate is different from failed, partial, inaccessible, or ambiguous state. Only the former can satisfy the contract's confirmed-absence branch, subject to approved trust/identity rules. OSD-01 still blocks acceptance of pre-existing unmarked objects.
- Status: all RETRY scenarios not implemented/not run; P0-010 remains open. No credentials, real Drive data, production paths, real logs, or deletion behavior are in scope.


## C-26 manifest artifact inventory — PR #100

- Present: prose requirements in staging-file-lifecycle.md, C-26 decision record, OSD-02/OSD-03 backlog, and MAN-01–10 scenarios.
- Present but distinct: contracts/drive-response.schema.json validates the Python adapter response envelope only; it must not be counted as the operational run-manifest schema.
- Absent: maintenance manifest JSON Schema, manifest reader/writer, latest-run resolver, transition validator, atomic-write implementation, runtime archive gate, and executable manifest lifecycle tests.
- Blockers: OSD-02 (remaining transitions/crash/concurrency and runtime tests), OSD-03 (run/period aggregation), EOLM-MAN-011 (approved policy still lacks runtime enforcement and executable tests). Timestamp/freshness policy is recorded in the 2026-10-21 decision update.


## P0-011 acceptance-gate consistency — PR #101

- The authoritative P0 readiness/acceptance gate is present in docs/development/implementation-workflow.md §4 and linked from README.md.
- The gate explicitly rejects P0 acceptance while any P0 item is open, any required decision is blocked/unapproved, or runtime evidence is absent. Documentation-only changes cannot satisfy runtime criteria.
- The decision register records fixed/deferred decisions; it is not itself evidence of overall P0 acceptance. The gap register and traceability remain the per-item status records.
- This consistency correction does not close P0-011: the maintainer must still perform the final cross-document acceptance review and classify every P0-001–012 item as complete, blocked, or incomplete with evidence.

## Latest tracked-tree disposition update (PR #106)

- Baseline: `caf24456400c4b8d57a564c38903022f2e56688a` (PR #106 merge, 2026-10-20).
- PR #101 aligned the P0-011 status records with the authoritative gate in `docs/development/implementation-workflow.md` §4. PRs #102–#105 refreshed audit baselines and corrected filename-helper, historical inventory, and runtime-sentinel/package-builder evidence descriptions. These updates did not complete the final maintainer review or close P0-011.
- P0-010 remains open: the source audit, inventory, traceability, executable runtime tests, and objective runtime evidence still require clause-level reconciliation. P0-012 remains open for complete deletion-capability absence proof.
- The gate consistency update is documentation evidence only. `scripts/SyncLogs.ps1` remains a sentinel without operational sync logic; `scripts/ArchiveLogs.ps1`, operational manifest lifecycle, Python Drive adapter, retry orchestration, and runtime IPC harness remain absent.


## Diagnostic C-45–C-54 helper evidence — PRs #140/#141

- Added the non-normative clause-to-helper/test crosswalk in docs/validation/diagnostic-contract-test-evidence.md. It records the exact scope of Test-DiagnosticErrorId.ps1, Test-DiagnosticRecordFinalizer.ps1, Test-DiagnosticPathSanitization.ps1, and Test-C54PatternContract.ps1.
- C-45/C-46 have a tested per-run counter helper. PR #145 records approved C-45 Option A: a conflict in immutable/core attributes under the same `error_id` blocks evidence finalization/publication via a fixed, non-disclosing consistency failure. This does not establish runtime event creation, one-allocation-per-event, propagation/deduplication, conflict detection/enforcement, or concurrency safety.
- C-47–C-49 and C-52–C-54 have helper/schema synthetic coverage as detailed in the crosswalk. PR #144 adds the pure C-50 token-to-code helper; PR #146 adds the pure C-51 operation-to-phase resolver and synthetic tests. Producer-side precedence selection, semantic context selection, runtime integration, event propagation, and end-to-end evidence remain absent.
- PR #140 and #141 exact-head Validate/Package Validation passed. PR #144 exact-head Validate and Package Validation passed on 2599f7eff949faa1f0e341aecc53d9d1a980159a. PR #140 post-merge main CI passed. PR #141 post-merge main Validate run 39509903050 and Package Validation run 39509903012 both succeeded on merge SHA 58aeb10e3661b7cd893e1a6bfed0469e29e4089f.
- P0-008, P0-010, and P0-012 remain open. No real logs, credentials, production paths, Drive operations, archive enablement, deletion behavior, or runtime acceptance evidence were introduced.


## OSD-02 timestamp/freshness decision update — 2026-10-21

- **Approved policy specification:** UTC ISO 8601 timestamps with uppercase `Z`; reject malformed, timezone-less, offset-form, or unparseable values; reject finish time before start time.
- **Approved configurable defaults:** maximum future skew 5 minutes; freshness threshold 24 hours.
- **Scope:** freshness applies only to timestamps generated/updated during the current execution. Historical manifest age alone does not invalidate history.
- **Clock assumption:** OS time synchronization is configured; inability to obtain reliable current UTC fails closed for time-dependent operations. No external monitoring service is required.
- **Still absent:** executable fixed-clock boundary, format/order, invalid-config, clock-unavailable, and historical-age tests; runtime validator and operational evidence. Documentation approval must not be counted as implementation.


## OSD-03 approved report-contract compatibility note (2026-10-21)

R1-B/R2-A/R3-B/R4-A/R5-A/R6-A/R7-A are approved. The report contains period summaries only and references the exact manifest and B2 evidence by canonical relative path, schema version, and SHA-256 of exact bytes. Report identity is (pc_id, log_type, run_id, report_schema_version), with no report_id field. Deterministic regeneration uses only immutable validated inputs; it must not re-enumerate mutable source directories. Period completion is complete/incomplete/indeterminate and remains report-only, not a manifest v1 enum. Local publication is authoritative; Drive replication is separate and must be content-verified before cross-PC use. These decisions do not alter manifest v1, B2 evidence structure, A2 inventory digest, or exhaustive count reconciliation. Executable schema, runtime implementation, and tests remain pending.

Evidence status: the new contract test scenarios are planned only and have not been executed. Existing schema/docs CI must not be promoted to runtime evidence.


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