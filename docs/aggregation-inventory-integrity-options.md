# Aggregation Inventory Integrity — Decision Options

- Status: partial decision record. Storage option C3, inventory digest A2, separate immutable completeness evidence B2, embedded inventory, exhaustive count reconciliation A, canonical evidence digest A, source-entry universe A, traversal completion rule A, best-effort source-mutation detection A, enumeration status semantics A, and distinct-event enumeration error counting A are approved by the maintainer on 2026-10-21.
- Related: docs/aggregation-report-v1-proposal.md, OSD-02, OSD-03, P0-008, P0-010.
- Purpose: preserve the approved inventory-integrity and enumeration-evidence decisions, their exact contract details, and remaining implementation/test requirements.
- Compatibility constraint: do not change the approved manifest v1 field set. Any additional evidence must be stored separately and referenced by the derived aggregation report.

## 1. Decision A — canonical frozen-inventory digest

The digest must be reproducible across supported runtimes, independent of JSON property ordering, and sensitive to changes in any target identity or expected-content field used by the aggregation contract.

### Option A1 — canonical JSON

Serialize the frozen eligible-target records using a formally specified canonical JSON algorithm, sort records by a specified key, then SHA-256 the UTF-8 bytes.

- Advantages: structured and inspectable.
- Risks: requires choosing and implementing a canonical JSON standard or specifying number, escaping, Unicode, and property-order rules precisely. Ordinary serializer output is not sufficient.

### Option A2 — versioned length-prefixed records (recommended)

Construct a byte stream with a fixed domain/version prefix, then encode each target record in a fixed field order. Sort records by normalized relative-path UTF-8 byte sequence using ordinal byte comparison. Encode each field as UTF-8 preceded by its byte length in a fixed-width unsigned integer representation. Include at minimum the canonical relative path, filename, size in bytes, and expected SHA-256 from the approved manifest target record. Hash the complete stream with SHA-256.

Approved normative framing (A2 approved 2026-10-21):

1. Prefix bytes are the ASCII bytes for `EO-LOG-MAINTENANCE-INVENTORY`, then one NUL byte, then ASCII `V1`, then one NUL byte.
2. Append the target-record count as an unsigned 64-bit big-endian integer. Reject an inventory count that cannot be represented in this field.
3. Each record has exactly four fields in this order: `relative_path`, `filename`, `size_bytes`, `expected_sha256`.
4. For each field, append its UTF-8 byte length as an unsigned 32-bit big-endian integer, then append the field bytes. Reject a field whose encoded byte length exceeds the unsigned 32-bit range.
5. `relative_path` uses `/` separators, is relative, has no leading or trailing slash, contains no empty, `.` or `..` segment, contains no NUL or backslash, and is not a drive-qualified or UNC path. Convert source-platform separators to `/` before validation. Reject rather than silently repair any remaining invalid path.
6. `filename` must exactly equal the final segment of `relative_path`. Compare Unicode strings by their exact scalar sequence; do not apply NFC/NFD or case normalization. Reject invalid UTF-8/scalar representations rather than replacing characters.
7. `size_bytes` is a non-negative integer. Its field bytes are canonical base-10 ASCII: `0` for zero, otherwise digits with no sign or leading zeroes. Reject fractional, negative, overflowed, or non-integer values.
8. `expected_sha256` is exactly 64 lowercase ASCII hexadecimal characters. Uppercase, prefixes, whitespace, and other encodings are rejected.
9. Sort records by the unsigned lexicographic order of their validated `relative_path` UTF-8 bytes. Reject duplicate relative paths after separator conversion and validation; do not deduplicate.
10. The inventory digest is SHA-256 over the complete byte stream above, represented as 64 lowercase hexadecimal characters. An empty inventory consists of the prefix and an encoded record count of zero, and therefore has a deterministic digest distinct from absent inventory evidence.
11. Since `filename` is the final path segment, including both is intentionally redundant but makes the two report identity fields independently covered by the digest and permits mismatch detection.

Implementation must use explicit UTF-8 encoding, byte comparisons, and explicit big-endian integer encoding. Do not use platform-default encodings, JSON serializer output, locale-sensitive sorting, filesystem timestamps, or file contents as part of this inventory digest.

### Option A3 — hash sorted newline-delimited records

Sort records and hash a UTF-8 line per target with fields separated by tabs or another delimiter.

- Advantages: simple to debug.
- Risks: requires escaping every delimiter/newline and defining final-newline behavior; less robust than length-prefix framing unless rigorously specified.

**Recommendation:** A2, provided the exact field set and path normalization are approved before coding. It avoids dependence on serializer behavior and makes field boundaries unambiguous.

### A2 implementation status (2026-10-22)

PR #156 implemented the approved length-prefixed A2 digest in `Common/RunInputEvidenceIntegrity.py`; exact-head Validate run `39644692787` and Package Validation run `39644693181` passed on `21fa869f222f2b88b7c0ecef20f2313b9ce7c515`, and post-merge Validate run `39644870405` plus Package Validation run `39644870386` passed on `7881fe0f74699dd8aceb1e72e48a4c583c6597cd`. The tests use independent fixed expected digests, rather than deriving expected values from the implementation under test.

