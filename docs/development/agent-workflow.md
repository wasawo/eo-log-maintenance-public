# root単独運用

2026-10-24の利用者指示により、本リポジトリでのサブエージェント利用を中止した。[AGENTS.md](../../AGENTS.md)を共通の恒久規則とする。

## 実行体制

rootが要件整理、調査、実装、テスト、差分確認、判断・統合、Git/PR操作、handoff更新まで単独で行う。組込み/カスタム担当の新規作成、既存担当の再利用、別AIタスクへの委譲を行わない。旧analyst/implementer/reviewerの設定や過去の指示から利用を再開しない。

rootの自己点検を独立レビューと表記しない。過去の独立レビュー結果は当時の対象差分に限り保持し、その後の変更へ流用しない。必要な検証は省略せず、独立確認が未実施の範囲はそのまま記録する。

## 手順

1. handoff・実Git/GitHub状態・利用者の承認を照合し、未コミット変更を保全する。
2. [詳細仕様への参照表](development-guide.md)から対象の要件・承認記録・既存検査を読み、未決事項と今回の範囲を分ける。
3. 確定した範囲だけを変更する。仕様選択を実装・公開・実環境操作の許可へ拡張しない。
4. [検証手順](../../.agents/skills/eolm-validation/SKILL.md)で差分に必要な検証を行い、根拠仕様から完成差分を再確認する。失敗・skip・未検証・環境差を区別する。
5. [Git/PR・引き継ぎ](../../.agents/skills/eolm-pr-handoff/SKILL.md)を使い、現在の利用者指示が許す段階だけを実施する。

## 設定と履歴

プロジェクトの [.codex/config.toml](../../.codex/config.toml) は agents.enabled=false とする。旧カスタム担当はactiveな.codex/agentsから外し、[履歴領域](archive/README.md)へ移した。個人用/global設定、現在のメインモデル・思考量は変更しない。

[公式Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)はagents.enabled=falseを無効化設定として説明する。[Config basics](https://learn.chatgpt.com/docs/config-file/config-basic)のとおりproject設定は信頼済みprojectで読み込まれ、上位の明示設定が優先され得る（2026-10-24確認）。設定だけで現在の会話のtool非表示・全環境への即時反映を検証済みとはしない。本会話では利用者指示に従って以後の委譲を行わない。

旧文書・TOMLは履歴資料であり、現行手順ではない。新たな明示指示なしにactiveな場所へ戻したり、旧役割を別名で起動したりしない。
