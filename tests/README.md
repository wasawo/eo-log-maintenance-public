# テスト計画

`test_power_status_observation.py`はAC観測のmock ABI/不明・失敗と既存使用点への合成接続を検査します。Windowsでは実APIを読取のみで一度照会します。電源の変更・実ログ/Driveアクセス・task登録・実運用受け入れは行いません。

`test_checkpoint_replace_probe.py`はcaller指定先を受けない専用OS-temp probeで、実CreateFileW共有guardとReplaceFileW、使用点検査後の競合反例を確認します。許可名外/root marker変更/hardlinkでもnative変更へ進みません。これは不十分なAPI組合せを検出する負例であり、provider採用・Tier B/C・電源断耐久性の証拠ではありません。

`test_completion_wait_usepoint.py`は保存前/記録後のexact bytes、plan偽装、最新scope/時計/期限/実行条件/ACを純粋検査し、既存の実mutex・staging・mock保存fixtureへ接続します。資格喪失時の確認停止/試行保持と、使用点検査後の競合にもprovider側の比較が必要なことを確認します。runtime provider/一回限りreceipt/in-flight中断の受け入れではありません。

`test_completion_wait_attempt.py`は1試行だけの純粋candidate planと、実Windows owner/mutex・create-only staging・メモリmock compare-and-publishを接続します。保存前/後の失敗、stale/競合、偽ack/読取不一致、確認失敗時の予算保全を合成検証します。実checkpoint置換・電源断・runtime受け入れの証拠ではありません。

`test_completion_wait_checkpoint.py`はclosed schema、exact bytes/時刻表記/配列順、期待scopeと信頼できる現在時計、25回/24時間/1時間間隔、精度の保持と変換拒否、欠落/破損・I/Oなしを合成検証します。既存budget helperへ接続しても、実保存/rollback防止/実確認の証明にはしません。

`test_manifest_transition_inspection.py`は採用済みfile/runペアの行列、初期状態、identity/凍結inventory、verification/hash/time、終端の不変性、入力不変・I/Oなし・固定理由を合成検証します。掲載ペアの結果もrequires_runtime_evidenceであり、実event/Drive/排他/集約/永続更新の受け入れではありません。

`test_drive_request_path.py`と`Test-DriveRequestPath.ps1`は共通L1 fixtureをschema/Python/PSへ適用します。両request path field・Dry Runの両値、予約名/Unicode/末尾改行/禁止文字、型の非変換・入力保持・操作副作用なし・固定maxLengthなしを検査します。実root/指定先/使用点やtransportの受け入れ試験ではありません。

`tests/Test-DriveResponseSemantics.ps1` は合成in-memory request期待値/response/exitだけで、4操作成功、exit2–10の独立対応表、既知codeと誤exit、ordinal相関・case、unknown/missing/null/type・implicit cast拒否、raw JSON由来Int64、入力不変、秘密非echoを検査します。4操作×9codeのretryable正常値と矛盾値、非bool拒否を検証し、process/file/network等の禁止commandが呼ばれないことも確認します。`tests/test_contract_schemas.py`も4操作×9codeで正常値、逆のbool、null/数値/文字列等と欠落を検査します。これはC-03/一部C-05のpure補助とschemaの証拠で、実child出力/timeout/transport、RETRY-02のorchestration、C-01/C-02/IPC全体を完了にしません。

`python -B -m unittest discover -s tests -p "test_aggregation_report_builder.py" -v` はpure report builderのT-01〜12を両log typeで検証し、跨期間・関連error/run-scope error・不完全validation、exact bytes/hashとinventory整合、terminal verification mapping、strict JSON、G1の終了時刻選択・同時の元表記・11桁精度・未来境界・再生成、入力不変・I/Oなしを確認します。source producerのmixed-validity合成連携も検査します。隔離fixtureを既存referenced-artifact validatorにも渡します。`Test-AggregationReportValidation.ps1` は生成出力をPS internal validatorへ通し、空period配列のno_work正例とnull/非配列拒否を確認します。schema成功はruntime受け入れ・archive/回復認可ではなく、B2 incomplete validationから網羅性を補完しません。参照validatorはG1不一致をPython importと直接CLIの両経路で拒否します。

## Dry Run Aの合成境界ハーネス

通常owned lockのtimeout検証では、NaNを `timeout_invalid` としてpath変換・token生成・mutex生成より前に拒否することを、呼出しを記録する合成依存で確認する。既存の範囲外・無限大・巨大整数の固定理由と、0/60秒を含む有限値の取得・解放も検査する。

`test_owned_run_lock.py` は `_NamedMutex.close` のWin32 BOOL戻り値をfake kernel32で注入し、成功時だけhandleをclearし再closeを行わず、失敗時は固定理由 `named_mutex_close_failed` とhandle参照を保持して自動retryしないことを検査する。`test_recovery_diagnostic_mutex.py` は実adapterメソッドとfake kernel32を組み合わせ、release→closeの順序と、close失敗が `diagnostic_mutex_cleanup_failed` へ変換されることを検査する。nativeの無効handleを閉じるテストではなく、実環境の資格や耐久性を証明しない。