### A2 reference vectors (for review and future cross-runtime tests)

These fixed reference vectors define the approved A2 contract. They are not runtime test results by themselves.

- Empty inventory:
  - Byte stream length: 40 bytes.
  - SHA-256: `453b679a83dc6d6b4fe7470294c111d4938547b92c63a6b452cba822138ab17e`
- One-record inventory:
  - Record fields in order: relative path `2026/09/example.txt`, filename `example.txt`, size `0`, expected SHA-256 = 64 ASCII zeroes.
  - Byte stream length: 151 bytes.
  - SHA-256: `85cdc7c9a41c212c7b6c83ccd85813ac4152e7cea9b3092e74e5882fd53cecbd`

Future tests should independently construct these bytes in every supported implementation language and assert both the encoded bytes and digest. The test must not merely call the same production serializer to generate its expected value.

## 2. Decision B — authoritative enumeration and validation-completeness evidence

The manifest's frozen eligible-target list cannot alone prove that initial enumeration was complete or that every relevant invalid/unclassifiable filename was recorded. A derived report must not certify no-work or period completeness without evidence for both the eligible inventory and relevant validation errors.

### Option B1 — trust the process outcome only

Use in-memory enumeration success/failure flags and the generated manifest/report.

- Advantages: few artifacts.
- Risks: cannot independently audit what was enumerated after a crash; absence of an error record is indistinguishable from failure to record it. Not recommended for durable report regeneration.

### Option B2 — immutable run-input evidence sidecar (recommended)

At the start of processing, persist a separate versioned evidence record for the run, before side effects that depend on the inventory. It records:
- run/PC/log-type identity and a unique evidence ID;
- enumeration start/end and an explicit completed/failed result;
- intended source root identity and scope, without secrets;
- number of directory entries observed and number of pages/batches if the source API is paginated;
- eligible-target records or an exact reference plus digest to the frozen eligible inventory;
- all relevant invalid/unclassifiable entries as sanitized structured records;
- validation completion result and counts by classification;
- evidence schema version and integrity digest.

The evidence record is immutable once the run begins processing. If enumeration fails or evidence cannot be durably written/validated, do not classify the run as a valid no-work run and do not certify periods complete. The evidence integrity digest is now normatively specified in `docs/run-input-evidence-v1-proposal.md` §5; the schema still requires implementation and independent vectors. The aggregation report references the exact evidence ID/path and verifies its identity and digest. Regeneration is permitted only from the same manifest plus this preserved evidence; never reconstruct historical completeness by rescanning mutable source directories.

- Advantages: durable audit trail; supports crash-safe regeneration and distinguishes empty source from failed/incomplete enumeration.
- Risks: additional schema, lifecycle, and storage decisions; the evidence must be written safely before the processing run relies on it.

### Option B3 — store completeness fields in the derived report only

Write enumeration and validation evidence directly into the final report.

- Advantages: one artifact.
- Risks: the report is produced after processing; a crash before report publication can lose the only completeness evidence. It does not support regeneration after a crash unless the evidence is separately preserved. Not recommended as the sole evidence source.

**Recommendation:** B2. Keep the manifest v1 schema unchanged, define a small separately versioned evidence artifact, and let the aggregation report reference it. If the evidence artifact cannot be established as immutable and trustworthy, fail closed.

## 3. Decision C — canonical storage and publication scope

### Option C1 — local-only evidence/report

Store sidecar and report under a local maintenance directory.

- Advantages: local atomic file operations are available and do not depend on Drive write semantics.
- Risks: a report is not automatically available to the other PC; PC-local durability and backup need explicit treatment.

### Option C2 — Drive-only evidence/report

Store both under the maintenance folder in Drive.

- Advantages: shared visibility across PCs.
- Risks: local filesystem atomicity assumptions do not apply; object identity, upload verification, and collision handling must be specified separately.

### Option C3 — local authoritative artifacts plus verified Drive copy

Write and validate local immutable artifacts first, then publish a Drive copy using the existing verified-upload discipline. Treat the Drive copy as unavailable until identity/content verification succeeds. Do not let an incomplete Drive copy replace the local authoritative artifact.

- Advantages: local crash-safe publication and cross-PC access after verified replication.
- Risks: two durability states must be modeled, and the report must not imply Drive availability before verification.

**Decision (2026-10-21): C3 approved.** The maintainer selected A: both PCs must be able to access the aggregation report and evidence. Therefore, create and validate immutable authoritative artifacts locally first, then publish verified copies to Google Drive for cross-PC visibility. A Drive copy is not considered available until its identity and content are verified. Local and Drive publication states must be represented separately; failure to replicate must not invalidate or overwrite the local authoritative artifact. This decision does not approve a particular Drive API upload/locking implementation.

## 4. Approval checklist

**Decision (2026-10-21): A2 approved.** The maintainer accepted the versioned length-prefixed record framing, including the four-field order, explicit UTF-8 and big-endian length encoding, path validation rules, byte-order sorting, duplicate rejection, and deterministic empty-inventory digest described above.

Before implementation, explicitly approve or revise each item:

