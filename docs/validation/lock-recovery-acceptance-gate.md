# Lock Ownership and Crash-Recovery Acceptance Gate

- Status: implementation gate / non-normative acceptance contract.
- Date: 2026-10-22.
- Related approved policy: OSD-02 crash/concurrency/latest-manifest decision (C1-A, C2-C, C3-B, C4-A), `docs/design/staging-file-lifecycle.md`, and `docs/design/runtime-entrypoint-validation-gate.md`.
- This document does not authorize runtime integration, Drive operations, archive, or deletion.

## 1. Purpose

Define a testable boundary for the next lock/recovery implementation slice. The gate must be satisfied before any official sync/archive entry point can acquire a lock, recover an interrupted run, publish authoritative manifests, or perform remote side effects.

## 2. Required ownership model

1. Acquire one OS named mutex per local maintenance scope; PC-A and PC-B use independent scopes.
2. Pair the mutex with an exclusive lock record containing a cryptographically random ownership token and the minimum identity/diagnostic fields required by the approved lock schema.
3. The process may mutate or remove the lock record only while it can prove ownership of both the mutex and the matching token. A PID, timestamp, lock age, or host name alone is never proof of ownership.
4. Wait/retry for at most 60 seconds. If acquisition cannot be established, exit before target enumeration, manifest writes, staging changes, Drive calls, archive, or deletion.
5. If the OS reports an abandoned mutex, treat this as evidence of prior abnormal termination, not proof that arbitrary lock-record content is safe to remove. Validate the record and prior-run state before proceeding.
6. If ownership is mismatched, the lock record is malformed, or lock state cannot be established, fail closed and preserve the record and operational artifacts for diagnosis.
7. Never forcibly terminate a process, steal a live lock, or remove a lock based only on age/PID.

## 3. Lock lifecycle and cleanup

- The ownership token is generated for each acquisition attempt and is not reused across runs.
- Create the lock record with exclusive create-if-absent semantics. A pre-check followed by an ordinary write is insufficient.
- Lock-record updates must use validated temporary-file publication and compare-before-replace semantics; they must not overwrite a record owned by another token.
- Normal release requires verifying that the on-disk token still matches the current owner token, removing only that owner's record, then releasing the mutex in a finally-style path.
- If release or cleanup fails, do not erase another owner's record; emit a sanitized diagnostic and leave state for explicit recovery.
- Lock-record schema/version and identity validation must reject unknown fields/versions rather than silently interpreting them.

## 4. Crash recovery and manifest invariants

1. A crash-left `running` manifest remains byte-for-byte unchanged; never rewrite it automatically to `failure` or `success`.
2. Recovery starts only after prior-owner termination is established and the lock state has been validated. Lock age or a stale-looking timestamp is not sufficient.
3. Once recovery checks pass, the next execution uses a new `run_id`, fresh source inventory, and fresh per-file states. Never resume by blindly copying old file statuses into the new run.
4. Before retrying any upload whose prior outcome is uncertain, reconcile current Drive state using a complete, trustworthy query and content verification. Incomplete listing, timeout, ambiguity, or unavailable content keeps the outcome unknown and blocks retry.
5. Preserve staging artifacts for unknown/unverified outcomes. No automatic residual-staging upload or deletion is introduced by this slice.
6. Latest-manifest selection must use the approved timestamp policy and fail closed on malformed, identity-mismatched, equal-maximal, or otherwise ambiguous candidates. A latest `running`, `partial_failure`, or `failure` record must not fall back to an older success.
7. Lock/recovery must not modify source logs, Google Drive objects, archive files, or historical manifests.

## 5. Required test matrix

All tests use synthetic fixtures, injected clocks/process probes, temporary directories, and fake Drive adapters. Never use production logs, production paths, credentials, or live Drive objects.

