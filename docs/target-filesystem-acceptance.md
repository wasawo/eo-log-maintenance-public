# Target-Filesystem and Crash-Recovery Acceptance Plan

- Status: required acceptance gate; planning only.
- Date: 2026-10-22.
- Scope: local publication primitives, artifact-set marker protocol, directory verification, and eventual official entrypoint integration.
- This document authorizes no production-log access, Google Drive writes, archive, or deletion.

## 1. Evidence boundary

Current CI exercises temporary directories on the hosted Windows runner. It provides useful evidence for the tested runner/filesystem and code path only. It does not establish behavior on either operator PC, a Google Drive for desktop mount, a network filesystem, after power loss, or across an actual host restart. Do not infer these properties from a green workflow.

Acceptance evidence must identify the exact environment, not just say "Windows":
- PC role (PC-A or PC-B), Windows build, PowerShell/Python versions, and repository commit.
- Volume and filesystem type for the test root; whether it is a local fixed disk, removable disk, network path, or Google Drive for desktop sync folder.
- Google Drive for desktop version and sync state if a mounted/synchronized path is ever tested.
- Test timestamp, scenario ID, process exit outcomes, observed directory entries, artifact SHA-256 values, marker contents, and sanitized failure code.
- Whether the run is a CI synthetic test, local disposable-directory test, or actual target-filesystem test.

Never put credentials, user paths outside the explicitly approved test root, or production log names/content in acceptance evidence.

## 2. Required test tiers

### Tier A — deterministic synthetic CI tests

Continue to run the current marker-last publication, directory verification, recovery classification, and spawned-process conflict tests on the Windows CI runner. These tests must be deterministic, bounded, use temporary directories, and never touch production paths. Inject failures at each publication boundary: before the first artifact, between every adjacent artifact pair, immediately before marker publication, and immediately after marker publication. After each injected failure, inspect on-disk state and verify that no incomplete set is classified as committed.

### Tier B — disposable local-volume acceptance on each operator PC

Before runtime integration, run an explicit opt-in harness against a newly created disposable directory on the same local volume intended for maintenance artifacts. Do not use the real maintenance root or log folders. Validate:
1. Exclusive no-overwrite publication for identical and conflicting bytes.
2. Two-process publication race: one winner for conflicting sets, marker hashes match the winning bytes, no unexpected/temp entries remain after process exit.
3. Process termination at every publication boundary, then a fresh-process directory inspection; a missing/invalid marker or partial set must never be accepted as committed.
4. Idempotent retry for identical existing bytes and fail-closed behavior for conflicting bytes.
5. Directory verifier rejects symlinks/reparse points, unexpected entries, malformed marker, missing artifacts, and read failures.
6. Run-lock ownership and recovery decision are tested together; a helper-only test does not prove integration.
7. Record whether the filesystem supports the required same-volume hard-link/no-overwrite primitive. Unsupported behavior must fail closed, not silently fall back to overwrite-capable publication.

The harness must refuse a path unless it is explicitly supplied as a disposable test root, and must print the resolved root before any writes. It must not accept a production log root, archive root, or shared Drive sync root.

### Tier C — synchronized/network target qualification

Google Drive for desktop and any network/synchronized folder require a separate qualification, only after Tier B and review of the exact test plan. Use a dedicated disposable test folder with no real logs. Record the sync client state and verify remote visibility through an approved read-only observation mechanism. A local file appearing on a mounted drive is not proof that remote content is uploaded or durable.

Test concurrent writers, local process crash/restart, offline/network interruption, delayed synchronization, duplicate/conflicting names, and reconciliation of uncertain outcomes. Do not claim power-loss durability unless it has been tested with a defensible method. If a behavior cannot be observed reliably, mark it unverified and block dependent destructive actions.

## 3. Required invariants

