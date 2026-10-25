# 現行実装に基づく4件の具体決定（2026-10-24）

状態：利用者の「現時点の実装状況で確定できる事項をピックアップ」「4つの具体案を確定させる」に基づく限定的な仕様決定。基準はローカルbranch `docs/selected-policy-decisions` の既存コード、既承認の[①〜㉜](selected-policy-decisions-20261024.md)。コード/schemaへの追従、正式runtime受け入れ、実OS/Drive資格、公開PR/マージを完了した記録ではない。

## 1. Drive失敗応答のretryable真偽表

[応答schema](../../contracts/drive-response.schema.json)と[現PS helper](../../Common/DriveResponseSemantics.ps1)が列挙する終了コード2〜10を、選択済み30cAの固定表として確定する。`retryable` は失敗応答で必須bool。`success: true` はexit 0、`error: null`で再試行しない。失敗時は対応する終了コード、`success: false`、`result: null`、固定error code、下表の真偽値がすべて一致しなければ拒否する。

| exit | error.code | retryable |
| ---: | --- | --- |
| 2 | `INVALID_REQUEST` | false |
| 3 | `AUTHENTICATION_FAILED` | false |
| 4 | `DRIVE_PERMISSION_DENIED` | false |
| 5 | `DRIVE_RESOURCE_NOT_FOUND` | false |
| 6 | `DRIVE_TRANSIENT_FAILURE` | true |
| 7 | `VERIFICATION_FAILED` | false |
| 8 | `INTERNAL_ERROR` | false |
| 9 | `OPERATION_TIMEOUT` | false |
| 10 | `CONFLICT_OR_AMBIGUOUS` | false |

未知code/exit、非bool、表との矛盾は拒否する。`true`は再試行の許可そのものではない。PowerShellが唯一のretry所有者として最大4回・1/5/15分を制御し、同じuploadの結果不明時は現在のDrive内容を完全かつ信頼できる形で照合するまで再送しない。timeout、応答喪失、列挙不完全を確定失敗や不在に変えない。Python/SDK/HTTPの自動retryは禁止する。

2026-10-25実装追従：[PS helper](../../Common/DriveResponseSemantics.ps1)とresponse schemaへ表を反映し、[PS試験](../../tests/Test-DriveResponseSemantics.ps1)と[schema試験](../../tests/test_contract_schemas.py)で4操作×9codeの正常/矛盾を確認する。決定当時のbool型のみの検査から厳格化した。schema versionは現1.0を維持し、従来schema-validな矛盾boolは不適合になる。外部consumer不在の証明、正式adapter/再試行orchestration/実upload照合の完成は含めない。

## 2. PC-A確認予算checkpointの最小契約

選択済み29Aの補助checkpointについて、[純粋helper](../../Common/CompletionWaitBudget.py)の状態を損失なく復元できる最小集合を次のように定める。manifestがrun結果の正本であり、checkpointは確認予算の補助状態に限る。

| 必須field | 型・制約 | 根拠 |
| --- | --- | --- |
| `checkpoint_schema_version` | integer `1` | 新しい補助契約の版。manifestの`schema_version`とは別 |
| `pc_id` | `"PC-A"` | helperのPC-A限定 |
| `log_type` | `"BattleLog"` または `"ErrorReport"` | helperのscope |
| `target_period` | BattleLogは4桁年＋`-`＋`01`〜`12`の月、ErrorReportは4桁年。年の追加制約は別途決める | helperのscope形式を維持 |
| `run_id` | UUID文字列。期待元run IDとの一致を別入力で検証 | 元runとのbinding |
| `started_at_utc` | UTC ISO 8601 `Z`日時 | 初回の適格待ち判定時刻。復旧時に再作成/延長しない |
| `check_times_utc` | UTC ISO 8601 `Z`日時の配列、0〜25件 | 各確認試行の開始前に確定する履歴 |

未知field、欠落、null、重複key、非UTF-8、不正日時、scope不一致、時計逆行、期限外・1時間未満の間隔、25件超は拒否する。配列順を保持し、UTC表記の精度を丸めて履歴を変えない。`next_check_at_utc`、成功/失敗、`may_archive`は保存しない。必要な次回時刻はhelperが履歴から導出する。実確認の前に試行1件を確定し、失敗した確認も消費する。試行確定後にクラッシュした場合も予算を戻さない。欠落/読取不能/不一致から空履歴を作らない。

保存・読取は既承認C1の同一directory一時保存・再読込検査・atomic publication/compare-before-replace、C2のmutex＋owner record、元runとscopeの独立照合に従う。具体的なfilename/root、作成時のtrusted evidence、FSのatomicity/電源断耐久性は別途資格を要する。現helperは永続化しないため、このschema・writer・readerは**未実装**である。[既存試験](../../tests/test_completion_wait_budget.py)も純粋判定の範囲である。