| ID | Scenario | Required assertion |
|---|---|---|
| LOCK-01 | First acquisition | Exactly one owner obtains mutex and exclusive token record. |
| LOCK-02 | Concurrent acquisition | Second process waits no more than 60 seconds, then exits without side effects if lock remains held. |
| LOCK-03 | Token mismatch | Current process cannot update or remove a record whose token differs. |
| LOCK-04 | Live owner with old timestamp | Age does not authorize takeover or removal. |
| LOCK-05 | PID reuse / dead PID ambiguity | PID alone does not establish ownership or authorize recovery. |
| LOCK-06 | Abandoned mutex, valid matching record | Recovery follows explicit validation path and records sanitized evidence. |
| LOCK-07 | Abandoned mutex, malformed/mismatched record | Fail closed; preserve lock record, manifest, staging, and source data. |
| LOCK-08 | Lock record already exists | Exclusive create fails safely; no overwrite occurs. |
| LOCK-09 | Mutex unavailable / OS error | No inventory, manifest, staging, Drive, archive, or delete side effect occurs. |
| LOCK-10 | Normal release | Only the matching owner's token record is removed; mutex is released even when later cleanup raises. |
| REC-01 | Crash before manifest publication | Temporary file is non-authoritative; no partial manifest is accepted. |
| REC-02 | Crash after manifest publication | Published artifact is complete; crash-left running manifest remains unchanged. |
| REC-03 | Crash during lock-record update | Existing authoritative record remains valid or operation fails closed; partial record is never trusted. |
| REC-04 | New run after validated recovery | New run_id and fresh inventory/states are used; prior manifest bytes remain unchanged. |
| REC-05 | Unknown upload with confirmed matching Drive object | Content verification permits reconciliation to verified without duplicate upload. |
| REC-06 | Unknown upload with incomplete/ambiguous Drive listing | Keep unknown; do not retry, claim success, clean staging, archive, or delete. |
| REC-07 | Equal latest timestamps / identity mismatch | No arbitrary winner and no fallback to older success. |
| REC-08 | Recovery interruption repeated | Idempotent fail-closed behavior; no ownership theft or data loss. |

Every test must assert return/result classification, relevant manifest bytes, token ownership, temporary-file state, and that source/Drive/archive data remain unchanged. A test is not passed if only the expected error code is asserted.

## 6. Implementation sequence and exit criteria

- Slice A: implement the lock ownership primitive and deterministic synthetic tests without connecting it to official entry points.
- Slice B: implement crash/recovery decision helpers and synthetic tests, including lock/manifest/latest-run reconciliation.
- Slice C: prove multi-artifact publication and recovery ordering under injected crashes and concurrent publishers.
- Only after A-C and the runtime-entrypoint gate pass may official entry points be integrated. Each slice requires Validate and Package Validation to pass on the exact latest PR HEAD and post-merge main workflows to be verified.
- Do not mark P0 complete until runtime acceptance evidence, packaging, role constraints, Drive verification, and end-to-end safety checks are independently confirmed.

## 7. Explicit exclusions

This gate does not implement a lock helper, stale-lock deletion, automatic staging recovery, Drive synchronization, archive, local-source deletion, Drive deletion, or official entry points. It is an acceptance contract only. P0 remains open.


## 8. Multi-artifact evidence classification (implementation not yet authorized)

The isolated `Common/ArtifactSetRecovery.py` helper classifies evidence only. Its synthetic commit-marker model is not yet the approved final transaction protocol.

- A set is reported `committed` only when the marker has the strict supported shape, its transaction ID is valid, its SHA-256 map exactly matches the expected artifact set, and every expected published artifact is present with matching content hash.
- A marker missing after all artifacts appear, a partial published set, malformed marker, unexpected artifact, or digest mismatch must not be reported as committed. Preserve existing artifacts and require reconciliation.
- The helper does not establish crash durability, filesystem atomicity across multiple artifacts, ownership, or Drive consistency. Those require separate injected-crash/concurrency tests and explicit review before any runtime integration.
- No cleanup or overwrite is authorized by a classification result.


## 9. Marker-last multi-artifact publication helper (implementation gate remains open)

The isolated `Common/ArtifactSetPublication.py` composes the single-file no-overwrite helper, publishes artifacts in deterministic order, then publishes a transaction marker last. This ordering provides a detectable incomplete-set state, not an atomic multi-file transaction.

- A crash before marker publication may leave some or all artifacts present; without a valid marker the set must not be reported committed.
- Existing identical artifact bytes may be retried idempotently; conflicting bytes fail closed and must not be overwritten.
- The helper must not roll back or delete previously published artifacts after a partial failure.
- Actual directory reconciliation must re-read bytes and verify hashes plus marker identity before classifying committed.
- This helper is not yet approved for official entry-point integration, Drive interaction, manifest lifecycle mutation, archive, or deletion. Cross-process crash/concurrency acceptance and target-filesystem behavior remain required.


### Exact temporary-file write counts (2026-10-26)

The single-file publisher writes its immutable payload in chunks of at most 1,048,576 bytes using memoryview slices. Every `write` result must be an exact integer equal to that chunk's length; short/zero/negative/oversized counts, bool, None or other types reject with fixed `artifact_write_incomplete`. The helper does not retry a partial write, explicitly flush/fsync it, or link it to the destination. Stream close may flush buffered data, so partial/unverified temp files remain preserved; they are not automatically repaired or removed. Existing readback, identity and parent checks remain required after complete writes. Empty payloads still flush, fsync and pass readback before publication.

