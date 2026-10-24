# 現在の引き継ぎ

更新日: 2026-10-24（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

- 最新mainは `67ca37a3f986ba89576e6961d12858f5ccf0170f`（[PR #34](https://github.com/wasawo/eo-log-maintenance-public/pull/34) マージ済み）。利用者が指定したmutex修正・C-01/C-02判断資料等の3コミットを1PRに統合した。PR最新HEADのValidate（attempt 2）/Package成功後にマージ。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40056434078) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40056434032) も成功。判断資料のマージは方針採用ではない。
- 現branch `feat/aggregation-report-builder` はこのmainから分離。承認済みOSD-03/R1〜R7/T-01〜12に基づく、副作用なしの集約report builderを実装し独立検証中。exact manifest/B2 bytesと明示時刻等からsummary/report bytesを導出し、状態遷移・正式writer・Drive・認可へ接続しない。zero-work空period配列とJSON整数を既存PS validatorが拒否する相互運用不具合も修正対象。
- 最終Python全337件成功（既存2件skip、新builder17件を含む）、PS internal validator 33アサーション成功、両役割package回帰成功。PowerShell 7.6.7の22ファイル構文/Error analyzerと修正後2PSの再検証成功。独立reviewの件数再導出P2を修正し、PS空配列/JSON整数型/大整数精度の相互運用不具合を修正した。変更5文書のローカルリンク44件欠落0、差分検査成功。Pythonはローカル3.11.9/CI3.12の差があり、このbranchのCI・push・PRは未実施。
- 未公開の判断資料等4コミットは別branch `docs/drive-auth-options-after-pr34` の `643eaf6f6978eb518a12ff8b748917b5aea5e8d8` に保全し、本branchへは取り込んでいない。それらのPR/マージ範囲とC-01方針は利用者回答待ち。未回答を承認とせず、今回builderはこれらの未決と独立した既承認集約契約の範囲に限定する。今回builder単位の新規公開/マージはまだ実施していない。
- B2 incomplete validationの網羅性、生成時刻の永続出所と後日の同一bytes再生成、完全状態遷移、runtime・両PC実root/FS・Drive内容/耐久性の受け入れは未完。pure helperやpackage成功をそれらの完了にしない。
- 利用者の継続指示: 5時間枠の残量10%まで後続作業を続ける。残量はagentから直接取得できないため、利用者が到達時に停止を知らせる。指定3役のみを再利用する。

## 旧進捗の参照

PR #27〜33前後の旧進捗節は [セッション記録](archive/pr27-pr33-session-history-20261024.md) に保存した。過去の承認待ち・CI待ち・agent生成禁止を現在の指示として実行しない。

## 次回の実装再開時

1. 正本mainと上記builder branch/保全済み文書branchのコミット・作業ツリーを照合する。C-01の回答待ちは上記を参照し、未回答なら依存schema改訂を保留する。Aは承認済みで再質問しない。IPC全体/C-02/OSD-05等の未決定は維持する。
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