- [x] Digest framing and field set: A2, including both filename and relative path.
- [x] Path syntax/normalization and duplicate-path rejection rules.
- [x] Completeness evidence source: B2 immutable run-input evidence sidecar.
- [x] Evidence sidecar stores full frozen target records (embedded inventory).
- [x] Report/evidence storage: C3 approved — local authoritative artifacts plus verified Drive copies.
- [x] Missing, malformed, conflicting, or not durably published evidence fails closed; no no-work or period-complete certification.
- [x] A report may certify period completion only when the manifest and completeness evidence both validate.

## 5. Acceptance tests required

- Identical inventory produces the same digest across supported runtimes and input ordering.
- Changing any included field changes the digest.
- Duplicate normalized paths, invalid path segments, invalid hashes, and invalid sizes are rejected.
- Empty inventory has a deterministic digest distinct from missing inventory evidence.
- Successful empty enumeration is distinguishable from access failure, interrupted enumeration, and missing evidence.
- Invalid/unclassifiable relevant names are preserved as structured evidence and cannot silently disappear.
- Report generation rejects identity/digest mismatch between report, manifest, and evidence.
- Crash before report publication can regenerate only from immutable validated inputs.
- Missing or incomplete evidence prevents no-work certification and period-complete certification.
- Tests use synthetic fixtures and temporary directories only; no real logs or Drive data.

No runtime implementation, executable tests, or operational evidence is claimed by this proposal.


## Enumeration completion rule — C-41

**Approved option A (2026-10-21):** enumeration is `completed` only after the root and every reached directory have been traversed to normal exhaustion with no enumeration, access, I/O, entry-inspection, or enumerator cleanup/disposal errors. Catch errors raised lazily during iteration; opening an enumerator successfully does not prove completion. On the first such error, stop traversal, record a sanitized diagnostic, increment `enumeration_errors`, and mark the enumeration `failed` or `incomplete` according to the schema. Never skip a failed subtree or certify count reconciliation, a complete inventory, or no-work from incomplete traversal.

Concurrent source mutation is addressed by the approved best-effort detection rule in C-42 below; this is not an atomic snapshot guarantee. This is a specification decision only; executable tests and runtime implementation are not claimed.


## Source mutation detection — C-42

**Approved option A (2026-10-21):** use best-effort change detection, not an atomic filesystem snapshot. Record each traversed directory's observed entry-name/type set and each regular file's relevant metadata (entry type, size, last-write timestamp at supported API precision). After enumeration and eligible-target hash collection, re-enumerate directories and re-check observed file metadata. Calculate eligible-target hashes from the bytes represented by the frozen inventory and reject a read if the target's relevant metadata changes across that read.

Any detected add/remove/rename/type/size/timestamp change, target-set mismatch, or error in the second pass invalidates the evidence; mark enumeration failed/incomplete and do not publish it as completed. Changes that occur and revert between checks or preserve all checked metadata may evade detection, so the implementation must not claim snapshot-level consistency or perfect mutation detection. Executable tests and runtime implementation remain pending.


## Enumeration status semantics — C-43

**Approved option A (2026-10-21):** status is determined by observed outcome.

- `completed`: root and every reached directory reached normal exhaustion and all required C-42 consistency checks passed.
- `failed`: an explicit failure/invalidating condition was observed (including enumeration/access/I/O or entry-inspection errors, unsupported non-regular entry types, detected source mutation, or inconsistent metadata/hash reads).
- `incomplete`: the run ended before completion without an observed failure cause (for example cancellation, timeout, interruption, or process termination), provided a durable evidence record can still be finalized. If no evidence record can be finalized, missing/unfinalized evidence is invalid and must not be synthesized.
- Only `completed` can support no-work or completeness certification. Both other statuses fail closed.

**C-44 is resolved below:** `enumeration_errors` counts distinct underlying error events, with propagated observations counted once and independent failures counted separately. Executable status-transition/interruption tests remain pending; no runtime implementation or test evidence is claimed.


## `enumeration_errors` counting semantics — C-44

**Approved option A (2026-10-21):** count distinct underlying enumeration-error events, not catch sites, log statements, or affected entries.

- The count equals the number of distinct error events represented by unique sanitized diagnostic records. Each event has one stable `error_id`; these errors are not added to the entry-classification totals.
- The same failure propagated through multiple layers is one event and is counted once. Independently observed failures count separately, even if they share a path or error code.
- Do not deduplicate solely by matching error code/path. If event identity is ambiguous, use a documented deterministic correlation rule and test it; do not silently drop a potentially distinct failure.
- Any enumeration-error event prevents `enumeration.status = completed`.

C-45 is resolved by the error-event identity rule below.


## Error-event identity — C-45

**Approved option A (2026-10-21):** assign one event ID when an enumeration failure is first observed and propagate it through subsequent layers. Wrappers must preserve the ID. Repeated observations with the same ID produce one diagnostic event and one count; independent failures receive distinct IDs even when path or code match. Conflicting immutable/core attributes for one ID are an internal consistency error. **Approved C-45 conflict disposition (Option A, 2026-10-21):** fail closed with a fixed, non-disclosing internal-consistency failure and reject finalization/publication of the affected diagnostic evidence artifact. Do not serialize either conflicting variant as valid completed evidence and do not increment the distinct-event count for the conflicting observation. Preserve the first observation only as safe in-memory context; do not mutate historical/published evidence. The run/evidence must remain incomplete or failed under the separately approved run-state contract; this decision does not define a new manifest status. IDs must be unique within the run/evidence artifact. Exact encoding and exhaustion handling are resolved by C-46 below; runtime implementation and acceptance tests are pending.