`python -B -m unittest discover -s tests -p "test_dry_run_boundary.py" -v` は、親が作成した専用一時fixtureを `-I -B` の子プロセスで検査する。9テスト内の33回のprobeで、読取・無資格/無効role/config/root・競合/abandonedの注入、依存write/delete/rename/mkdir/chmod/temp/network/subprocess要求、計測用normal経路を検証する。Python audit event名の履歴と、前後の存在・bytes/hash・modeを比較する。途中で拒否されたwriteも記録し、単なる最終snapshot一致とは区別する。

実 `Common.RecoveryDiagnosticMutex.acquire_diagnostic_mutex` を監査hook設置後にimportして呼び、test-only mutexのcreate/acquire/abandoned/lease body/release/close履歴を固定文字列で検査する。`-I` で除外されたimport検索先には、環境入力を使わずハーネスの配置から求める信頼済みcheckoutだけを追加し、`-B` を維持する。取得成功でも `qualification_pending` とし後続観測へ進まない。timeout、abandoned、create/acquire/observation/cleanup失敗を固定理由で拒否し、取得・lease body・release・close中の依存writeも監査で拒否する。helper import自体も監査下で観測する。

対象dispatcherもfixtureコードであり、正式runtimeは呼ばない。role/config/root/競合は合成注入、実ACL/Windows mutex資格の証拠ではない。Python audit hookは任意のnative処理を閉じ込めるsandboxでもなく、全依存の無書込み・電源断・cloudの保証でもない。出力は固定status/event名と常にfalseのrun/archive権限だけ。trusted test環境でのみ実行し、実ログ/実設定/Driveへ接続しない。fixture準備・削除は親テストの仕事で、Dry Runアプリへの許可ではない。CIにも個別登録する。

監査hookの設置はstdlib importとfixture確認の後で、起動/import時の全副作用は観測していない。snapshotのmodeは実効ACLではなく、比較対象も合成root内に限る。`-I -B`だけで全プロセスの書込み不在を証明したとは扱わない。

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

`Test-DriveResponseSemantics.ps1`には再試行観測も含めます。4操作×全error×試行1〜4で候補/上限/照合待ちを検査し、1/5/15分・upload/timeoutの非再送・不正応答/番号の拒否を確認します。実sleep・API・再送を行わず、RETRY-02全体の受け入れにはしません。

`test_terminal_manifest_plan.py`はsnapshot遷移＋B2＋report builderの純粋接続です。両log種別のT01〜T12相当、PC-B、不正遷移・凍結inventory/B2不一致・偽成功・終端不変・exact bytes参照を検査し、実保存・Drive・archiveを実行しません。

report builder/参照validatorの合成試験は、履歴再導出と通常builderのclock gateを分け、終端plan readback、偽status/件数/period completion/error/順序、float整数表現、任意cwdからの直接CLIも確認します。参照hash一致だけでreportの意味論を受け入れません。

`test_terminal_bundle_integration.py`は終端planの候補snapshot一式を、自作OS-tempで実mutex/owner＋create-only/marker-lastへ接続します。元runningは不変で、部分失敗・競合・応答喪失・別transaction・改変を検査します。候補bundleの検証を正式manifest比較更新やruntime受け入れに読み替えません。

`test_artifact_read_stability.py`は参照validatorのhandle/path/親chain/read集合の変更検出、reparse属性と専用temp内のWindows junction、静的schema外部取得禁止を検査します。実FSの包括的資格や敵対的ABAの排除を実証しません。

`test_manifest_report_selection.py`は最新manifestとreportのexact path/bytes binding、検査後再選択、両PC/log種別・旧report流用・改変・新しい未完run・欠落report/時計不明を合成検証します。通常のvalidator/CLI互換を維持し、読取成功をarchive資格へ変換しません。

artifact-setの既存試験へ期待transactionの型/不一致/未指定互換と、directory/file/markerの途中変更・handle不一致・期待hash mapの変更を追加しています。終端bundle接続も共通の期待transaction照合を使い、reparse/read失敗試験の注入先はstream openへ整合します。

単一file公開の試験はstaging readback、内容/identity差替え、cleanup時の別file保全、final identity不一致・既存handle不一致を追加確認します。全変更は専用tempの合成artifactで、実データ削除・回復・比較更新は実装しません。

Windowsのmultiprocessingを含む試験は、stdinへPythonスクリプトを渡す起動を避け、`python -B -m unittest discover ...` または一時的な`PYTHONPATH=tests`設定下で`python -B -m unittest <module/case> ...`を使います。spawnが起動元を再読込できる形で、対象caseをまとめて指定します。

