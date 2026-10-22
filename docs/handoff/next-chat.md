# 現在の引き継ぎ

更新日: 2026-10-23（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準

- 基準main: 3ae8b76a5025c7abc43943f03915efbf8e2585e3（PR #12マージ）。
- mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39841288497) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39841288504) 成功を照合。
- PR #12最新HEAD ee356be0e7a15de8b7e712a44ee46a69a79eae30 の39840997905 / 39840997808成功後マージ。旧HEADのPackage workflow停止はjob成功で代替せず、未反映だった引き継ぎを反映した新HEADの通常CIで検証した。
- PR #11はe7d4e8e600a6f744fde4801565afe043b45d10c6へマージ済み。main 39834657799 / 39834657703成功。PC-B予定NTFSの21テスト部分証拠は tests/evidence/pc-b-internal-crash-local-volume-20261023.json。
- 利用者は優先順の継続と、最新HEADの必要検査成功後のマージを承認。初回確認後90秒間隔で最大5回再確認し、未完/失敗ならマージしない。
- 新クローンのブランチ fix/source-inventory-reparse-guards。以前の未コミット再現テストを保持して移り、今回の修正へ統合。

## 現在の作業: 元ログ列挙のreparse拒否

- SourceInventoryEvidenceBuilderでroot/ancestorをresolveせずlstatで検査。scandir前にqueued directoryを再確認し、entryをfresh lstat属性で分類。hash前後にもpath/ancestorを検査。
- root/ancestor junctionはsource_root_invalid、属性不明rootはsource_root_unavailable。子entry拒否/属性不明はenumeration_errorsを増やし未完了。元ログへ書込/削除は追加しない。
- 実Windows junction root/ancestor/childの修正前3件失敗を修正後成功。queued directory差し替え、root/entry属性失敗、hash直前ancestor拒否を加え7件成功。CIとopt-in local-volumeへ登録。全Python156テスト成功、既存symlink権限の2件スキップ。
- 最新HEAD CI・PR/マージは未確定。PC-B追加部分証拠はソース確定後に記録する。
- atomic snapshot、任意の敵対的namespace変更、物理approved-root/cross-root gate、後続利用までの保護、正式復旧/同期入口、Tier B全体/P0受け入れは未完了。

## 設定基盤の完了範囲

- PR #8: maintenanceLocal必須化、公開exampleと字句的重複拒否。
- PR #9: strict UTF-8/JSON構造・役割・型・unknown/duplicateキー・パス構文検証。285アサーション成功。
- PR #10: create-only補助処理。既存設定をbytes単位で保持、安全exampleだけ新規生成。22アサーションと配布テスト成功。
- PR #10最新HEAD e5df9a197a4644a29a0ae7d9bd38d0a2d9e06a65 のValidate 39830715865（attempt 2）/Package 39830715899成功後マージ。初回はPSGallery登録で失敗、検査は弱めていない。
- 実設定・実導入先では実行していない。物理approved-root/reparse/短縮名alias分離、正式導入/実行入口接続・移行は未完了。設定値は認可ではない。

## この作業でマージした内容

