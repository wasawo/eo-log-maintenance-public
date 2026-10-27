# Filename and Period Selection Specification

## 1. Purpose

2026-10-27 revision: Q1–Q10 and the flattening instruction in the [review ledger](../development/requirements-design-task-review-20261027.md) supersede copy-only archive and both-PC completion waiting. Filename/date rules are retained; implementation and deletion verification contracts remain pending.

Define deterministic filename validation and date-based eligibility rules
for ElectronicObserver BattleLog and ErrorReport files.

## 2. Filename Patterns

Patterns are anchored to the complete filename.

| Log type | Pattern | Date field |
|---|---|---|
| BattleLog | `^(?<Date>\d{8})_\d{8}@.+\.txt$` | First eight characters |
| ErrorReport | `^(?<Date>\d{8})_\d{8}\.txt$` | First eight characters |

Matching is case-sensitive for the documented `.txt` extension.
The extracted date must parse as a real calendar date using the exact
format `yyyyMMdd` and invariant culture.

A filename that does not match its log type's pattern, or whose extracted
date is invalid, is a per-file validation error. Do not use LastWriteTime
as a fallback.

Unexpected files must not be silently treated as eligible log files.
Record validation errors in the run results. A run must not report a
period as fully successful if a relevant file validation error prevents
the period from being verified.

## 3. Synchronization Eligibility

Eligibility is calculated from the filename date, not filesystem timestamps.

- BattleLog: include files dated on or before the final calendar day
  of the previous month.
- ErrorReport: include files dated on or before December 31 of the
  previous calendar year.
- Process every eligible backlog period, not only the most recent period.

## 4. Archive Eligibility

Archiving is a PC-A-only operation and is subject to all archive-gate
requirements defined elsewhere in the project.

- BattleLog: include files dated on or before December 31 of the
  previous calendar year.
- ErrorReport: include files dated on or before December 31 of the
  year two years before the current calendar year.
- Process every eligible backlog period.
- Archive completion includes copy (or verified reuse), destination-content verification, source unchanged since copying verified immediately before deletion, and deletion of only that cloud source. Unverifiable/changed/mismatched sources remain. PC-B completion is not a prerequisite.
- Both move routes select eligible files recursively but place them directly in the shared log-type destination without reproducing source folders. Preserve source identity separately; identical names do not imply the same source.

## 5. Boundary Examples

For an execution date in October 2026:

| Log type | Operation | Latest eligible date |
|---|---|---|
| BattleLog | Synchronization | 2026-09-30 |
| BattleLog | Archive | 2025-12-31 |
| ErrorReport | Synchronization | 2025-12-31 |
| ErrorReport | Archive | 2024-12-31 |

These examples illustrate the rules; implementation must calculate the
boundaries at runtime.

## 6. Failure and Safety Rules

- Invalid or unexpected filenames are errors, not automatic exclusions
  that disappear from the run report.
- Never substitute LastWriteTime for a missing or invalid filename date.
- Do not overwrite a different file merely because its filename matches.
- File completion and archive processing require current source/destination
  identity and content checks, and the applicable records specified elsewhere.
  A different PC's period completion is not a prerequisite.
- Dry Run and filename selection must not modify, move, or delete source
  files.

## 7. Validation Errors and Completion Status

- A filename that cannot be classified by the expected log-type pattern
  has no trustworthy period. Record it as a validation error and prevent
  the run from being reported as fully successful.
- A filename whose date field is syntactically present but is not a real
  calendar date is also a validation error. Do not silently skip it.
- Other valid files may be processed individually if doing so is safe.
  Processing valid files does not cancel the validation error.
- If any relevant validation error remains unresolved, the run must not
  produce a fully successful completion record for the affected scope.
- If an invalid filename cannot be assigned to a period, do not certify
  the overall synchronization run as fully successful.
- Missing, invalid, or ambiguous evidence needed for a particular file blocks
  that dependent operation. Another PC's missing/failed period manifest alone
  does not block processing current cloud files. A failed file does not erase
  successful independent file moves.
- The exact manifest status names and transition rules are governed by
  the manifest schema specification and must be finalized before
  manifest implementation.
