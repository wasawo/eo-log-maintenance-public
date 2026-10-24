# 初回配布までの実装棚卸し・作業順序

更新日: 2026-10-25（日本時間）。確認した正本mainは `fd9cc8a931496d31601f062bf66448ea295eec65`（PR #39マージ）。選択①〜㉜と[実装由来の限定4件](../decisions/implementation-grounded-four-decisions-20261024.md)は、PR #39で統合済みの[決定記録](../decisions/selected-policy-decisions-20261024.md)に従う。今回のretryable表追従を含む現況表であり、実環境適用の承認ではない。

[pure report builder](../../Common/AggregationReportBuilder.py)と[Drive応答の純粋な相関・終了コード・retryable真偽表検査](../../Common/DriveResponseSemantics.ps1)までが実装済み。2026-10-25にresponse schemaとPS helperへ固定retryable表を反映した。B2 V1・report G1へproducer/consumerは未追従。正式writer・Drive adapter・runtime受け入れは未完。

## 結論と配布の区別

安全基盤の独立した補助処理・スキーマ・合成テストは実装済みだが、正式な同期・アーカイブ入口とDriveアダプターは未実装。初回の実運用配布には未到達である。`scripts/` の追跡ファイルは README のみで、`SyncLogs.ps1`、`ArchiveLogs.ps1`、正式な導入・更新処理はない。

レビュー用ZIPは作れるが、`-AllowNonDeployable` による非配布マーカー付き成果物であり、導入可能なリリースではない。現行0.1.0レビュー成果物の[40ファイル一覧](../decisions/implementation-grounded-four-decisions-20261024.md)は確定済み。通常のビルドは正式入口不在を拒否する。入口ファイルの存在によるdeployable判定も、処理の安全性・完成の証明ではない。VERSIONの `0.1.0` は配布実績を意味しない。

初回実運用配布の前提は既存計画どおりPC-Aの同期・検証・アーカイブとPC-Bの同期・検証、各端末への手動導入である。PC-Bだけの先行配布などへの縮小は、この棚卸しでは決めない。定期実行は手動運用の受け入れ後に進める。

## 実装済みの範囲と限界

| 分野 | 現在あるもの | 初回運用までの主な不足 |
| --- | --- | --- |
| 設定 | [厳密な設定読取](../../Common/MachineConfiguration.ps1)、[create-only生成](../../Common/MachineConfigurationBootstrap.ps1)、両PCの安全なexample、maintenanceLocalの字句的分離 | 正式導入入口、実root認可、実効権限・祖先・利用直前までの保護。example生成後の実値は各PCのGit管理外設定へ手動入力 |
| ファイル選択 | [日付・期間等の共通処理](../../Common/LogFunctions.ps1)、[完全列挙・ハッシュ証拠構築](../../Common/SourceInventoryEvidenceBuilder.py) | 正式runへの接続、列挙後の変更と利用までの整合性 |
| root検査 | [既存Windowsディレクトリの読取専用metadata検査](../../Common/MachineConfigurationRootInspection.ps1) | 対象FS・ACL・実トークンの認可、安全な生成と継続利用の資格確認 |
| 証拠・集約 | [contracts](../../contracts/)、[A2/B2検証](../../Common/RunInputEvidenceIntegrity.py)、[参照成果物検証](../../Common/validate_aggregation_artifacts.py)、[pure report builder](../../Common/AggregationReportBuilder.py)、条件付き採用済み状態遷移表 | B2 V1・report G1への追従、実run writer/遷移強制、決定的再生成・意味論的統合、Drive反映 |
| 公開・クラッシュ | [単一ファイル公開](../../Common/AtomicArtifactPublication.py)、[marker-last公開](../../Common/ArtifactSetPublication.py)、復旧分類・ディレクトリ検証 | 永続run状態・処理全体との接続。複数ファイルの原子的トランザクションや電源断耐久性の証明はない |
| 排他・manifest選択 | [所有run lock](../../Common/OwnedRunLock.py)、[最新候補選択](../../Common/LatestManifestSelection.py)、読取adapter | 旧lockの自動引継ぎはしない。実owner証拠、復旧手順、新runとfresh inventoryの作成、実環境での統合 |
| 明示回復 | 診断・専用mutex、[private証拠のメモリ上のbinding](../../Common/PrivateRecoveryEvidence.py)、供給ACL/descriptorの検査、v1の5field互換境界 | v2の全fieldと適格machine/boot provider、実効ACLと保存先検証、非公開の実保存。v1は診断・保全限定 |
| 月次・確認上限 | [月次観測](../../Common/MonthlyScheduleObservation.py)、[24時間・初回含め25回の確認予算](../../Common/CompletionWaitBudget.py)、補助checkpointの最小field契約 | 信頼できる永続writer/readerと原子的試行計上、時計/session/account/ACとの接続、未実行補完・毎時確認・正式task |
| Drive | request/response schema、[相関・終了コード・固定retryable表の純粋helper](../../Common/DriveResponseSemantics.ps1)、P1/V1/L1・R1/N1/D1 | C-01/C-02のschemaと具体result形、公式Python client adapter、Desktop OAuth/drive.fileの実folder資格、PS retry統合・結果不明upload照合 |
| 配布 | 役割別ビルダー、example検査、PC-Bのarchive除外、現行0.1.0の非配布レビュー一覧 | 正式入口、PC別/version別の最終JSON file manifest、tag/VERSION/commitのprovenance、E1承認後Actions配布用identity、Drive内容検証、手動導入・専用PS移行・復旧 |

