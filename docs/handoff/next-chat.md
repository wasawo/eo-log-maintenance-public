# 現在の引き継ぎ

更新日: 2026-10-27（日本時間）
恒久ルール: [AGENTS.md](../../AGENTS.md)。正本: `wasawo/eo-log-maintenance-public`。
本書は記録時点。開始時は実Git/作業ツリーを優先する。

## 現在地

- 作業branch: `docs/requirements-design-task-review`。今回開始HEAD: `712a906`。mainのコード基準: `27e99fec`（PR #46）。現在のbranchは文書変更のみで、push/PR/mergeはまだ行わない。
- 正式文書: [要件定義書](../requirements/log-move-requirements.md)、[設計書](../design/log-move-design.md)、[受け入れ条件・実装計画](../development/implementation-workflow.md)。Q1〜Q12/平坦化は確認済み。承認根拠は要件定義書「承認記録」。提示済みの未回答質問はない。
- 初回完成は手動で両経路を確認済み元の直接削除まで。新しい削除/記録/状態/IPC/実API/FS保証等は未確定で、T0とruntime受け入れは未完。実装再開指示は未受領。

## 前回までのリポジトリ整理

利用者の「正式文書をベースにリポジトリ配下の整理」を受け、参照を調べて次を実施した。

- 判断/比較の25文書をdocs/archive/decisionsへ、過去基準の監査7文書をdocs/archive/validationへ移した。[履歴索引](../archive/README.md)から辿れる。承認済み選択の撤回や、未決候補の採用ではない。
- 実装済みhelperの観測/比較等の14文書をdocs/design/referenceへ整理。[参照索引](../design/reference/README.md)を設けた。Commonの長い説明は同配下の参照ノートへ保持し、Common/READMEは機能索引へ短縮。
- 旧handoff約980行は[2026-10-27までの履歴](archive/requirements-review-through-20261027.md)へ完全保管し、本書を現状と次の作業に絞った。古い未回答/次作業/権限を現在指示として復活させない。
- 全Markdownの相対リンクとcanonicalなdocs内path参照を更新。移動対象文書に非Markdownファイルからの直接参照がないことを確認。Common/contracts/Config/scripts/tests/.github等の実行/契約/配布fileは移動・削除しない。
- 無関係な個人設定/無視対象/実設定・秘密・runtimeデータには触れず、.git内部の手動整理も行っていない。コード/schema/配布allowlist/CI・AGENTSの恒久規則は不変。履歴書き換え/force push/branch削除なし。

## 今回の文書日本語化

利用者の指示により、docs内のMarkdown84文書を対象に、現行文書・参照資料・過去の監査・引き継ぎの英語の見出し、本文、表、リンク表示を日本語化した。既に日本語の本文は維持した。翻訳補助の取得済み訳文を使い、英文の折り返しを段落へまとめ、残りの114項目と主要な期間・削除条件等はrootが原文から補正した。翻訳サービスの呼び出し上限到達後は外部依頼を停止し、ローカルで完了した。

コード例・インラインコード・ファイル名・識別子・フィールド名・列挙値・URLは契約どおり保持する。英語見出しの旧参照を維持するため明示アンカーを残した。歴史記録の日付・承認・未実装・未実行の扱いは変更せず、旧指示を現在の指示として復活させない。新しい承認や実装完了は追加していない。

## 検証

現存Markdown93文書の相対参照先909件・見出し参照109件を検査し、欠落・不一致0。翻訳対象のコードブロック、インラインコード、リンク先を原文と照合し、一致を確認。表の列構造と技術識別子も比較し、不一致0。ファイル名・期間、2経路の確認と削除、復旧・証拠の限界を原文と自己点検した。機械的な照合は全訳文の独立した意味レビューではない。引き継ぎの基準SHA・作業記録の更新は別途含む。

変更はdocs内の文書のみ。コード/schema/設定/CI/allowlistとAGENTS/.agents/.codex/.gitignoreは差分なし。`git diff --check`成功。root自己点検のみ、独立レビューなし。文書のみのため無関係な全試験・配布物生成は実行していない。今回の変更も同じ作業ブランチに蓄積し、push/PR/mergeは行わない。

## 次の作業と未完

- 正式設計の未決API/FS能力・確認と削除対象の結合・記録の型/版/永続化・経路間照合を具体化し、T0を閉じる。helperの小さな追加を自動選択しない。
- 実装再開・実データ操作・本番適用へ進まない。PRは利用者のタイミングで同branchの変更をまとめる。
- PR #46までの試験/CI・部分Tier B等の根拠は上記の旧handoff履歴と[実装計画§10](../development/implementation-workflow.md#10-旧棚卸しの証拠基準歴史)を参照。現在SHAに対する新しいruntime証拠とはしない。
