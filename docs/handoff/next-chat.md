# 現在の引き継ぎ

更新日: 2026-10-24（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の棚卸し

- 基準main: `9fc85477907c169454104fe2b88b2933d855856f`（PR #27マージ）。Validate 39971249609 / Package Validation 39971249630成功を確認。
- 作業ブランチ: `docs/first-release-readiness-inventory`。棚卸し `6d9036e`、役割別設定・スキル分離 `44c2602`、構成整理 `d0fe6b6` をpushし、[PR #28](https://github.com/wasawo/eo-log-maintenance-public/pull/28) を作成。
- 最新指示（2026-10-24）: ここまでの変更をpush・PR作成し、最新HEADのCIとマージ要件を満たしたらスカッシュマージする承認あり。機能実装・本番適用の再開は含まない。記録時点では本PRの最終CI・マージは未確定であり、実PR/mainを照合する。
- [2026-10-24棚卸し・作業順序](../status/first-release-readiness-20261024.md) を現行の入口とする。正式Sync/Archive・Drive adapterが不在で、初回実運用配布には未到達。review ZIPと正式配布を区別する。
- 利用者の既存ステージ済み表整形は `6d9036e` に含めて保全済み。

## 今回の作業: リポジトリ構成の整理

- [全体構成・文書索引](../README.md) を追加。旧docs直下の53文書をdevelopment/requirements/design/decisions/validation/release/statusへ分類し、相対リンク・root基準の文書参照・役割TOML・スキル内参照を更新した。
- 固定入口AGENTS.md、docs/handoff/next-chat.md、Codex検出用の.agents/.codex、実装・設定・schema・テスト・CI・配布ビルダーの配置は維持。承認状態をファイル名や分類だけで判断しない。
- 古いPR表・検証項目別メモを [検証履歴](archive/validation-history-20261023.md) に分離し、既存の表整形を保全。以前からあった旧履歴内C-54文書へのリンク切れ1件も修正した。
- GitHub最新mainは `9fc85477907c169454104fe2b88b2933d855856f` と読み取り照合。作業開始時はクリーン。文書/設定参照のみの変更で、機能テスト・CI再実行・担当起動・push/PR/マージは行っていない。
- 検証: 全66 Markdownのローカルリンク切れ0、文書索引漏れ0、旧docs直下参照の残存0。移動53文書は参照以外の本文差分0・外部URL差分0。3担当TOML解析と差分検査成功。実装/schema/CI/依存ファイル変更0。過去検証表の整形・内容もアーカイブ先に保持した。

## 直前の作業: 役割別設定と開始文書の最適化

- AGENTS.mdは共通の開始・安全・委譲境界と参照に絞り、細かい仕様は [参照表](../development/development-guide.md) 経由で既存仕様へ誘導。検証とGit/PR/CI/handoff手順はプロジェクト内の2スキルへ移動した。
- [役割別運用](../development/agent-workflow.md) と `.codex/agents/` のanalyst/implementer/reviewerを追加。モデル・思考量の正本は各TOML、rootの推奨設定は役割別文書を参照する。現在のメインモデル・個人用設定・外部プロバイダーは変更していない。
- 設定はプロジェクト配下のみ。実ランタイム・同期/検証/archive/削除の条件や既存承認を変更しない。今回の変更開始時の作業ツリーはクリーン。
- 検証: 3つのTOMLをPython標準tomllibで解析成功。変更文書のローカルファイルリンク、2スキルの限定形式frontmatter/name一致・未完scaffold不在、差分検査は成功。skill-creatorのquick_validateはPyYAML未導入で起動不可のため、代替確認と区別する。AGENTS.mdは69行から25行へ縮小。文書/設定のみで機能テスト・CIは再実行していない。
- 担当/スキルの実起動・自動検出・モデル適用は未検証。次のセッションで認識を確認する。今回の変更自体ではサブエージェントを起動せず、PR/push/マージも行わない。

## 完了した直前の実装: PC-A確認予算（PR #27）

- 最大24時間・初回含め25回、1時間以上の間隔、不変scope/run履歴を検査する純粋helperと16合成テストをマージ済み。期限ちょうどの最終適格確認を含め、それ以降はhold。
- `Common/CompletionWaitBudget.py` はIO/待機/task/Drive/保存を行わず、archive/state変更を許可しない。永続履歴・原子的試行計上・喪失/巻き戻し耐性は未実装。
- 既存ローカル結果: Python 3.11.9全306件（2件skip）、PowerShell 7.6.7配布回帰成功。今回の文書変更では再実行しない。

## 次回の実装再開時

1. PR #28の最新HEAD・CI・マージ状態、実mainと作業ツリーを確認し、未コミット変更を保全する。今回の依頼は構成整理のスカッシュマージまで。機能実装は次の指示に従う。
2. 棚卸しの順序に従い、残りの状態遷移/DryRun/IPC契約と、ローカルroot・永続run状態・復旧の不足を整理する。確認予算の永続化はその一部で、単独で初回配布へ進めない。
3. Drive adapter/認証資格、両PCのTier B、正式手動runtime統合、E2E/Tier C、正式配布/導入と進む。taskは初回手動受け入れ後。実環境検証・実適用は別途の承認範囲を確認する。
4. 旧lock自動処分・新run自動生成・実保存・task登録・Drive/本番復旧を、helper/CI成功から許可されたと解釈しない。

承認済み: 明示回復、v1保全/v2対象、private maintenanceLocal保管/自動削除なし、同一account、ログオン中のみ、毎月1日PC-B20:00/PC-A21:00 JST、PC-A確認24時間/25回。これらを同じ内容で再質問しない。

## 設定基盤の完了範囲

- PR #8: maintenanceLocal必須化、公開exampleと字句的重複拒否。
- PR #9: strict UTF-8/JSON構造・役割・型・unknown/duplicateキー・パス構文検証。285アサーション成功。
- PR #10: create-only補助処理。既存設定をbytes単位で保持、安全exampleだけ新規生成。22アサーションと配布テスト成功。
- PR #10最新HEAD e5df9a197a4644a29a0ae7d9bd38d0a2d9e06a65 のValidate 39830715865（attempt 2）/Package 39830715899成功後マージ。初回はPSGallery登録で失敗、検査は弱めていない。
- 実設定・実導入先では実行していない。既存rootのmetadata補助検査は上記の追加範囲。approved-root権限/FS資格/利用直前までの保護、正式導入/実行入口接続・移行は未完了。設定値は認可ではない。

## 過去の検証・マージ記録

PR #3〜6のマージ表と旧項目別メモは [検証履歴](archive/validation-history-20261023.md) へ移動。利用者の既存表整形も保全済み。現在の作業順は上記の棚卸しを参照する。

## 利用者への確認中・既に確認したこと

- 現在の端末はPC-B。管理成果物とは、そのPCが生成するマニフェスト・一覧/検証証拠・集計レポート・marker/lock等。PC-Aの原本はPC-A側に置き、両PC向けの検証済みコピーをDriveへ公開する方針。
- PC-B予定固定ディスク上に新規合成領域を作る検証を実施した。実パスや実ボリューム文字は公開しない。実設定はGit管理外のConfig/PC-B.jsonへ将来入力する。
- 承認済み（2026-10-23）: 両PC設定へ `maintenanceLocal`（そのPCのマニフェスト・検証証拠・レポートのローカル原本領域）を追加する。exampleはダミー、実値は非追跡設定、実行先/元ログ/Drive/archiveとの重複を拒否。実パスは推測しない。
- OSD-04（Dry Run副作用）、OSD-05（Drive認証）、OSD-06/07（配布/保持）、OSD-08（予定実行）、OSD-09（最終allowlist/移行）と残る状態遷移/契約の承認・証拠は別途必要。
- 台帳の古い「sentinelあり」「過去PRのCI待ち」などは現物と照合して関係PRで直す。台帳全体の再監査完了とはしない。