| PR | 変更 | 検証・マージ |
|---|---|---|
| [#3](https://github.com/wasawo/eo-log-maintenance-public/pull/3) | 自分の子プロセスを4つの公開境界で実終了し、別プロセスで検証・同一内容再試行。新規OS-temp領域だけの安全ガードとCI登録 | HEAD a44adc8 のValidate 39821756925 / Package 39821757018成功。マージfeecbcc、main 39822076933 / 39822077240成功 |
| [#4](https://github.com/wasawo/eo-log-maintenance-public/pull/4) | 実Windows mutexと公開・復旧判定の統合4件。競合、放棄、token不一致、検証後外部変更を確認 | HEAD 80e1c91 の39822745714 / 39822746256成功。マージ44b7002、main 39823075893 / 39823076056成功 |
| [#5](https://github.com/wasawo/eo-log-maintenance-public/pull/5) | 役割/予定ボリューム一致/明示ackを要求する実行入口。checkout直下の新規使い捨て領域だけを使用。PC-Bで10件の部分証拠 | HEAD 30a62ca の39824117058 / 39824117153成功。マージf96607c、main 39824401046 / 39824401199成功 |
| [#6](https://github.com/wasawo/eo-log-maintenance-public/pull/6) | 実ジャンクションroot/祖先の拒否漏れ2件を再現し、lstatのreparse属性・祖先・entryチェックでbytes読取前に拒否。実junction3件+読取失敗1件を追加 | HEAD 66162b9 の39824877670 / 39824877595成功。マージ19abd3f、main Validate 39825147373 / Package 39825147040成功 |

- 最新ローカル全Python: 137テスト成功、既存symlink権限のため2件スキップ。PowerShellは7.6.7、配布テストもPR #3準備時に成功。各PRの公開CIはPython 3.12等のCI環境で成功。
- PC-Bの予定ローカル固定NTFSボリューム: 修正後14件すべて成功、スキップなし。[部分証拠](../../tests/evidence/pc-b-reparse-local-volume-20261023.json)は実パス・ボリューム文字・ホスト名・tokenを含まない。
- 実設定・実ログ・Drive・アーカイブ・元ログ/Drive削除へは触れていない。ジャンクションは新規合成領域内だけに作成・除去。
- 検証は一点時点の防御。電源断耐久性、原子的な複数ファイル更新、任意の敵対的FS変更への完全防御、実運用復旧を証明しない。

## 残作業・依存順

| 順位 | 現在地 | 次の具体作業 |
|---|---|---|
| 1: クラッシュ注入 | 成果物間の公開境界の合成ハーネス実装済み | 単一ファイル内部5境界×2公開対象と残骸拒否の合成検証はPR #11でマージ済み。電源断試験へ拡大解釈しない |
| 2: 所有権/復旧/公開統合 | 合成統合証拠を追加済み | stale記録の実運用回復、新run/fresh inventory生成、source-race/検証から利用までの保護は未完了。記録の自動削除/引き継ぎを勝手に実装しない |
| 3: Tier B | PC-Bの21件部分証拠のみ | PC-Aの予定ボリュームで実行、残るadversarial FS/source-race/統合条件を収集。Tier B全体は未受け入れ |
| 4: 設定/初期導入 | maintenanceLocalと構造ローダーはマージ済み | create-only補助処理はPR #10でマージ済み。物理root gate・正式導入入口・最終allowlist/移行は未完了 |
| 5: Drive/IPC | 未実装・契約/認証の決定待ち | Python1呼出し1試行、PowerShell再試行、不明結果照合、metadataだけの検証拒否。OSD-05と契約条項を解決 |
| 6: 正式同期 | 未実装 | 承認済みOSD-02/03と残る遷移表を整合し、安全ゲート完了後に正式入口を統合 |
| 7: Tier C/PC-A archive | 未実施・未実装 | Tier B/専用計画の承認後、使い捨て同期領域で検証。両PCの証拠と直前Drive内容検証を要求。copy/verify/recordのみ |
| 8: E2E/P0 | 未受け入れ | SEL-RT/IPC/Dry Run/非破壊性、要件→実装→実行証拠、削除機能不在を検証。P0-010/P0-012は未完了 |
| 9: 本番配布 | 未承認・未実装 | OSD-06/07/09を解決。版/来歴/承認・PC別allowlist・実設定保持・手動適用/回復を確認 |

4の確定済み設定基盤は1〜3と並行設計可能だが、未決定事項を推測しない。
参照: [対象FS計画](../target-filesystem-acceptance.md)、[ロック/復旧](../lock-recovery-acceptance-gate.md)、[正式入口ゲート](../runtime-entrypoint-validation-gate.md)。

## 利用者への確認中・既に確認したこと

- 現在の端末はPC-B。管理成果物とは、そのPCが生成するマニフェスト・一覧/検証証拠・集計レポート・marker/lock等。PC-Aの原本はPC-A側に置き、両PC向けの検証済みコピーをDriveへ公開する方針。
- PC-B予定固定ディスク上に新規合成領域を作る検証を実施した。実パスや実ボリューム文字は公開しない。実設定はGit管理外のConfig/PC-B.jsonへ将来入力する。
- 承認済み（2026-10-23）: 両PC設定へ `maintenanceLocal`（そのPCのマニフェスト・検証証拠・レポートのローカル原本領域）を追加する。exampleはダミー、実値は非追跡設定、実行先/元ログ/Drive/archiveとの重複を拒否。実パスは推測しない。
- OSD-04（Dry Run副作用）、OSD-05（Drive認証）、OSD-06/07（配布/保持）、OSD-08（予定実行）、OSD-09（最終allowlist/移行）と残る状態遷移/契約の承認・証拠は別途必要。
- 台帳の古い「sentinelあり」「過去PRのCI待ち」などは現物と照合して関係PRで直す。台帳全体の再監査完了とはしない。
