# ランタイム安全性テストシナリオ

- 状態：レビュー用ドラフト
- 対象：PowerShell の同期・アーカイブ制御、および Python Drive アダプターとの連携
- 前提：本書は期待動作を定義する。実行時スクリプトが未実装の項目は、テスト合格済みを意味しない。
- 安全原則：検証不能・不一致・欠落・期限切れ・タイムアウト・曖昧な結果はすべて失敗として扱い、元データを保持する。初期実装にはローカル元ファイル削除・Drive削除の機能自体を含めない。

## 1. テスト実施ルール

1. 実ログ、実運用パス、実際の Google Drive データを使わず、一時ディレクトリ、合成ファイル、模擬 API 応答、合成マニフェストを使う。
2. 初期実装のテストで実際の削除操作を呼び出さない。削除コード・操作・設定が存在しないことを静的検査や契約テストで確認する。
3. 各ケースで、終了コード／処理結果、生成マニフェスト、構造化ログ、元データとコピー先データの存在、SHA-256 を記録する。
4. 異常系では、単にエラーが返るだけでなく、同期元ファイルとDrive上の元データが保持されることを確認する。
5. 時刻は固定クロックまたは注入可能なテスト時刻を用いる。マニフェストの鮮度判定を実時間に依存させない。
6. 「クラウド確認済み」は Drive for desktop のローカルフォルダー上の存在ではなく、Drive API によるクラウド側の識別・状態確認を意味する。API が SHA-256 を提供しない場合は、API経由でダウンロードしてSHA-256を計算する。検証不能なら失敗とし、元データを保持する。

## 2. 共通テストデータ

- PC-A / PC-B の役割と設定が有効な正常構成
- 同一内容ファイル：同じファイル名・同じ内容・同じ SHA-256
- 競合ファイル：同じファイル名・異なる内容・異なる SHA-256
- マニフェスト：有効、欠落、破損、失敗状態、期限切れ、期間不一致、ログ種別不一致、実行 ID 不一致
- Drive API 応答：正常、権限エラー、Not Found、429/5xx、タイムアウト、曖昧な複数候補、必要なメタデータ不足
- 実行状態：未実行、実行中、成功（0件）、成功（1件以上）、一部失敗、失敗

## 3. 同期・コピー検証シナリオ

| ID | 分類 | 初期条件／操作 | 期待結果・合格条件 |
|---|---|---|---|
| SYNC-01 | 正常系 | 元ファイルをステージング先へコピーし、コピー後の SHA-256 を計算する | 元とコピーの SHA-256 が一致。検証完了を記録し、対象ファイルを成功として扱う |
| SYNC-02 | 正常系・冪等性 | 同名のコピー先ファイルが存在し、SHA-256 が元と一致する | 不要な再コピーを行わず、同一内容の重複として記録。別ファイルを作成・削除しない |
| SYNC-03 | 異常系 | 元ファイルが存在しない | 失敗。成功マニフェストを作成せず、削除操作を呼び出さない |
| SYNC-04 | 異常系 | コピー先ファイルが欠落、またはコピー途中で切り詰められている | 検証失敗。元ファイルを保持し、コピーを検証済みと記録しない |
| SYNC-05 | 異常系 | コピー後の内容を変更し、SHA-256 を不一致にする | 検証失敗。元ファイルを保持し、同期完了扱いにしない |
| SYNC-06 | 競合 | 同名のコピー先ファイルが元と異なる内容を持つ | 上書きしない。仕様に従って安全な別名を決定できる場合のみ別名保存し、できなければ競合として停止 |
| SYNC-07 | 競合 | _PCA / _PCB 付きの候補名も異なる内容で既に存在する | 上書き・削除・推測による名前変更を行わず、競合エラーとして停止 |
| SYNC-08 | クラウド確認 | Drive for desktop のローカル同期フォルダーにファイルが見えるが、Drive API でクラウド側の存在を確認できない | クラウド確認未完了として扱う。元ファイルを保持 |
| SYNC-09 | クラウド確認 | API で候補が複数見つかり、対象ファイルを一意に特定できない | 曖昧性エラー。候補を暗黙に選ばず、元ファイルを保持 |
| SYNC-10 | クラウド確認 | API応答に必要な識別情報がない、またはクラウド側SHA-256が取得できない | SHA-256がない場合はAPI経由でダウンロードしてハッシュを計算する。識別不能・ダウンロード不能・ハッシュ不一致なら失敗し、元ファイルを保持 |
| SYNC-11 | API異常・再試行 | APIが認証失敗、権限拒否、429/5xx、タイムアウトを返す | Pythonは1回だけ試行する。PowerShellは一時的エラーのみ初回を含む最大4回（待機1分・5分・15分）で再試行し、恒久エラーは再試行しない。HTTPクライアントの暗黙の再試行もないことを確認し、元ファイルを保持 |
| SYNC-12 | 回復 | 同期に失敗した期間を、原因修正後に再実行する | 前回の未完了ファイルを再処理できる。既存の異なる内容を上書きせず、二重処理を成功扱いにしない |