The artifact-set publisher propagates the same fixed reason. If a later artifact fails its write, earlier published artifacts remain, no marker is published, and the partial temp remains for separately authorized reconciliation. Synthetic tests cover bounded multichunk writes, invalid return values without retry/link, empty payload publication, and a second-artifact short write. These checks do not add runtime integration, durable recovery, qualified ownership/filesystems, or power-loss guarantees; caller payload memory is not bounded by chunking.

### Destination basenames before publication (2026-10-26)

The artifact-set publisher applies the single-file publisher's existing prohibition on trailing spaces/dots to every artifact basename and the marker basename during whole-set input validation. Invalid artifact names raise `artifact_name_invalid`; invalid marker names raise `commit_marker_name_invalid`, before any call to publish an artifact. Previously, a later invalid basename or the invalid marker could be discovered only after earlier valid files had been published. Invalid input no longer creates that avoidable partial set; an existing partial set remains unchanged.

The single-file publisher also checks its existing basename rule before parent inspection, so `destination_name_invalid` takes precedence over an unavailable parent for such invalid names. This reorders existing single-file validation and tightens the set preflight to the same rule. It does not define a complete Windows namespace/alias policy, change valid-file ordering or no-overwrite behavior, or authorize cleanup/recovery. Synthetic tests cover invalid trailing spaces/dots on later artifacts and markers, preservation of existing partial sets, and absence of parent inspection/temp allocation for invalid single-file basenames.

### Publication comparisons bounded by expected bytes (2026-10-26)

`AtomicArtifactPublication._same_bytes` rejects an inspected regular file whose initial size differs from the immutable expected payload length without opening its content. For an existing destination this remains `destination_conflict`; it does not allocate a temp file or overwrite the destination. A staging/final readback size conflict still fails its existing verification gate, and changed/unverified temporary content is preserved under the existing ownership-based cleanup checks.

When initial sizes agree, each read is at most 1,048,576 bytes and the total comparison stops at expected length plus one byte. Observed growth immediately rejects with `artifact_changed_during_read`, preventing a continuously growing file from extending the comparison indefinitely. Handle/path/ancestor signatures and byte comparisons remain required for an identical result. Empty and multichunk payloads retain idempotent behavior. This uses known caller bytes rather than introducing configurable production limits. It does not bound caller payload memory or read latency, qualify ownership/filesystems, prevent ABA, or establish durability/runtime acceptance. Synthetic tests cover pre-open size conflicts, exact empty/multichunk comparisons, growth during reading, and size change between inspection and open.

### Publisher and classifier transaction grammar (2026-10-26)

The publisher now uses the existing classifier's shared `is_artifact_transaction_id` grammar before payload validation or any publication call: a hyphenated UUID with version 1 through 8 and RFC variant (fourth group starting 8, 9, a or b), accepting upper/lowercase hex. The supplied spelling is preserved in the marker; independent transaction expectations remain exact string comparisons rather than UUID normalization. The marker classifier and expected-ID validator use the same grammar.

Previously, the publisher's generic UUID parse accepted nil IDs, unsupported versions or non-RFC variants that the classifier could never accept as committed. Such inputs now fail with fixed `transaction_id_invalid` before publishing any artifact or marker. Existing partial sets remain unchanged. This tightens invalid producer inputs to the already established consumer contract; it does not migrate or repair old invalid markers. Synthetic tests cover invalid types/forms, all 64 combinations of supported version/variant/case through real publication and directory verification, and preservation of an existing partial set. Crash/concurrency and formal runtime qualification remain separate gates.

## 10. Read-only directory-state verification (synthetic implementation)

`Common/ArtifactSetDirectoryVerification.py` now reads observed artifact bytes from one directory, computes SHA-256, parses the marker with duplicate-key rejection, rejects unexpected directory entries and non-regular files, and delegates to the strict artifact-set classifier. It performs no repair, publish, overwrite, or deletion.

- A successful classification is only a point-in-time observation. A concurrent writer can change files after verification; a lock/ownership boundary and revalidation at the actual consumer remain required.
- Missing markers and partial sets never report committed. Invalid marker JSON, duplicate keys, unexpected entries, symlinks, unreadable files, or invalid directories fail closed.
- This slice does not establish multi-file atomicity, durable directory entries, crash recovery, network/Windows filesystem semantics, Drive consistency, or official entrypoint safety. Cross-process crash/concurrency tests remain required before integration.


### Artifact-set expectations before filesystem access (2026-10-26)

