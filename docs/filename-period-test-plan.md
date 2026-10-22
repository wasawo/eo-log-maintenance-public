# Filename and Period Selection Test Plan

## Filename validation

| Case | Input | Expected result |
|---|---|---|
| Valid BattleLog | `20260930_12345678@sample.txt` | Accept; date 2026-09-30 |
| Valid ErrorReport | `20251231_12345678.txt` | Accept; date 2025-12-31 |
| Invalid calendar date | `20260230_12345678.txt` | Reject |
| Invalid month | `20261301_12345678.txt` | Reject |
| Missing underscore | `2026093012345678@sample.txt` | Reject |
| Wrong extension | `20260930_12345678@sample.log` | Reject |
| Empty BattleLog suffix | `20260930_12345678@.txt` | Reject |
| ErrorReport with suffix | `20251231_12345678@sample.txt` | Reject |
| Unexpected filename | `unknown.txt` | Reject; no LastWriteTime fallback |

## Synchronization boundaries

For an execution date of 2026-10-20:

- BattleLog 2026-09-30: eligible
- BattleLog 2026-10-01: not eligible
- ErrorReport 2025-12-31: eligible
- ErrorReport 2026-01-01: not eligible

## Archive boundaries

For an execution date of 2026-10-20:

- BattleLog 2025-12-31: eligible
- BattleLog 2026-01-01: not eligible
- ErrorReport 2024-12-31: eligible
- ErrorReport 2025-01-01: not eligible

## Calendar edge cases

The executable cases in `tests/Test-LogFunctions.ps1` include:

- Valid leap day `20240229`; invalid leap day `20250229`
- Invalid month `20261301`
- January 2026 sync/archive cutoffs crossing the year boundary
- Leap-year February 2024 cutoffs
- Historical BattleLog eligibility across multiple years
- Filename structure rejection for missing underscore, wrong extension, and empty BattleLog suffix

Remaining gaps are runtime-level, not helper cutoff coverage:

- Explicit mix of eligible, ineligible, and invalid files in a single runtime run
- Directory enumeration and filename-date versus `LastWriteTime` disagreement fixtures
- Run-level error aggregation and distinction between verified zero-work and enumeration failure

The helper suite already includes February 28/29, April 30, and June 30 cutoff assertions. Those helper checks do not prove runtime enumeration or run-status behavior.

## Safety and reporting

- Invalid filenames are reported as errors.
- A filename with no trustworthy date prevents the run from being reported as fully successful.
- Valid files can be processed individually if safe, but errors cannot be hidden.
- Selection must not modify, move, or delete files.
- Archive selection alone never authorizes archiving.

## Runtime target-selection fixture matrix (design only; not implemented)

The following cases translate the filename/period specification into isolated future runtime tests. They are test design, not evidence that enumeration or run-status handling exists. Use only temporary directories, synthetic files, injected reference dates, and fixed test timestamps. Do not access real ElectronicObserver logs, production paths, or Google Drive.

| Case ID | Requirement IDs | Synthetic fixture / setup | Required assertions |
|---|---|---|---|
| SEL-RT-01 | EOLM-FIL-006–009, EOLM-TST-003 | A temporary BattleLog source contains filename dates from 2024, 2025, September 2026, and October 2026; reference date 2026-10-20. | Select every eligible backlog file through 2026-09-30, including older periods; exclude 2026-10-01 and later. Do not limit selection to the latest eligible month. |
| SEL-RT-02 | EOLM-FIL-006–009, EOLM-TST-003 | A temporary ErrorReport source contains filename dates from 2023, 2024, 2025, and 2026; reference date 2026-10-20. | Select all eligible years through 2025; exclude 2026 files. Do not process only the immediately preceding year if older backlog exists. |
| SEL-RT-03 | EOLM-FIL-003, EOLM-FIL-004, EOLM-FIL-009 | Eligible filename date 20250930 with synthetic LastWriteTime in October 2026. | Eligibility follows filename date; a recent filesystem timestamp must not make the file ineligible. |
| SEL-RT-04 | EOLM-FIL-003, EOLM-FIL-004, EOLM-FIL-009 | Ineligible filename date 20261001 with synthetic LastWriteTime in September 2025. | The file remains ineligible; an old filesystem timestamp must not make it eligible. |
| SEL-RT-05 | EOLM-FIL-004–005, EOLM-FIL-009, EOLM-TST-003 | A relevant file has an unclassifiable name such as unknown.txt and an otherwise eligible-looking old LastWriteTime. | Do not fall back to LastWriteTime or classify the file as eligible. Record a validation error; do not report the affected run/scope as fully successful. |
| SEL-RT-06 | EOLM-FIL-004–005, EOLM-FIL-009, EOLM-TST-003 | A relevant file has an impossible date such as 20260230_12345678@sample.txt, with a timestamp that would otherwise make it eligible. | Reject the filename date; do not use filesystem time as fallback. A plausible timestamp cannot repair an invalid filename. |
| SEL-RT-07 | EOLM-FIL-001–008, EOLM-TST-003 | A temporary root has separate BattleLog and ErrorReport directories, with eligible, ineligible, old-backlog, and invalid-name fixtures in each. | Apply the correct filename pattern and cutoff by log type and operation. Do not mix one log type's rules with the other. Consider all eligible backlog periods. |
| SEL-RT-08 | EOLM-FIL-005, EOLM-FIL-010, EOLM-TST-003 | One isolated run contains valid eligible files plus one relevant invalid/unclassifiable file. | Valid independent files may remain identifiable for safe processing, but the validation error cannot be hidden and the affected scope cannot be certified fully successful. Do not invent a final manifest status name; OSD-03 governs unresolved status aggregation. |
| SEL-RT-09 | EOLM-FIL-006, EOLM-TST-003 | Empty temporary source versus a source containing only ineligible files; separately inject an enumeration/access failure. | Distinguish a verified no-work result from an enumeration failure. Exact run/period status transitions remain blocked by OSD-03 and must be resolved before implementation. |
| SEL-RT-10 | EOLM-SYN-001, EOLM-SAF-005, EOLM-TST-003 | Snapshot synthetic source names, bytes, hashes, and timestamps before and after selection-only execution. | Selection must not modify, move, or delete source files. Hashes and existence remain unchanged on success and failure. |

### Execution gate

- These cases cannot be reported as passed until an official runtime target-enumeration entry point exists and invokes the selection logic.
- Before that entry point is implemented, helper-only tests may prove date parsing and cutoff calculations but cannot prove directory enumeration, timestamp non-fallback, mixed-input handling, or final run status.
- Implement the future suite using temporary directories and synthetic fixtures only. The test must fail if it resolves a configured real log path or uses real Drive data.
- Do not settle the exact mixed-file/run/period status table in test code; OSD-03 remains blocked pending an explicit decision.