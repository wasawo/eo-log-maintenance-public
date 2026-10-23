# 現在の引き継ぎ

更新日: 2026-10-23（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準

- 基準main: a0d99f097c6a291876c13ae3fdc4330c4ba8db10（PR #26マージ）。
- mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39968901406) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39968901349) 成功を照合。
- PR #15 HEAD f82aa2860ab3510a9002bc5bb771a3f0a48badb5 の39944930803 / 39944930629成功後マージ。existing-root metadata helper、142合成アサーション（短縮名skip 0）を追加。既存PC-B予定volume証拠を拡張しない。
- PR #14（13503f6）はstrict lock/recovery evidence、#13（41811bd）はsource reparse拒否、#12（3ae8b76）はhash handle identity、#11（e7d4e8e）は公開内部クラッシュ境界。各main両CI成功。
- 利用者は優先順の継続と、最新HEADの必要検査成功後のマージを承認。初回確認後90秒間隔で最大5回再確認し、未完/失敗ならマージしない。
- 新クローンのブランチ feat/pc-a-completion-wait-budget。

## 今回の作業と中断位置: PC-A確認予算の実装・マージまで

- PR #26 HEAD a13dee25c21f1769caf2d863bfcf3116a2234ed2のValidate 39968593998 / Package 39968594091成功後マージ。mainも上記両CI成功。
- 利用者は「最大24時間・初回含め25回で保留」を承認（2026-10-23）。同じ上限を再確認しない。期限到達をmanifest失敗/成功、archiveやlock回復/upload retry許可へ変換しない。
- 最新指示: いったん「次PR作成で中断」とした後、今回の確認予算について「実装とマージまで進めてよい」と変更。今回はこのPRの検証・マージ・main確認まで実施し、そこで一時中断する。以前の自動継続承認で次の作業を始めず、明示的な再開指示を待つ。
- Common/CompletionWaitBudget.py: PC-A/log/period/元run_idと最初の適格観測UTC・全試行UTCの不変履歴にbinding。24時間、1時間以上、最大25回を検証し、check_due/wait/holdだけ返す。結果は常にmay_archive/may_change_state=false。
- 期限ちょうどの最終適格確認は許可候補に含め、それ以降は保留。遅い確認の次も1時間空け、機会不足で回数が余っても期限を延長しない。clock逆行/不明、scope/履歴不正、未確認gateも保留。
- record_completion_check_attemptは全条件を再検証し、候補時だけ新しいtupleを返す。IO/待機/task/Drive/保存は行わない。実確認前の信頼できる永続更新が必要で、失敗試行も消費する。履歴喪失・巻き戻し耐性はこのhelperだけでは実装しない。
- 新規16合成テスト成功。Python 3.11.9全306件成功（既存symlink権限で2件skip）、PowerShell 7.6.7配布回帰成功。CI・配布fixture・コード・関連仕様・引き継ぎを同じPRへ。PR/最新HEAD CI・マージ結果は記録時点では未確定。確定結果は本PRと実main/CIを照合する。
- [承認記録](../pc-a-completion-wait-budget-proposal.md)、[実装の契約と限界](../completion-wait-budget.md)を更新。OSD-08の予算未承認という記述は解消するが、runtime qualification/rolloutやP0/Tier Bは未完了。

## 再開時の具体手順

1. 本PRの状態・最新main SHA・両CIを確認し、未コミット変更を保全する。中断指示は再開指示があるまで維持。
2. 次の実装候補は確認予算の信頼できる永続化/読取・scope/run binding・原子的試行計上とクラッシュ/再試行検証。元の開始時刻・試行履歴を失った場合は停止し、新しい予算へ黙って置き換えない。
3. その後、最新manifest/Drive内容検証・実clock/session/account・mutexと統合する。待ち時間の間ずっとmutexを保持せず、不正manifestを時間待ちに読み替えない。
4. 正式task登録、実効ACL/provider/祖先/safe creation/実保存、旧lock処分、新run、Drive/本番復旧は未実装/未承認。公開schema/helper/CI成功で本番受け入れを済ませない。

承認済み: 明示回復、v1保全/v2対象、private maintenanceLocal保管/自動削除なし、同一account、ログオン中のみ、毎月1日PC-B20:00/PC-A21:00 JST、PC-A確認24時間/25回。これらを同じ内容で再質問しない。

