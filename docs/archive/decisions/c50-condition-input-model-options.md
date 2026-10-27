# C-50 structured condition input model — non-normative proposal

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

**Status:** design alternatives for maintainer decision only. This document does not amend the approved C-50 mapping/precedence table and does not authorize implementation.

## Problem statement

C-50 already defines a normative priority order from observable failure conditions to the schema-v1 error_code allowlist. The repository now has a finalizer that validates a supplied error code and an event-ID allocation helper, but no executable C-50 classifier. The classifier cannot be implemented safely until the shape and validation rules of its trusted structured input are explicit.

The classifier must never inspect localized/free-form exception messages, exception class names, stack traces, raw OS text, paths, or arbitrary metadata to infer a category. It must not allocate or rewrite event identity. It must use the existing C-49 error_code values only.

## Candidate models

| Option | Input shape | Advantages | Risks / limitations |
|---|---|---|---|
| A — caller-selected condition | One required condition identifier, already selected by the event producer. | Small API; easy to validate; minimal DTO. | Each producer must independently apply the full C-50 precedence table. Overlapping observations can be classified differently by different call sites; central precedence is not enforced. |
| B — observed condition set (**recommended**) | A non-empty or empty array of distinct, exact condition identifiers that the trusted producer has positively observed. The classifier centrally selects the highest-priority matching C-50 row. An empty array maps to unknown_error; an unknown identifier or duplicate identifier rejects the input. | Centralizes precedence; straightforward table-driven tests; no free-form values; supports multiple simultaneous observations without caller-side priority logic. | Correctness still depends on producers asserting only conditions supported by structured evidence. Condition-specific prerequisites must be normative and tested. |
| C — typed observation object | A versioned internal object with explicit artifact kind/read result/validation result, mutation observation, filename result, access-denied signal, operation kind/result, and other facts needed by C-50. The classifier validates cross-field consistency and derives the observed conditions itself. | Strongest field-level validation; can reject contradictory evidence and enforce prerequisites centrally. | Largest contract and test surface; risks defining fields that no current runtime entry point can populate; requires a separate review of nullability, allowed values, and cross-field invariants. |

## Option B: candidate condition identifiers and prerequisites

The following identifiers are **proposed**, not approved. Each token represents a condition positively established by trusted structured state; it is not an error_code and does not become a persisted diagnostic field.

| C-50 priority | Proposed condition identifier | Required evidence before producer may include it | Resulting error_code |
|---:|---|---|---|
| 1 | manifest_contract_invalid | Manifest was read successfully; its syntax/schema/identity/integrity check failed. | manifest_invalid |
| 2 | run_input_evidence_invalid | Run-input evidence was read successfully; its schema/identity/inventory/count/integrity check failed. | evidence_invalid |
| 3 | observed_source_mutation | An approved before/after identity or metadata comparison observed a mismatch. | source_mutation_detected |
| 4 | target_filename_invalid | Strict filename/date/period/eligibility validation failed during classification. | invalid_filename |
| 5 | structured_access_denied | Platform/API supplies an explicit structured access-denied signal for the failed operation. | file_access_denied |
| 6 | directory_enumeration_failed | Source-root/reached-directory enumeration failed, excluding a more specific access-denied or mutation condition. | enumeration_failed |
| 7 | target_metadata_failed | Required type/size/timestamp metadata could not be retrieved or validated. | file_metadata_failed |
| 8 | target_content_read_failed | Target bytes could not be read before hashing completed. | file_read_failed |
| 9 | content_digest_failed | Intended bytes were available, but digest computation failed. | hash_failed |
| 10 | general_contract_validation_failed | An explicit validation failure is not covered by the manifest/evidence-specific conditions above. | validation_failed |
| 11 | report_serialization_failed | Serialization of a validated report/evidence object failed. | serialization_failed |
| 12 | aggregation_failed | Summary/count/reconciliation derivation failed after validated inputs. | aggregation_failed |
| 13 | report_publication_failed | Writing/publishing the final report failed after successful aggregation/serialization. | publication_failed |
| 14 | *(no recognized condition)* | A failure event exists, but no proposed/approved condition matches. | unknown_error |

Under Option B, if multiple distinct valid condition identifiers are supplied, the classifier returns the error_code from the lowest numeric priority row. Conditions whose prerequisites are not satisfied must not be supplied. An unknown condition token, duplicate token, wrong input type, or malformed condition collection is an invalid classifier input and must be rejected with a fixed non-disclosing error; it must not silently map to unknown_error.

## Shared constraints for any option

1. The input is trusted structured state from the event producer, never parsed from exception text.
2. Mapping is deterministic and uses the existing C-50 priority order. No new error_code, phase, or operation values are introduced.
3. Classification occurs once when the underlying event is first created. Later wrappers preserve error_id, error_code, phase, and operation; they do not reclassify the same event.
4. unknown_error means a real observed failure does not match a known condition; it must not conceal missing instrumentation, malformed classifier input, or a known mapping defect.
5. Classifier failure must not discard the original event silently. The caller must fail evidence finalization closed if required diagnostic fields cannot be populated safely.
6. Unit tests must cover each C-50 row, every precedence overlap, access-denied versus generic I/O, readable-invalid versus unreadable manifest/evidence, read-versus-hash failure, invalid filename before content processing, unknown fallback, malformed input rejection, deterministic output, and proof that exception text/class names do not influence classification.

## Decision requested

Select **A, B, or C** as the structured input model. If B or C is selected, approve the exact field/token names and invalid-input behavior before normative records or executable classifier code are changed. The recommendation is **B** because it centralizes the already-approved precedence table without introducing a large fact DTO before runtime entry points exist. This remains a proposal; no choice has been applied.

## Evidence and safety boundary

The current helper/schema tests do not constitute runtime C-50 classification evidence. scripts/SyncLogs.ps1 remains a sentinel and scripts/ArchiveLogs.ps1 is absent. P0-008, P0-010, and P0-012 remain open. No real logs, credentials, production paths, Google Drive operations, archive enablement, or deletion behavior are in scope.
