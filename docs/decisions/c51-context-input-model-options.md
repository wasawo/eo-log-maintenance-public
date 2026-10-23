# C-51 structured processing-context input model options

**Status:** Decision recorded 2026-10-21. The maintainer approved Option C as the input contract. The alternatives remain explanatory only; the normative C-51 mapping table and schema-v1 phase/operation allowlist are unchanged.

## Problem

C-51 already approves the phase/operation mapping and propagation rules, but it does not define the exact input contract used by a future event creator to select a row. A helper must not infer context from exception text, stack traces, paths, localization, or whichever layer happens to catch the failure. Runtime entry points are not yet implemented, so this proposal does not create a runtime DTO or claim integration.

## Constraints common to all options

- Use only the exact C-51 mapping table in `docs/decisions/aggregation-inventory-integrity-options.md`.
- The context describes the failed action at event creation, not a later observer/wrapper.
- Preserve the selected pair unchanged when propagating the same event.
- Unknown/unknown is valid only when trusted structured context genuinely cannot identify the failed action; missing instrumentation and invalid tokens must not silently become unknown.
- Reject null, empty, non-string, unknown, case-variant, or malformed inputs with a fixed non-disclosing error.
- Do not add schema fields, enum values, aliases, or free-form context strings.
- A pure helper and synthetic tests do not establish producer correctness, propagation/deduplication, runtime sink behavior, or P0 acceptance.

## Option A — one exact context identifier

The trusted event producer supplies one required, case-sensitive scalar identifier representing a row of the C-51 table. A pure helper maps that identifier to the exact phase/operation pair.

Illustrative identifiers (proposal only): `source_enumeration`, `target_classification`, `target_metadata_read`, `target_content_read`, `content_digest_computation`, `source_mutation_check`, `manifest_validation`, `evidence_validation`, `evidence_finalization`, `aggregation`, `report_serialization`, `report_publication`, `context_unavailable`.

**Advantages**
- One input determines one approved pair, preventing invalid pair combinations.
- Simple table-driven positive/negative tests.
- Similar to the approved C-50 single-token input model.

**Risks**
- Adds a second internal token vocabulary that must stay synchronized with C-51.
- The producer must select the correct token; this helper cannot detect a producer choosing a semantically wrong but valid token.

## Option B — explicit phase and operation pair

The trusted event producer supplies two required scalar strings, `Phase` and `Operation`. A pure validator accepts only exact pairs in the C-51 table.

**Advantages**
- Inputs directly match the diagnostic schema fields and make the producer's captured context explicit.
- No additional context-token vocabulary.

**Risks**
- Two fields permit invalid or mismatched pairs and require exhaustive pair rejection tests.
- The producer can accidentally construct a pair from different processing layers; validation proves pair membership, not provenance or semantic correctness.

## Option C — one exact operation identifier, phase derived centrally

The trusted event producer supplies one required, case-sensitive scalar operation identifier from the existing C-51 table. A pure helper maps that operation to its unique approved phase. The `unknown` operation maps only to `unknown` phase.

**Advantages**
- Reuses the existing operation vocabulary and avoids a second set of tokens.
- One input prevents invalid phase/operation combinations.
- Central mapping keeps phase derivation deterministic.

**Risks**
- The producer must still choose the operation correctly; helper validation cannot prove it represents the failed action.
- The contract must explicitly reserve `unknown` for genuinely unavailable trusted context and reject missing/invalid input rather than treating it as unknown.

## Comparison

| Criterion | A: context token | B: explicit pair | C: operation token |
|---|---|---|---|
| Single scalar input | Yes | No | Yes |
| Reuses existing schema vocabulary | Partly | Yes | Yes |
| Invalid pair possible at input | No | Yes | No |
| New internal token set | Yes | No | No |
| Central deterministic mapping | Yes | Validation only | Yes |
| Producer semantic correctness independently proven | No | No | No |

## Recommendation

**Recommend Option C** because it reuses the existing operation allowlist, has a single scalar input, and deterministically derives the only permitted phase without introducing a parallel context-token vocabulary. Option A is a reasonable alternative if the maintainer prefers a separate semantic identifier. Option B is the most explicit but admits more invalid combinations.

**Decision:** Option C is approved. The exact input is one required, case-sensitive scalar named `Operation`, containing an existing C-51 operation token. `Resolve-DiagnosticPhaseOperation -Operation` derives the approved phase and returns the operation unchanged. Null, empty, non-string, unknown, case-variant, and collection inputs reject with a fixed non-disclosing error. `unknown` is reserved for trusted producer context that genuinely cannot be established; it is not a fallback for missing instrumentation. The pure resolver and synthetic tests are implemented in PR #146. Runtime event production and end-to-end acceptance remain out of scope.

## Acceptance tests and implementation status

- Every approved mapping row resolves to its exact phase/operation pair.
- Null, empty, non-string, unknown, case-variant, collection-shaped, and malformed input is rejected without echoing the input.
- `unknown` is accepted only through the explicitly approved context-unavailable representation.
- Repeated calls are deterministic.
- No exception message, exception type, stack trace, path, or ambient observer context is consulted.
- Existing schema-v1 finalizer tests remain passing.
- Implemented in PR #146: `tests/Test-DiagnosticPhaseOperationResolver.ps1` is wired into Validate CI; the normative contract, evidence crosswalk, traceability/inventory/audit/gap records, and `docs/handoff/next-chat.md` are updated in the same PR.
