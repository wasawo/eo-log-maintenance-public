# C-45 event identity conflict handling options

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

**Status:** Approved decision (Option A) as of 2026-10-21. This document records the selected C-45 conflict disposition; runtime behavior remains unimplemented until the event pipeline is implemented and tested.

## Problem statement

C-45 already requires one stable `error_id` per distinct failure event, preservation of that ID through wrappers, one count for repeated observations of the same event, distinct IDs for independent events, and treatment of conflicting core attributes under one ID as an internal consistency error. C-46 fixes the per-run ID format and prohibits reuse.

The remaining policy question is how an implementation must disposition an observed conflict: the same `error_id` arrives again with a different core attribute (at minimum `error_code`, `phase`, `operation`, or the event's immutable identity). Runtime event propagation is not implemented, so this proposal compares fail-closed dispositions only.

## Invariants for every option

- Never overwrite the first event silently or treat conflicting observations as two valid events.
- Never deduplicate by path or error code alone.
- Do not expose raw exception data or conflicting values in logs/messages.
- Do not count the conflicting observation as an independent valid event merely to avoid resolving identity.
- Do not mutate historical or already-published evidence in place.
- A conflict must prevent the run from being certified as complete/successful.
- No real logs, credentials, Drive operations, production paths, or deletion behavior are involved.

## Options

### Option A — Fail closed for the diagnostic evidence artifact (recommended)

When a repeated `error_id` has any conflicting immutable/core attribute, raise a fixed, non-disclosing internal-consistency failure and reject finalization/publication of the affected diagnostic evidence artifact. Preserve the first observation only as in-memory diagnostic context if safe; do not serialize either conflicting variant as a valid completed record. Do not increment the distinct-event count for the conflicting observation. The run/evidence must remain incomplete or failed according to the separately approved run-state contract; this proposal does not choose a new manifest status.

**Advantages**
- Strongest integrity guarantee: no ambiguous identity is published as valid evidence.
- Simple and deterministic; no new schema field or `error_code` value is needed.
- Avoids recursive diagnostic creation while the diagnostic pipeline itself is inconsistent.

**Costs**
- One conflict can prevent publication of an otherwise useful evidence artifact.
- The conflict itself may be visible only through a fixed process-level failure signal unless a separately approved reporting mechanism exists.

### Option B — Preserve the first observation and emit a separate conflict diagnostic

Keep the first event as canonical, reject the later conflicting observation, and create a new diagnostic event with a fresh ID and a fixed message indicating an internal identity conflict. The evidence/run is still non-successful and must not claim completeness.

**Advantages**
- Can leave a sanitized indication of the conflict in the resulting report.
- Preserves the original event record for investigation.

**Costs**
- Requires a safe, non-recursive path for allocating and finalizing a second diagnostic while the diagnostic subsystem is already inconsistent.
- Needs an explicit choice of existing `error_code`, `phase`, and `operation` values; adding a new code is out of scope.
- Risks making partial evidence look more complete than it is unless the artifact status is independently enforced.

### Option C — Invalidate the ID and retain a conflict marker

Reject all observations for the conflicted ID, record a separate conflict marker in the evidence envelope, and fail validation of the diagnostic evidence. The marker would not be a schema-v1 diagnostic record and would require a separately specified envelope field or error channel.

**Advantages**
- Explicitly represents that neither variant is trustworthy.
- Avoids privileging the first observation.

**Costs**
- Requires an additional evidence-envelope contract and versioning review because schema v1 rejects unknown fields.
- Increases implementation complexity and is incompatible with current schema-v1 output unless separately versioned.

## Comparison

| Criterion | Option A | Option B | Option C |
|---|---|---|---|
| Fail closed on ambiguity | Yes | Yes, if status gate is enforced | Yes |
| Adds schema fields / new error code | No | No new field, but needs code/context selection | Requires envelope contract/version review |
| Avoids recursive diagnostic creation | Yes | No, requires explicit safe path | Usually, but adds envelope mechanism |
| Keeps partial report for investigation | Limited | Yes | Potentially, with new envelope contract |
| Implementation complexity | Lowest | Medium | Highest |

## Decision record

- **Selected: Option A**, approved by the maintainer on 2026-10-21.
- Any conflict blocks successful/complete evidence.
- No new `error_code`, schema-v1 field, manifest status, or reporting channel is introduced by this decision.
- Runtime event handling is not implemented by this document; helper/schema tests are not runtime acceptance evidence.

## Acceptance boundary

This is an approved policy decision, not a runtime implementation. It does not implement event creation, propagation, deduplication, concurrency handling, raw JSON duplicate-key rejection, runtime sink non-disclosure, or end-to-end evidence finalization. C-45/C-46 helper tests remain helper-level evidence only. P0-008, P0-010, and P0-012 remain open.