## 4. マニフェスト／両 PC 完了条件シナリオ

| ID | 分類 | 初期条件／操作 | 期待結果・合格条件 |
|---|---|---|---|
| MAN-01 | 正常系 | PC-A と PC-B の双方に、対象期間・ログ種別・実行 ID が対応し、成功かつ検証完了のマニフェストがある | 他の安全条件も満たす場合に限り、後続アーカイブ判定へ進める |
| MAN-02 | 異常系 | PC-B のマニフェストが存在しない | PC-A のアーカイブをブロック |
| MAN-03 | 異常系 | PC-B のマニフェストが失敗または一部失敗状態 | PC-A のアーカイブをブロック |
| MAN-04 | 異常系 | PC-B のマニフェストが許容鮮度を超えて古い | PC-A のアーカイブをブロック。古い記録を最新の完了証明として流用しない |
| MAN-05 | 異常系 | マニフェストの対象期間が処理対象と一致しない | PC-A のアーカイブをブロック |
| MAN-06 | 異常系 | マニフェストのログ種別（BattleLog / ErrorReport）が対象と一致しない | PC-A のアーカイブをブロック |
| MAN-07 | 異常系 | マニフェストが不正 JSON、必須フィールド欠落、未知バージョン、または実行 ID 不一致 | 検証失敗として停止。成功扱いにしない |
| MAN-08 | 境界値 | 対象期間の処理対象が0件で、明示的な成功スキップのマニフェストがある | 「正常に処理した結果0件」として扱える。未実行状態とは区別する |
| MAN-09 | 異常系 | スクリプトが未実行で、マニフェストがない、または前回のマニフェストしかない | MAN-08 と区別し、PC-A のアーカイブをブロック |
| MAN-10 | 異常系 | 片方の PC が成功、もう片方が未実行・実行中・失敗 | 両 PC 完了とはみなさず、PC-A のアーカイブをブロック |

## 5. アーカイブ安全条件シナリオ

