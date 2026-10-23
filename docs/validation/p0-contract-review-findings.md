# P0 PowerShell/Python Contract Review Findings

- Status: Technical pre-review complete; operator approval is still pending. Retry/unknown-upload scenario crosswalk refreshed against PR #95 (`d744ec68954d9460159952dca70b896503d03811`).
- Scope: static comparison of `docs/design/powershell-python-contract.md`, request/response schemas, `tests/test_contract_schemas.py`, C-18/C-29 decisions, and RETRY-01–06 in `docs/validation/runtime-safety-test-scenarios.md`.
- No runtime adapter or retry orchestrator is implemented in the current tracked tree. These findings and scenario definitions are not evidence of a live PowerShell/Python integration test.

## Findings requiring resolution before adapter implementation

| ID | Observation | Risk / consequence | Proposed disposition | Approval needed? |
|---|---|---|---|---|
| C-01 | The prose contract says `local_path` and `staging_path` must be absolute Windows paths and be checked against configured allow-roots. The request schema only requires strings of minimum length; schema tests accept ordinary drive-rooted examples but do not reject relative paths. | A schema-valid request may still contain a relative or out-of-policy path. Runtime validation remains mandatory even if the schema is strengthened. | Decide whether schema validation will enforce drive-rooted paths only, drive-rooted plus UNC paths, or leave path syntax to the adapter while requiring allow-root validation in PowerShell and Python. Then add positive and negative cases. | Yes: path policy |
| C-02 | The response schema constrains the envelope and success/error consistency but leaves `result` as any object. It does not define operation-specific result fields. | The schema cannot independently detect missing or mistyped result fields for list, metadata, upload, or download operations. | Before adapter implementation, define minimum result shapes per operation and add schema fixtures. If result shape intentionally remains open during Phase 1, keep the limitation explicit and require runtime consumer assertions. | Yes: response contract scope |
| C-03 | The contract says response `request_id` and `operation` must exactly match the request, but the JSON Schema validates each document independently and cannot compare two documents. Current tests validate examples but do not test a PowerShell caller against a Python-produced response. | Cross-message correlation can only be enforced by the caller/integration test, not by the individual response schema. | Add contract-level tests with mismatched request IDs and operation names once the adapter/caller harness exists; keep the PowerShell caller responsible for fail-closed checks. | No policy change; implementation required |
| C-04 | The contract assigns exactly one API attempt to Python and disables implicit HTTP-client retries, but no Python adapter or test currently verifies the underlying client retry configuration. PR #95 maps this to RETRY-01, which remains not implemented/not run. | Future library defaults could violate the single-attempt contract while schema tests still pass. | When the adapter is introduced, pin the HTTP/client library behavior and test that one request causes exactly one API attempt per invocation, including the absence of implicit HTTP-client/library retries; do not claim this is proven by schema tests. | No policy change; implementation required |
| C-05 | Exit-code/error-code mapping and `retryable` semantics are described in prose, while current tests only validate the JSON shape and a subset of error-code rejection cases. PR #95 maps bounded retry ownership to RETRY-02, which remains not implemented/not run. | A future adapter could return a schema-valid but semantically contradictory error code, retryable flag, and process exit code. | Add table-driven semantic contract tests for all defined error codes, retryability policy, and exit-code consistency before integration acceptance; RETRY-02 must also prove PowerShell-only retry ownership, the four-attempt ceiling, 1/5/15-minute waits, and no retry for permanent errors. | No policy change; implementation required |

## C-06 — Unknown upload outcome and Drive reconciliation

| ID | Observation | Risk / consequence | Proposed disposition | Approval needed? |
|---|---|---|---|---|
| C-06 | C-29 requires Drive-state reconciliation before retrying an upload whose outcome is unknown. PR #95 defines RETRY-03–06 for timeout-after-upload, confirmed absence, incomplete/inaccessible listing, ambiguous identity, content mismatch, and unmarked objects; all remain not implemented/not run. | A timeout or lost response cannot distinguish “upload did not happen” from “upload succeeded but the response was lost.” Treating failed/partial listing as absence can create duplicate uploads or incorrectly authorize later steps. | Before retry, require a successful complete listing and unambiguous candidate identity. Only a confirmed absence under the approved trust/identity policy can qualify for another attempt; uncertain, incomplete, mismatching, or ambiguous state fails closed. OSD-01 still blocks trust decisions for pre-existing unmarked objects. Add deterministic runtime tests and preserve source/staging data on uncertainty. | No new policy approval beyond the existing OSD-01 trust decision; implementation and tests required |

## Existing controls confirmed

- Request schema rejects unknown top-level fields and operation-specific extra parameters.
- Request schema permits only `list_files`, `get_file_metadata`, `upload_file`, and `download_file`; deletion operations are not allowed.
- Response schema requires the envelope fields and enforces success/result/error consistency.
- CI currently runs schema tests; this verifies schema validity and sample instances, not the runtime semantics listed above.

## Acceptance criteria for P0-005

1. Resolve C-01 and C-02 in a reviewed contract revision before adapter implementation.
2. Add negative schema tests for path policy if that policy is represented in the schema.
3. Add semantic contract tests for response/request correlation, exit-code consistency, retryability, and single-attempt behavior when the adapter/caller harness exists.
4. Obtain operator review and record the approval decision in the decision register. Do not mark P0-005 complete merely because this pre-review document exists.

## References

- `docs/design/powershell-python-contract.md`
- `contracts/drive-request.schema.json`
- `contracts/drive-response.schema.json`
- `tests/test_contract_schemas.py`
- `docs/decisions/decision-register-c18-c32.md` C-18/C-29
- `docs/validation/runtime-safety-test-scenarios.md` RETRY-01–06
- Contract testing guidance: Pact recommends explicit request/response expectations and provider verification; see https://docs.pact.io/getting_started/matching. This is general guidance, not project-specific evidence.