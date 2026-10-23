# Diagnostic contract C-45–C-54: implementation and test evidence

**Status:** non-normative evidence crosswalk, refreshed for PRs #140, #141, #144, and #146 on 2026-10-21. Normative decisions remain in docs/decisions/aggregation-inventory-integrity-options.md and docs/decisions/decision-record-c54-sensitive-path-detection.md.

## Current tracked implementation

| Contract | Tracked implementation / tests | What the tests establish | Remaining gap |
|---|---|---|---|
| C-45 event identity | Common/LogFunctions.ps1: New-DiagnosticErrorId; tests/Test-DiagnosticErrorId.ps1; docs/decisions/c45-event-identity-conflict-options.md | A caller-owned per-run monotonic counter yields unique sequential IDs in a single test sequence. Maintainer-approved Option A requires conflicting immutable/core attributes under one ID to fail closed at evidence finalization/publication. | Runtime event creation, one-allocation-per-distinct-event, propagation/deduplication, conflict detection and fail-closed enforcement are not implemented/tested. The policy decision is not runtime acceptance evidence. |
| C-46 ID encoding and exhaustion | Same allocator and test | Exact ERR-000001-style fixed-width format; ERR-999999 is the final ID; exhaustion fails closed; formatting is culture-invariant. | No runtime run-scoped allocator owner or concurrency/serialization contract is implemented. |
| C-47 record/path constraints | ConvertTo-FinalizedDiagnosticJson; ConvertTo-SafeDiagnosticRelativePath; tests/Test-DiagnosticRecordFinalizer.ps1; tests/Test-DiagnosticPathSanitization.ps1 | Seven-field record shape; safe optional path; path cap of 1024 Unicode scalar values; over-limit/unsafe path becomes JSON null. | No end-to-end evidence pipeline; source-root relationship is represented as a relative-path contract and is not resolved against the filesystem. |
| C-48 version compatibility | ConvertTo-FinalizedDiagnosticJson; Test-DiagnosticRecordFinalizer.ps1 | Schema version 1 must be an integer; missing/unsupported/non-integer versions and missing/unknown fields are rejected. | API accepts an already-structured dictionary, not raw JSON. Duplicate JSON property names must be rejected at any future raw-JSON ingestion boundary before dictionary materialization. |
| C-49 controlled vocabularies | ConvertTo-FinalizedDiagnosticJson; Test-DiagnosticRecordFinalizer.ps1 | Exact error-code allowlist and valid phase/operation pairs; invalid values and case variants reject. | No runtime failure-to-code mapping is integrated. |
| C-50 failure-condition mapping | Resolve-DiagnosticErrorCode in Common/LogFunctions.ps1; tests/Test-DiagnosticErrorCodeClassifier.ps1; normative contract in aggregation-inventory-integrity-options.md | Approved Option A scalar condition tokens map deterministically to the C-49 error_code allowlist; 14 mappings and malformed-input rejection cases run in Validate CI. | Producer-side precedence selection, event creation/propagation/deduplication, raw JSON duplicate-key rejection, runtime sink non-disclosure, and end-to-end evidence remain unimplemented/not run. Helper coverage is not runtime acceptance. |
| C-51 phase/operation mapping | Resolve-DiagnosticPhaseOperation in Common/LogFunctions.ps1; tests/Test-DiagnosticPhaseOperationResolver.ps1; Test-DiagnosticRecordFinalizer.ps1; normative contract in aggregation-inventory-integrity-options.md | Approved Option C operation token maps deterministically to its unique phase; exact operation is preserved; all 13 rows, invalid inputs, case variants, collection-shaped values, non-strings, and repeatability are tested in Validate CI. | Producer semantic correctness, runtime event creation/propagation, original-event identity preservation, and end-to-end evidence remain unimplemented/not run. Resolver coverage is not runtime acceptance. |
| C-52 fixed messages | ConvertTo-FinalizedDiagnosticJson; Test-DiagnosticRecordFinalizer.ps1 | Each allowlisted code is paired with the exact approved message; mismatch/null/control-bearing messages reject; output is stable across culture. | No runtime failure event feeds this finalizer; exception-derived message non-disclosure at a process boundary is not established. |
| C-53 path syntax and field nulling | ConvertTo-SafeDiagnosticRelativePath; ConvertTo-FinalizedDiagnosticJson; both diagnostic tests | Relative-path syntax, canonical separators, sensitive-policy ordering, Unicode validity, 1024-scalar maximum, explicit JSON null on unsafe optional path, and preservation of event ID/classification. | No actual runtime diagnostic pipeline or raw JSON ingestion boundary. |
| C-54 sensitive-path detection | ConvertTo-SafeDiagnosticRelativePath; tests/Test-C54PatternContract.ps1; tests/Test-DiagnosticPathSanitization.ps1 | Approved fixed sensitive names/tokens and P1–P6 patterns are covered by synthetic fixtures. | No production logs/credentials or end-to-end logging sink is exercised; runtime non-disclosure remains unverified. |

## CI evidence

- PR #140 merged at 454041f4337d5f22550a288dfd74afecde76635a. Exact-head Validate run 39509321771 and Package Validation run 39509321735 succeeded on 6a7222db4387019c6dc598c2b9bf38b6efca3c4c. Post-merge main Validate run 39509466949 and Package Validation run 39509467065 succeeded on 454041f4337d5f22550a288dfd74afecde76635a.
- PR #141 merged at 58aeb10e3661b7cd893e1a6bfed0469e29e4089f. Exact-head Validate run 39509756240 and Package Validation run 39509756267 succeeded on fe5428248fe5fbef51acd396a1e4bca33438ae53. Post-merge main Validate run 39509903050 and Package Validation run 39509903012 both succeeded on merge SHA 58aeb10e3661b7cd893e1a6bfed0469e29e4089f.

## Acceptance boundary

This crosswalk records helper and synthetic-test coverage only. C-50 now has a pure token-to-code helper, but this does not claim trusted producer integration, precedence enforcement, runtime diagnostic generation, event propagation, raw JSON duplicate-key rejection, runtime log-sink non-disclosure, or P0 acceptance. P0-008, P0-010, and P0-012 remain open; docs/schema/helper/package CI must not be promoted to runtime evidence.


## OSD-02 timestamp/freshness policy — acceptance crosswalk (PR scope)

- Approved policy: UTC ISO 8601 with uppercase `Z`; reject malformed/offset/timezone-less timestamps and finish-before-start.
- Initial configurable defaults: 5-minute maximum future skew; 24-hour freshness threshold.
- Freshness scope: timestamps generated or updated during the current execution only; historical manifest age alone does not invalidate history.
- Clock: assume OS synchronization is configured; fail closed for time-dependent operations if current UTC cannot be obtained reliably. No external monitoring service is mandated.
- Required tests not yet evidenced: fixed-clock boundary cases, malformed/order cases, invalid configuration, clock-unavailable handling, historical-age behavior.
- Status: approved specification only. No runtime implementation or executable test result is claimed.