`verify_published_artifact_set` copies the caller's expected hash mapping before root/path inspection and validates that snapshot plus the optional expected transaction ID with the existing pure classifier. Invalid filename/hash grammar or transaction identity returns the classifier's blocked decision without filesystem access. Non-mapping/empty inputs, collision with the marker name, and mapping-copy failure raise the fixed `expected_artifact_set_invalid` directory error before I/O; custom mapping exception details are suppressed. Existing marker-name and resource-limit checks also remain before I/O.

This changes rejection timing: caller errors take precedence over an unavailable or malformed directory, and invalid expectations no longer trigger scans or payload reads. Valid expectations retain the same marker/hash/transaction classification and full before/after observations. A mutation to the original mapping during the first root inspection cannot change the copied expectations. Copying is not an atomic snapshot of an externally mutated custom mapping and does not prove caller authenticity or root/owner qualification. The preliminary empty-publication classifier result is discarded for valid inputs; it cannot report an observed directory or authorize publication. Synthetic tests cover invalid hashes/names/transactions, invalid containers, sanitized copy failure and mutation at first root inspection.

### Caller-selected artifact-set read bounds (2026-10-26)

`verify_published_artifact_set` accepts optional `maximum_artifact_bytes` and `maximum_total_bytes`, each None or a positive exact integer. Invalid values reject with `artifact_read_limit_invalid` before filesystem access. After the initial metadata scan, every observed artifact and the marker are checked before any payload opens. A file over its bound rejects with `artifact_read_limit_exceeded`; the sum of observed initial sizes over the set bound rejects with `artifact_total_limit_exceeded`. Partial sets and marker-missing states do not bypass these checks. Empty directories still classify as not published.

The total is the initial observed set size, not cumulative I/O: final rereads must match the same signatures and exact bytes but are not charged again. Each read uses chunks of at most 65,536 bytes and stops at the inspected initial size plus one byte, rejecting observed growth with `artifact_changed`, even without caller bounds. Existing marker/hash/transaction classification, final rereads and directory rescans remain required. No truncation, fallback or mutation occurs on a resource failure.

None imposes no caller ceiling; no production default, schema constraint or retention policy is selected. These controls do not bound caller mapping size, native enumeration/read latency, JSON complexity or total memory, and do not establish qualified roots/owners, atomicity, ABA protection, durability or runtime authorization. Synthetic directory tests cover exact boundaries, every payload including the marker, pre-open rejection, incomplete sets and bounded growth. Tests-only terminal candidate integration supplies bounds on both observations for both PC roles and verifies that rejection preserves the bundle/prior and releases ownership. A committed classifier result remains an observation of the marker/hash snapshot, not permission to update a manifest or archive.

## 11. Cross-process marker-last publication race (synthetic test)

The publication tests now exercise two spawned processes concurrently publishing sets with the same manifest bytes but conflicting report bytes to one temporary directory. Acceptance requires exactly one success, one fail-closed conflict, and a commit marker that validates against the winning on-disk bytes. This only tests the host runner's temporary local filesystem; it does not prove behavior on Drive/network filesystems, power loss, cross-file atomicity, or coordination with the owned-run lock. Official integration remains gated.


## 12. Target-filesystem qualification (required before official integration)

See `docs/validation/target-filesystem-acceptance.md` for the tiered evidence plan. Hosted Windows CI is Tier A only. Before official entrypoint integration, Tier B disposable-root tests must pass on each operator PC's intended local volume, including crash injection, conflicting concurrent publishers, strict marker/hash revalidation, and no-overwrite capability checks. Any Google Drive for desktop or network-target-dependent behavior requires separately gated Tier C evidence in a dedicated disposable folder. Do not infer remote sync completion or power-loss durability from local visibility. Unknown, ambiguous, or unobservable states block dependent archive/deletion. No production log path or Drive operation is authorized by this plan.


## Owned publication/recovery integration evidence (2026-10-23)

`tests/test_owned_publication_integration.py` uses real Windows machine-wide
named mutexes and spawned processes in a fresh harness-owned temp root. It
verifies competing-publisher timeout without artifact changes, normal token
cleanup plus exact-byte retry, actual abandoned-mutex fail-closed behavior,
ownership-token mismatch preservation, and revalidation after an external writer
changes previously verified bytes. A parent handle keeps the mutex object alive
so the abandonment assertion does not accidentally test a newly created mutex.

