# 初回配布までの実装棚卸し・作業順序

確認日: 2026-10-24（日本時間）。基準は main `9fc85477907c169454104fe2b88b2933d855856f`（PR #27マージ）。仕様や承認を変更する文書ではなく、実装と未完了事項を結び直した現況表である。

## 結論と配布の区別

安全基盤の独立した補助処理・スキーマ・合成テストは実装済みだが、正式な同期・アーカイブ入口とDriveアダプターは未実装。初回の実運用配布には未到達である。`scripts/` の追跡ファイルは README のみで、`SyncLogs.ps1`、`ArchiveLogs.ps1`、正式な導入・更新処理はない。

レビュー用ZIPは作れるが、`-AllowNonDeployable` による非配布マーカー付き成果物であり、導入可能なリリースではない。通常のビルドは正式入口不在を拒否する。入口ファイルの存在によるdeployable判定も、処理の安全性・完成の証明ではない。GitHubの公開済みReleaseは確認時点で0件。VERSIONの `0.1.0` は配布実績を意味しない。

初回実運用配布の前提は既存計画どおりPC-Aの同期・検証・アーカイブとPC-Bの同期・検証、各端末への手動導入である。PC-Bだけの先行配布などへの縮小は、この棚卸しでは決めない。定期実行は手動運用の受け入れ後に進める。

## 実装済みの範囲と限界

| 分野 | 現在あるもの | 初回運用までの主な不足 |
| --- | --- | --- |
| 設定 | [厳密な設定読取](../../Common/MachineConfiguration.ps1)、[create-only生成](../../Common/MachineConfigurationBootstrap.ps1)、両PCの安全なexample、maintenanceLocalの字句的分離 | 正式導入入口、実root認可、実効権限・祖先・利用直前までの保護。example生成後の実値は各PCのGit管理外設定へ手動入力 |
| ファイル選択 | [日付・期間等の共通処理](../../Common/LogFunctions.ps1)、[完全列挙・ハッシュ証拠構築](../../Common/SourceInventoryEvidenceBuilder.py) | 正式runへの接続、列挙後の変更と利用までの整合性 |
| root検査 | [既存Windowsディレクトリの読取専用metadata検査](../../Common/MachineConfigurationRootInspection.ps1) | 対象FS・ACL・実トークンの認可、安全な生成と継続利用の資格確認 |
| 証拠・集約 | [contracts](../../contracts/)、[A2/B2検証](../../Common/RunInputEvidenceIntegrity.py)、[参照成果物検証](../../Common/validate_aggregation_artifacts.py) | 規範的な全状態遷移、実run writer、集約結果再生成・実運用の意味論的統合、Drive反映 |
| 公開・クラッシュ | [単一ファイル公開](../../Common/AtomicArtifactPublication.py)、[marker-last公開](../../Common/ArtifactSetPublication.py)、復旧分類・ディレクトリ検証 | 永続run状態・処理全体との接続。複数ファイルの原子的トランザクションや電源断耐久性の証明はない |
| 排他・manifest選択 | [所有run lock](../../Common/OwnedRunLock.py)、[最新候補選択](../../Common/LatestManifestSelection.py)、読取adapter | 旧lockの自動引継ぎはしない。実owner証拠、復旧手順、新runとfresh inventoryの作成、実環境での統合 |
| 明示回復 | 診断・専用mutex、[private証拠のメモリ上のbinding](../../Common/PrivateRecoveryEvidence.py)、供給ACL/descriptorの検査 | v2の取得時owner証拠契約・provider、実効ACLと保存先検証、非公開の実保存。v1は診断・保全限定 |
| 月次・確認上限 | [月次観測](../../Common/MonthlyScheduleObservation.py)、[24時間・初回含め25回の確認予算](../../Common/CompletionWaitBudget.py) | 信頼できる永続履歴と原子的試行計上、時計/session/accountとの接続、未実行補完・毎時確認・正式task |
| Drive | request/response schema、IPC・再試行・不明結果に関する仕様 | API adapter、操作別意味検証、認証・最小権限、実体検証、PS側の再試行統合 |
| 配布 | 役割別ビルダー、example検査、PC-Bのarchive除外、レビュー成果物CI | 正式入口、最終allowlist、tag/VERSION/commitのprovenance、Driveへの検証付き配布、手動導入・更新・復旧 |

個別helperの成功を正式ランタイムの受け入れに読み替えない。詳細な安全ゲートは [runtime gate](../design/runtime-entrypoint-validation-gate.md)、[対象FS受け入れ](../validation/target-filesystem-acceptance.md)、[P0台帳](../requirements/p0-gap-register.md) を維持する。

## 初回配布までの依存順序