| ID | 分類 | 初期条件／操作 | 期待結果・合格条件 |
|---|---|---|---|
| ARC-01 | 正常系・Dry Run | PC-A で有効な両 PC マニフェストと検証済み Drive ファイルを用いて Dry Run を実行 | 対象・予定操作を報告するが、アーカイブ／Drive／元ファイルの削除は一切行わない |
| ARC-02 | 正常系・検証順序 | PC-A がDriveファイルをアーカイブ先へコピーする | アーカイブ先のSHA-256と対象ファイル集合を検証し、結果を記録する。Drive上の元ファイルは削除しない |
| ARC-03 | 異常系 | アーカイブ先のファイルが欠落・破損、SHA-256 不一致、または対象ファイルの一部が未処理 | Drive 元ファイルを保持し、アーカイブ処理を失敗とする |
| ARC-04 | 役割制約 | PC-B 設定でアーカイブ／削除入口を呼び出す、または設定の役割値を偽装する | 処理を拒否し、ファイル／Drive データを変更しない。PC-B 配布物にアーカイブ入口を含めない |
| ARC-05 | 異常系 | PC-Aの設定、許可ルート、役割、または `allowArchive` が欠落・不正 | フェイルクローズし、アーカイブを開始しない |
| ARC-06 | 異常系 | アーカイブ直前または検証直後に API がタイムアウトし、状態が不明になる | 結果不明として停止。Drive 元データを削除しない |
| ARC-07 | 初期実装の能力制約 | リポジトリと配布物を検査する | ローカル元ファイル削除・Drive削除のコード、操作、設定が存在しない。削除操作を呼び出さず、検査結果を記録 |
| ARC-08 | 回復 | コピー成功後、検証またはマニフェスト更新の前にプロセスを中断し再実行する | 再実行時にDrive元ファイルとアーカイブ先を照合する。アーカイブ先にファイルがない場合は再コピー候補として扱い、コピー後にSHA-256を検証する。同名ファイルがありSHA-256が一致する場合は内容一致を確認して結果記録を回復する。同名ファイルのSHA-256が不一致の場合は上書き・削除せず競合として停止する。Drive側またはアーカイブ先の存在・内容を確認できない場合も停止し、Drive元ファイルを保持する。検証・結果記録が完了するまで成功扱いにしない。
| ARC-09 | 初期実装の能力制約 | 設定例・スキーマ・ソース・配布物を検査する | `allowDelete` および削除操作が存在しない。Dry Runやコマンドライン引数で削除機能を有効化できない |

## 6. Python アダプター連携シナリオ

| ID | 分類 | 初期条件／操作 | 期待結果・合格条件 |
|---|---|---|---|
| IPC-01 | 異常系 | Python の終了コードが0以外 | JSON の内容にかかわらず呼び出しを成功扱いにしない |
| IPC-02 | 異常系 | stdout が空、JSON 不正、複数 JSON、JSON 以外の文字列を含む | 連携失敗として停止。結果を利用しない |
| IPC-03 | 異常系 | レスポンスの request_id または operation がリクエストと不一致 | 連携失敗として停止。結果を利用しない |
| IPC-04 | 異常系 | 終了コードと JSON の success が矛盾する | 連携失敗として停止 |
| IPC-05 | 異常系 | PowerShell が子プロセスをタイムアウトで終了させる | タイムアウトとして記録し、成功や未実施と推定せず、破壊的処理を行わない |
| IPC-06 | セキュリティ | 標準出力・標準エラー・運用ログにトークン等の秘密情報を含む模擬例外を渡す | 秘密情報がログに出力されない。固定エラーコードとマスキング済み情報のみ記録 |

## 6.1 再試行・アップロード結果不明シナリオ（C-29）

| ID | 分類 | 初期条件／操作 | 期待結果・合格条件 |
|---|---|---|---|
| RETRY-01 | アダプター再試行制御 | 模擬APIが成功または失敗を返すアダプター呼び出しを行う | 1回のPythonアダプター呼び出しにつきAPI試行は厳密に1回。HTTPクライアント／ライブラリの暗黙の再試行も発生しない |
| RETRY-02 | オーケストレーター再試行制御 | PowerShellに一時エラー、恒久エラー、検証失敗を順に注入する | PowerShellだけが再試行を制御し、初回込み最大4回・待機1/5/15分を守る。認証、権限、入力不正、検証失敗、競合は原因解消なしに再試行しない |
| RETRY-03 | 不明結果の照合 | Driveへのアップロードは成功したが、応答受信前にタイムアウトした状態を模擬する | 再アップロード前にDriveを照合する。一意に特定でき、信頼できる内容検証が一致した場合は既存アップロードを完了として照合し、重複アップロードしない |
| RETRY-04 | 確認済み不在 | アップロード結果が不明で、Driveへの完全かつ成功した一覧・照合結果が対象の不在を示す | 不在確認を受けてからのみ再試行候補とする。試行上限を守り、ソース／ステージングを保持する |
| RETRY-05 | 照合不能・一覧不完全 | Drive照会の権限エラー、タイムアウト、途中ページ失敗、ページネーション未完了、応答欠落を模擬する | 不在と推定しない。結果不明として停止し、再アップロード・成功判定・アーカイブ・クリーンアップを許可しない |
| RETRY-06 | 競合・信頼性不足 | 同名別親、複数候補、サイズ／ハッシュ不一致、識別情報不足、未マークの既存オブジェクトを模擬する | 任意候補を選択・上書きしない。フェイルクローズする。未マークオブジェクトの受入れはOSD-01の承認までブロックする |

