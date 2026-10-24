# 現在の引き継ぎ

更新日: 2026-10-24（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

- 最新mainは `179787f62ad0e07d58e139d7059ea84de149ed05`（[PR #38](https://github.com/wasawo/eo-log-maintenance-public/pull/38) マージ済み）。PRの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40084689827) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40084689833)、mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40085003755) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40085003841) 成功後の停止記録は `54f1418`。runtime実装の継続ではなく、利用者の未決事項選択・記録と指示文書改訂だけをbranch `docs/selected-policy-decisions` で進めている。未push・新規PRなし。
- [仕様決定記録](../decisions/selected-policy-decisions-20261024.md)へ①〜㉑の回答を反映。C-01 P1/検査V1/L1全体/現1.0改訂、B2 V1、report G1、C-02 R1/N1/D1、Drive I1/A1/S1/T1、owner F1/B1、条件付き状態遷移表採用、release E1、全version保持・自動cleanupなし、PC別version別file manifest、明示的設定移行、ローカル画面通知＋状態ログの方向が確定した。質問と回答の範囲を越えてfield集合・provider・実施を確定しない。
- **2026-10-24の最新利用者指示によりサブエージェント利用を中止。root単独運用。** 新規作成・既存再利用・組込み/カスタム担当・別AIタスクへの委譲を行わない。中止時の確認では稼働中担当はなく、既存担当は完了または終了状態だった。旧目標の「既存3担当のみ再利用」は撤回済みで、過去記録・環境の担当一覧から再開しない。
- AGENTS.md、[現行手順](../development/agent-workflow.md)、両skill・索引をroot単独へ更新し、project .codex/config.tomlをagents.enabled=falseとした。旧3役割TOMLと旧分担手順は [失効した履歴](../development/archive/README.md) に保全。役割TOMLは移動前後hash一致、Git改行正規化後の本文一致とparseを確認。旧手順は失効banner/相対リンク以外の本文一致を確認。個人/global設定・主モデル/思考量は変更していない。project設定の信頼/読込と現会話への即時tool反映は未検証で、以後の不使用は利用者指示と現行手順で徹底する。
- 利用中止前の初期7文書は独立reviewでP1/P2なし、invariants節分断P3を修正。追加⑦〜⑫のreviewでは旧承認待ち表記P2を指摘されrootで修正した。これらは当時の差分だけの履歴であり、⑬以降や利用中止対応を含む最新全差分はrootが単独点検し、独立レビューは実施していない。独立レビュー済みと表記しない。
- 今回のroot単独点検: 変更20 Markdownの相対リンク189件欠落0、差分検査成功。project/旧役割のTOML計4ファイルをparseし、agents.enabled=false、主思考量不変、active役割ファイルなしとarchived本文保全を確認した。文書・指示・Codex設定のみで無関係な機能/package検査は再実行していない。新CI未実行。
- 未確定/未完：C-02の具体field集合・型・値域・plan形、具体store/SDK/flow/ACL、owner-v2全fieldと適格machine/boot provider、移行mapping、最終実file一覧とmanifest形式、task trigger/電源等の具体運用。G1/B2 V1等へのコード/schema追従、実保存・認証・実API・両PCroot/FS・runtime/Drive/耐久性の受け入れも未実施。今回の設定変更はCodex作業設定に限り、アプリケーションコード/runtime schema/tests/実設定は変更していない。
- 仕様選択と実装/公開/PRマージ/本番適用の許可を分離し、PR/マージは個別承認、1PRマージ後の中断・継続可否確認を維持する。新たな実装や実接続を独断開始しない。旧C-01資料branch `9343f71` は選択前の履歴として保全し、現選択はこのbranchの決定記録を優先する。

## 旧進捗の参照

PR #27〜33前後の旧進捗節は [セッション記録](archive/pr27-pr33-session-history-20261024.md) に保存した。過去の承認待ち・CI待ち・agent生成禁止を現在の指示として実行しない。

## 次回の実装再開時

1. まず利用者の継続指示を確認し、正本mainとローカル保全branchのコミット・作業ツリーを照合する。C-01のP1/検査V1/L1/現1.0改訂の選択は済んでいるので再質問しない。実装実施の承認と残る具体契約は別途確認する。Aは承認済みで再質問しない。IPC全体、C-02具体field、OSD-05の具体store/API/資格等の残る未確定を区別する。
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