**C-46 resolved:** the error ID encoding, scope, and collision policy are defined below.


## `error_id` format and collision handling — C-46

**Approved option A (2026-10-21):** use a per-run monotonic sequence formatted as `ERR-000001`, `ERR-000002`, and so on. Allocate once when a distinct error event is first created and preserve that ID through all subsequent layers. IDs must not be reused within one run/evidence artifact. For cross-run identification, combine the run identifier with `error_id`; the ID alone is not globally unique. If the sequence range is exhausted, fail closed rather than wrap, reuse, or truncate an ID. Executable tests and runtime implementation remain pending.

**C-47 resolved:** diagnostic fields, nullability, and sanitization rules are defined below.


## Diagnostic record schema and sanitization — C-47

**Approved option A (2026-10-21; canonical field contract):** each diagnostic has required keys `error_id`, `error_code`, `phase`, `operation`, `target_relative_path`, and `message`. `error_id`, `error_code`, `phase`, and `operation` are non-null; `target_relative_path` and `message` may be explicit JSON `null` when no safe value exists. Non-null paths use normalized `/` separators, are relative to the configured source root, and cannot contain absolute roots, drive letters, UNC roots, or traversal outside that root. A non-null path is limited to 1024 Unicode scalar values after separator normalization; a longer path is unsafe and must be emitted as JSON `null` without truncation. A non-null message is a sanitized summary limited to 512 Unicode characters; redact credentials, tokens, connection strings, secret-bearing query parameters, personal data, absolute paths, and control characters. Never serialize raw exception objects, raw exception text, stack traces, environment variables, request/response bodies, or arbitrary metadata. Do not silently truncate required identifiers. If a required non-null field cannot be safely populated, fail evidence finalization closed rather than emit a malformed record. Count distinct events by unique `error_id`. Executable schema and sanitization tests remain pending.

**C-49 approved:** the diagnostic vocabularies are fixed allowlists with reserved unknown values as specified below. C-50 mapping rules are recorded below.


### Diagnostic schema versioning and compatibility — C-48

**Approved option A (2026-10-21):** each diagnostic record must contain an explicit positive integer `schema_version`. Validators accept only versions for which an exact validator is implemented. Missing, malformed, non-integer, non-positive, or unsupported versions are rejected; unknown fields are rejected rather than ignored.

- The meaning, required keys, types, nullability, field constraints, allowed values, and sanitization semantics of each released version are immutable.
- Any change that makes an existing record structurally or semantically incompatible requires a new integer schema version. Because unknown fields are rejected, adding a field is also a schema-version change.
- Never silently migrate, rewrite, repair, or relabel historical evidence. A validator may read an older version only when an explicit version-specific validator remains implemented; validation must not mutate the record.
- The containing run-input evidence keeps its separate `evidence_schema_version`; the diagnostic record's `schema_version` governs only the diagnostic object. Version values must not be inferred from one another.
- Reject duplicate/unknown properties and validate the complete record against the exact selected version before counting the diagnostic as valid evidence.
- Required tests: valid supported version; missing, null, string, fractional, zero, negative, and unsupported versions; unknown fields; missing/extra fields; per-version type/nullability constraints; no implicit migration or mutation; old-version acceptance only while its explicit validator exists.

Runtime implementation and executable tests remain pending.

**C-49 approved:** the diagnostic vocabularies are fixed allowlists with reserved unknown values as specified below. C-50 mapping rules are recorded below.


### Diagnostic controlled vocabularies — C-49

**Approved option A (2026-10-21):** `error_code`, `phase`, and `operation` are restricted to the fixed allowlists below. Unrecognized failure types map to `unknown_error`; an unidentifiable phase or operation maps to `unknown`. Raw exception class names and exception messages must never be used as enum values.

**Initial diagnostic schema v1 allowlists**

- `error_code`: `enumeration_failed`, `invalid_filename`, `file_access_denied`, `file_read_failed`, `file_metadata_failed`, `hash_failed`, `source_mutation_detected`, `manifest_invalid`, `evidence_invalid`, `validation_failed`, `serialization_failed`, `aggregation_failed`, `publication_failed`, `unknown_error`.
- `phase`: `enumeration`, `classification`, `metadata`, `content_read`, `hashing`, `manifest_validation`, `evidence_validation`, `evidence_finalization`, `aggregation`, `report_serialization`, `report_publication`, `unknown`.
- `operation`: `enumerate_entries`, `classify_target`, `read_metadata`, `read_content`, `compute_hash`, `detect_source_mutation`, `validate_manifest`, `validate_evidence`, `finalize_evidence`, `aggregate_results`, `serialize_report`, `publish_report`, `unknown`.