- A marker is necessary but not sufficient: verify exact marker schema, transaction identity, expected artifact names, and hashes of observed bytes.
- A partial set, markerless set, mismatched marker, unexpected entry, ambiguous transaction, or unavailable directory is never committed.
- Publication never overwrites conflicting bytes and never removes pre-existing artifacts to "repair" a set.
- Recovery creates a new run identity and fresh inventory; it does not rewrite a crash-left manifest into success.
- A directory verification result is point-in-time evidence only. Any consumer must hold the approved ownership boundary and revalidate the bytes/identity at the point of use to address verification-to-use races.
- If lock ownership, prior-owner termination, latest-manifest uniqueness, Drive reconciliation, filesystem capability, or observed state is uncertain, stop before archive or deletion.
- No target-filesystem result grants permission to delete local source logs or Drive files. Destructive operations remain separately gated.

## 4. Acceptance record and exit criteria

For every tier, retain a concise record with commit SHA, OS/filesystem identity, test root category (never a sensitive full path), scenarios executed, pass/fail/unverified outcomes, sanitized reason codes, and artifact/marker digest comparisons. A green CI run satisfies Tier A only.

Do not connect official entrypoints until Tier A and Tier B pass, lock/recovery/publication/verification integration has its own tests, source-change races are covered, and the runtime-entrypoint safety gate is satisfied. Tier C remains mandatory before any behavior relies on a Google Drive/network target. Any unresolved or unobservable behavior is a blocker, not an inferred pass.

## 5. Current status

- Tier A: historical source-repository CI passed on source commit `f979a5200d48a7ccccfed6ad31de07529bd340df`, including cross-process conflict publication. This is historical evidence, not a CI result for the new public repository or this PR; require fresh exact-head validation here.
- Tier B: not run; no operator-PC filesystem qualification has been established.
- Tier C: not run; Google Drive/network semantics and remote durability are unverified.
- Official `scripts/SyncLogs.ps1` and PC-A-only `scripts/ArchiveLogs.ps1` are still absent. P0 remains open.


## Synthetic crash-boundary harness (2026-10-23)

`tests/crash_publication_harness.py` terminates only its own spawned publisher
after a checkpoint before publication and after each completed atomic publish
(two synthetic payloads, then marker). A fresh interpreter observes the directory
before an exact-byte retry. Missing/partial sets must not be committed; only the
complete marker-bound set is committed, and retry must preserve existing bytes.
This covers process termination between completed single-file publications, not
power loss or termination inside the atomic single-file primitive.

The first harness slice is deliberately Tier A only: require explicit disposable
acknowledgement and a new `eo-crash-harness-<32 lowercase hex digits>` directory
directly beneath the resolved OS temp directory. Existing paths (including empty
directories), relative/traversal paths, reparse ancestors, and non-fixed Windows
temp volumes are rejected. No arbitrary target-volume/Drive/network path is
accepted. Scenario artifacts are retained; the harness never cleans existing
artifacts. The unittest owns and removes only its freshly created test root.

Run the regression matrix using:

```powershell
python -m unittest discover -s tests -p "test_crash_publication_harness.py" -v
```

An explicit local-only invocation is also supported:

```powershell
$disposableRoot = Join-Path ([IO.Path]::GetTempPath()) ("eo-crash-harness-" + [guid]::NewGuid().ToString("N"))
python tests/crash_publication_harness.py --disposable-root $disposableRoot --acknowledge-disposable
```

The CLI prints the requested root locally before writes for operator review;
never copy that line into public evidence. Machine-readable results contain
scenario IDs, exit codes and invariants, not private paths. Tier B/Tier C, lock
integration, operator-volume qualification and runtime entry points remain open.


## Opt-in intended-local-volume evidence

`tests/run_local_volume_checks.py` requires PC role, expected local drive and
explicit disposable acknowledgement. It accepts no arbitrary root path: the
expected drive must match this checkout's fixed local volume. It runs the crash
matrix and owned-publication tests using fresh UUID-named children of this
checkout, with existing/reparse/known synchronized locations rejected.
Default CI tests continue to use OS temp. Unknown environment modes are rejected.

```powershell
# Set $plannedVolume locally; do not commit its real value or any real paths.
python tests/run_local_volume_checks.py --pc-role PC-B --expected-volume $plannedVolume --acknowledge-disposable
```

Generated root directories are Git-ignored. The unittest removes only roots it
created. JSON output includes role, source commit, UTC timestamp, Windows/Python
versions, filesystem type, counts and sanitized result identifiers. It excludes
absolute paths, volume letters/labels/serials, usernames, hostnames and lock tokens.
A passing subset is explicitly recorded as incomplete Tier B acceptance:
PC-A evidence, complete adversarial filesystem cases and remaining required
integration/source-race acceptance are not inferred from these checks.