A schema-valid synthetic crash-left running manifest and actual surviving lock
record are supplied to the pure recovery classifier. Missing termination proof,
ambiguous latest candidate, incomplete reconciliation, unresolved uploads and
record-identity mismatch all block. A positive result still requires fresh
inventory/new run identity and does not authorize stale-record deletion/adoption.
The tests preserve that manifest, lock record and published bytes; operational
recovery and lock-protected use of real source/Drive data remain unimplemented.
This is hosted/local synthetic evidence, not Tier B/C or complete runtime
integration. P0-010/P0-012 remain open.

## Strict lock and recovery evidence (2026-10-23)

OwnedRunLock rejects duplicate JSON keys before checking ownership. A matching
token does not make a malformed record removable: schema_version must be an
actual integer equal to 1, pid an actual positive integer (not boolean), and
host a nonempty string. Non-ASCII tokens are rejected before constant-time
comparison. Unverified or malformed records remain byte-for-byte unchanged;
the mutex is normally released. No stale-record adoption/removal is introduced.

CrashRecoveryDecision also rejects duplicate manifest keys, including when the
last duplicate would otherwise overwrite an invalid value with a valid one.
Only boolean true proves the supplied abandoned-mutex observation. Invalid
manifest/reconciliation primitive types return the existing fixed block reasons
rather than escaping as unhandled type errors. The decision remains pure; no
prior manifest is rewritten and no actual recovery/run starts here.

Regressions reproduced unintended malformed-record deletion and acceptance of
ambiguous recovery evidence before the fix. A spawned Windows worker verifies
duplicate/boolean/non-ASCII malformed records remain intact, stays alive after
release, and a parent acquires the same non-abandoned mutex while that worker
is alive. Subsequent acquisition remains blocked by the preserved record.
These are synthetic evidence checks, not proof of atomic compare/delete against
arbitrary external writers, validated stale-lock disposition, or complete REC-04
new-run/fresh-inventory integration. LOCK/REC and P0 acceptance remain open.

[PC-B strict-lock follow-up](../../tests/evidence/pc-b-lock-validation-local-volume-20261023.json) records 29 passing disposable-root checks without skips at source 302682abb7fd3b45b6745247dfa5297542f81c4b on the intended local fixed NTFS volume. This adds real-mutex malformed-record preservation/release to earlier crash/reparse cases. Pure lock/recovery unit regressions are covered separately by the full Python suite. Complete Tier B and operational recovery remain unaccepted.

## Latest candidate selection evidence (2026-10-23)

The read-only [C4 core](../design/latest-manifest-selection.md) independently parses the defined filename and selects only a unique validated latest start time. It rejects ambiguous/malformed/unreadable candidates and never falls back from a newer incomplete run to old success. It does not enumerate/read operational manifests, establish owner termination, dispose stale locks or start a new run; REC-04/REC-07 runtime acceptance remains open.

## Latest-directory composition evidence (2026-10-23)

Seven synthetic composition tests feed the exact latest-directory byte snapshot
into the existing pure recovery classifier. Latest failure, equal maxima, older
corruption and read uncertainty never permit recovery via an older candidate.
The actual Windows abandoned-mutex test now selects its prior running manifest
from the defined PC directory and confirms that a subsequent normal acquisition
still refuses the unchanged stale record even after a positive classification.
Changes after a snapshot demonstrate why classification is not a current-use
permit. This extends bounded evidence only; REC-04 operational new-run creation,
explicit disposition, termination proof and protection through use remain open.

## Explicit recovery entrypoint direction (2026-10-23)

Maintainer approved designing a dedicated explicit recovery command while normal synchronization continues to stop on stale records. [The command design](../design/explicit-recovery-command-design.md) defines read-only diagnosis/planning, non-authorizing results, safe mutex lifetime and a pending synthetic test matrix. It does not implement an entrypoint or authorize disposition. Persistent owner identity, root/clock qualification, private evidence storage and protected state changes remain open.

Diagnosis-only lease slice (2026-10-23): RecoveryDiagnosticMutex adds record-free acquisition of the existing named mutex and non-authorizing abandonment observations. Thirteen lifetime tests cover actual Windows contention, consumed abandonment and cross-process reacquisition after failure. It does not change acquire_owned_lock or authorize stale-record removal. See the [legacy-record policy proposal](../decisions/recovery-owner-evidence-v2-proposal.md).

Owner-evidence design slice (2026-10-23): v1 preservation/v2-only future recovery direction is approved. The [logical contract](../design/recovery-owner-evidence-v2-contract.md) specifies source/binding requirements, non-authorizing termination observation and OWNER-01 through OWNER-06 as pending tests. No OS provider, v2 schema/writer or record disposition is implemented. Old lock/manifest bytes remain unchanged.
