# リポジトリ構成・文書索引

利用者向け概要は[README](../README.md)、恒久規則は[AGENTS](../AGENTS.md)、現在地は[handoff](handoff/next-chat.md)。全履歴を一括で読むのではなく、正式文書から必要な根拠へ進む。

## 現行の正式文書

| 文書 | 役割 |
| --- | --- |
| [要件定義書](requirements/log-move-requirements.md) | 目的/完成範囲/2経路/役割/配置/削除/競合/再実行、Q1〜Q12の承認 |
| [設計書](design/log-move-design.md) | 構成・フロー・識別/Q5確認・記録/状態/照合/応答、確定と方式候補の区別 |
| [受け入れ条件・実装計画](development/implementation-workflow.md) | AC-01〜12/T0〜T5、既存要件対応、実装資産と不足、過去証拠の基準 |

正式化は具体方式の一律承認・runtime受け入れ・実装再開/本番操作の指示ではない。

## 配置と依存関係

```text
Common/                    既存PS/Python helper（Common/READMEは機能索引）
Config/                    公開exampleのみ。実設定はGit/配布対象外
contracts/                 現行JSON Schema。新しい移動契約への暗黙変更なし
scripts/                   正式入口の配置先。現在はREADMEのみ
tests/                    合成テスト/ハーネス/匿名化済み部分証拠
.github/                   役割別packageビルダーとCI
.agents/skills/             検証/PR/引き継ぎ手順
.codex/                    root単独運用のproject設定

docs/
  requirements/            正式要件・追跡/P0/未決台帳
  design/                  正式設計・維持する個別契約
    reference/             既存helperの詳しい観測/検証仕様
  development/             正式実装計画・開発参照表・単独運用
  decisions/               現行決定台帳
  validation/              現行試験/対象FS/復旧の受け入れ計画
  release/                 配布/導入設計
  archive/                 過去の比較/判断記録・監査根拠
  handoff/                 現在地。archive/に旧引き継ぎ
```

コード/contract/import/配布/CIの配置は維持する。テストやhelperを未使用と推測して削除しない。無視対象の個人設定・実設定・runtimeデータは整理対象にしない。

## 必要な分野から読む

| 目的 | 参照先 |
| --- | --- |
| 実装前の詳細確認 | [開発参照表](development/development-guide.md)、[root単独運用](development/agent-workflow.md) |
| 現要件と未完を追う | [要件追跡](requirements/requirements-traceability.md)、[P0](requirements/p0-gap-register.md)、[未決仕様](requirements/p0-open-specification-decisions.md)、[現行決定](decisions/decision-register-c18-c32.md) |
| 設定/選択/IPC/入口 | [設定root](design/configuration-local-root.md)、[名前/期間](design/filename-and-period-selection.md)、[PS/Python](design/powershell-python-contract.md)、[runtime gate](design/runtime-entrypoint-validation-gate.md) |
| 現schema/状態と復旧 | [manifest v1](design/manifest-schema-v1-proposal.md)、[遷移](design/manifest-state-transition-v1-proposal.md)、[staging](design/staging-file-lifecycle.md)、[明示回復](design/explicit-recovery-command-design.md)、[private証拠](design/recovery-private-evidence-contract.md)、[owner-v2](design/recovery-owner-evidence-v2-contract.md) |
| Dry Run | [無書込み実行設計](design/dry-run-execution-design.md) |
| 既存実装の詳細 | [Common機能索引](../Common/README.md)、[helper参照索引](design/reference/README.md)、[schema](../contracts/) |
| 検証/配布 | [tests](../tests/README.md)、[runtimeシナリオ](validation/runtime-safety-test-scenarios.md)、[日付試験](validation/filename-period-test-plan.md)、[C53/C54](validation/c53-c54-policy-test-matrix.md)、[対象FS](validation/target-filesystem-acceptance.md)、[lock復旧](validation/lock-recovery-acceptance-gate.md)、[配布](release/distribution-design.md) |
| 過去の選択/証拠 | [履歴索引](archive/README.md)、[旧handoff](handoff/archive/requirements-review-through-20261027.md)、[失効した旧担当定義](development/archive/README.md) |
| 作業手順 | [検証skill](../.agents/skills/eolm-validation/SKILL.md)、[PR/handoff skill](../.agents/skills/eolm-pr-handoff/SKILL.md) |

proposal/optionsというファイル名だけで承認/失効を決めない。archiveへの移動は承認の撤回ではなく、既存の適用範囲を保持する。正式文書へ完全に置換した不要作業文書だけは、利用者の整理指示と移行先/Git基準を残して削除する。新しい文書/移動時は参照元と相対リンクを同時更新する。