| 順序 | 作業と具体的成果物 | 次へ進む条件 |
| --- | --- | --- |
| 1 | 未決定事項を実装単位へ絞る。OSD-02の残りの状態遷移、OSD-04のDryRun副作用表、IPC C-01/C-02の操作別応答・path・相関・exit/retry意味論を確定。認証・配布の未決定も並行して整理 | 承認済みの契約と実装予定テストが対応し、未決定をコードの既定値で補わない |
| 2 | ローカル安全基盤を閉じる。実root・token・ACL・祖先・安全な生成/利用、永続run状態、確認予算の原子的計上と巻き戻し/喪失停止、明示回復とprivate証拠の契約・実装を使い捨て領域で検証 | 所有権・クラッシュ・競合・証拠喪失時に停止できる。自動stale takeoverなし。確認予算の永続化だけで全基盤完了とはしない |
| 3（2と並行可） | Drive adapterとPS/Python IPCを合成応答で実装。Python側の単一API試行、PS側の規定再試行、不明upload結果の照合、現在内容の再検証を接続 | 契約・障害・不明結果のテスト成功。OAuth主体/最小scope、対象folder権限・所有・quotaをOSD-05/C-23で決定。実環境確認は別途承認した限定計画で行う |
| 4 | 両PCの対象ローカルvolumeでTier Bを完了。個別helperと隔離ハーネスで資格を確認 | PC-Bの部分証拠だけで完了としない。PC-A証拠と全受け入れ項目を揃え、正式runtime接続前のFSゲートを満たす |
| 5 | 正式な手動Sync入口とPC-A専用Archive入口を実装。凍結inventory、manifest/report writer、排他・復旧・現在Drive照合を接続。既存/出所不明Driveデータの初回inventory・復元は通常成功runと分離 | PC-A archiveは両PCの対象期間/ログ種別・鮮度・内容を独立確認しcopy/verify/recordのみ。PC-B archiveなし。元ログ/Drive削除なし。DryRun・診断の契約を満たす |
| 6 | P0全体の追跡表、失敗・競合・クラッシュ・no-deleteのE2Eと両役割package検証。Tier B後、別途承認した専用使い捨て同期/ネットワーク領域のTier Cを実施 | P0-010/P0-012を含む受け入れ証拠が揃う。CI成功だけで代替しない。実ログ・本番Driveを通常テストに使わない |
| 7 | 正式配布・導入を仕上げる。tag/承認/VERSION/commit、最終allowlist・前提環境、Driveへのversioned upload→内容検証→latest更新、手動差分確認・設定保持・rollback | OSD-06/07/09が解決し、両PC用成果物と導入/更新手順を検証。設定はexampleから各PCで生成し実パスを手動設定。配布設計の実装自体は前段と並行可能だが公開・実適用は受け入れ後 |
| 8 | 明示承認のもと初回配布・限定的な手動適用。その受け入れ後に月次task・未実行補完・毎時確認を実装/検証して段階導入 | 手動運用の結果を確認してから [実装計画](../development/implementation-workflow.md) の定期運用フェーズへ進む。今回の棚卸しは配布・task登録・本番適用の承認ではない |

## 再判断が必要なもの／不要なもの

- 未決定: OSD-02の残りの規範的遷移、OSD-04のローカル副作用、OSD-05/C-23のOAuth/実folder資格、OSD-06のrelease認可とprovenance、OSD-07の配布package保持、OSD-09の最終allowlist・導入移行。OSD-03は集約方針とreport契約が承認済みだがruntime writer/統合が未完了。
- 承認済み: 専用の明示回復、v1診断・保全/v2証拠設計、maintenanceLocal内のprivate保全と自動削除なし、各PC内の手動/task同一account、初期taskはログオン中のみ、毎月1日PC-B20:00/PC-A21:00 JST、PC-A確認は最大24時間・初回含め25回。再質問しない。
- private回復証拠の「自動削除なし」は、配布packageの保持方針OSD-07を解決しない。未承認の自動cleanupは追加しない。
- OSD-08の日時等は決定済み。永続状態・task context・補完・通知・実環境受け入れは残るが、個別のscheduler補助処理を手動初回配布の基盤より優先しない。

## 検証証拠と今回の変更範囲

- 基準mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39971249609) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39971249630) は成功を確認した。
- 同じコード基準の既存ローカル結果はPython 3.11.9で306件（2件skip）、PowerShell 7.6.7の配布回帰成功。CI Pythonは3.12。最終導入環境の前提と依存導入も配布時に確認する。
- PC-Bのローカルvolume・reparse・crash・source・lock証拠は段階的な部分検証で、件数を足して独立した受け入れ総数としない。最新lock証拠のsource SHAは `302682abb7fd3b45b6745247dfa5297542f81c4b` で現在HEADとは異なり、Tier Bは明示的にincomplete。PC-Aのvolume受け入れは未収集、Tier Cは未実施。電源断/実再起動耐久性は未証明。
- 今回は文書のみ。リンク、差分・整合性を確認し、機能テストの再実行・実環境検証は行わない。全要件行の再監査や公開情報の網羅的再監査を完了したという意味ではない。
- README・Common/scripts README・配布設計と古い現況案内を更新。履歴として残す過去のPR記録は当時の状態であり、本棚卸しを現時点の入口とする。利用者の既存ステージ済みの引き継ぎ表整形も同じ文書コミットに含める。PR作成・マージ・機能実装は今回再開しない。
