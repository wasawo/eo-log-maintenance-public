# Codex 作業規則 — ElectronicObserver Log Maintenance

このリポジトリ全体の共通の恒久規則。正本は GitHub の `wasawo/eo-log-maintenance-public`。旧Privateリポジトリは参照用で、変更・履歴を無断で取り込まない。

## 開始と分担

- 全担当はこの文書と割当指示を読む。rootは [引き継ぎ](docs/handoff/next-chat.md) とGitのブランチ・作業ツリー・リモートを照合し、必要なGitHub状態を確認する。実ファイル・実Git状態を古い記録より優先する。
- サブエージェントは割当範囲・基準SHA・対象仕様を確認し、handoffは関連部分だけ読む。handoffの次作業を独自に開始しない。編集前には作業ツリーを確認する。
- [役割別運用](docs/agent-workflow.md) に従う。analystは調査、implementerは割当範囲の編集、reviewerは独立検証、rootは判断・統合・Git/PR操作・handoff更新を担う。小さな作業はrootだけでよい。
- 未コミット・ステージ済み変更を保全する。同じファイルの並行編集を避け、担当外の変更・仕様矛盾・未決定事項はrootへ返す。

## 全担当が維持する境界

- PC-Bにはarchive・削除能力を提供しない。初期実装に元ログ/Driveログの削除コード・操作・設定を追加しない。PC-A archiveは明示許可と両PC証拠・現在のDrive内容の検証を満たしたcopy/verify/recordのみ。不明・欠落・不一致は保留する。
- 実ログ・本番Driveを通常テストに使わない。合成データ・隔離一時領域・模擬APIを使い、実環境検証は承認された限定計画に従う。
- helper・schema・package・CIの成功をruntime受け入れ、クラウド同期、電源断耐久性の証明にしない。未実装・未確認・未実行を完了扱いしない。
- 実運用パス、Drive URL/ID、個人メール、実設定、実行時ログ/証拠、token・鍵を追跡ファイル・PR・ログへ追加しない。公開例はダミー、実値はGit/配布対象外とする。
- 未決定仕様を実装都合で確定しない。設定値・文書編集・役割への委譲は認可にならない。公開範囲変更、履歴書き換え、force push、ブランチ削除、本番適用は明示承認の範囲内のみ。PR作成許可をマージ許可と解釈しない。

## 必要時に読むもの

- 変更前に [詳細仕様への参照表](docs/development-guide.md) から対象仕様・承認記録・既存テストを読む。全仕様や履歴を毎回一括読込しない。
- 検証時は [eolm-validation](.agents/skills/eolm-validation/SKILL.md) を読む。文書のみならリンク・記述整合・差分を確認し、無関係な全テストを繰り返さない。
- コミット・PR・CI確認・handoff更新時は [eolm-pr-handoff](.agents/skills/eolm-pr-handoff/SKILL.md) を読む。関連する仕様・コード・テスト・引き継ぎは同じPRにまとめる。
- 恒久規則はここ、役割は `.codex/agents/`、作業手順は `.agents/skills/`、変動する進捗・承認/中断状態は `docs/handoff/next-chat.md` に置く。過去記録は現行指示として実行しない。
