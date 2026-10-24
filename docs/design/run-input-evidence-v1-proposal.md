# Run Input Evidence v1 Proposal

- Status: B2 evidence-artifact direction, embedded inventory, exhaustive count reconciliation, and canonical evidence-digest direction approved on 2026-10-21; strict structural schema and synthetic contract tests are introduced in PR #153; runtime implementation and full acceptance remain outstanding.
- Related: `docs/design/aggregation-report-v1-proposal.md`, `docs/decisions/aggregation-inventory-integrity-options.md`, OSD-02, OSD-03, P0-008, P0-010.
- Compatibility: this is a separate artifact. It must not add fields to or rewrite the approved manifest v1 schema.
- Storage direction approved 2026-10-21: local authoritative evidence/report artifacts, followed by verified Google Drive replication for cross-PC access.
- Validation V1 approved 2026-10-24: completed means all input classification processing finished, independently of whether relevant errors were found. See the [selected-policy record](../decisions/selected-policy-decisions-20261024.md#2-b2-v1の意味と保全). Producer/consumer and synthetic-test follow-up remains unimplemented.

## 1. Purpose

Preserve trustworthy evidence that initial source enumeration and filename validation completed, including relevant unclassifiable entries. This allows a derived aggregation report to distinguish a genuinely empty/zero-eligible run from incomplete enumeration or missing validation evidence.

The evidence is frozen before processing depends on the inventory. It is not reconstructed by re-enumerating a mutable source directory after the run.

## 2. Proposed artifact identity and path

Proposed local path:

```text
<local-maintenance-root>/_maintenance/run-input-evidence/<PC-ID>/<LogType>/<run_id>.input-evidence.json
```

The corresponding Drive copy uses a configuration-defined maintenance root and the same relative path. Do not hard-code a user-specific absolute path in the artifact. Exact root configuration and collision/locking behavior remain open.

The tuple `pc_id`, `log_type`, and `run_id` must match the originating manifest. A repeated identity with different content is a conflict, not permission to overwrite.

## 3. Proposed JSON shape

This is a field-shape proposal, not an executable JSON Schema.

```json
{
  "evidence_schema_version": 1,
  "evidence_id": "<stable identity derived from run identity>",
  "run_id": "<originating run id>",
  "pc_id": "PC-A",
  "log_type": "BattleLog",
  "source_scope": {
    "root_id": "<configured non-secret source identifier>",
    "relative_scope": "."
  },
  "enumeration": {
    "status": "completed",
    "started_at_utc": "2026-10-21T00:00:00Z",
    "finished_at_utc": "2026-10-21T00:00:02Z",
    "entries_observed": 100,
    "eligible_target_count": 12,
    "inventory_sha256": "<64 lowercase hex chars>"
  },
  "validation": {
    "status": "completed",
    "valid_eligible_count": 12,
    "valid_ineligible_count": 85,
    "invalid_relevant_count": 3,
    "errors": [
      {
        "error_id": "VAL-0001",
        "code": "unclassifiable_relevant_filename",
        "filename": "unexpected-name.txt",
        "relative_path": "unexpected-name.txt"
      }
    ]
  },
  "inventory": {
    "kind": "embedded",
    "targets": [
      {
        "filename": "20260930_example.txt",
        "relative_path": "2026/09/20260930_example.txt",
        "size_bytes": 1234,
        "expected_sha256": "<64 lowercase hex chars>"
      }
    ]
  },
  "integrity": {
    "algorithm": "sha256",
    "canonicalization": "EO-LOG-MAINTENANCE-RUN-INPUT-EVIDENCE-V1",
    "digest": "<64 lowercase hex chars>"
  }
}
```

Example values are illustrative only and are not operational evidence.

## 4. Required invariants

1. Reject missing, malformed, or unsupported `evidence_schema_version`; never silently migrate or repair.
2. Evidence identity must match the manifest and the aggregation report exactly.
3. Enumeration status must distinguish `completed` from `failed` or `incomplete`. Only `completed` can support no-work classification.
4. Validation status must distinguish `completed` from `failed` or `incomplete`. Under approved V1 (2026-10-24), `completed` means classification processing covered all inputs, not just eligible targets; it does not mean no invalid/relevant errors were found. Preserve errors and counts independently. Missing errors or missing counts cannot be interpreted as zero errors; count/digest agreement alone does not prove coverage.
5. **Approved count rule (2026-10-21, decision A):** every entry returned by a completed enumeration must be assigned exactly one mutually exclusive classification: `eligible_targets`, `valid_ineligible`, `invalid_relevant`, or `ignored_entries` (only for entry types explicitly excluded by the source contract). The sum of these category counts must equal `entries_observed`. `enumeration_errors` is a separate diagnostic count and is not added to that sum; if any enumeration error occurs, enumeration cannot be `completed`. A category must never be silently omitted or double-counted. The exact source-entry universe and pagination contract must be specified before implementation.
6. The embedded eligible inventory must match the manifest frozen target set and its independently specified digest. The digest canonicalization is a separate open decision; do not implement from this illustrative shape alone.
7. Relevant invalid/unclassifiable entries are structured and sanitized. Never infer their period from `LastWriteTime`.
8. Write and validate the local evidence artifact before side effects depend on its inventory. If this fails, stop dependent processing or classify the run conservatively; never certify no-work or period completion.
9. Treat local publication and Drive replication as separate states. The local evidence remains authoritative after successful local validation. Cross-PC consumers must not use the Drive copy until identity and content verification succeeds.
10. The evidence is immutable for a given run identity. A conflicting existing artifact stops processing and requires reconciliation; it is not silently replaced.
11. Do not include file contents, OAuth tokens, credentials, or unsanitized exception details.
12. Regeneration uses only the validated evidence artifact and the exact originating manifest. Do not rescan mutable source directories to recreate historical enumeration facts.

### Validation V1 compatibility and implementation boundary (2026-10-24)

The approved direction retains the existing v1 field set and status values; it adds neither a coverage field nor a new version. Completed classification with relevant errors must keep `invalid_relevant_count` and `errors`; it cannot certify run success or no-work. Known-period completion still requires the approved OSD-03 inventory, all-outcome accounting and error-scope conditions independently of the status string.

Historical `incomplete` records remain exact original bytes: do not rewrite, repair or promote them to completed from matching counts/digests. Do not infer complete coverage from incomplete/failed observations. The current `Common/SourceInventoryEvidenceBuilder.py` still emits validation incomplete whenever it finds validation errors. That is implementation status, not conformity to selected V1; producer/consumer changes, compatibility verification and synthetic tests remain unimplemented. The [comparison history](../decisions/b2-validation-coverage-report-time-options.md) distinguishes the selected policy from this pending work.

## 5. Inventory representation — decision A approved

**Decision (2026-10-21): A — embed the complete frozen eligible-target inventory in the B2 evidence artifact.** This keeps the evidence self-contained and avoids a separate inventory-artifact dependency during recovery. The manifest remains the authoritative per-file outcome record; the evidence proves the initial enumeration/validation input set. The embedded records must match the manifest frozen target set and the approved A2 digest. Duplicate representation is intentional; any mismatch is a hard integrity failure.

B2 itself is approved: enumeration and validation completeness evidence is a separate immutable artifact.

- **Embedded inventory (shown above):** store the complete frozen eligible-target records in this artifact. This makes the evidence self-contained but duplicates target data from the manifest.
- **Referenced inventory:** store a canonical inventory artifact separately and include its exact path, count, and digest. This reduces duplication but adds another artifact and publication dependency.

The approved choice is embedded inventory. If measured artifact size later proves impractical, changing to a referenced inventory requires a new explicit decision and schema version; implementations must not silently switch representations.

## 6. Local publication and Drive replication

1. Serialize deterministically to a temporary file in the destination local filesystem.
2. Flush and close, re-read, and validate schema, identity, counts, inventory digest, and integrity digest.
3. Publish locally without exposing a partially written final file; do not overwrite an existing artifact with conflicting content.
4. Only after local publication, upload a copy to the configured Drive destination.
5. Verify the remote object's identity and content using the approved Drive matching/verification policy before declaring the copy available to PC-B.
6. If the upload outcome is uncertain, query and reconcile current Drive state before retrying.
7. A Drive failure must not change the local evidence or imply that cross-PC replication succeeded.

The exact atomic publication, Drive object identity, upload verification, and locking/recovery implementation remain open.

### 6.1 Approved evidence integrity digest canonicalization

**Decision (2026-10-21):** hash a fixed, deterministic canonical byte representation of the evidence object, excluding only `integrity.digest` itself. This is separate from the A2 inventory digest.

Canonicalization contract:

1. Validate the evidence against the versioned schema before canonicalization. Reject unknown schema versions, duplicate JSON object keys, missing required fields, invalid types, invalid UTF-8, and values outside schema constraints. Do not silently coerce or repair.
2. Build the digest input from the complete evidence object with only the `integrity.digest` member removed. Retain `integrity.algorithm` and `integrity.canonicalization`; their values are fixed to `sha256` and `EO-LOG-MAINTENANCE-RUN-INPUT-EVIDENCE-V1`. The digest field is omitted, not replaced by an empty string or null.
3. Serialize as UTF-8 JSON with no byte-order mark, no insignificant whitespace, no trailing newline, and object member names sorted by unsigned lexicographic order of their UTF-8 bytes at every nesting level.
4. Arrays retain schema-defined semantic order. In particular, inventory targets are ordered by the approved A2 relative-path UTF-8 byte ordering; validation errors are ordered by `error_id` byte order. Any other array must have an explicit schema-defined order; unordered collections must not be serialized from incidental runtime iteration order.
5. Strings are encoded as UTF-8 without Unicode normalization or case folding. JSON escaping must be deterministic: escape quotation mark, reverse solidus, and U+0000–U+001F using the shortest valid JSON escapes, using lowercase hexadecimal digits for `\\u00xx` escapes when needed. Do not escape non-ASCII scalar values unnecessarily. Reject unpaired surrogate values.
6. Integers use canonical base-10 JSON notation: zero is `0`; other non-negative integers have no sign or leading zeroes. Floating-point values are prohibited in the evidence schema. Booleans and null use lowercase JSON literals.
7. Compute SHA-256 over the resulting bytes. Store the digest as exactly 64 lowercase hexadecimal ASCII characters. Verification repeats the same schema validation and canonicalization and compares the computed digest in constant time where supported.
8. The canonicalization identifier is versioned. Any change to member ordering, string escaping, number rules, array ordering, or excluded fields requires a new canonicalization identifier or evidence schema version; never silently change v1 behavior.

This specifies the digest representation but does not replace the need for an executable schema, duplicate-key-detecting parser, and cross-runtime reference vectors before implementation.

## 7. Acceptance tests required

- Valid completed enumeration with zero eligible targets is distinguishable from failed/incomplete enumeration.
- Missing or incomplete validation evidence cannot produce a valid no-work result.
- Evidence/manifest/report identity mismatch is rejected.
- Count mismatch, duplicate target, duplicate normalized path, invalid hash, invalid size, and digest mismatch are rejected.
- Relevant unclassifiable filenames are preserved and block run-level success.
- Local write failure prevents dependent processing from relying on uncommitted evidence.
- Crash before local publication leaves no authoritative partial artifact.
- Crash after local publication but before Drive replication preserves the local artifact and reports replication as incomplete.
- Uncertain Drive upload is reconciled before retry; conflicting remote content is not overwritten.
- Regeneration uses the exact manifest and evidence, never a rescan of mutable source data.
- Tests use synthetic fixtures and temporary directories only; no real logs, production paths, credentials, or Drive writes.

## 8. Decisions still needed

- [x] Approve A2 inventory digest field order, path normalization, Unicode treatment, and integer encoding.
- [x] Embedded versus referenced inventory: embedded inventory approved.
- [x] Count reconciliation: every enumerated entry receives exactly one classification and category counts sum to `entries_observed`; enumeration errors prevent `completed`. The source-entry universe is approved; traversal and pagination acceptance tests remain pending.
- [x] Evidence digest canonicalization: fixed UTF-8 JSON representation, with `integrity.digest` omitted from its own input; exact contract in §6.1.
- Define local root and Drive root configuration, remote identity checks, locking, and crash recovery.
- Specify executable schema and table-driven tests.

No runtime implementation, executable tests, or operational evidence is claimed.


## Implementation status — A2/B2 integrity validator slice (2026-10-22)

Canonicalization now rejects Python floating-point values recursively before the JSON roundtrip, including integer-valued floats, negative zero, fractional and nonfinite values; it never coerces them to integers. JSON Schema's abstract integer acceptance of `1.0` is not proof of §6.1 canonical compliance. Synthetic regressions preserve integer reference vectors and verify rejection through digest/invariant, report-builder and exact-byte referenced-artifact paths, even with an independently reproduced old faulty digest. Normal source-builder integer output, canonical vectors, integer-derived report counts and exact original-byte reference hashes remain unchanged. Previously misaccepted B2 evidence containing floats is rejected without repair or conversion. This implements the approved number rule; it does not introduce a general lexical-number parser policy beyond values parsed as floating point, decide B2 status or timestamp questions, or prove runtime/Drive acceptance.

PR #156 introduces `Common/RunInputEvidenceIntegrity.py` to recompute the approved A2 inventory digest and B2 evidence digest, validate the evidence against the strict v1 schema, and enforce the approved exhaustive count reconciliation for completed enumeration. Synthetic tests cover the documented A2 reference vectors and fail-closed integrity/count cases; CI execution is pending until the PR head is checked.

Scope boundaries: this helper validates an already-constructed evidence object. It does not enumerate source entries, prove source traversal completion, compare the embedded inventory against the originating manifest, persist immutable evidence, publish atomically, replicate to Drive, or authorize archive/deletion. These remain acceptance gaps.

## OSD-03 approved report-contract compatibility note (2026-10-21)

R1-B/R2-A/R3-B/R4-A/R5-A/R6-A/R7-A are approved. The report contains period summaries only and references the exact manifest and B2 evidence by canonical relative path, schema version, and SHA-256 of exact bytes. Report identity is (pc_id, log_type, run_id, report_schema_version), with no report_id field. Deterministic regeneration uses only immutable validated inputs; it must not re-enumerate mutable source directories. Period completion is complete/incomplete/indeterminate and remains report-only, not a manifest v1 enum. Local publication is authoritative; Drive replication is separate and must be content-verified before cross-PC use. These decisions do not alter manifest v1, B2 evidence structure, A2 inventory digest, or exhaustive count reconciliation. Executable schema, runtime implementation, and tests remain pending.


## Manifest/evidence frozen-target binding implementation slice (2026-10-22)

PR #157 extends the referenced-artifact validation path to recompute A2/B2 digests and require the embedded B2 target set to equal the originating manifest `files` set by relative path, filename, size, and SHA-256. It also checks report inventory count/digest against the validated evidence. Synthetic tests cover a manifest/evidence target-set divergence. This remains a standalone validation helper, not source enumeration or official sync/archive entry-point integration; exact-head CI must pass before this slice is considered verified.
