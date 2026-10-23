# IPC Contract-to-Test Evidence Audit

- Historical origin: PR #48 merge `f689d020d1384d54260d87dd37c3bb208e3f7fd7`. Current review baseline: PR #123 merge `6b543930f9a9805f50693bd6333a8278c416fe05` (2026-10-21).
- Scope: `IPC-01`–`IPC-06` in [runtime-safety-test-scenarios.md](runtime-safety-test-scenarios.md), the PowerShell/Python contract, JSON schemas, schema tests, and CI workflow inventory.
- Status: static audit only; the latest documentation-only reconciliations did not add runtime IPC implementation or tests. The PowerShell orchestrator and Python Drive adapter are not implemented; none of these IPC runtime scenarios is evidenced as executed.
- Related requirements: `EOLM-DRV-001`–`EOLM-DRV-016`, `EOLM-TST-004`–`EOLM-TST-006`, `EOLM-SEC-001`, `EOLM-SAF-001`–`EOLM-SAF-006`.

## Evidence matrix

| Scenario | Contract expectation | Existing artifact/test evidence | Status and remaining evidence |
|---|---|---|---|
| IPC-01 non-zero process exit | A non-zero Python exit code must fail the call regardless of JSON content. | Contract describes checking exit code and response; response schema validates JSON shape only. | **Not implemented / not run.** Need a PowerShell process-boundary test with exit-code/response combinations. |
| IPC-02 empty, malformed, multiple, or mixed stdout | Exactly one UTF-8 JSON response on stdout; diagnostics go to stderr. | Contract specifies one JSON object and stderr diagnostics. Schema tests validate parsed objects, not raw stdout streams. | **Not implemented / not run.** Need process-level tests for empty stdout, invalid JSON/UTF-8, multiple JSON values, and non-JSON text. |
| IPC-03 request correlation | Response `request_id` and `operation` must match the originating request. | Request/response schemas constrain UUID and operation enum; schema tests cannot compare two separate messages. | **Not implemented / not run.** Need mismatch tests at the PowerShell/Python boundary. |
| IPC-04 exit code versus `success` | Contradictory process exit code and response `success` must fail closed. | Response schema enforces internal `success/result/error` consistency, not consistency with a process exit code. | **Not implemented / not run.** Need a cross-product test of exit code and valid success/failure response. |
| IPC-05 timeout | Timed-out child process is failure/unknown; no success inference or destructive follow-on action. | Contract states timeout/fail-closed expectations; no runtime orchestrator exists. | **Not implemented / not run.** Need deterministic timeout injection and assertions that no follow-on mutation occurs. |
| IPC-06 secret redaction | Tokens and secret-bearing exception details must not leak to stdout, stderr, or operational logs. | Contract states redaction requirements; schema tests do not exercise process output or logs. | **Not implemented / not run.** Need synthetic-secret tests against all output channels and logs. |

## What current CI does and does not prove

- `contracts/drive-request.schema.json` and `contracts/drive-response.schema.json` describe structural JSON constraints. The request schema restricts the four allowed operations and rejects unknown fields; neither schema implements the process boundary.
- `tests/test_contract_schemas.py` validates schema definitions and selected request/response examples. It does not launch the adapter or PowerShell, simulate OS process behavior, or test stdout/stderr, exit codes, timeout, correlation across messages, or log redaction.
- Validate workflow success proves only the checks invoked by that workflow, including schema/helper checks and static PowerShell analysis. Package Validation is package-builder evidence, not IPC runtime evidence.
- Relevant latest baseline runs from PR #48: [Validate](https://github.com/wasawo/eo-log-maintenance/actions/runs/39394695292) and [Package Validation](https://github.com/wasawo/eo-log-maintenance/actions/runs/39394695287). They do not change any IPC row to passed.

## Required follow-up

1. Keep IPC-01–06 marked not implemented/not run until a real, isolated process-boundary harness exists.
2. Before implementing the adapter, reconcile contract details and schemas (including path allow-root checks, response/request correlation, and exit-code mapping) and obtain the required contract review.
3. Use only synthetic payloads, temporary paths, mocked API behavior, and fixed/injected timeout behavior. Do not use real logs, production paths, real Google Drive data, or secrets.
4. Do not add deletion capability. Keep OSD-02, OSD-03, and EOLM-MAN-011 blocked pending explicit decisions.

This audit does not close P0-010 and does not authorize runtime implementation beyond the approved phase. PR #123 is the latest merged docs baseline; no MAN/IPC scenario has changed to implemented, run, or passed.
