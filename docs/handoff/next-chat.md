# 現在の引き継ぎ

更新日: 2026-10-23（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準

- 基準main: `0cfb0926bb4def84840bff991650abc069423a30`（PR #9 スカッシュマージ）。
- PR #9 mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39829840930) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39829840979) は同基準SHAで成功を確認。
- ローカル作業先は新クローン。作業ブランチ: `feat/create-only-machine-configuration`。旧エクスポート用ディレクトリは使わない。
- 利用者は優先順の継続と、必要検査成功後のマージを承認。CIは初回確認後90秒間隔で最大5回、最新HEADの両ワークフロー成功と競合状態を確認する。

## 現在の作業: 初回だけ設定を生成する補助処理

- PR #8（https://github.com/wasawo/eo-log-maintenance-public/pull/8）マージ済み。HEAD 2c517caec33ee517a2454eabe4bdd418271dc6e1 のValidate 39828401343 / Package 39828401425成功後にマージ。main fa13cf655b786b3caeecd2f61685b06e18b38b4f の39828675074 / 39828675339も成功。
- 構造ローダーの旧ブランチ feat/read-only-machine-configuration はマージ済み。現在は feat/create-only-machine-configuration。
- Common/MachineConfiguration.ps1: strict UTF-8（BOM可）のreaderとJSON構造/役割/型/maintenanceLocal分離parser。unknown/missing/duplicateキー、不正JSON/型/パス/PC役割を固定reasonで拒否。設定値・実パスはエラーへ出さない。
- PC-AのallowArchive trueは明示booleanデータとして許容するが、実行許可ではない。PC-Bはプロパティ自体を拒否。exampleは引き続きfalse既定をbuilderで要求。
- builderも同じ構造parserを使用。実設定・ディレクトリ・成果物を作成せず、元設定bytesを変更しない。285アサーションと配布テストがPowerShell 7.6.7でローカル成功。
- PR #9はHEAD 5be3bc95122de75ab9680188d7d1bef96d489ccf のValidate 39829546581 / Package 39829546536成功後、main 0cfb0926bb4def84840bff991650abc069423a30 へマージ。マージ後CIはValidate 39829840930 / Package 39829840979成功。
- 未実装: 物理的approved-root/reparse/短縮名alias/ボリューム分離確認、正式入口接続。初回生成/既存保持の補助処理は今回の追加範囲を参照。構造ローダー成功をruntime認可にしない。
- 今回は導入時のcreate-only設定生成（既存ファイルを変更しない）の限定補助処理を追加。OSD-09の未決定部分を推測しない。90秒間隔・最大5回で最新HEAD CI成功時のみマージ。

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
| 1: クラッシュ注入 | 成果物間の公開境界の合成ハーネス実装済み | 必要な追加の単一ファイル内部境界・クラッシュ残骸は別ケースとして評価。電源断試験へ拡大解釈しない |
| 2: 所有権/復旧/公開統合 | 合成統合証拠を追加済み | stale記録の実運用回復、新run/fresh inventory生成、source-race/検証から利用までの保護は未完了。記録の自動削除/引き継ぎを勝手に実装しない |
| 3: Tier B | PC-Bの14件部分証拠のみ | PC-Aの予定ボリュームで実行、残るadversarial FS/source-race/統合条件を収集。Tier B全体は未受け入れ |
| 4: 設定/初期導入 | maintenanceLocalと構造ローダーはマージ済み | create-only補助処理を追加中。物理root gate・正式導入入口・最終allowlist/移行は未完了 |
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

### 今回の追加範囲（PR #10）

- feat/create-only-machine-configuration: Common/MachineConfigurationBootstrap.ps1。
- 明示的な既存Configディレクトリだけを対象とし、対象PCの設定が存在すれば内容を変えずpreserved。未作成時だけ安全なexampleを検証し、専用tempへ書込/flush後に非上書きmove。PC-A allowArchive trueテンプレートは拒否。
- 既存設定（不正bytesを含む）の保持、PC別の新規生成、失敗時の未作成/残骸なしを合成領域で22アサーション成功。構造285アサーション・配布テストも成功。CI/マージは未確定。
- ソースcheckoutや実導入先で実行していない。実設定/実ログ/Driveへは触れていない。正式インストーラー、自動移行、物理root gate、敵対的race/クラッシュ/電源断の受け入れは含まない。
- 次は残る安全ゲートと未決定事項を照合する。PC-A/Tier Cや本番適用を推測で進めない。

- PR #10初回CI: Package 39830322174成功。Validate 39830322210は全テスト後のPSScriptAnalyzer外部ダウンロードで失敗（解析未実行）。失敗ジョブを再実行し、引き継ぎ基準SHAの補正を含む最新HEADで改めて両CIを確認する。
