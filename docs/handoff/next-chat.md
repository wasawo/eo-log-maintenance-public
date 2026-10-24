# 現在の引き継ぎ

更新日: 2026-10-24（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

- 最新mainは `c4de355ac9810769036746401a2ef3235329bc74`（[PR #37](https://github.com/wasawo/eo-log-maintenance-public/pull/37) マージ済み）。利用者のOKに基づき判断資料とhandoffの9文書を対象に、最新HEAD `4a6ff27ff6cf1dbc84a4485dc0b07ed3a60555a2` の [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40082476232) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40082476316) 成功後にsquash mergeした。
- 認証・owner-v2の保全済み比較を統合し、[B2 validation網羅性/report生成時刻](../decisions/b2-validation-coverage-report-time-options.md)の選択肢と互換性・R5改訂・将来合成vectorsを整理した。[認証資料](../decisions/osd-05-drive-auth-identity-scope-options.md)・[owner-v2資料](../decisions/owner-v2-field-binding-options.md)を含め、**資料のマージは方針採用ではない**。コード/schema/設定/承認状態は変更せず、実OS/Drive接続・保存・本番適用を認可していない。private保全/自動削除なし・各PC内manual/task同一accountは既承認のまま文書を整合した。
- 文書検証: 9文書のローカルリンク118件欠落0、差分検査成功。reviewerはhandoffを除く8文書/112リンクを独立確認し指摘なし。文書のみのため機能/package検査のローカル再実行なし。外部事実の再調査、実OS/Drive/runtime受け入れも実施していない。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40082642915) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40082642880) も成功。
- 従来の未公開資料branch `docs/remaining-contract-decisions`（`4e72846`）、`docs/drive-auth-options-after-pr34`（`643eaf6`）は履歴保全のため保持するが、判断資料の現行本文はPR #37後のmainを優先する。未公開資料のままという旧記録を現在の公開状態に適用しない。
- [C-01/C-02](../decisions/c01-c02-ipc-contract-options.md)、認証/owner-v2のfield・source・資格、B2 validation網羅性/incompleteの意味、生成UTCの永続出所/同一bytes再生成は未決。完全状態遷移、runtime、両PC実root/FS・Drive内容/耐久性の受け入れも未完。schema/helper/合成テスト/package/CI成功をこれらの完了にしない。集約builderはPR #35、B2 float拒否はPR #36でマージ済み。
- 現在は**PR #37マージ後の中断状態**。既存analyst/implementer/reviewerのみ再利用し、未決仕様を推測せず合成/隔離検証・独立review・handoffを完了、PR/マージ権限は個別承認内とする。**1PRマージごとに中断して継続可否を尋ねる**という利用者指示に従い、次作業は継続指示待ち。この記録は `docs/pr37-paused-handoff` にローカル保全し、未push・追加PRなし。

## 旧進捗の参照

PR #27〜33前後の旧進捗節は [セッション記録](archive/pr27-pr33-session-history-20261024.md) に保存した。過去の承認待ち・CI待ち・agent生成禁止を現在の指示として実行しない。

## 次回の実装再開時

1. まず利用者の継続指示を確認し、正本mainとローカル保全branchのコミット・作業ツリーを照合する。C-01の回答待ちは上記を参照し、未回答なら依存schema改訂を保留する。Aは承認済みで再質問しない。IPC全体/C-02/OSD-05等の未決定は維持する。
2. [初回配布棚卸しの順序](../status/first-release-readiness-20261024.md)に従い、残りの状態遷移/DryRun/IPC契約と、ローカルroot・永続run状態・復旧の不足を整理する。確認予算の永続化はその一部で、単独で初回配布へ進めない。
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
- OSD-04はA承認済みで実装・受け入れが未完。OSD-08の日時等は決定済みで、永続状態/task/補完/受け入れは未完。OSD-05（Drive認証）、OSD-06/07（配布/保持）、OSD-09（最終allowlist/移行）、残る状態遷移/IPC契約の未決・未確認は維持する。
- 台帳の古い「sentinelあり」「過去PRのCI待ち」などは現物と照合して関係PRで直す。台帳全体の再監査完了とはしない。