## 3. version 0.1.0のレビューpackage snapshot（2026-10-24）

[builder](../../.github/scripts/Build-ReleasePackage.ps1)と追跡中の[VERSION](../../VERSION)から、**現行の非配布レビュー成果物**について両role共通の40ファイルを確定する。正式入口は`SyncLogs.ps1`も`ArchiveLogs.ps1`も現ツリーにない。`PACKAGE-STATUS.txt`はレビュー成果物だけの生成物であり、正式配布packageでは禁止する。この一覧は最終runtime版のPC別file manifestへ転用しない。

```text
CHANGELOG.md
Common/AggregationArtifactReference.ps1
Common/AggregationReferencedArtifacts.ps1
Common/AggregationReportBuilder.py
Common/AggregationReportValidation.ps1
Common/ArtifactSetDirectoryVerification.py
Common/ArtifactSetPublication.py
Common/ArtifactSetRecovery.py
Common/AtomicArtifactPublication.py
Common/CompletionWaitBudget.py
Common/CrashRecoveryDecision.py
Common/DriveResponseSemantics.ps1
Common/LatestManifestSelection.py
Common/LogFunctions.ps1
Common/MachineConfiguration.ps1
Common/MachineConfigurationBootstrap.ps1
Common/MachineConfigurationRootInspection.ps1
Common/ManifestDirectoryReader.py
Common/MonthlyScheduleObservation.py
Common/OwnedRunLock.py
Common/PrivateEvidenceAclProfile.py
Common/PrivateFileSecurityDescriptor.ps1
Common/PrivateRecoveryEvidence.py
Common/README.md
Common/RecoveryDiagnostic.py
Common/RecoveryDiagnosticMutex.py
Common/RunInputEvidenceIntegrity.py
Common/SourceInventoryEvidenceBuilder.py
Common/validate_aggregation_artifacts.py
Config/PC-A.example.json
Config/PC-B.example.json
PACKAGE-STATUS.txt
README.md
VERSION
contracts/aggregation-report-v1.schema.json
contracts/manifest-v1.schema.json
contracts/private-recovery-evidence-v1.schema.json
contracts/run-input-evidence-v1.schema.json
requirements-runtime.txt
scripts/README.md
```

2026-10-25のC-01字句実装で`Common/DriveRequestPath.ps1`と`Common/DriveRequestPath.py`を追加したため、C-01時点のレビューpackageは旧40件＋2件となる。続くmanifest transition inspector 1件の追加後は43件となる。上の一覧は承認時点のsnapshotとして保持し、正式配布manifestとしない。

現在のbuilderは`Common`/`scripts`配下の許容拡張子を走査し、役割別入口の存在を確認する。選択済み31aAの将来の正式manifestでは、このようなglob走査ではなく、**各PC・各versionでファイルを明示列挙するstrict JSON＋JSON Schema**を採る。現行レビュー一覧には両roleの差分がない。最終file一覧・required/optional・manifestのfield/digest、builderの実装変更は正式入口と依存が完成してから別途決める。`docs`/`tests`/`.github`、実設定、token、ログ、private証拠を含めず、PC-Bへarchive入口を渡さない。現行packageテストは[合成試験](../../tests/Test-ReleasePackage.ps1)であり配布可の証明ではない。

## 4. owner record v1の固定境界とv2へ進む条件

[現v1 writer](../../Common/OwnedRunLock.py)が生成するrecordは`schema_version: 1`、`scope_id`、`owner_token`、`pid`、`host`の**ちょうど5field**。JSONはUTF-8、key順をソートしたcompact表現、末尾LF。scopeは1〜64文字のASCII英数字・`-`・`_`、tokenは取得時に新規生成するASCII文字列（現writerの既定は32byte乱数のhex表現）、長さ32〜256、PIDは正整数、hostは非空文字列である。現readerは重複key/未知fieldを拒否する。これは既存v1の互換基準として確定し、正常取得・releaseとv1診断/保全を維持する。

v1の`pid`/`host`/token一致は旧owner終了やmachine/boot同一性の証明ではない。v1をv2へ自動変換・補完・修復しない。v2のF1 `process_created_filetime` はcanonical十進文字列、B1 digestはrecord外の元bytes全体に対するSHA-256という既承認方針だけを固定する。v2の全field集合・数値version・token/scope制約の継承範囲、machine/boot provider、実writer、回復資格はこのv1実装からは確定できない。[v2判断資料](owner-v2-field-binding-options.md)と[論理契約](../design/recovery-owner-evidence-v2-contract.md)に従って別途選択する。合成v2構造検証が将来成功しても、実OS provider資格や回復許可にはならない。

## 検証範囲

4件は現物と承認済み方針を照合した文書決定である。アプリケーションコード、runtime schema、テスト、実設定、実ログ/Drive、task、package、PR/マージは変更しない。rootの自己点検を独立レビューとは記録しない。