Values are exact, case-sensitive identifiers; no aliases, whitespace normalization, dynamic enum extension, or free-form values are accepted. An implementation must map known failures to the most specific applicable code and use `unknown_error` only when no known code applies. The `unknown` phase/operation values indicate that the context genuinely cannot be determined; they must not conceal a known mapping defect. Adding an allowlist value requires a reviewed schema/contract update and corresponding positive/negative tests. A change that alters the schema contract follows C-48 versioning rules.

**Required tests:** every listed value accepted; unlisted values, case variants, empty strings, and null rejected for these non-null fields; known failures map deterministically to specific codes; unmapped failures map to `unknown_error`; genuinely unknown phase/operation map to `unknown`; exception text/class names are never emitted as values.

Runtime implementation and executable tests remain pending.

**C-50 approved:** the deterministic failure-condition mapping and precedence rules are defined below. **C-51 approved:** the deterministic phase/operation mapping and fallback rules are defined below. **Next decision C-52:** define diagnostic message template selection and sanitization behavior for each known error category.


### Deterministic failure-condition mapping and precedence — C-50

**Approved option A (2026-10-21):** map each distinct failure event to exactly one primary `error_code` using explicit conditions and precedence. Use only the C-49 schema-v1 allowlist. The mapping is based on structured operation context, validation result, and stable platform error categories—not exception-message text or raw exception class names.

| Priority | Observable condition | `error_code` | Classification rule |
|---:|---|---|---|
| 1 | A manifest is readable but fails its defined syntax, schema, identity, or integrity validation | `manifest_invalid` | Use only for invalid manifest content; access/read failures use the more specific I/O rules below. |
| 2 | Run-input evidence is readable but fails its defined schema, identity, inventory, count, or integrity validation | `evidence_invalid` | Use only for invalid evidence content; access/read failures use the more specific I/O rules below. |
| 3 | A source entry or frozen target set changes during the approved consistency checks, or the before/after metadata or target identity does not reconcile | `source_mutation_detected` | Requires an observed mismatch; do not infer mutation merely from an unrelated read error. |
| 4 | A filename violates the documented naming/period/eligibility syntax | `invalid_filename` | Apply during classification before attempting target-content processing. Preserve the invalid entry in validation evidence. |
| 5 | The platform reports an explicit access-denied/permission-denied condition for the attempted operation | `file_access_denied` | Use only when the platform provides a structured access-denied signal; do not infer from free-form message text. |
| 6 | Opening or enumerating the configured source root or a reached directory fails for a reason other than explicit access denial | `enumeration_failed` | Includes iteration failure, interrupted directory enumeration reported as an operation failure, and enumerator cleanup/disposal failure. |
| 7 | Required file metadata cannot be retrieved or validated before content reading, without a more specific access-denied or mutation classification | `file_metadata_failed` | Includes inability to obtain required type/size/timestamp metadata. |
| 8 | Reading file content fails before hashing can complete, without a more specific access-denied or mutation classification | `file_read_failed` | Do not classify a hash-algorithm/computation failure as a content-read failure when reading completed. |
| 9 | Hash computation fails after the intended content bytes have been read, or the hash operation itself reports failure | `hash_failed` | A content-read failure takes precedence when bytes could not be read. |
| 10 | A report/evidence/manifest object fails a general validation rule not covered by the specific manifest/evidence categories above | `validation_failed` | Use only for other explicit contract validation failures; do not use as a catch-all for operational failures. |
| 11 | Deterministic serialization of a validated report/evidence object fails | `serialization_failed` | Distinguish serialization from the later write/publish step. |
| 12 | Deriving period summaries/counts or reconciling validated inputs into the aggregation model fails | `aggregation_failed` | Use for aggregation logic failures, not invalid input artifacts already classified above. |
| 13 | Writing or publishing the final report artifact fails after successful aggregation/serialization | `publication_failed` | Includes final local publication or verified Drive-copy publication; preserve local authoritative artifacts when possible. |
| 14 | A failure is observed but no preceding condition matches deterministically | `unknown_error` | Required fallback. Do not guess from exception text; retain only sanitized context permitted by C-47. |

**Precedence and event rules**

1. Evaluate the table from top to bottom and select the first condition whose required evidence is present. The table priority resolves overlapping descriptions.
2. An explicit access-denied signal is classified as `file_access_denied` for the affected operation, except when the failure is actually a readable-but-invalid manifest/evidence validation result or an independently observed source-mutation mismatch. A failure to open/read an artifact is not a content-validation failure.
3. Assign one primary `error_code` per distinct `error_id`. The same event propagated through layers retains its original code and ID; downstream wrappers must not reclassify it. An independently observed failure gets a new ID and is classified separately.
4. When multiple independent failures are observed, classify each event independently; do not collapse events merely because they share a path or code. A single event must not be double-counted under multiple codes.
5. Mapping must use structured context and stable error categories. Do not parse localized/free-form exception messages to choose a code. Do not include raw exception text in diagnostic enum values or sanitized messages.
6. If a known failure cannot be distinguished reliably from another category using available structured evidence, use `unknown_error` rather than making an unsupported inference. `unknown_error` must not conceal a known mapping defect.
7. The mapping table and precedence are normative for diagnostic schema v1. Changing the allowlist, field contract, or versioned semantics requires review under C-48; never silently reinterpret historical diagnostics.