個別helperの成功を正式ランタイムの受け入れに読み替えない。詳細な安全ゲートは [runtime gate](../design/runtime-entrypoint-validation-gate.md)、[対象FS受け入れ](../validation/target-filesystem-acceptance.md)、[P0台帳](../requirements/p0-gap-register.md) を維持する。

## 初回配布までの依存順序

| 順序 | 作業と具体的成果物 | 次へ進む条件 |
| --- | --- | --- |
| 1 | 確定済み方針を実行可能な契約へ落とす。C-01 P1/V1/L1と現IPC 1.0改訂、C-02の4操作別closed executed/plan field表、Dry Run Aのfile-free IPC、B2 V1/G1、採用済みmanifest遷移表をschema/仕様/fixtureへ整合。固定retryable表はschema/PS helperへ追従済み。owner-v2全field・provider、credential store/SDK/配布identityなど未選択の詳細は別に決定 | 方針済み/詳細未決/実装未了を分け、未知field・結果不明・資格不足を既定値で補わない。retryable表適合を再送の認可やRETRY-02統合完了にしない |
| 2 | ローカル安全基盤を統合する。実root・token・ACL・祖先・使用点、C1〜C4に従う永続run/manifest、補助checkpointの信頼できる保存と試行前計上、明示回復/private証拠を合成・使い捨て領域で検証 | 所有権・クラッシュ・競合・証拠喪失時に保留できる。v1 ownerからv2を補完せず、machine/boot provider未資格のまま実回復しない。checkpointだけで全基盤完了とはしない |
| 3（2と並行可） | Google公式Python clientで4操作のDrive adapterとPS/Python IPCを合成応答で実装。multipart初期上限、Python/SDKの暗黙retry/page禁止、PS側の4回/1・5・15分制御、不明upload照合を確認 | 契約・障害・全page・結果不明の合成試験成功。I1/A1/S1/T1方向と実folder可視性/権限/所有/quotaの適合は別途承認された限定計画で確認し、不適合を「不在」に変えない |
| 4 | 両PCの対象ローカルvolumeでTier Bを完了し、root/FS/ACL/atomicityの資格を確認 | PC-B部分証拠を全体受け入れにしない。PC-Aも含む全項目と対象volume証拠を揃える。電源断耐久性は別に検証する |
| 5 | 正式な手動Sync入口とPC-A専用Archive入口を実装。凍結inventory、manifest/B2/report writer、G1再生成、排他・復旧・現在Drive照合を接続。初期inventory/復元は通常成功runと分離 | PC-A同期に続くarchive判定でも明示許可・両PC証拠・現在Drive内容が必須。copy/verify/recordのみ。PC-B archiveなし、元ログ/Drive削除なし。Dry Run Aを維持 |
| 6 | P0全体の追跡表、失敗・競合・クラッシュ・no-deleteのE2Eと両役割package検証。Tier B後、別途承認した専用使い捨て同期/ネットワーク領域のTier Cを実施 | P0-010/P0-012を含む受け入れ証拠が揃う。CI成功だけで代替しない。実ログ・本番Driveを通常テストに使わない |
| 7 | 正式配布・導入を仕上げる。PC別/version別の明示file JSON manifest、tag/VERSION/commit/package照合、E1 releaseイベント＋maintainer手動承認後のActions公開、versioned upload→内容検証→latest更新、手動差分確認・実設定保持・専用PS移行・rollback | 現行0.1.0の40ファイルは非配布レビュー用で、最終allowlistではない。全version保持/自動cleanupなし。配布identity/provenance、最終fileと移行mappingを確定・検証してから公開。配布設計作業は前段と並行可能 |
| 8 | 別途明示承認のもと初回配布・限定的な手動適用。手動受け入れ後に毎月1日PC-B 20:00/PC-A 21:00 JST、月内未実行補完、PC-Aの24時間/25回確認とローカル通知をtaskへ接続 | 初期は各PCで同じ実行accountのログオン中・AC接続時のみ、処理のためのwakeなし。AC切断・確認履歴/通知失敗を成功にしない。task登録/本番適用は別の実行許可 |

