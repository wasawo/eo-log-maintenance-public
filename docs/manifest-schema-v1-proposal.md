# Maintenance Manifest Schema v1 — Approved Field Specification

- Status: approved field names, types, enums, nullability, and field-level constraints are encoded in the strict Draft 2020-12 structural schema `contracts/manifest-v1.schema.json`; synthetic structural contract tests are in `tests/test_contract_schemas.py`. Runtime file/filename identity binding, cross-artifact checks, timestamp policy enforcement, state transitions, locking, and archive authorization remain unimplemented/unverified.
- Related decision: OSD-02 / C-26.
- Scope: operational synchronization manifest fields only. This is not the Drive adapter request/response schema.

## 1. Design principles

1. Keep run identity, run outcome, per-file result, and Drive content-verification evidence in one manifest.
2. Record immutable facts needed to correlate a run and its files; do not duplicate verbose operational logs.
3. A manifest is untrusted input. Schema validity is necessary but never sufficient for archive authorization.
4. Archive processing must re-query/re-verify current Drive state independently; a stored Drive ID or previous verification result is not a permanent authorization.
5. schema_version is the required integer 1. Missing, malformed, or unsupported versions are rejected. No implicit migration or rewrite is allowed.
6. This proposal does not approve the complete transition table, freshness threshold, clock-skew policy, run/period aggregation, or stale-running recovery policy.

## 2. Proposed run-level fields

| Field | Required | Proposed type / constraint | Meaning |
|---|---:|---|---|
| schema_version | Yes | integer; exactly 1 | Manifest format version |
| run_id | Yes | UUID string | Unique identifier for one execution on one PC |
| pc_id | Yes | enum: PC-A, PC-B | Originating PC |
| log_type | Yes | enum: BattleLog, ErrorReport | Log category |
| target_period | Yes | YYYY-MM for BattleLog; YYYY for ErrorReport | Filename-derived period being reported |
| status | Yes | enum: running, success, partial_failure, failure | Run status already named in lifecycle specification |
| outcome | Yes | null or enum containing no_work | Distinguishes a successful zero-target run |
| started_at_utc | Yes | UTC timestamp string ending in Z | Run start time |
| finished_at_utc | Yes | UTC timestamp string ending in Z, or null | Finalization time; proposed null while status is running |
| files | Yes | array of per-file records; may be empty | Frozen target inventory and per-file result records |

### Run-level consistency constraints proposed for review

- The filename identity <PC-ID>_<LogType>_<TargetPeriod>_<run_id>.json must agree with the corresponding JSON fields.
- target_period must follow the pattern for log_type; it is derived from validated filename dates, never LastWriteTime.
- outcome: no_work is only for a successful zero-work run. Other outcomes remain unspecified until the aggregation decision is approved; do not invent additional outcome strings.
- started_at_utc and finished_at_utc use UTC (Z). A timestamp being syntactically valid does not establish freshness or authorize archive.
- Full temporal constraints (future timestamps, freshness threshold, clock skew, ordering tolerance) remain blocked by EOLM-MAN-011.
- The proposed status/time consistency rule (running => finished_at_utc: null; terminal status => non-null finish time) needs approval with the state-transition table.

## 3. Proposed per-file fields

| Field | Required | Proposed type / constraint | Meaning |
|---|---:|---|---|
| relative_path | Yes | non-empty normalized relative path | Source-relative path; must not be absolute or escape the configured source root |
| filename | Yes | non-empty basename | Original filename used for period classification |
| size_bytes | Yes | integer >= 0 | Frozen source size |
| sha256 | Yes | 64 hexadecimal characters | Frozen source content hash |
| status | Yes | enum: staging, ready, pending, uploaded, verified, failed, unknown | Per-file lifecycle state already named in the staging lifecycle |
| drive_file_id | Yes | non-empty string or null | Stable Drive object ID when identified; null before identification or when not established |
| verification | Yes | object | Explicit record of Drive content-verification result |

### Proposed verification object

| Field | Required | Proposed type / constraint | Meaning |
|---|---:|---|---|
| status | Yes | enum: not_checked, verified, mismatch, unavailable, ambiguous, failed | Result of the most recent explicit content-verification attempt |
| method | Yes | enum: not_performed, drive_sha256, download_sha256 | Method actually used to obtain the observed content hash; `not_performed` when no observed hash was obtained |
| checked_at_utc | Yes | UTC timestamp string ending in Z, or null | Time of verification; null if not checked |
| observed_sha256 | Yes | 64-hex string or null | Observed Drive content hash where available |

### Per-file constraints proposed for review

- sha256 is the expected local source hash. verification.observed_sha256 is the observed cloud content hash; these must not be conflated.
- drive_file_id identifies a Drive object but does not prove its contents or provenance.
- A verified verification status requires a real content-verification method; metadata-only lookup is not sufficient.
- The maintainer approved the following exhaustive status/method/time/hash combinations on 2026-10-21; any combination outside this table is invalid and must be rejected:

  | `verification.status` | `verification.method` | `checked_at_utc` | `observed_sha256` |
  |---|---|---|---|
  | `not_checked` | `not_performed` | null | null |
  | `verified` | `drive_sha256` or `download_sha256` | required UTC timestamp | required valid 64-hex hash |
  | `mismatch` | `drive_sha256` or `download_sha256` | required UTC timestamp | required valid 64-hex hash |
  | `unavailable`, `ambiguous`, or `failed` when no observed content hash was obtained | `not_performed` | required UTC attempt timestamp | null |