**Required tests:** one positive fixture for each mapping row; access-denied versus generic I/O; invalid filename before content access; read failure versus hash failure; readable-invalid manifest/evidence versus unreadable artifact; mutation versus ordinary read failure; serialization versus publication failure; overlapping-condition precedence; same-event propagation preserves original code and ID; independent events remain distinct; unknown condition falls back to `unknown_error`; mapping never inspects free-form exception text; every emitted code is in the C-49 allowlist.

Runtime implementation and executable tests remain pending; this decision defines the contract only.



**Runtime input contract — approved model A:** the trusted event producer supplies exactly one required, case-sensitive scalar Condition identifier when the distinct event is first created. The pure classifier Resolve-DiagnosticErrorCode maps that identifier to exactly one C-49 error_code; it does not inspect exception messages/classes, stack traces, paths, or arbitrary metadata, and does not allocate or modify error_id, phase, or operation. Producer-side selection must follow the priority table above when more than one condition could apply. Propagation layers preserve the first event's identity and classification and must not call the classifier again for that event.

| Exact Condition identifier | Required structured evidence | error_code |
|---|---|---|
| manifest_readable_invalid | Manifest read completed; syntax/schema/identity/integrity validation failed | manifest_invalid |
| evidence_readable_invalid | Evidence read completed; schema/identity/inventory/count/integrity validation failed | evidence_invalid |
| source_mutation_observed | Approved before/after identity or metadata comparison observed a mismatch | source_mutation_detected |
| target_filename_invalid | Strict filename/date/period/eligibility validation failed | invalid_filename |
| access_denied_observed | Platform/API supplied an explicit structured access-denied result | file_access_denied |
| directory_enumeration_failed | Root/reached-directory enumeration failed, without a more specific condition above | enumeration_failed |
| target_metadata_failed | Required metadata retrieval/validation failed before content read | file_metadata_failed |
| target_content_read_failed | Intended content bytes could not be read before hashing completed | file_read_failed |
| content_digest_failed | Intended bytes were available but digest computation failed | hash_failed |
| general_contract_validation_failed | Explicit contract validation failed outside the manifest/evidence-specific cases | validation_failed |
| report_serialization_failed | Serialization of a validated report/evidence object failed | serialization_failed |
| aggregation_failed | Summary/count/reconciliation derivation failed after input validation | aggregation_failed |
| report_publication_failed | Final report writing/publication failed after successful aggregation/serialization | publication_failed |
| unmatched_failure | A real failure was observed but no listed condition applies | unknown_error |

These condition identifiers are internal call-contract values, not persisted schema fields or new error_code values. Input must be a scalar string matching one exact token. Null, empty, non-string, unknown, collection-shaped, or case-variant inputs are rejected with a fixed non-disclosing error; they do not silently map to unknown_error. unmatched_failure is reserved for a real observed failure with no matching known condition, not missing instrumentation or malformed classifier input.

**Evidence boundary:** this pure mapping helper verifies only token-to-code mapping. It does not prove event-producer correctness, precedence selection across multiple observations, event-ID propagation/deduplication, runtime sink behavior, or end-to-end evidence finalization. Those remain runtime acceptance gaps.

### Deterministic phase and operation mapping — C-51

**Approved option A (2026-10-21):** derive phase and operation from the explicit processing context at the point the diagnostic event is first created. Use the following normative mapping table. The pair describes the operation that failed, not merely the layer that later observed or logged the failure.

| Processing context / failed action | phase | operation |
|---|---|---|
| Enumerating the source root or traversing a reached directory | enumeration | enumerate_entries |
| Parsing/classifying a target filename or determining its period/eligibility | classification | classify_target |
| Reading required file metadata (type, size, timestamp) | metadata | read_metadata |
| Opening/reading target file content | content_read | read_content |
| Computing the content digest after bytes are available | hashing | compute_hash |
| Comparing frozen inventory/metadata/identity to detect source changes | metadata | detect_source_mutation |
| Validating manifest syntax, schema, identity, or integrity | manifest_validation | validate_manifest |
| Validating run-input evidence schema, inventory, counts, or integrity | evidence_validation | validate_evidence |
| Finalizing and validating the completed diagnostic/evidence object | evidence_finalization | finalize_evidence |
| Deriving summaries, counts, and reconciliations from validated inputs | aggregation | aggregate_results |
| Serializing a validated report into its canonical output representation | report_serialization | serialize_report |
| Writing/publishing the final report artifact or verifying its published copy | report_publication | publish_report |
| The actual processing context cannot be established from trusted structured state | unknown | unknown |

**Selection and propagation rules**

