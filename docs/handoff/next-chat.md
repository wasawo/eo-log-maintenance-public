# 現在の引き継ぎ

更新日: 2026-10-23（日本時間）

恒久ルールは [AGENTS.md](../../AGENTS.md)。過去の記録は [アーカイブ](archive/pre-agents-history.md)。
この文書の優先順は作業候補であり、未決定仕様の承認・実端末検証・本番適用の許可ではない。

## 最新基準・完了事項

- 正本: `wasawo/eo-log-maintenance-public`（Public）。元リポジトリは Private。
- GitHub main: `f96607cea72ffa8e25c1a5874b18d272379fa974`。PR #5 のスカッシュマージを確認。
- main の [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39820210106) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/39820210102) は同SHAで成功。
- PR #1: 正本参照更新・旧PR #168の受け入れ計画移植がマージ済み。マージSHA `40357512cb1c1327fd1cbfdf34e7596ee20a327d` のmain CIも両方成功。
- PR #2: リポジトリ固有ルールを AGENTS.md、進捗を本書へ分離し、長い過去記録を保存。マージ済み。
- 実設定 `Config/PC-A.json` / `Config/PC-B.json` は .gitignore 対象。汎用名 config.json は現行の設定名ではなく除外対象でもない。
- ローカル作業ブランチ: test/owned-publication-recovery-integration。PC-B端末で作業中。前作業の残作業整理をPR #3へ保全済み。

## 現在の作業: Tier B異常系で再現したジャンクション拒否漏れ

- PR #5（https://github.com/wasawo/eo-log-maintenance-public/pull/5）マージ済み。HEAD 30a62cac9d594d45880774d28811b8f6b2f95ae7 の Validate 39824117058 / Package Validation 39824117153 が成功後にマージ。マージSHA f96607cea72ffa8e25c1a5874b18d272379fa974 のmain Validate 39824401046 / Package Validation 39824401199 も成功。
- ブランチ: fix/reparse-artifact-directory-verification。
- 実Windowsジャンクションで、検証rootと祖先がis_symlinkだけでは拒否されずbytes読取へ到達する2件の不具合を先に再現。
- Common/ArtifactSetDirectoryVerification.py をlstatのreparse属性と祖先チェックで強化。既存仕様のfail-closed条件を維持し、弱めない。TOCTOU完全防御ではない。
- 実ジャンクション3件と読取失敗1件を追加。ローカル全Python137テスト成功（既存symlink権限2件スキップ）。CI登録と予定ボリュームrunnerにも追加。
- PC-Bの実パス・ドライブ文字は公開しない。前回の部分証拠はtests/evidence/pc-b-local-volume-20261023.jsonに保持。修正版での14件が予定固定NTFSボリュームでも全成功（スキップなし）。tests/evidence/pc-b-reparse-local-volume-20261023.json に実パスなしで記録。
- 最新PR HEAD CI・この修正のマージは未確定。各PRは90秒間隔・最大5回確認し、最新HEADの必要検査成功後にマージする承認あり。
- 次の設定基盤ではローカル原本領域 maintenanceLocal の追加案を利用者へ確認中。既存exampleには対応項目がなく、未承認の保存場所を推測しない。PC-A側証拠・残るsource-race/統合・Tier Cは未実施。

## 実装・証拠の現在地

- あり: ファイル名/期間判定、診断処理、スキーマ、成果物参照・整合性検証、読み取り専用インベントリ、単一/複数成果物公開、ディレクトリ検証、所有権ロック、復旧判定の補助実装と合成テスト。
- なし/未完: 正式なSyncLogs/PC-A専用ArchiveLogs、実設定ローダー、導入時の実設定生成、Driveアダプターとランタイム統合、E2E受け入れ、本番配布。
- 部分証拠: 例外注入による中断、複数プロセスの公開競合。すべての公開境界での実プロセス終了・新プロセスでの復旧検証やロックとの統合は未完了。
- Tier B/Cは未実施。既存CI成功を対象PC/Drive/ネットワーク/電源断耐久性の証明としない。P0は未受け入れ。

## 残作業の推奨順序

