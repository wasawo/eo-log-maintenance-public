# 現在の引き継ぎ

更新日: 2026-10-24（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

- 利用者の継続指示: 5時間枠の残量10%まで後続作業を続ける。残量はagentから直接取得できないため、利用者が到達時に停止を知らせる。指定3役のみを再利用する。
- 最新基準mainは `a0b37bf30f1329209d5516888cc93c65c1e58f9e`（[PR #33](https://github.com/wasawo/eo-log-maintenance-public/pull/33) マージ済み）。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40045585873) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40045585917) 成功、開始時clean。前回の「コミット準備中」記録より本項を優先する。
- branch `fix/mutex-close-failure` で、analystが指摘したnative mutex adapterのCloseHandle失敗見逃しと通常lockのNaN timeout入力検証不足を修正。closeのBOOL失敗を固定理由で拒否し、成功時だけhandle参照をclear、診断helperのcleanup失敗へ接続。NaNはtoken/path/mutex準備前に拒否し、無限大・巨大整数の既存理由を維持する。両小修正の独立reviewer指摘なし。
- 検証: Python 3.11.9、対象lock16件/diagnostic mutex14件成功。通常環境で全320件成功（既存2件skip）、PowerShell 7.6.7を使う既存合成回帰を含む。差分検査成功。CI Python3.12は未実行。PS実装・配布の変更はなく独立PS/package回帰は未実行。native無効handleを実際にcloseする検証は行わずfake kernel32で戻り値を注入した。
- この修正単位はローカルに記録し、未push・PR未作成。scope identity/access、root authority、IPC等の未確定仕様は含めず、runtime・実環境資格/耐久性の受け入れは未完。後続候補は承認済み部分の残存ギャップ、またはC-01/C-02の判断資料をanalystが調査中。新しいPR/マージはまだ実施していない。
- 上記mutex修正はローカル `93537b01da58f4febeef69a3cd486eef74327e1ab` に記録済み。継続branch `docs/ipc-path-result-decision-options` はこのローカルコミット上で、[C-01/C-02の回答用判断資料](../decisions/c01-c02-ipc-contract-options.md) と索引・所見参照を追加。独立reviewer指摘なし、4文書のローカルリンク91件欠落0、差分検査成功。文書のみのため機能テスト再実行なし。
- schema・規範契約・adapterの変更や承認状態の更新は行っていない。C-01のP1（drive-rootedのみ）+ V1（schemaにも構文検査）で未実装1.0を改訂する案を利用者へ確認中。回答なしを承認としない。C-02の操作別field/null/計画形と移行、root/排他資格、OSD-05、IPC全体レビューは未決/未完のまま。正本mainは引き続き `a0b37bf`。両作業単位は未pushで新しいPRなし。
- 判断資料へGoogle公式REST資料の根拠と確認日を追加し、API生値/adapter正規化候補/SDK未確認を分離した。独立reviewerは補足内容の指摘なし。旧進捗56行は相対リンク以外の本文を保持してarchiveへ移動し、currentのOSD-04/08表記と再開手順を整合。reviewerの棚卸し直接リンク不足（P3）を修正した。文書のみで機能テスト再実行なし。

## 旧進捗の参照

PR #27〜33前後の旧進捗節は [セッション記録](archive/pr27-pr33-session-history-20261024.md) に保存した。過去の承認待ち・CI待ち・agent生成禁止を現在の指示として実行しない。

## 次回の実装再開時

1. 正本mainとローカル2作業単位のブランチ/コミット・作業ツリーを照合する。C-01の回答待ちは上記を参照し、未回答なら依存schema改訂を保留する。Aは承認済みで再質問しない。IPC全体/C-02/OSD-05等の未決定は維持する。
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
