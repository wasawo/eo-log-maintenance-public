# SEL-RT Fixture Traceability Audit

- Status: static design-to-requirement audit; runtime tests are not executed.
- Baseline: `564f01ffec7157c67dc9ed3e61cbbd0a7a0dd7ed` (PR #86 merge; current review baseline).
- Related design: `docs/filename-period-test-plan.md`, section “Runtime target-selection fixture matrix”.
- Purpose: map each SEL-RT fixture to requirement IDs, actual implementation, executable test evidence, and unresolved decisions without treating a design row as a passed test.

## Audit rules

1. A fixture description is a planned test, not executable coverage.
2. Helper-level date parsing/cutoff tests do not establish directory enumeration, filesystem timestamp non-fallback, mixed-file error handling, manifest status, or source immutability during orchestration.
3. The repository at PR #86 baseline still has no official `scripts/SyncLogs.ps1` or `scripts/ArchiveLogs.ps1` runtime entry point. Therefore SEL-RT-01–10 are not executable against the intended runtime and must remain **not implemented / not run**.
4. No run/period status names or transitions are inferred while OSD-03 is blocked. OSD-02 manifest schema/state-transition approval and EOLM-MAN-011 freshness policy remain separate blockers.
5. No real logs, production paths, Google Drive data, or deletion operations are used or introduced.

## Fixture-by-fixture crosswalk

| Fixture | Intended assertion | Requirement mapping | Existing implementation / executable evidence | Disposition |
|---|---|---|---|---|
| SEL-RT-01 | Select all eligible BattleLog backlog dates through previous month-end; exclude current-month dates; do not truncate to latest period | EOLM-FIL-006–009; EOLM-SYN-002; EOLM-TST-003 | Date/cutoff helpers exist; no runtime directory enumerator or backlog-selection test | Not implemented; runtime test not run |
| SEL-RT-02 | Select all eligible ErrorReport backlog dates through previous year-end; exclude current-year dates | EOLM-FIL-006–009; EOLM-SYN-002; EOLM-TST-003 | Date/cutoff helpers exist; no runtime directory enumerator or all-years backlog test | Not implemented; runtime test not run |
| SEL-RT-03 | Eligible filename date remains eligible despite recent LastWriteTime | EOLM-FIL-003; EOLM-FIL-004; EOLM-FIL-009 | Helper parses filename date; no orchestration test injects/conflicts with filesystem timestamps | Not implemented; timestamp non-fallback unproven |
| SEL-RT-04 | Ineligible filename date remains ineligible despite old LastWriteTime | EOLM-FIL-003; EOLM-FIL-004; EOLM-FIL-009 | Same helper-only boundary; no runtime timestamp-conflict test | Not implemented; timestamp non-fallback unproven |
| SEL-RT-05 | Unclassifiable filename is not eligible via timestamp fallback; affected scope cannot be declared fully successful | EOLM-FIL-004–005; EOLM-FIL-009; EOLM-TST-003 | Invalid-name helper assertions exist; no runtime error aggregation or run-status path | Partial helper evidence only; runtime test not run; OSD-03 blocks exact status policy |
| SEL-RT-06 | Impossible calendar date is rejected even if LastWriteTime looks eligible | EOLM-FIL-003–004; EOLM-FIL-009; EOLM-TST-003 | Invalid date helper assertions exist; no runtime timestamp-conflict test | Partial helper evidence only; runtime test not run |
| SEL-RT-07 | Correct patterns/cutoffs are applied independently to BattleLog and ErrorReport; all eligible backlog periods considered | EOLM-FIL-001–008; EOLM-TST-003 | Filename helper tests cover parsing and cutoff boundaries; no mixed-directory enumeration test | Partial helper evidence only; runtime test not run |
| SEL-RT-08 | Valid files do not hide a relevant invalid file; affected scope is not fully successful | EOLM-FIL-005; EOLM-FIL-010; EOLM-TST-003 | No runtime orchestrator, per-file result aggregation, or manifest status implementation | Not implemented; OSD-03 blocks exact status mapping |
| SEL-RT-09 | Verified no-work is distinguished from enumeration/access failure | EOLM-FIL-006; EOLM-TST-003 | No runtime enumerator or access-failure injection test | Not implemented; status behavior blocked by OSD-03 |
| SEL-RT-10 | Selection-only execution does not mutate/move/delete source files; pre/post existence and hashes match | EOLM-SYN-001; EOLM-SAF-005; EOLM-TST-003 | No runtime selection entry point or isolation guard proving production paths cannot be touched | Not implemented; no no-mutation runtime evidence |

## Evidence boundary

- Existing helper tests can support only the specific filename parsing and cutoff assertions they actually execute.
- Validate / Package Validation success is evidence for the checks in those workflows, not for any unimplemented SEL-RT runtime scenario.
- The test plan calls for temporary directories, synthetic files, fixed reference dates/timestamps, and mocked APIs. An automated guard that rejects configured production paths is not yet evidenced by the inventory.
- Do not update a requirement to `verified` based solely on this crosswalk.

## Next actions

1. Link this crosswalk from `docs/requirements-source-audit.md` and `docs/p0-source-test-inventory.md`.
2. When an official runtime selection entry point is introduced, implement SEL-RT tests using temporary synthetic fixtures and explicit production-path rejection.
3. Keep P0-010 open until every normative clause and artifact has a verified ID mapping and objective implementation/test/CI disposition. PR #86's staging-state audit further records EOLM-REQ-001 and EOLM-STG-001–012 as not implemented/not run or blocked; it does not change SEL-RT-01–10 status.
4. Keep OSD-02, OSD-03, and EOLM-MAN-011 blocked pending explicit decisions; do not implement deletion or real Drive operations.