実装状態：この表は期待動作の追加であり、ランタイム実装やテスト合格を示さない。RETRY-01〜06は未実装／未実施。成功した完全な照合による不在と、照合失敗・部分一覧・曖昧性による不明状態を区別する。

## 7. テスト結果の判定基準

各ケースは次のすべてを満たした場合に合格とする。

- 期待する成功／失敗の判定と一致する。
- 異常系・不確実系では、対象の元ファイルとDrive元データが保持されている。
- SHA-256 を確認するケースでは、実測値と期待値を比較している。
- マニフェストが処理実態を正しく表し、失敗や未実行を成功と誤記していない。
- ログに判定理由が記録され、秘密情報が含まれていない。
- Dry Runでは、アップロード・最終配置・アーカイブ配置・削除などのデータ変更が発生していない。

いずれかの条件が確認できない場合は「合格」ではなく「未検証」とする。

## 8. 実装順序

1. **優先度 P0：** SYNC-01、SYNC-03～05、SYNC-08～11、RETRY-01～06、MAN-02～10、ARC-01～07、IPC-01～05
2. **優先度 P1：** SYNC-02、SYNC-06～07、SYNC-12、ARC-08～09、IPC-06
3. これらを一時ディレクトリと模擬 Drive アダプターで自動化する。
4. テスト合格は削除機能の実装・有効化を許可しない。初期実装のテストでは削除機能が存在しないことを確認する。


## OSD-02 crash/concurrency test requirements — pending execution

- Inject crashes before/during temporary write, after flush/validation, before publication, and after publication; prove incomplete temp files are never authoritative and failed publication leaves prior content unchanged.
- Race concurrent first publishers and concurrent updates; prove create-if-absent and compare-before-replace prevent overwrite.
- Test named-mutex contention/failure, process termination, lock ownership-token mismatch, and stale-lock recovery. Age/PID alone must not authorize lock removal.
- Preserve crash-left `running` manifest byte-for-byte; after verified owner recovery, create a new `run_id` with a fresh inventory; reconcile uncertain uploads before retry.
- Test unique latest timestamp, equal maxima, malformed or identity-mismatched candidates, read/enumeration failure, and latest non-success blocking fallback to older success.
- Use synthetic fixtures and temporary directories only. Evidence status: **not run / not yet evidenced**; no runtime acceptance is implied.


## OSD-03 report-contract acceptance tests — approved design, execution pending