1. Capture the phase/operation pair from structured state when the underlying event is first converted into a diagnostic. The event creator assigns the pair together with error_id and error_code.
2. Propagation, wrapping, retry reporting, cleanup, and logging layers preserve the original pair. They must not replace it with their own context simply because they observe the same event later.
3. Select the most specific table row matching the failed action. For example, a manifest that is read successfully but fails contract validation uses manifest_validation / validate_manifest; a failure to read content uses the applicable read operation/context.
4. Use unknown only when trusted structured context genuinely cannot identify the phase or operation. Do not use it as a shortcut for missing instrumentation, an unimplemented mapping, or an avoidable ambiguity.
5. The phase and operation are independent controlled values but must form a semantically valid pair under this table. Reject combinations not defined by the schema-v1 mapping contract rather than normalizing aliases or inferring values from exception messages.
6. No new fields or allowlist values are introduced. The contract remains within C-48/C-49 diagnostic schema v1. Any future change to the mapping semantics requires review and explicit versioning assessment.

**Required tests:** positive fixture for every row; each allowlisted phase/operation appears in valid fixtures; invalid pair rejection; same-event propagation preserves the original pair across wrappers/cleanup/logging; operation failure is distinguished from later observer context; manifest/evidence read failure versus validation failure; genuinely unavailable context maps to unknown/unknown; missing instrumentation is surfaced by tests rather than silently accepted; no free-form exception parsing; deterministic repeated results.

**Approved input contract — Option C (2026-10-21):** the trusted producer supplies exactly one required, case-sensitive scalar `operation` identifier from the existing C-51 operation allowlist when the distinct diagnostic event is first created. `Resolve-DiagnosticPhaseOperation -Operation` derives the unique approved `phase` and returns the exact input operation unchanged. It does not allocate `error_id`, classify `error_code`, inspect exception messages/classes, stack traces, paths, or ambient observer context, or create/propagate runtime events.

Accepted values are exactly the operation column in the table above: `enumerate_entries`, `classify_target`, `read_metadata`, `read_content`, `compute_hash`, `detect_source_mutation`, `validate_manifest`, `validate_evidence`, `finalize_evidence`, `aggregate_results`, `serialize_report`, `publish_report`, and `unknown`. The `unknown` value is reserved for a trusted producer that has positively established that the actual failed processing context cannot be determined from trusted structured state. Missing instrumentation, missing input, invalid input, or an unimplemented mapping must be rejected, not converted to `unknown`. The resolver can validate the token and derive its pair; it cannot independently prove the producer selected the semantically correct operation.

The pure resolver and synthetic table-driven tests are implemented in `Common/LogFunctions.ps1` and `tests/Test-DiagnosticPhaseOperationResolver.ps1`, and are wired into Validate CI. This helper-level evidence does not implement runtime event creation, precedence enforcement, event identity propagation/deduplication, raw JSON duplicate-key rejection, sink non-disclosure, or end-to-end acceptance.


### Diagnostic message templates and sanitization — C-52

**Approved option A (2026-10-21):** use fixed, deterministic message templates selected by the validated `error_code`. Do not include raw exception messages, exception class names, stack traces, OS-provided error text, environment variables, request/response bodies, credentials, tokens, connection strings, absolute paths, or other uncontrolled data. Initial schema-v1 templates have no interpolated parameters; safe target context, when useful, belongs only in the separately validated `target_relative_path` field.

| `error_code` | Normative `message` template |
|---|---|
| `enumeration_failed` | `Source enumeration failed.` |
| `invalid_filename` | `Target filename does not satisfy the naming rules.` |
| `file_access_denied` | `Access to the target entry was denied.` |
| `file_read_failed` | `Target file content could not be read.` |
| `file_metadata_failed` | `Required target metadata could not be read.` |
| `hash_failed` | `Target content digest could not be computed.` |
| `source_mutation_detected` | `Source entry changed during inventory validation.` |
| `manifest_invalid` | `Manifest validation failed.` |
| `evidence_invalid` | `Run-input evidence validation failed.` |
| `validation_failed` | `Input contract validation failed.` |
| `serialization_failed` | `Report serialization failed.` |
| `aggregation_failed` | `Aggregation failed.` |
| `publication_failed` | `Report publication failed.` |
| `unknown_error` | `An unclassified processing error occurred.` |

**Normative rules**

1. The selected template is determined solely by the already validated `error_code`; message generation must not inspect exception text or other free-form diagnostic data.
2. Templates are fixed English ASCII strings in schema v1. They are below the C-47 maximum of 512 Unicode characters and are emitted exactly as specified, with no locale-dependent changes, dynamic interpolation, trimming, or punctuation variation.
3. If a future requirement needs a parameter, it requires an explicit reviewed contract update that defines the parameter's source, type, maximum length, character policy, sanitization order, and fallback. Parameters must come from trusted structured state and a field-specific allowlist; raw exception-derived text is never an allowed parameter. Do not add parameters implicitly.
4. If a template cannot be selected because the `error_code` is missing or invalid, reject diagnostic finalization; do not guess a template from exception data. If a validated code is `unknown_error`, use its exact generic template above.
5. Apply the C-47 record-level constraints as well: valid UTF-8/scalar sequence, control-character safety, no raw exception object/stack trace, and message length at most 512 Unicode characters. These fixed templates inherently satisfy the length bound.
6. Keep the message field present according to the diagnostic schema. A valid `error_code` always has a non-null template message; do not substitute JSON null for a template that is defined here. If the record cannot be finalized safely, fail evidence finalization rather than emitting a malformed diagnostic.
7. Do not change `error_code`, `phase`, `operation`, or the event's `error_id` to make the message fit. Message content is descriptive only and is not an input to classification, deduplication, aggregation, or integrity decisions.