## 再判断が必要なもの／不要なもの

- 方針決定済み: ①〜㉜、OSD-02の条件付き規範遷移、OSD-04のDry Run A、OSD-05のI1/A1/S1/T1と暗号化専用file方向、OSD-06のE1/Actions公開方向、OSD-07の全version保持、OSD-09のPC別/version別明示manifestと専用移行、OSD-08の時刻/ログオン/account/AC/wake。第10回の限定4件も[別記録](../decisions/implementation-grounded-four-decisions-20261024.md)に確定。
- 詳細未決/資格待ち: C-02の結果field、owner-v2全fieldと適格provider、具体store API/ACLとSDK資格、実folderのS1可視性、CI配布identity/provenance、正式runtimeの最終file一覧/移行mapping、通知登録・重複抑制、checkpoint保存root/FS資格とAC切断時の停止境界。実装・試験・Tier B/C・手動runtime受け入れも未完了。
- 専用の明示回復、v1診断・保全、maintenanceLocal内のprivate保全と自動削除なし、各PC内の手動/task同一account、PC-A確認最大24時間/25回等は再質問しない。private証拠・元ログ・Driveログの保持と配布package保持は別。どちらにも自動削除を追加しない。

## 検証証拠と今回の変更範囲

- PR #39のmainで [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40105135888) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40105134099) が成功した。今回のretryable実装はローカル検証まででPR/CIは未実施。[現行handoff](../handoff/next-chat.md)に対象試験と環境差を記録する。
- 旧棚卸し基準のローカル結果は当時Python 3.11.9で306件（2件skip）、PowerShell 7.6.7の配布回帰成功。現mainの全検査件数やruntime受け入れ値に流用しない。CI Pythonはworkflowを基準とし、最終導入環境の前提と依存導入も配布時に確認する。
- PC-Bのローカルvolume・reparse・crash・source・lock証拠は段階的な部分検証で、件数を足して独立した受け入れ総数としない。最新lock証拠のsource SHAは `302682abb7fd3b45b6745247dfa5297542f81c4b` で現在HEADとは異なり、Tier Bは明示的にincomplete。PC-Aのvolume受け入れは未収集、Tier Cは未実施。電源断/実再起動耐久性は未証明。
- 今回は固定retryable真偽表のschema/PS helper/合成試験と関連文書を更新した。全要件行の再監査や公開情報の網羅的再監査を完了したという意味ではない。
- 旧PR・CI・部分Tier B証拠は当時の履歴として保持する。現在の作業順序と未完はこの表と[現行handoff](../handoff/next-chat.md)を参照する。