1. Required fields, strict integer schema version, unsupported versions, no implicit migration, and absence of report_id.
2. Canonical report identity tuple and filename agreement for PC/log type/run/schema version.
3. Canonical relative manifest_ref and evidence_ref; exact bytes SHA-256; malformed digest, absolute/traversal path, identity mismatch, and stable-path content replacement all fail closed.
4. R1-B: report period rows contain summaries only; counts recompute from the referenced manifest and B2 evidence; no duplicated per-target inventory is trusted from the report.
5. Inventory digest/count mismatch; missing, extra, duplicate, or multiply assigned target; missing/duplicate period row; report/manifest/evidence identity mismatch; inconsistent error scope.
6. R6-A: complete, incomplete, and indeterminate boundaries; indeterminate never becomes complete and these values never enter manifest v1 run-status enums.
7. R4-A publication crash points, concurrent create, identical idempotent retry, conflicting retry, unsupported atomic primitive, mutex/lock ownership, and temp-file ownership cleanup. Orphan cleanup cannot rely on age alone.
8. R5-A regeneration only from exact immutable manifest and B2 evidence; refuse if evidence is missing, corrupt, incomplete, or inconsistent; never rescan mutable source.
9. R7-A local publication succeeds independently of Drive replication; replication failure preserves local report; cross-PC use is blocked until identity and content verification succeeds.
10. UTC timestamp format/future tolerance, historical age, zero-work versus failed enumeration versus only-invalid filenames, known-period completion with unrelated run-scope errors, and all approved OSD-03 aggregation cases.
11. Synthetic fixtures and temporary directories only. No real logs, credentials, production paths, Drive writes, archive enablement, or deletion. Evidence status: **not run / not yet evidenced**.


## OSD-03 executable schema implementation slice — PR #150 (2026-10-21)

- Added `contracts/aggregation-report-v1.schema.json` as a strict Draft 2020-12 structural schema candidate for the approved R1–R7 report shape. It rejects unknown properties, `report_id`, unsupported/non-integer report schema versions, invalid enums/count types, non-UTC-Z timestamps, malformed lowercase SHA-256 values, and non-canonical relative paths.
- Added schema-definition and synthetic structural-contract tests in `tests/test_contract_schemas.py`. They cover partial-failure and zero-work examples, all three period completion values, strict versioning, unknown fields, reference path/hash validation, timestamp form, enums/counts, and run-scope error shape.
- These tests are authored but **not yet executed/evidenced** in this PR. CI must pass on the exact latest PR HEAD before merge. No runtime report reader/writer, cross-artifact digest verification, tuple/path binding, count recomputation, deterministic regeneration, atomic publication, lock integration, or Drive replication implementation is included in this slice.
- The JSON Schema validates structure only. Cross-field and cross-artifact invariants remain mandatory fail-closed runtime checks; schema acceptance alone is not proof of report correctness or authorization for any side effect.
- No manifest v1 fields, B2 evidence contract, A2 digest contract, or OSD-02 safety boundaries are changed. No real logs, credentials, production paths, Drive writes, archive enablement, or deletion.


## PR #151 status note — OSD-03 internal consistency slice (2026-10-22)

PR #150 merged the structural aggregation-report v1 JSON Schema and its synthetic schema tests; PR-head and post-merge CI passed. PR #151 adds a report-local PowerShell consistency validator and synthetic tests for period uniqueness, safe reference paths/digest shape, summary count reconciliation, completion consistency, run-scope error count, and zero-work/success consistency. Until PR #151 CI passes on its exact latest HEAD, these tests are authored but not yet verified. This slice does not validate exact referenced manifest/evidence bytes, B2/A2 integrity, full target-set completeness, cross-artifact identity, deterministic regeneration, atomic publication, lock ownership, or Drive replication. P0 acceptance remains open.

## OSD-03 status correction — 2026-10-22

PR #151 is merged at `e93f0ea552496831c69efb1e8dd2818ac86f4e5b`. Validate and Package Validation passed on exact PR HEAD `846cfdbb1ce76f3ec1363460c4f0576b7c10a2b6` (runs `39635268289`, `39635268115`) and on the post-merge commit (runs `39636402422`, `39636402408`). The report-local consistency validator is now implemented and CI-verified within its stated scope. PR #152 adds a narrow exact-byte reference verifier; its tests are not yet CI-verified. Neither PR implements full manifest/B2 schema validation, identity binding, A2 digest recomputation, exhaustive target/count reconciliation, deterministic report regeneration, atomic publication, lock recovery, or Drive replication. P0 acceptance remains open.

