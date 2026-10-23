# テスト計画

テストは実ログや本番パスに依存しないように構成します。

## 実装済み：JSON Schema 契約テスト

`test_contract_schemas.py` は、Drive アダプターのリクエスト／レスポンス JSON Schema の定義と適合性を検証します。

- Draft 2020-12 スキーマ自体の妥当性
- 4つの許可操作の正常リクエスト
- 必須フィールド、型、UUID、SHA-256 形式
- 未知の操作（削除操作を含む）と未知のフィールドの拒否
- 成功／失敗レスポンスの整合性
- 未知のエラーコードの拒否

ローカル実行方法（Python 3.11 以降を想定）：

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -p "test_contract_schemas.py" -v
```

GitHub Actions の `Validate` ワークフローでも同じテストを実行します。

## 未実装のランタイム安全性テスト

1. コピー元とコピー先の SHA-256 が一致する。
2. ファイルが欠落・破損・変更された場合に検証が失敗する。
3. PC-B のマニフェストが存在しない、失敗状態、古い、期間不一致、ログ種別不一致の場合に PC-A のアーカイブがブロックされる。
4. クラウド同期完了または内容検証を確認できない場合にアーカイブがブロックされる。
5. アーカイブ先の検証が失敗した場合にDrive上の元ファイルが残る。
6. PC-B にアーカイブ入口が含まれず、PC-B設定に allowArchive があれば設定検証で停止する。
7. 初期実装にローカル元ファイル削除・Drive削除のコード、操作、設定が存在しないことを確認する。Dry Run はデータ変更を行わない。
8. 0件の正常実行と、スクリプト未実行をマニフェストで区別できる。

これらのランタイムテストは未実装です。削除機能の実装・有効化をテスト合格条件に含めません。テスト合格は将来の削除機能を許可するものではありません。JSON Schema テストの成功は、ランタイム処理の安全性や Google Drive の同期完了を保証しません。

再試行テストでは、PowerShell が初回を含む最大4回（待機1分・5分・15分）を管理し、Python/HTTPクライアントに暗黙の再試行がないことを確認します。アップロード結果が不明な場合は、再アップロード前にDrive上の状態を照合します。


## C-54 approved pattern-contract tests

`Test-C54PatternContract.ps1` checks the approved C-54 URI user-info, Bearer, GitHub token-like, AWS AKIA, and PEM private-key marker grammars using synthetic positive, negative, boundary, and case fixtures.

Run with PowerShell 7.6.7:

```powershell
./tests/Test-C54PatternContract.ps1
```

This is a contract-level regex test, not a runtime sanitizer test. It does not prove C-53/C-54 path processing, whole-field nulling, or diagnostic non-disclosure. Those runtime tests remain pending.

## C-53/C-54 diagnostic path sanitizer tests

The test script `Test-DiagnosticPathSanitization.ps1` checks the deterministic optional-path sanitizer against the approved C-53 syntax contract and C-54 sensitive-name/token/value-format policy, using synthetic paths only.

Run with PowerShell 7.6.7:

```powershell
./tests/Test-DiagnosticPathSanitization.ps1
```

These tests cover the standalone path sanitizer's return value. They do not yet prove diagnostic-record schema validation, JSON serialization to a literal `null`, preservation of event identity/classification through finalization, or non-disclosure by a runtime diagnostic pipeline. No Google Drive or real-log operations are performed.

## Diagnostic record schema-v1 finalizer tests

Run the standalone C-47–C-53 schema-v1 finalizer tests with PowerShell 7.6.7 using:

    ./tests/Test-DiagnosticRecordFinalizer.ps1

The finalizer accepts an already-structured dictionary with exactly seven fields, validates schema version, event ID, allowlisted error code, the approved phase/operation pair, and the exact fixed message template. It emits a fresh ordered JSON object; an unsafe optional path becomes an explicit JSON null. The C-47 path maximum is 1024 Unicode scalar values; over-limit paths fail closed to null.

This is a pure structured-record finalizer and synthetic test suite. It does not parse arbitrary input JSON, generate event IDs, infer failure mappings from exceptions, implement runtime orchestration, access logs or Google Drive, or prove end-to-end P0 acceptance. Duplicate JSON properties must be rejected by any future raw-JSON ingestion boundary before a dictionary is materialized.

## Diagnostic event ID allocation tests

Run the synthetic C-45/C-46 event ID allocation tests with PowerShell 7.6.7 using:

    ./tests/Test-DiagnosticErrorId.ps1

The allocator mutates a caller-owned per-run Int32/Int64 sequence by reference, emits invariant-culture IDs in the exact ERR-000001 format, and fails closed after ERR-999999. The runtime caller remains responsible for allocating once per distinct event and preserving that ID through wrappers and later observers. The helper is not thread-safe by itself and does not define event correlation or runtime orchestration.


## Crash-recovery decision gate (synthetic only)

`test_crash_recovery_decision.py` covers the pure recovery decision helper using synthetic manifest bytes and lock records. It checks fail-closed behavior for lock/owner/latest-manifest/identity/Drive reconciliation failures and confirms that an eligible decision preserves the old manifest and requires a new run with fresh inventory. It does not perform recovery, mutate files, access Drive, archive, or delete. CI validation is required before acceptance.


## Artifact-set recovery classifier (synthetic only)

`test_artifact_set_recovery.py` covers exact staged sets, valid marker + complete published set, missing marker, partial publication, digest mismatch, unexpected artifacts, and malformed markers. It uses synthetic hashes only; no filesystem publication, recovery, Drive, archive, or deletion is performed. CI validation is required before acceptance.


## Marker-last artifact-set publication (synthetic filesystem tests)

`test_artifact_set_publication.py` covers marker-last success, injected mid-set failure, idempotent retry, existing-content conflict, invalid inputs, and concurrent identical publishers using temporary directories only. Partial publication must leave no marker and must not be treated as committed. These tests do not access production paths or Drive and do not prove cross-file atomicity.


## Artifact-set directory verification (synthetic filesystem tests)

`test_artifact_set_directory_verification.py` inspects temporary directories and hashes actual artifact bytes before classifying the commit marker. It covers valid publication, missing marker, partial sets, tampering, duplicate JSON keys, unexpected entries, symlinks, invalid inputs, and empty state. The verifier is read-only and does not repair or remove artifacts. These tests do not establish crash durability, cross-file atomicity, cross-process locking, target/network filesystem behavior, source stability, Drive consistency, or runtime acceptance. CI validation is required before acceptance.


### Cross-process artifact publication race

The marker-last publication test suite includes a spawned-process race in which two publishers target the same directory with conflicting bytes for one artifact. The expected result is one complete committed winner and one fail-closed destination conflict, with the marker matching the winner's actual bytes. This is synthetic local-filesystem coverage, not evidence for network shares, Google Drive, power-loss durability, run-lock integration, or runtime entrypoint safety.


## Target-filesystem acceptance tiers

See `docs/validation/target-filesystem-acceptance.md`. Hosted Windows CI covers Tier A synthetic tests only. Tier B disposable local-volume tests on each operator PC and Tier C synchronized/network-target qualification have not been run. A green CI result must not be reported as evidence for Google Drive for desktop semantics, remote upload completion, network filesystem behavior, or power-loss durability. Any future crash-injection harness must use an explicitly supplied disposable test root and must refuse production log, archive, and shared Drive roots.


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


## Read-only configuration structure loader

`Common/MachineConfiguration.ps1` provides
`ConvertFrom-EoMachineConfigurationJson` and `Read-EoMachineConfiguration`.
The reader accepts strict UTF-8 (optional BOM), returns a fresh validated object,
and never creates configuration, root directories, manifests or other artifacts.

The parser rejects non-object/malformed JSON, duplicate/unknown/missing keys,
wrong primitive types, role mismatch, non-drive-qualified/ambiguous path syntax,
and maintenanceLocal equality/ancestor/descendant overlap after normalization.
PC-B must omit allowArchive; PC-A may explicitly set a boolean true or false.
A true value is configuration data only, never archive authorization.

Errors are fixed reason codes without rejected values, file contents or private
paths. The package builder shares this structural parser and additionally
requires safe template defaults (PC-A allowArchive false).

This is structural/lexical evidence, not an approved-root filesystem gate.
It does not inspect actual target volumes, resolve short-name/reparse aliases,
prove cross-root physical separation, acquire a runtime lock, contact Drive,
or integrate official entry points. Those checks remain mandatory before effects.
Bootstrap/create-once migration is a separate pending implementation.

## Create-only configuration bootstrap helper

See [configuration specification](../docs/design/configuration-local-root.md#create-only-configuration-bootstrap-helper) for Initialize-EoMachineConfiguration, safety boundaries and pending deployment integration. Run tests/Test-MachineConfigurationBootstrap.ps1 for synthetic create-once and preservation checks.

Internal publication crash tests: python -m unittest discover -s tests -p test_internal_publication_crash.py -v. See [filesystem acceptance](../docs/validation/target-filesystem-acceptance.md#internal-single-file-crash-boundaries-2026-10-23) for the 10 crash scenarios, orphan rejection and evidence limits. Included in opt-in local-volume checks.

Source hash identity regressions: python -m unittest discover -s tests -p test_source_hash_identity.py -v. These use synthetic file replacement/restoration and injected fstat failures; see [scope and limitations](../docs/validation/target-filesystem-acceptance.md#source-hash-handle-identity-2026-10-23).

Source reparse regressions: python -m unittest discover -s tests -p test_source_inventory_reparse.py -v. Seven tests include real Windows junction root/ancestor/child/queued replacement and metadata failures. Included in opt-in local-volume checks; synthetic fixtures only.

Strict lock/recovery regressions run in the existing test_owned_run_lock.py, test_crash_recovery_decision.py and test_owned_publication_integration.py suites. They cover duplicate JSON, boolean/integer confusion, invalid state types, record byte preservation and real-mutex normal release while the publisher remains alive.

Run pwsh -NoProfile -File tests/Test-MachineConfigurationRootInspection.ps1 for both-PC OS-temp metadata checks, real junction/available short-name fixtures and injected canonical aliases. The script reports unavailable 8.3 checks as skips. No real configs or production roots are used.

Run python -m unittest discover -s tests -p test_latest_manifest_selection.py -v for 32 in-memory C4 naming/identity/ambiguity/no-fallback/time regressions. No filesystem enumeration or production data is used.

`test_manifest_directory_reader.py` exercises synthetic local manifest enumeration/read binding, opened-file replacement, final rescan changes, partial enumeration and real Windows junction rejection. It never uses operational roots and does not establish full Tier B or runtime acceptance.

`test_manifest_recovery_integration.py` adds seven synthetic compositions of checked manifest-directory snapshots and pure recovery classification. The real Windows abandonment scenario in `test_owned_publication_integration.py` also uses the disk reader. A positive classification never adopts/removes the stale record; later external changes require fresh observations. These tests do not authorize operational recovery or extend the recorded PC-B Tier B result.

`test_recovery_diagnostic.py` covers the pure diagnostic result boundary: incomplete/unknown owner and Drive evidence, rejected raw secrets and invalid scopes, public-field allowlisting, immutable snapshots, tampered export refusal and absence of file I/O. These tests do not execute the full DIAG command acceptance matrix.

`test_recovery_diagnostic_mutex.py` adds 13 synthetic lifetime tests, including actual Windows contention/abandonment and a different-process probe after a body exception. The old synthetic record stays byte-identical and no new record appears. This is bounded helper evidence, not the full DIAG matrix or an extension of recorded PC-B Tier B results.

`test_private_recovery_evidence.py` adds 13 in-memory raw/metadata binding tests, including same-size substitution, truncation, opaque non-UTF-8 originals, duplicate keys, permission/path injection and sanitized schema failure. Package regression also excludes synthetic private originals/metadata while including the static schema. This does not exercise actual private saving, ACLs or the STORE acceptance matrix.

`test_private_evidence_acl_profile.py` adds 13 synthetic SID/ACL-observation boundary tests. It checks foreign/world grants, null versus empty DACL, inheritance, unsupported ACE/masks, no group-right inference, input preservation and SID-free fixed results. No real ACL/token/account is queried or changed; STORE-01 remains incomplete.

`test_private_acl_descriptor_normalization.py` runs six Python/PowerShell integration tests over sixteen synthetic binary descriptors, including null/absent/empty DACL, unsigned generic rights, deny/inheritance, callback/object ACE, SACL, missing owner and malformed bytes. The fixture worker uses .NET memory objects only. No real account/token/file ACL is queried or modified.

`test_monthly_schedule_observation.py` adds 12 fixed-clock tests covering JST/UTC month/year boundaries, leap year, staggered role times, exact microsecond boundaries, logged-off/untrusted context, overflow and non-authorizing immutable output. It does not test task registration, missed-run completion or PC-A hourly polling.

`test_completion_wait_budget.py` adds 16 synthetic history/clock tests: full 25-attempt boundary, inclusive deadline, delayed checks without compressed spacing or extended budget, copied state preserving its origin, corrupt history/scope, clock rollback, unconfirmed context and failed attempts. It does not establish actual restart-safe persistence or execute hourly tasks.