| 順位 | 作業 | 完了条件・依存 |
|---|---|---|
| 1 | 使い捨て領域のクラッシュ注入ハーネスを設計・実装 | 明示root・本番/Drive領域拒否・合成データのみ。全公開境界で子プロセスを終了し、新プロセスでmarker/bytes/hash/不完全状態を確認。CI用の一時領域から始める |
| 2 | ロック・復旧判定・公開・再検証を統合した合成テスト | 所有権不一致、競合、異常終了、同一内容再試行、異内容拒否、検証から利用までの競合、元成果物不変を確認。1に依存 |
| 3 | Tier B: 各PCの想定ローカルボリュームを適格性検証 | 別途承認した使い捨てrootで1/2を実行し、OS/FS/版/シナリオ/結果を秘密情報なしで記録。未対応FSはfail closed |
| 4 | 実設定ローダー・導入初期設定生成 | PC役割・未知フィールド・絶対パス・root分離・安全既定値を検証。未作成時のみexampleから実設定生成、更新時保持。手動作業は実パス入力のみ。OSD-09の未決部分は先に合意 |
| 5 | Driveアダプター・IPC・再試行/照合 | OSD-05と契約の未決事項を解決。Pythonは1呼出し1試行、PowerShellが再試行管理。不明結果は再送前照合、metadataのみの検証を拒否 |
| 6 | マニフェスト状態遷移・同期処理の統合 | 承認済みOSD-02/03を実装し、残る遷移表・意味論を確定。正式入口は安全ゲートの前提完了後。全対象期間・元ログ不変・異常時副作用なしを検証 |
| 7 | Tier CとPC-A専用アーカイブ統合 | Tier Bと専用計画承認後、使い捨て同期/ネットワーク領域で検証。両PCの現行証拠と直前Drive内容検証を要求。コピー・検証・記録のみ、削除なし |
| 8 | E2E・P0受け入れ判定 | SEL-RT/IPC、Dry Run、失敗時の非破壊性、ソース/設定/契約/配布物/ランタイムの削除機能不在、要件IDと実行証拠を照合。文書やhelper CIだけでは完了にしない |
| 9 | 本番配布・更新・回復/運用手順 | OSD-06/07/09を解決。タグ/版/承認/来歴・PC別許可リスト・実設定保持・手動適用・ロールバックを検証。正規入口未実装中は非配布マーカーを維持 |

4の設定基盤や次節の仕様決定は1〜3と並行して設計可能。上の順序は依存関係の目安で、既存承認を変更するものではない。
受け入れ条件の詳細は [対象FS計画](../target-filesystem-acceptance.md)、[ロック/復旧](../lock-recovery-acceptance-gate.md)、[正式入口ゲート](../runtime-entrypoint-validation-gate.md)。

## 先に解決する仕様・承認

- OSD-02/03: 承認済み部分は再決定せず、残る状態遷移・集約・実行時証拠を特定する。
- OSD-04: Dry Runで許容するローカル出力/ロック/一時ファイル/マニフェストの副作用表。
- OSD-05: 最小権限のDrive認証方式・スコープと実フォルダのアクセス検証。合成テストだけでは代用不可。
- OSD-06/07: リリース承認・版/来歴・保持/旧配布物整理方針。
- OSD-08: スケジュール実行と重複実行の運用条件。既存ロック方針と整合させる。
- OSD-09: 最終PC別配布許可リスト・移行手順・実設定保持。
- Drive契約のパス/操作別応答/相関・終了コード等の未決事項を、実装前に条項単位で確認。
- 参照: [未決事項台帳](../p0-open-specification-decisions.md)、[決定記録](../decision-register-c18-c32.md)。

## 台帳の整合と今回の検証

- P0台帳には古い「SyncLogs sentinelあり」等の表現が残るが、現物のscriptsにはREADMEのみ。未決事項台帳にも過去PRの「CI待ち」記載がある。後続でソースと最新承認記録に照合して修正する。台帳全文を再監査済みとは扱わない。
- P0-010（要件→実装→実行テスト→証拠）、P0-012（削除機能不在）は引き続き未完了。各実装PRで関係行を更新する。
- この作業では合成プロセスクラッシュと実Windows mutexの統合テストを追加。実端末ボリュームのTier B適格性検証・Drive操作・正式ランタイムは未実行。PR #3のマージとCIを確認し、次の統合テストPRを準備中。
- 次に着手する最小単位の推奨: 順位1の安全なroot受付とクラッシュ注入シナリオの実装計画を、既存出版ヘルパー/テストと照合して具体化する。