## 9. Lock ownership and crash-recovery acceptance IDs (OSD-02; pending execution)

The normative acceptance boundary for the next lock/recovery implementation slice is `docs/validation/lock-recovery-acceptance-gate.md`. The following IDs are traceability anchors; they are test requirements, not evidence that tests have run.

| ID | Scenario | Required result |
|---|---|---|
| LOCK-01 | First acquisition | One owner obtains the named mutex and exclusive token record. |
| LOCK-02 | Concurrent acquisition | Wait no more than 60 seconds; if still held, exit before any side effect. |
| LOCK-03 | Ownership token mismatch | Do not update or remove another owner's record. |
| LOCK-04 | Old timestamp with live owner | Age alone does not permit takeover. |
| LOCK-05 | PID reuse/dead PID ambiguity | PID alone is not ownership proof. |
| LOCK-06 | Abandoned mutex and valid record | Run explicit owner/record/prior-state validation before recovery. |
| LOCK-07 | Abandoned mutex with malformed/mismatched record | Fail closed and preserve lock record and artifacts. |
| LOCK-08 | Existing lock record | Exclusive create fails without overwrite. |
| LOCK-09 | Mutex unavailable or OS error | No inventory, manifest, staging, Drive, archive, or delete side effect. |
| LOCK-10 | Normal release | Remove only matching token record and release mutex safely. |
| REC-01 | Crash before artifact publication | Temporary artifact is not authoritative. |
| REC-02 | Crash after running manifest publication | Keep published manifest complete and byte-for-byte unchanged. |
| REC-03 | Crash during lock-record update | Partial/malformed record is never trusted. |
| REC-04 | New run after validated recovery | Use new run_id, fresh inventory/states, and preserve old manifest. |
| REC-05 | Unknown upload reconciles to matching content | Verify current content and avoid duplicate upload. |
| REC-06 | Drive listing incomplete/ambiguous | Keep outcome unknown; do not retry or clean up. |
| REC-07 | Equal latest timestamps or identity mismatch | No arbitrary winner and no fallback to older success. |
| REC-08 | Recovery interrupted again | Fail closed without ownership theft or data loss. |

All cases require synthetic fixtures, injected process/clock state, and explicit assertions about source/archive/Drive preservation. Status: not run; no runtime acceptance is implied.

## 10. OSD-04 Dry Run提案用受け入れfixture計画（未実装・未実行）

部分実装: `tests/test_dry_run_boundary.py` が合成dispatcherの拒否経路と依存呼出しを別プロセスで検査する。9テスト/33probeは限定ハーネスの証拠で、下表の正式runtime/実root/実排他のfixtureを実行済みとするものではない。実 `acquire_diagnostic_mutex` helperを監査下でimport/実行し、test-only mutexによる取得成功でも資格未完で停止、timeout/abandoned/create/acquire/observation/cleanup失敗の拒否、取得・lease body・cleanup中のwrite拒否、finally履歴と既存物不変を検査する。fakeはWindows mutexのidentity/access・writer共通scope資格を証明しない。以下の未実装・未実行はそれら全受け入れ対象についての状態。

対象は[利用者承認済みのA方針](../decisions/dry-run-side-effect-policy-proposal.md)。**Aを採用、以下のDRY fixtureは未実装・未実行**であり、既存helperのテスト結果や本書の既存シナリオを成功証拠として転用しない。規範契約とAの期待値を照合してから実装する。Bの書込みを許すテストは採用しない。

合成データ・隔離領域・mockのみを使う。fixtureごとに元ログ、archive、Drive同期領域、maintenanceLocal（運用manifest/report/frozen inventory/marker/lock/private証拠/budget/scheduler状態を含む）、config、credential/temp領域のbefore/afterを採取する。相対名・存在・bytes/hash・適用可能なACL/所有者を比較し、アプリのcreate/write/rename/delete/ACL変更の呼出しも捕捉する。最終snapshot一致だけでは途中の書込み後削除を見逃すため、呼出し履歴と併用する。OS自動atime等は別観測とし、物理書込みzeroの証明にしない。