**Required tests:** one exact expected-message fixture for every C-49 `error_code`; unknown-code rejection before message generation; `unknown_error` template; deterministic byte-for-byte output across repeated runs and locale settings; no interpolation; maximum length; control/secret/absolute-path/stack-trace/exception-text non-disclosure; valid UTF-8; message never influences code, event identity, or aggregation; invalid message-generation context fails finalization rather than emitting null or malformed output.

Runtime implementation and executable tests remain pending; this decision defines the contract only.


### Structured-field sanitization and path safety — C-53

**Approved option A (2026-10-21):** validate structured values before emission; never repair a dangerous path into a different apparently valid path. If `target_relative_path` cannot be proven safe under this contract, emit JSON `null` for that field while retaining the diagnostic event and its stable classification fields.

**Normative processing order for `target_relative_path`:**

1. Read the value only from trusted structured state. If absent, null, not a string, or not valid Unicode scalar text, emit `null`.
2. Create a validation-only candidate by translating backslash separators to forward slashes. Do not collapse repeated separators, remove dot segments, trim characters, or resolve the path against the current directory; those operations could conceal unsafe input.
3. Reject the candidate if it is empty; begins with `/`; has a drive prefix (for example, `C:`); has a UNC/device-path prefix; contains a NUL or any control character; contains a colon (including alternate-data-stream syntax); contains an empty segment, `.`, or `..` segment; or otherwise fails the defined relative-path grammar. On rejection, emit `null` for the entire field.
4. Check each segment and the complete candidate against the project's explicit sensitive-path policy. This includes credential/token-like material and configured sensitive names/patterns. Do not infer safety merely because a value is syntactically relative. If any segment or the full candidate matches a sensitive rule, emit `null` for the entire field; do not partially redact or replace segments.
5. Only if every check passes, emit the canonical candidate with `/` separators. Do not resolve symlinks, query the filesystem, or use the current working directory during diagnostic serialization.

**Other structured fields:**

- `error_id`, `error_code`, `phase`, and `operation` must pass their schema and allowlist validators. Invalid values reject diagnostic finalization; do not sanitize an invalid enum into a nearby allowed value.
- `message` is selected solely from the exact C-52 template table. Do not interpolate path, exception, or other runtime values.
- JSON output must use the serializer's correct string escaping. Escaping is not a substitute for validation or sensitive-data checks.
- Sanitization must not alter event identity, classification, phase/operation, aggregation results, or source artifacts. An unsafe optional path becomes `null`; an invalid required field fails finalization.
- The validation result must be deterministic and independent of locale, machine-specific path rules, current directory, and filesystem state.

**Required tests:** null/non-string/invalid-Unicode path input; slash and backslash handling; leading slash; drive-qualified, UNC, and device paths; colon/alternate-data-stream; NUL and control characters; empty/repeated segments; `.` and `..` segments; sensitive-pattern match in first/middle/last segment; no partial redaction; valid canonical relative path; no filesystem or current-directory dependency; serializer escaping; invalid required enum rejection; unsafe optional path becomes JSON null without changing error identity/classification; deterministic results across locale and host OS settings.

The sensitive-path policy's concrete pattern/segment rules and precedence are approved under C-54; see `docs/decision-record-c54-sensitive-path-detection.md`. Runtime implementation and executable tests remain pending; this decision defines the contract only.


### C-54 — Approved sensitive-path pattern grammars (P1–P6, 2026-10-21)

The maintainer approved option A for each P1–P6. The exact normative grammars, case rules, ASCII boundaries, scope limits, and C-53 processing-order caveat are defined in `docs/decision-record-c54-sensitive-path-detection.md`, section “C-54 approved secret-format grammars — P1–P6”. That decision record is the single canonical source for regex text; do not duplicate or independently reinterpret those expressions here.

The required pattern-contract tests are `tests/Test-C54PatternContract.ps1`, run by the Validate workflow. They use synthetic fixtures and verify the approved regex rules only. They are not runtime sanitizer tests. Runtime sanitization and end-to-end diagnostic non-disclosure remain unimplemented/unverified; this approval does not close P0-010 or P0-012.


## OSD-03 approved report-contract compatibility note (2026-10-21)

R1-B/R2-A/R3-B/R4-A/R5-A/R6-A/R7-A are approved. The report contains period summaries only and references the exact manifest and B2 evidence by canonical relative path, schema version, and SHA-256 of exact bytes. Report identity is (pc_id, log_type, run_id, report_schema_version), with no report_id field. Deterministic regeneration uses only immutable validated inputs; it must not re-enumerate mutable source directories. Period completion is complete/incomplete/indeterminate and remains report-only, not a manifest v1 enum. Local publication is authoritative; Drive replication is separate and must be content-verified before cross-PC use. These decisions do not alter manifest v1, B2 evidence structure, A2 inventory digest, or exhaustive count reconciliation. Executable schema, runtime implementation, and tests remain pending.
