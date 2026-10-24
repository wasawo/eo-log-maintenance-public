# 現在の引き継ぎ

更新日: 2026-10-24（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

- 最新mainは `179787f62ad0e07d58e139d7059ea84de149ed05`（[PR #38](https://github.com/wasawo/eo-log-maintenance-public/pull/38) マージ済み）。利用者の「作成したPRをマージして作業中断」に基づき、未作成だった確認済みhelperの9ファイルからPRを作成。最新HEAD `160dce0b591f008d07244e96c4214854aea17699` の [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40084689827) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40084689833) 成功とmerge要件を確認してsquash mergeした。C-01詳細案はこのPRへ含めていない。
- `Common/DriveResponseSemantics.ps1` はcaller-supplied decoded値のrequest ID/operation相関とexit/envelope/error-code対応だけを純粋に検査する。Ordinal比較とOrdinal許可集合を使い、不可視文字を許可operation/codeへ一致扱いにしない。固定Status/ReasonCodeのみ出力し、入力不変・秘密非echoを維持。consistentはresult信頼・retry・運用続行・認可を意味しない。
- 実装時検証: CI固定hashと版を確認した一時PowerShell7.6.7で最終117検査成功、reviewer独自54負例成功。両役割package回帰、変更PS3ファイルの構文/PSScriptAnalyzer Error（Ordinal修正後2PSも再検証）、変更5文書リンク28件欠落0、差分検査成功。独立reviewの未解決指摘なし。schema/Python変更なしで無関係な全Python/既存PSは再実行せず、個人/global設定は変更していない。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40085003755) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40085003841) も成功。
- C-01 L1詳細字句候補は別branch `docs/c01-lexical-candidate` の `9343f71` にローカル保全。`docs/decisions/c01-drive-rooted-lexical-candidate.md` と参照元/索引/handoffの4文書で、独立review指摘なし・リンク99件欠落0・差分検査成功。未push・PRなし。P1/V1、L1詳細、schema1.0互換・実施範囲の回答は未承認で、schema/runtime/fixtureは未実装。元停止記録branchや旧資料branchも保全する。
- [C-01/C-02](../decisions/c01-c02-ipc-contract-options.md)、[認証](../decisions/osd-05-drive-auth-identity-scope-options.md)、[owner-v2](../decisions/owner-v2-field-binding-options.md)、[B2検証網羅性/生成UTCの永続出所](../decisions/b2-validation-coverage-report-time-options.md)の選択は未決。新helperもC-03/部分C-05の補助に限り、transport/UTF-8/JSON一件/schema/実request由来/操作別result、retryable真理値表・RETRY-02、実child/Drive/root/FS/runtime受け入れは未完。資料やhelper/CI成功を方針採用・P0-005/IPC全体の完了としない。
- 現在は**利用者指示によるPR #38後の作業中断状態**。次作業を独断で開始しない。再開後も既存analyst/implementer/reviewerのみ再利用し、未決仕様を推測せず合成/隔離検証・独立review・handoffを完了、PR/マージ権限は個別承認内とする。1PRマージごとに中断して継続可否を確認する。本停止記録は `docs/pr38-paused-handoff` にローカル保全し、未push・追加PRなし。

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