- `method` records the method that actually produced an observed content hash, not merely the method that was attempted. If an operation fails before a hash is obtained, do not claim `drive_sha256` or `download_sha256` as the method.
- For `unavailable`, `ambiguous`, or `failed`, `checked_at_utc` records the attempt time even when no hash was obtained. The detailed attempted method, sanitized error, and retry-by-retry diagnostics belong in operational logs, not in this manifest field set.
- Do not place an arbitrary candidate hash in `observed_sha256` when the candidate identity is ambiguous. Without one established observed hash, use `not_performed` and null hash.
- `mismatch` means an observed hash was obtained and differs from the expected source hash. A missing hash cannot be classified as `mismatch`.
- `mismatch`, `unavailable`, `ambiguous`, or `failed` must not authorize success or archive. Interactions with file/run status are governed by the approved mapping and still-open aggregation rules.
- Error details, retry-by-retry history, verbose logs, and local staging paths are intentionally not included in this minimum proposal. They belong in sanitized operational logs unless a separate requirement establishes that durable manifest storage is necessary.

## 4. Validation and compatibility

- Reject malformed JSON, unknown fields, missing required fields, wrong types, invalid enums, invalid hashes, invalid identity, invalid period formats, absolute/traversing relative paths, and unsupported schema versions.
- Validate filename identity against JSON identity before selecting a latest manifest.
- Do not infer a missing field, default a malformed value, or silently migrate older manifests.
- Write updates through a temporary file, re-read and validate the result, then replace the official local manifest where atomic replacement is supported.
- A crash-left running manifest remains incomplete. This proposal does not define an automatic transition to failure.
- Latest-manifest selection and archive authorization remain separate from schema validation. A valid manifest cannot bypass the current Drive re-verification gate.

## 5. Decisions still required

This field specification records the maintainer's approval of the listed field names, types, enums, nullability, and field-level constraints on 2026-10-21. This approval does not close OSD-02. The following remain open:

1. Exhaustive allowed/forbidden transitions for file and run states, including remaining transition rules beyond the approved run-level status/time constraint.
2. outcome values and run/period aggregation (coordinate with OSD-03); do not invent additional outcome values.
3. Concrete configuration values and application contexts for timestamp freshness, allowed future-time tolerance, and clock-skew (EOLM-MAN-011); policy shape is approved, numeric values remain open.
4. Runtime implementation and executable validation evidence.
5. Numeric timestamp freshness/future-time tolerance configuration and exact contexts of applicability.
5. Runtime validator, transition acceptance tests, and operational evidence remain outstanding. The executable structural schema and synthetic schema-negative tests now exist; they do not establish runtime enforcement.

The run-level status/time consistency rule approved on 2026-10-21 is normative: `running` requires `finished_at_utc: null`; terminal statuses (`success`, `partial_failure`, `failure`) require non-null `finished_at_utc`. `started_at_utc` is required in every run state. Timestamp validation policy shape approved on 2026-10-21: require UTC ISO 8601 timestamps; reject finish-before-start; use configurable future-time/clock-skew tolerance and context-appropriate freshness thresholds. Numeric values and exact application contexts remain open. No runtime implementation or operational evidence is claimed.

## Approved crash, concurrency, and latest-manifest policy shape — 2026-10-21

- A candidate manifest must pass structural validation, including consistency between its filename identity and the identity recorded inside the JSON, before it can be considered current.
- Timestamp alone must not select a unique latest manifest when candidates collide or remain indistinguishable. Treat the selection as ambiguous and stop the dependent operation rather than choosing arbitrarily.
- Detect concurrent updates to the same target. Do not overwrite state using a stale read; re-read and re-validate or fail safely.
- A crash-left `running` manifest remains unfinished and must not be silently rewritten to `success` or `failure`.
- Until remote state can be re-established and verified, do not authorize archive or deletion.
- **Still open:** concrete atomicity/locking mechanism, identity fields and filename convention used for correlation, stale-run recovery procedure, and executable tests. This policy-shape approval does not claim runtime support.


## OSD-03 aggregation contract and representation gate — 2026-10-21

The run/period aggregation policy shape is approved. Run-level status must follow `docs/osd-03-status-aggregation-options.md`: `success` requires every eligible target to be verified with no relevant error; verified zero-work requires successful enumeration and validation and uses `outcome: no_work`; verified work combined with unresolved eligible-file failure/unknown or an unclassifiable run-scope error yields `partial_failure`; no verified eligible work with a processing/validation failure or inability to establish valid no-work yields `failure`. Period completion requires all eligible targets in the period to be verified and no relevant error affecting that period. Unclassifiable files remain run-scope errors and must not be assigned by timestamp fallback.

**Approved schema boundary (2026-10-21):** keep the approved manifest v1 field set unchanged. Period summaries and unassigned run-scope validation errors must be recorded in a separate, durable derived aggregation report, not added to the manifest. The report must be linked to the originating `run_id` and validated against the frozen eligible inventory; missing, malformed, stale, or inconsistent report data must not certify period completion. The proposed report contract is documented in `docs/aggregation-report-v1-proposal.md`; its schema and operational rules remain unapproved pending the decisions and tests listed there. This decision does not authorize new manifest fields or close OSD-02/OSD-03.


## Timestamp validation policy cross-reference — 2026-10-21

The maintainer separately approved timestamp/freshness policy: UTC ISO 8601 with uppercase `Z`; malformed, offset-form, timezone-less, and unparseable timestamps are rejected; finish must not precede start. Initial configurable defaults are 5 minutes of future-time tolerance and 24 hours for freshness. Freshness applies only to timestamps generated/updated during the current execution; historical manifest age alone does not invalidate history. Host OS time synchronization is assumed configured; if current UTC cannot be obtained reliably, time-dependent operations fail closed. This cross-reference does not make schema validation executable or claim runtime support.
