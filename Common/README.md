# Common — 既存の共通処理

このディレクトリはPowerShell/Pythonの共通helper。正式な移動入口や、本番実行可能なアプリではない。全helperを一律に削除せず、[正式設計書](../docs/design/log-move-design.md)と[実装計画§9](../docs/development/implementation-workflow.md#9-既存の実装資産と不足)で利用先/限界を確認する。

## 機能から探す

[DriveSetup.py](DriveSetup.py)は初回登録と保護設定の不足を解消する明示CLI。既存PKCE/state/DPAPI/ACLを再利用し、Desktop Pickerの選択ID検証・loopback受領・非上書き初期保存を接続する。`prepare`/`validate`はcredentialを読まず、`enroll`の実行には別途の実操作承認が必要。[PC別手順](../docs/design/drive-metadata-reader.md)を参照。実Driveアクセスや削除は提供しない。

[DriveTransferAdapter.py](DriveTransferAdapter.py)は呼出し側が渡す公式SDK serviceを使う単試行のupload/download結合。既存metadata/list/content readerを再利用し、新規createのみ行って内容と現在候補の一意性を再確認する。S3の不足していたupload接続のため追加した。認証情報の探索/保存/refresh・上書き・削除は行わず、service/認証/実環境の資格を確定しない。[DriveAdapterBridge.ps1](DriveAdapterBridge.ps1)は正式入口からtests専用の模擬HTTP workerを呼ぶ隔離試験用接続で、運用IPC schema/認証storeの完成ではない。

[SyntheticLogTransfer.ps1](SyntheticLogTransfer.ps1)はS1 Sync/S2 Archiveの合成E2Eだけで再利用する列挙・期間判定・非上書きコピー・SHA-256照合・件数集計。Archive入口の接続に同じ処理が必要なためS1から抽出した。固定の合成fixture/役割以外は拒否し、実設定・実Drive・元削除は提供しない。

所有wrapperは[境界ごとの所有確認](../docs/design/owned-simulation-run.md#処理境界での所有確認)をモデルへ渡す。確認不能後は後続のモデルコピー/元除去・永続保存を止めるが、実providerの原子的な所有保証にはしない。

[ファイルスナップショット接続](../docs/design/file-snapshot-simulation.md)は`SimulationFileSnapshot.py`/`.ps1`で合成フォルダを読取り、全列挙を確認してから所有ロック付きモデルへ渡す。物理ファイルは変更しない。

[所有ロック付き模擬実行](../docs/design/owned-simulation-run.md)は`OwnedLogMoveSimulation.ps1`から既存モデル・journal・レポートを囲む。開始/終了記録と実OS mutexを接続するが、実providerやprivate root資格の保証ではない。

[模擬実行結果レポート](../docs/design/simulation-run-report.md)は`SimulationRunReport.py`/`.ps1`で別領域へ保存する。prepared前の失敗も含めるが、削除判定の証拠や実runの完成にはしない。

SDKの[内容取得・hash・版再確認](../docs/design/drive-content-reader.md)は`DriveContentReader.py`で行う。結果は版付きの内容観測だけで、download保存・元削除を提供しない。

共通SDK転送を使う[所有された隔離stagingへの保存接続](../docs/design/sdk-download-staging.md)はtests専用であり、Commonに実運用root向けの保存factoryを追加したものではない。

| 分野 | 実装/参照先 | 現在の境界 |
| --- | --- | --- |
| 設定 | [MachineConfiguration.ps1](MachineConfiguration.ps1)、[bootstrap](MachineConfigurationBootstrap.ps1)、[root検査](MachineConfigurationRootInspection.ps1) | 構造/既存root観測等の補助。正式導入/実体保護は別 |
| 日付/期間・source証拠 | [LogFunctions.ps1](LogFunctions.ps1)、[SourceInventoryEvidenceBuilder.py](SourceInventoryEvidenceBuilder.py)、[source再観測](../docs/design/reference/source-inventory-revalidation.md) | 選択/列挙/hashと凍結入力比較。削除許可ではない |
| staging/残存物 | [staging lifecycle](../docs/design/staging-file-lifecycle.md)、[残存物観測](../docs/design/reference/staging-residual-observation.md) | コピー/容量/残存物の観測と正式runtimeを区別 |
| 内容/Drive比較 | [DriveContentComparison.py](DriveContentComparison.py)、[SDK読取接続](../docs/design/drive-metadata-reader.md)、[内容比較仕様](../docs/design/reference/drive-content-comparison.md)、[応答検査](DriveResponseSemantics.ps1) | SDKの一覧/metadataと比較を接続。実認証・転送・元削除・正式adapterは未完 |
| manifest/集約 | [A2/B2検証](RunInputEvidenceIntegrity.py)、[report builder](AggregationReportBuilder.py)、[参照成果物検証](validate_aggregation_artifacts.py)、[遷移観測](../docs/design/reference/manifest-transition-inspection.md) | 旧v1観測/検証。verifiedを移動完了へ読み替えない |
| 公開/排他/復旧 | [単一公開](AtomicArtifactPublication.py)、[bundle公開](ArtifactSetPublication.py)、[所有lock](OwnedRunLock.py)、[明示回復設計](../docs/design/explicit-recovery-command-design.md) | 所有権/現在性/対象FS/電源断の実受け入れは別 |
| 診断/非公開証拠 | [従来の詳細ノート](../docs/design/reference/common-module-notes.md)、[private証拠契約](../docs/design/recovery-private-evidence-contract.md) | 各実装の型/証拠/秘匿境界を維持 |
| 月次/電源・旧確認予算 | [月次](../docs/design/reference/monthly-schedule-observation.md)、[電源](../docs/design/reference/power-status-observation.md)、[確認予算](../docs/design/reference/completion-wait-budget.md) | 定期実行は後続。旧PC-B完了待機はarchive前提にしない |

両経路をメモリ上でつなぐ[LogMoveSimulation.ps1](LogMoveSimulation.ps1)を追加した。[模擬契約](../docs/design/log-move-simulation.md)と[任意のjournal接続](../docs/design/simulation-journal-integration.md)を参照。実ログ/Drive操作は提供せず、正式な移動入口ではない。

[MoveJournal.py](MoveJournal.py)は[移動記録v1](../docs/design/move-record-v1.md)の非上書き保存・参照検査・読戻しを提供する。元/保存先の実観測や削除権限は提供せず、private root・所有権・ACL・排他の資格確認は呼出し側に必要。

[MoveRunReport.py](MoveRunReport.py)は検査済み記録を実行別に集計し、[概要表示コマンド](../scripts/Show-MoveRun.ps1)へ限定した表示項目だけを返す。実移動の制御や実行成功の認定は行わない。[集計仕様](../docs/design/move-run-report.md)を参照。

## 詳細と検証

S3の不足していた認証と明示接続のため、[DriveCredentialStore.py](DriveCredentialStore.py)・[DriveAuthentication.py](DriveAuthentication.py)・[IsolatedDriveRunner.py](IsolatedDriveRunner.py)を追加した。既存ACL profileとSDK reader/transferを再利用する。Windows DPAPI/保護ACLと合成credential、SDK/API模擬の検証に限定し、実認証/両PCの資格/実Drive受け入れは未完。[実装境界と操作承認](../docs/design/drive-metadata-reader.md#認証storeservice接続runnerの実装境界)を確認する。

- 全モジュールの従来説明は[Commonモジュール参照ノート](../docs/design/reference/common-module-notes.md)へ移した。個別の観測条件/未実装境界を削っていない。
- [helper参照索引](../docs/design/reference/README.md)、[現行schema](../contracts/)、[テスト手順](../tests/README.md)から必要な分野だけを読む。
- 2026-10-27の配置整理ではruntime名/配置・schema・import・CI/配布allowlistを変更していない。その後の実装変更は各設計と引き継ぎで確認する。helperの未使用推測や旧方針を理由にコード/試験を削除しない。
