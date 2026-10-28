# Common — 既存の共通処理

このディレクトリはPowerShell/Pythonの共通helper。正式な移動入口や、本番実行可能なアプリではない。全helperを一律に削除せず、[正式設計書](../docs/design/log-move-design.md)と[実装計画§9](../docs/development/implementation-workflow.md#9-既存の実装資産と不足)で利用先/限界を確認する。

## 機能から探す

| 分野 | 実装/参照先 | 現在の境界 |
| --- | --- | --- |
| 設定 | [MachineConfiguration.ps1](MachineConfiguration.ps1)、[bootstrap](MachineConfigurationBootstrap.ps1)、[root検査](MachineConfigurationRootInspection.ps1) | 構造/既存root観測等の補助。正式導入/実体保護は別 |
| 日付/期間・source証拠 | [LogFunctions.ps1](LogFunctions.ps1)、[SourceInventoryEvidenceBuilder.py](SourceInventoryEvidenceBuilder.py)、[source再観測](../docs/design/reference/source-inventory-revalidation.md) | 選択/列挙/hashと凍結入力比較。削除許可ではない |
| staging/残存物 | [staging lifecycle](../docs/design/staging-file-lifecycle.md)、[残存物観測](../docs/design/reference/staging-residual-observation.md) | コピー/容量/残存物の観測と正式runtimeを区別 |
| 内容/Drive比較 | [DriveContentComparison.py](DriveContentComparison.py)、[内容比較仕様](../docs/design/reference/drive-content-comparison.md)、[応答検査](DriveResponseSemantics.ps1) | 純粋比較/応答相関。実Drive adapter/元削除は未実装 |
| manifest/集約 | [A2/B2検証](RunInputEvidenceIntegrity.py)、[report builder](AggregationReportBuilder.py)、[参照成果物検証](validate_aggregation_artifacts.py)、[遷移観測](../docs/design/reference/manifest-transition-inspection.md) | 旧v1観測/検証。verifiedを移動完了へ読み替えない |
| 公開/排他/復旧 | [単一公開](AtomicArtifactPublication.py)、[bundle公開](ArtifactSetPublication.py)、[所有lock](OwnedRunLock.py)、[明示回復設計](../docs/design/explicit-recovery-command-design.md) | 所有権/現在性/対象FS/電源断の実受け入れは別 |
| 診断/非公開証拠 | [従来の詳細ノート](../docs/design/reference/common-module-notes.md)、[private証拠契約](../docs/design/recovery-private-evidence-contract.md) | 各実装の型/証拠/秘匿境界を維持 |
| 月次/電源・旧確認予算 | [月次](../docs/design/reference/monthly-schedule-observation.md)、[電源](../docs/design/reference/power-status-observation.md)、[確認予算](../docs/design/reference/completion-wait-budget.md) | 定期実行は後続。旧PC-B完了待機はarchive前提にしない |

両経路をメモリ上でつなぐ[LogMoveSimulation.ps1](LogMoveSimulation.ps1)を追加した。[模擬契約](../docs/design/log-move-simulation.md)と[任意のjournal接続](../docs/design/simulation-journal-integration.md)を参照。実ログ/Drive操作は提供せず、正式な移動入口ではない。

[MoveJournal.py](MoveJournal.py)は[移動記録v1](../docs/design/move-record-v1.md)の非上書き保存・参照検査・読戻しを提供する。元/保存先の実観測や削除権限は提供せず、private root・所有権・ACL・排他の資格確認は呼出し側に必要。

[MoveRunReport.py](MoveRunReport.py)は検査済み記録を実行別に集計し、[概要表示コマンド](../scripts/Show-MoveRun.ps1)へ限定した表示項目だけを返す。実移動の制御や実行成功の認定は行わない。[集計仕様](../docs/design/move-run-report.md)を参照。

## 詳細と検証

- 全モジュールの従来説明は[Commonモジュール参照ノート](../docs/design/reference/common-module-notes.md)へ移した。個別の観測条件/未実装境界を削っていない。
- [helper参照索引](../docs/design/reference/README.md)、[現行schema](../contracts/)、[テスト手順](../tests/README.md)から必要な分野だけを読む。
- 2026-10-27の配置整理ではruntime名/配置・schema・import・CI/配布allowlistを変更していない。その後の実装変更は各設計と引き継ぎで確認する。helperの未使用推測や旧方針を理由にコード/試験を削除しない。