`test_initial_manifest_plan.py`はB2→running/pendingの純粋構築を、両PC/log、改変/scope/時計境界、空/失敗/不完全、Unicode/元bytes、掲載ペアを経る終端report接続で検証します。実run生成/保存/Drive操作は実行しません。

`test_initial_source_integration.py`は専用tempの実source列挙/hashからB2・初期plan・別candidateへの実mutex/create-only/marker-last公開/読戻しを接続します。両PC/log・分類/失敗・source変更/競合を扱います。固定clockとfixture IDは合成観測で、runtime資格やUpload認可ではありません。

`test_source_inventory_revalidation.py`は凍結B2と実再列挙/hashの合成比較です。変更・分類・coverage不完全・scope/clock/date不明を拒否し、元B2を補完せず全may_*がfalseであること、non-target内容が比較範囲外であることを確認します。

`test_initial_source_usepoint.py`は初期planの再構成とAC/source再観測を接続し、改変・scope不一致・AC不明の事前拒否と、合成所有lock内でのcandidate保存/書込み前停止を検証します。観測からruntime権限を付与しません。

`test_source_enumeration_stability.py`はhash後/空scan後の追加・削除・rename・属性変更・directory差替え・rescan不明をincompleteとして保持し、使用点でcandidateを書かないことを合成検証します。最後の再確認後の変更や敵対的ABAは未実証です。

`test_source_hash_identity.py`はhandle identityの読取前拒否、観測サイズ超過時の早期停止、short read、空/1 MiB境界のexact hashも合成検証する。OS readのtimeoutやruntime受け入れではない。

`test_terminal_plan_usepoint.py`は終端planの独立prior/B2/contextからの再導出と、所有mutex内の候補公開前停止を合成検証する。C1比較更新やDrive/runtimeの受け入れではない。

`test_drive_content_comparison.py`はOSD-01の0/1/複数候補、完全列挙・scope・source信頼の必須性、metadata/download SHA照合と不明時保留を合成検証する。API接続や復元・archive認可は含まない。

`test_download_hash_observation.py`は合成streamのexact bytes/hash、サイズ上限/不足/途中失敗・未完了・不正chunkと、OSD-01比較へのfallback接続を検証する。実SDK/Driveやdownload成功の真正性は検証しない。

`test_drive_listing_observation.py`は内部pageの連続性/終端/重複・失敗を検査し、全page観測からdownload hash・OSD-01比較までを合成接続する。実API paginationの受け入れではない。

`test_comparison_source_revalidation.py`はPC-AのB2/実sourceからpage・download hash・同一内容比較までを合成接続し、変更・不完全・未信頼と同名別pathの境界を検証する。実Drive/出所認証/runtime受け入れではない。

`test_drive_comparison_reobservation.py`はdownload前後の完全列挙観測の集合照合と比較への接続を合成検証する。保存済み観測やmetadata一致を実再取得/現在性・archive許可へ昇格しない。

`test_comparison_source_batch.py`は複数targetを1回の全source再観測へまとめる処理と、共通page/download観測からの比較を合成検証する。空選択をno_workへ変換せず、呼出し間のcacheや実行許可を設けない。

`test_drive_comparison_batch.py`は共通Drive観測の一括検査・混在結果/順序・空入力・非認可と、source数に乗算されないfile検査を確認する。単一比較の既存境界も維持する。

`test_content_download_plan.py`は不足hash候補の計画・共有IDの一意化/安定順序・不明時保留と、合成download/一括比較への接続を確認する。計画をdownload権限や完了観測へ変換しない。

`test_planned_drive_comparison.py`は計画と完了download集合の全件整合、改変/欠落/余分/サイズ不一致と、比較結果の保留・非認可を合成検証する。

`download_staging_fixture.py` / `test_download_staging_integration.py`は自作OS-tempの新規stagingと実読戻しhash、部分file保全・別試行・競合/変更拒否を実mutex内で合成検証する。配布対象外のtests専用で、正式download writerやDry Run許可ではない。

`Test-StagingCapacity.ps1`はupload stagingの整数容量式、10%切上げ・0/巨大値・1 byte不足・型/信頼不正・容量変化を合成検証する。実volumeの容量取得や作成/Upload許可は検証しない。

`Test-StagingCapacity.ps1`は明示size配列の全件検査/合計、型付き配列/空/巨大合計・合算後の切上げ・部分合計禁止も確認する。残り対象選択やinventory真正性は外部gateに残す。

`test_staging_size_observation.py`は凍結manifest/B2から明示size集合を取り出す純粋検査を確認する。file状態から残り対象を推測せず、巨大整数・空選択・不完全/改変/別scopeの境界を扱う。

`test_staging_capacity_bridge.py` / `staging_capacity_bridge.ps1`は合成manifest/B2のsize射影→stdin JSON→PS 7.6.7容量観測→stdout整数を接続する。実行版を確認し、ローカルでは必要に応じEOLM_TEST_PWSHで固定版を指定する。tests専用で正式IPCや実容量取得ではない。
