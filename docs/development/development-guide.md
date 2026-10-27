# 開発時の詳細仕様・手順の参照表

共通の開始規則は [AGENTS.md](../../AGENTS.md)。この表は対象別の読取先で、すべてを毎回読む一覧ではない。対象の承認記録・仕様・実装・テストを照合し、矛盾や未決定はrootへ返す。文書を移動・参照化しても仕様・承認範囲は変更しない。

現行の正本は[要件定義書](../requirements/log-move-requirements.md)、[設計書](../design/log-move-design.md)、[受け入れ条件・実装計画](implementation-workflow.md)の3本。要件の確定と設計内の方式候補/未決を区別する。現在は文書/詳細契約の整理で、利用者の実装再開指示までコード/schemaを追加しない。小さなhelper単位の追加実装を自動選択しない。

承認の根拠は要件定義書の「承認記録」、現在地はhandoffで確認する。以下の個別契約は現schema/helperや維持する条件を調べるために参照し、旧版のverified/reportを元削除完了へ読み替えない。

| 変更対象 | 読む文書・実体 | 維持する条件 |
| --- | --- | --- |
| 全体・未完了 | [現行handoff](../handoff/next-chat.md)、[実装計画（§3作業順/§9資産/§10旧証拠）](implementation-workflow.md)、[要件台帳](../requirements/requirements-traceability.md)、[P0台帳](../requirements/p0-gap-register.md) | 記録より実ファイル・実Git状態を優先し、実装済みhelperと正式runtime完成を区別 |
| 承認と未決定 | [決定台帳](../decisions/decision-register-c18-c32.md)、[未決定仕様](../requirements/p0-open-specification-decisions.md)、対象の個別承認記録 | 未決定の値・遷移・認証・配布条件を推測して実装しない |
| 設定・root | [maintenanceLocal](../design/configuration-local-root.md)、[Config](../../Config/)、[Common](../../Common/README.md) | PC別フィールド、安全既定値、絶対Windowsパス、領域分離を維持。導入時は未作成の場合だけexampleから生成し、利用者は実パスのみ入力。更新時は既存実設定を保持。設定値は認可ではない |
| ファイル選択・期間 | [ファイル名・期間](../design/filename-and-period-selection.md) | 承認済みファイル名日付を使いLastWriteTimeで代用しない |
| IPC・Drive | [PS/Python契約](../design/powershell-python-contract.md)、[contracts](../../contracts/)、[runtime gate](../design/runtime-entrypoint-validation-gate.md) | Drive for desktopの可視性はクラウド反映の証拠ではない。同名競合を上書きせず出所を推測しない |
| 同期・manifest・archive・復旧 | [runtime gate](../design/runtime-entrypoint-validation-gate.md)、[staging lifecycle](../design/staging-file-lifecycle.md)、[テストシナリオ](../validation/runtime-safety-test-scenarios.md)、対象の個別契約 | 現在の対象ごとの保存先内容一致・元不変確認、不明時の元保全、所有権に基づく復旧。両PCの期間完了はarchive条件にしない。初期inventory/復元は通常移動と分離し、未照合・競合・出所不明を自動復元しない。現v1/helperの制約と新しい移動完了契約を区別する |
| 実環境検証 | [対象FS受け入れ](../validation/target-filesystem-acceptance.md) | 通常テストは合成・隔離領域のみ。予定volumeの部分証拠をTier B/C全体の完了にしない |
| 配布・導入 | [配布設計](../release/distribution-design.md)、[ビルダー](../../.github/scripts/Build-ReleasePackage.ps1)、[package tests](../../tests/Test-ReleasePackage.ps1) | 役割別allowlist、PC-B archive除外、非配布マーカーを維持。実設定 `Config/PC-A.json` / `Config/PC-B.json` はGit/配布対象外 |

検証手順は [eolm-validation](../../.agents/skills/eolm-validation/SKILL.md)、Git/CI/引き継ぎ手順は [eolm-pr-handoff](../../.agents/skills/eolm-pr-handoff/SKILL.md) を必要時に読む。