mock Driveのbefore/afterと呼出し履歴を照合し、mutation、upload、download bytes取得が0回であることを確認する。liveネットワーク・認証refresh/storeを拒否するmockも使う。Aでは診断report・一時物・cleanupも許さず、途中書込みを含め履歴を検査する。診断は入力由来・観測時点・未検証状態を保ち、runtime authorizationやcloud内容確認済みへ変換されないことを確認する。

| 新規ID | 既存シナリオとの対応 | fixture / 注入条件 | 承認済みAで検証する期待結果 |
|---|---|---|---|
| DRY-01 | ARC-01、SYNC-01/08、MAN-01/08 | PC-A sync/archive候補、PC-B sync候補、正常/0件をAで実行 | 予定操作のみ。元/Drive/archive無変更、mutation/download呼出し0。運用run・成功manifest・完了状態を作らない |
| DRY-02 | MAN-02–10、REC-01/02/04 | 既存manifest/report/frozen inventory/private原本、成功・不正・欠落を配置 | 運用証拠を作成・修復・再生成・削除しない。既存private原本を保持し、0件も運用成功にしない |
| DRY-03 | LOCK-03–08/10、REC-03/08 | live/stale/不正/別ownerのordinary lock record、abandoned診断mutex | record作成・heartbeat・解除・stale処分0。自動回復・新run0。abandoned/所有不明は停止、既存物不変 |
| DRY-04 | LOCK-02/09、IPC-05 | writerとの同時起動、mutex取得失敗、読取り中の証拠/経路変更 | 安定した観測を保証できなければ保留。writerの所有権を奪わず、timeoutで運用stateを書かない |
| DRY-05 | ARC-04/05、IPC-01–04 | PC-B archive要求、役割偽装、無効config、未作成config/root、root分離/ACL/reparse不正 | ファイル/Drive変更前に拒否。bootstrap、directory作成、既存ACL修復なし。PC-Bにarchive能力を追加しない |
| DRY-06 | SYNC-08–11、REC-05/06 | hashなし、曖昧/不完全metadata、供給snapshot、refresh必須credential | download fallback・live認証0、未検証を維持。snapshotを現在cloud内容の証拠にしない。OSD-05未解決中はlive readも0 |
| DRY-07 | IPC-01–06 | Aで通常IPC/log/temp/cache書込みを要求する依存、模擬token例外 | ファイル書込み呼出し0。ファイル不要経路が不成立なら停止。stdout JSON 1件とstderr分離を維持し、秘密を出さない |
| DRY-08 | IPC-05/06、REC-01/08 | 未採用Bのreport/temp出力をAで要求、衝突、disk/ACL失敗、途中強制終了 | report/temp作成・上書き0。書込みへfallbackせず停止。運用成功0、既存private原本・証拠を保持 |
| DRY-09 | LOCK-03、REC-01/08 | 過去の診断一時物、他owner物、古い残骸、cleanup要求とpath差替え | Aでは所有が確認できてもcleanup 0。残骸を保持し状態を報告。private/元ログ/Drive無変更 |
| DRY-10 | MAN-08–10、ARC-01 | confirmation budgetとscheduler完了記録を配置し、診断成功/失敗/0件/再実行 | 予算消費/reset・完了更新0。診断IDを運用runに流用せず、後続実処理はその時点で再検証 |

各実行では選択案、実装SHA、fixture版、mock呼出し数、before/after差分、途中失敗・role/race負例の結果、未確認範囲を公開可能な合成証拠として記録する。既存LOCK/RECの運用record作成・回復やSYNC-10のdownload期待値をDry Runへ流用しない。本節はその差分を検証する計画であり、テスト成功、実環境FS耐久性、cloud同期、Phase 1/7またはP0受け入れの証明ではない。