### Recorded partial PC-B evidence

See [sanitized result](../tests/evidence/pc-b-local-volume-20261023.json): 10 synthetic crash/ownership checks passed on the operator-confirmed intended local fixed NTFS volume, with no skips. The result names the exact tested source commit. It is not complete Tier B acceptance; PC-A and the remaining adversarial filesystem/integration/source-race matrix remain open. The evidence contains no real paths or volume letters.


## Windows junction rejection regression (2026-10-23)

The directory verifier now checks lstat-based symlink/reparse attributes on the
requested directory, every lexical ancestor, and each observed entry before
reading artifact bytes. This closes a reproduced Windows junction-root/ancestor
gap where is_symlink alone did not detect junctions. Reparse uncertainty fails
closed with sanitized reasons; no files are changed by verification.
Checks are point-in-time defense-in-depth, not race-free path containment.

The regression suite creates real junctions only inside fresh owned synthetic
roots, asserts that root/ancestor rejection occurs before artifact read, rejects
a junction under an expected artifact name, and injects a sanitized read failure
without modifying existing bytes. CI runs this Windows suite; local-volume
evidence now includes it. P0 and remaining Tier B/C gates stay open.

[PC-B reparse/read-failure follow-up](../tests/evidence/pc-b-reparse-local-volume-20261023.json) records 14 passing checks with no skips, including actual junction roots/ancestors and injected read failure. It supersedes the earlier subset for these scenarios only; complete Tier B remains unaccepted.

## Internal single-file crash boundaries (2026-10-23)

The test-only crash harness now pauses the real single-file publisher after
exclusive temporary creation, before/after fsync, and before/after the actual
hard-link create. The parent terminates its own paused child without publisher
cleanup. Each point is tested for both the first artifact and final marker:
10 crash scenarios in 5 tests, plus invalid-scenario and missing-ack guards.

A fresh spawned observer inspects the leftovers and performs an exact-byte
low-level retry. Each crash leaves an owned test temporary file. The directory
verifier rejects that unexpected entry before and after retry, including when
a complete marker was already linked. Retry preserves all observed bytes and
does not remove the orphan. Thus a low-level publish result or visible marker
alone is not completion/recovery authorization.

This supplements completed-file boundary tests; it does not change production
publication/recovery code, authorize orphan cleanup, establish a full restart
workflow or prove power-loss durability. Interception is limited to test child
processes. All roots retain the existing fresh UUID/selected-parent/explicit-ack
guards. Tests remove only their own synthetic root after assertions.

[PC-B internal-crash follow-up](../tests/evidence/pc-b-internal-crash-local-volume-20261023.json) records 21 passing tests without skips on the operator-confirmed intended local fixed NTFS volume. This includes 10 internal crash scenarios and earlier boundary/ownership/reparse checks at source commit 63e5a4d5af674912940d8fa0ee26c726b06eb78b. Tier B remains incomplete; PC-A, remaining source-race and integration acceptance are still required.

## Source hash handle identity (2026-10-23)

SourceInventoryEvidenceBuilder now compares device, inode/file identity, size
and nanosecond mtime across four observations: pathname before open, opened
handle before read, the same handle after read, and pathname after close. A
difference rejects the file as source_mutation_detected. Unavailable fstat
fails as source_file_unavailable; enumeration remains incomplete with no
eligible target for that file. Errors do not include private exception details.

The regression reproduces an actual same-size/same-mtime replacement between
the initial path stat and open, restoring the original after close. Before the
fix, the wrong content hash was accepted; after the fix, it is rejected. Tests
also cover unchanged content, both handle-stat failure points and propagation
to schema-valid incomplete evidence without private path/exception leakage.

This narrows an observed ABA pathname gap. It is not a filesystem snapshot,
approved-root/reparse gate or protection until later upload/use. Same-object
content modifications that restore all compared metadata, changes after the
last check, directory enumeration races and arbitrary hostile filesystem
changes remain outside this evidence. No source writes or cleanup are added
to the helper; only tests mutate their own synthetic fixtures.