## 設定基盤の完了範囲

- PR #8: maintenanceLocal必須化、公開exampleと字句的重複拒否。
- PR #9: strict UTF-8/JSON構造・役割・型・unknown/duplicateキー・パス構文検証。285アサーション成功。
- PR #10: create-only補助処理。既存設定をbytes単位で保持、安全exampleだけ新規生成。22アサーションと配布テスト成功。
- PR #10最新HEAD e5df9a197a4644a29a0ae7d9bd38d0a2d9e06a65 のValidate 39830715865（attempt 2）/Package 39830715899成功後マージ。初回はPSGallery登録で失敗、検査は弱めていない。
- 実設定・実導入先では実行していない。既存rootのmetadata補助検査は上記の追加範囲。approved-root権限/FS資格/利用直前までの保護、正式導入/実行入口接続・移行は未完了。設定値は認可ではない。

## この作業でマージした内容

| PR | 変更 | 検証・マージ |
|---|---|---|
| [#3](https://github.com/wasawo/eo-log-maintenance-public/pull/3) | 自分の子プロセスを4つの公開境界で実終了し、別プロセスで検証・同一内容再試行。新規OS-temp領域だけの安全ガードとCI登録 | HEAD a44adc8 のValidate 39821756925 / Package 39821757018成功。マージfeecbcc、main 39822076933 / 39822077240成功 |
| [#4](https://github.com/wasawo/eo-log-maintenance-public/pull/4) | 実Windows mutexと公開・復旧判定の統合4件。競合、放棄、token不一致、検証後外部変更を確認 | HEAD 80e1c91 の39822745714 / 39822746256成功。マージ44b7002、main 39823075893 / 39823076056成功 |
| [#5](https://github.com/wasawo/eo-log-maintenance-public/pull/5) | 役割/予定ボリューム一致/明示ackを要求する実行入口。checkout直下の新規使い捨て領域だけを使用。PC-Bで10件の部分証拠 | HEAD 30a62ca の39824117058 / 39824117153成功。マージf96607c、main 39824401046 / 39824401199成功 |
| [#6](https://github.com/wasawo/eo-log-maintenance-public/pull/6) | 実ジャンクションroot/祖先の拒否漏れ2件を再現し、lstatのreparse属性・祖先・entryチェックでbytes読取前に拒否。実junction3件+読取失敗1件を追加 | HEAD 66162b9 の39824877670 / 39824877595成功。マージ19abd3f、main Validate 39825147373 / Package 39825147040成功 |

- PR #3〜6当時のローカル全Python: 137テスト成功、既存symlink権限のため2件スキップ。PowerShellは7.6.7、配布テストもPR #3準備時に成功。各PRの公開CIはPython 3.12等のCI環境で成功。
- PC-Bの予定ローカル固定NTFSボリューム: 修正後14件すべて成功、スキップなし。[部分証拠](../../tests/evidence/pc-b-reparse-local-volume-20261023.json)は実パス・ボリューム文字・ホスト名・tokenを含まない。
- 実設定・実ログ・Drive・アーカイブ・元ログ/Drive削除へは触れていない。ジャンクションは新規合成領域内だけに作成・除去。
- 検証は一点時点の防御。電源断耐久性、原子的な複数ファイル更新、任意の敵対的FS変更への完全防御、実運用復旧を証明しない。

## 残作業・依存順

| 順位 | 現在地 | 次の具体作業 |
|---|---|---|
| 1: クラッシュ注入 | 成果物間の公開境界の合成ハーネス実装済み | 単一ファイル内部5境界×2公開対象と残骸拒否の合成検証はPR #11でマージ済み。電源断試験へ拡大解釈しない |
| 2: 所有権/復旧/公開統合 | 合成統合証拠を追加済み | 最新候補選択コアはPR #16、read-only disk adapterはPR #17済み。復旧分類との合成接続を検証。専用の明示的回復入口の設計方針は承認済み。診断設計を追加。stale記録の実運用回復、新run/fresh inventory生成、source-race/検証から利用までの保護は未完了。記録の自動削除/引き継ぎを勝手に実装しない |
| 3: Tier B | PC-Bの29件部分証拠のみ | PC-Aの予定ボリュームで実行、残るadversarial FS/source-race/統合条件を収集。Tier B全体は未受け入れ |
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
