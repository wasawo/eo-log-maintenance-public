# 現在の引き継ぎ

更新日: 2026-10-24（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

- 利用者の「継続して」でPR #36後の中断から再開。現branch `docs/contract-decision-packet` はmain `b3ad373` + 停止記録 `a9b68a8` から分離。保全済みの認証/owner-v2判断資料6ファイルを最新基準へ統合し、[B2検証網羅性とreport生成時刻の永続出所の未承認比較](../decisions/b2-validation-coverage-report-time-options.md)を追加し、独立review指摘なし。コード/schema/設定/承認状態は変更しない。資料の公開・マージは未承認で、方針採用とは別に扱う。

- 今回資料の検証: 変更9文書のローカルリンク118件欠落0、差分検査成功。reviewerはhandoffを除く8文書/112リンクを独立確認し指摘なし。文書のみで機能・package検査は再実行せず、コード/schema/設定・方針承認を変更していない。ローカル保全のみで未push・新規PR/CI未実行。
- 最新mainは `b3ad37379458309d3412573a20124439b7e524ff`（[PR #36](https://github.com/wasawo/eo-log-maintenance-public/pull/36) マージ済み）。利用者の「マージして」に基づき、B2修正とhandoffの6ファイルを対象に、最新HEAD `a05fe3f0c8b2d85fee74cba943a9d37d46d1f1f3` の [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40079437538) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40079437529) 成功後にsquash mergeした。
- 承認済みB2契約§6.1が禁止するfloatをcanonical JSON化前に再帰的に固定理由で拒否。`1.0`等を整数へ変換・修復しない。旧誤digestやexact参照hashが一致しても、integrity/report builder/参照成果物の各経路で拒否する。通常整数出力・既存vector・入力bytes/hashを維持し、schema/版/規範契約を変更していない。独立review指摘なし。
- 実装時ローカル検証: Python 3.11.9で関連48件・全346件成功（既存2件skip）。reviewerも関連48件を独立実行。変更2文書リンク5件欠落0、差分検査成功。PS/設定/依存/配布allowlist変更なしで無関係なPS/package検査は再実行せず、CI Python3.12のValidateとPackageが成功。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40079607571) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40079607574) も成功。
- 未公開判断資料は `docs/remaining-contract-decisions` の `4e72846` に再統合して保全済み。元の `docs/drive-auth-options-after-pr34` の4コミット（HEAD `643eaf6`）も保持し、PR #36へ取り込んでいない。認証/owner-v2の資料6ファイルのローカルリンク102件欠落0、差分検査成功。公開・マージ範囲とC-01方針は未承認で、回答なしを承認としない。
- B2 validation網羅性とincompleteの意味、生成UTCの永続出所/後日の同一bytes再生成、完全状態遷移、runtime・両PC実root/FS・Drive内容/耐久性の受け入れは未決・未完。helper/合成テスト/package/CI成功をそれらの完了にしない。集約report builderはPR #35でマージ済み。
- PR #36後に中断し、その後利用者の継続指示で再開した。利用者指定のセッション目標は、既存analyst/implementer/reviewerのみ再利用し、未決仕様を推測せず合成/隔離検証・独立review・handoffを完了、PR/マージ権限は個別承認内とし、**1PRマージごとに中断して継続可否を尋ねる**。次のPRマージ時に再び中断し、継続可否を尋ねる。停止記録は `docs/pr36-paused-handoff` の `a9b68a8` に保全し、新規PR/マージはまだ実施していない。

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
