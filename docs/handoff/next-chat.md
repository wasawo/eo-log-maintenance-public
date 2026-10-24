# 現在の引き継ぎ

更新日: 2026-10-25（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

- 2026-10-25の追加規則をAGENTS.md・現行手順・Git/PR skillへ反映：mainへの直接push禁止。マージ後は最新mainから新規作業ブランチを作り、次のPR作成指示までの変更・コミットを同じブランチに蓄積する。今回の`codex/work-branch-policy`はmain `fea8753`から新規作成し、mainをupstreamに設定していない。
- [PR #40](https://github.com/wasawo/eo-log-maintenance-public/pull/40)は`fea8753a84fe5ca7c9a64b7ec43a3b4686e546b0`でマージ済み。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40109038116) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40109038171) 成功を前作業で確認済み。今回は規則追加の文書変更のみをローカルコミットし、実装の一時中断と次の指示待ちを維持する。

## 前作業の反映記録（PR #40作成前の状態）

- 最新確認main：`51c5e221366fbc2d6e74e4c3190a134993adf904`。2026-10-25のPR作成依頼時、remote mainはすでに`985c90a`（retryable表）→`ff69e3b`（B2 V1/G1）→`51c5e22`（C-01字句）まで直接push済みだった。3コミットとmainの差分はなく、GitHubの関連PR照会でも対象PRは存在しなかった。この3件をPRでマージしたとは記録しない。
- このmainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40108634766) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40108634789) は成功済み。ローカルの各単位の検証と、この累積main CIを区別する。正式runtime/実Drive/FS耐久性の受け入れは未完。
- 利用者は実反映状態の説明を受け、「反映記録・中断状態の文書PRを作成してマージ」を明示選択した。今回の文書branchは`codex/record-main-integration-pause`で、この記録時点はPR作成前。文書PRの最新HEADで両CI成功を確認してからマージする。
- **一時中断指示**：利用量上限が近いため、今回の文書PRマージ後は作業を中断する。次候補には着手せず、新たな利用者の再開指示を待つ。通常運用は引き続き「関連範囲の実装→対象検査を一括→ローカルコミット→指示待ち」で、PR作成/マージは任意のタイミングの明示指示に従う。

## 直前の実装単位（C-01字句・51c5e22）

- 今回の基準：`ff69e3b`から同じ`codex/drive-retryable-contract`でC-01 P1/V1/L1の字句範囲を実装。現1.0 request schemaのlocal_path/staging_pathへ同一grammarを適用し、PS/Pythonに独立した副作用なしbool helperを追加した。
- 範囲：drive-rooted prefix、非空component、separator、禁止文字/control/DEL、末尾dot/ASCII space、予約stemと拡張子/末尾space/superscript/console alias。ASCII比較とUnicode原文字列保持、固定maxLengthなしを共通fixtureで検査する。root/token/FS、実file種別、使用点/差替え検知、transportと正式adapterは未実装。
- 互換性：現1.0を改訂し、従来schema-validな一部入力を拒否する。fallback/暗黙migrationは導入しない。外部consumer不在は未確認。新helper 2件は両roleのレビューpackageへ追加され、旧40件snapshotから42件となる。正式入口・PC-B archive禁止・非配布markerは維持する。
- 検証：Python 3.11.9（CI 3.12）で既存schema＋専用grammar 43件、PS 7.6.7で共通fixture等161件、副作用なし、package回帰成功。PS試験側の入力保持比較で空文字の扱いを修正し、PS範囲のみ再確認した。変更3スクリプトの構文/PSScriptAnalyzer Error検査成功。作業ツリー直下buildは既存__pycache__を拒否したため、cacheを変更せずGit対象のクリーンsnapshotを隔離作成して両role各42件・非配布状態を確認。最終文書リンク欠落0・差分検査成功。root自己点検のみで独立レビュー未実施。今回もローカルコミット後に待機し、push/PR/CI/実API/実環境適用は行わない。
- 次候補：採用済みmanifest遷移表の純粋検査と合成遷移試験。C-02具体field/provider等の未決は推測せず、正式writer接続とruntime受け入れは別に残す。

## 直前の実装単位（B2 V1/G1・ff69e3b）

- 追加運用（2026-10-25利用者指示）：実装単位を関連producer/consumer・契約・合成連携まで広げ、改修完了時に対象検査を一括実行する。小編集ごとの反復や成功済み検査の再実行を避ける。失敗・追加変更・具体的リスクがある範囲のみ再確認する。ローカルコミット後に次の指示を待ち、push/PR/マージは任意のタイミングの明示指示に従う。
- 基準：main `fd9cc8a`からの`codex/drive-retryable-contract`、直前コミット`985c90a`（retryable表）。今回も同branchで累積する。PR #39のマージとmain CI成功は前作業で確認済み、今回のCIは未実行。
- 今回の範囲：B2 V1の分類完了をエラー有無から分離し、source列挙/read/hashが不確実ならincompleteを維持。G1はexact manifest/B2終了UTCの遅い方を小数11桁まで比較し、同時はmanifestの元表記を保持。builderの任意caller時刻は照合値となり、不一致を拒否する。参照validatorも同じ導出を検査し、import/直接CLIを合成検証した。field/version/digest方式は維持し、過去incomplete recordと旧reportは書き換えない。
- 検証：Python 3.11.9（CIは3.12）で関連6moduleの107件を一括実行し、103件成功・4件はsandboxのjunction fixture作成拒否。失敗4件だけをsandbox外の専用合成一時領域・PS 7.6.7で再実行して成功。PS 7.6.7のreport validator 33件成功（PATH確認前の7.6.5実行は固定版検証に数えない）。最終文書リンク欠落0・`git diff --check`成功。root自己点検のみで、正式writer/公開・Drive・runtime/FS耐久性の受け入れは未完。
- 環境：公式archiveをCI記載SHA-256で確認してPowerShell 7.6.7をユーザー専用の恒久配置へ導入し、元User PATHを同配置のGit管理外backupへ保全して先頭に追加した。User PATH反映済みprocessで`pwsh`が7.6.7となることを確認。起動済みCodex processは旧PATHを保持し得るため、検証時は新User PATHをprocess PATHへ反映するか7.6.7の実体を明示し、起動版を確認する。sandbox内のLOCALAPPDATAはredirectされるので配置先の推測に使わない。個人の実path・PATH内容を追跡ファイルへ記載しない。
- 次候補：C-01 P1/V1/L1をrequest schema・PS/Python検査と合成連携へまとめて反映。C-02詳細field、owner-v2/provider等は未決として維持する。今回コミット後の継続指示まで着手しない。

## 直前の実装単位（retryable表・985c90a）

- 現行運用（2026-10-25利用者指示）：1作業単位は実装単位の選択→実装・検証・root自己点検→関連文書更新→ローカルコミット→次の指示待ち。PRは実装単位ごとに作らず、利用者が任意のタイミングで指示した範囲をまとめる。今回の直前指示「PR作成→マージまで1単位」と旧「1PR後に中断」はこの運用に置き換える。push/PR/マージは今回は実施しない。古い目標はサブエージェント再利用・残量までの自動継続も含めて再開しない。
- 最新確認main：`fd9cc8a931496d31601f062bf66448ea295eec65`（[PR #39](https://github.com/wasawo/eo-log-maintenance-public/pull/39)）。PRのValidate/Package Validation成功後にsquash merge済み。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40105135888) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40105134099)成功も前作業で確認済み。今回のbranchはこのmainから作成した`codex/drive-retryable-contract`。
- 今回の実装単位：固定code別retryable表を現1.0 response schemaと`Common/DriveResponseSemantics.ps1`へ反映。`DRIVE_TRANSIENT_FAILURE`のみtrue、他8codeはfalseを必須とし、矛盾は固定理由`retryable_error_code_mismatch`で拒否する。旧schema-validな矛盾boolが不適合になる互換性の厳格化を契約へ記録。外部consumer不在は未確認。
- 検証：Python 3.11.9（CIは3.12）の`test_contract_schemas.py`39件、PowerShell 7.6.7の`Test-DriveResponseSemantics.ps1`171件成功。PATH上のPS 7.6.5による初回実行後、CIと同じ公式archive/hashで7.6.7を一時領域へ用意して再確認した。4操作×9codeの正常/矛盾、型/欠落、exit対応、入力不変・秘密非echo・操作副作用なしを確認。PS 7.6.7で変更2ファイルの構文解析・PSScriptAnalyzer Error検査も成功。変更文書の相対リンク欠落0、`git diff --check`成功。今回のroot自己点検であり独立レビューではない。CI・実API・正式retry orchestration・runtime受け入れは未実施。配布file集合は変更せず、package回帰は再実行していない。この記録を含むローカルコミットで区切り、次の指示を待つ。
- 次の候補：C-01 P1/V1/L1のschema/PS/Python検査、またはB2 V1/G1のproducer/builder追従。継続指示後に1単位を選ぶ。C-02の4操作別fieldとowner-v2/provider等は未決のままで、推測して実装しない。

## 前作業までの記録（当時の状態）

以下はPR #39へまとめた過程の履歴であり、現行運用と進捗は上の最新欄を優先する。

- 今回の文書整備：`docs/selected-policy-decisions` からmain `179787f`を基準に、[未決定台帳](../requirements/p0-open-specification-decisions.md)、[P0差分台帳](../requirements/p0-gap-register.md)、[要件追跡](../requirements/requirements-traceability.md)、[決定台帳](../decisions/decision-register-c18-c32.md)と[初回配布の依存順序](../status/first-release-readiness-20261024.md)を①〜㉜・限定4件へ整合。過去の段階的承認文と部分検証の履歴は、その当時の記録として残す。新PRの最新HEADでValidate/Package Validationを確認してから、今回の明示依頼の範囲で1PRをマージして作業を中断する。正式runtime/実auth/Drive/task/配布は未実装・未適用。
- 今回のroot単独検証：mainとの差分35ファイル内のMarkdown相対リンク297件は欠落0、`git diff --check`成功。文書/作業指示/project設定だけの変更で、機能・package試験と実環境検証は再実行していない。今回差分の独立レビューは実施していない。PRとCIの結果は作成後のGitHub実状態で確認する。
- 第10回指示で[現行実装に基づく4件の限定決定](../decisions/implementation-grounded-four-decisions-20261024.md)を記録した。固定code別retryable真偽表、PC-A確認予算checkpointの最小field/拒否境界、VERSION 0.1.0の現行非配布レビューpackage 40ファイル、owner record v1の既存互換境界である。31aAの正式PC別/version別manifest形式は維持するが、最終実file一覧は正式runtime完成後。owner-v2全field/providerも未確定。PS helperと試験はretryable真偽表へ未追従、checkpoint writer/schema、正式package manifestも未実装。追加9文書のroot自己点検でfile一覧40件、retryable表9行と現codeの対応、相対リンク132件欠落0、差分検査成功。文書のみのため機能/package試験・新CI・独立レビューは未実施。PR/マージや実接続は行っていない。
- 第9回回答：㉙A、㉚aA/bA/cA、㉛aA/bA、㉜aA/bAを採用し、[決定記録](../decisions/selected-policy-decisions-20261024.md)と[比較資料](../decisions/remaining-policy-options-20261024.md)を更新。manifest正本＋補助checkpoint、Google公式Python client、multipart/5 MB以下・超過保留、固定code別retryable表、strict JSON＋Schemaのpackage manifest、専用PS移行、Windows App SDK通知、初回/状態変化時のみ再通知の方向が確定。具体field、SDK版/flow、正確なbyte境界、保護API/ACL、owner provider、CI配布identity、通知登録/重複抑制等は残る。①〜㉜の提示済み選択は回答済みで、詳細契約/実装/受け入れの完了ではない。
- 第8回回答：㉒A（PC-A同期に続けてarchive可否判定）/㉓A（両PC AC接続時のみ）/㉔A（wakeなし）/㉕A（4操作全体のresult契約を提示して確定）/㉖A（user-bound保護API＋専用暗号化file）/㉗A（owner field契約/providerを段階確定）/㉘A（E1承認後ActionsからDrive公開）を決定記録へ追記。具体API・field・配布identity等は未確定。文書のみのローカル差分で、実装/実task/認証/Drive/PR/マージは行っていない。直前記録コミットは8169eb7。
- 第9回反映後の追加5文書のroot自己点検：相対リンク30件の欠落0、git diff --check成功。コード/schema/runtime変更がないため機能/package検査は再実行せず、独立レビュー・新CIは未実施。追加分は未コミット。
- 最新mainは `179787f62ad0e07d58e139d7059ea84de149ed05`（[PR #38](https://github.com/wasawo/eo-log-maintenance-public/pull/38) マージ済み）。PRの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40084689827) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40084689833)、mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40085003755) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40085003841) 成功後の停止記録は `54f1418`。runtime実装の継続ではなく、利用者の未決事項選択・記録と指示文書改訂だけをbranch `docs/selected-policy-decisions` で進めている。未push・新規PRなし。
- [仕様決定記録](../decisions/selected-policy-decisions-20261024.md)へ①〜㉑の回答を反映。C-01 P1/検査V1/L1全体/現1.0改訂、B2 V1、report G1、C-02 R1/N1/D1、Drive I1/A1/S1/T1、owner F1/B1、条件付き状態遷移表採用、release E1、全version保持・自動cleanupなし、PC別version別file manifest、明示的設定移行、ローカル画面通知＋状態ログの方向が確定した。質問と回答の範囲を越えてfield集合・provider・実施を確定しない。
- **2026-10-24の最新利用者指示によりサブエージェント利用を中止。root単独運用。** 新規作成・既存再利用・組込み/カスタム担当・別AIタスクへの委譲を行わない。中止時の確認では稼働中担当はなく、既存担当は完了または終了状態だった。旧目標の「既存3担当のみ再利用」は撤回済みで、過去記録・環境の担当一覧から再開しない。
- AGENTS.md、[現行手順](../development/agent-workflow.md)、両skill・索引をroot単独へ更新し、project .codex/config.tomlをagents.enabled=falseとした。旧3役割TOMLと旧分担手順は [失効した履歴](../development/archive/README.md) に保全。役割TOMLは移動前後hash一致、Git改行正規化後の本文一致とparseを確認。旧手順は失効banner/相対リンク以外の本文一致を確認。個人/global設定・主モデル/思考量は変更していない。project設定の信頼/読込と現会話への即時tool反映は未検証で、以後の不使用は利用者指示と現行手順で徹底する。
- 利用中止前の初期7文書は独立reviewでP1/P2なし、invariants節分断P3を修正。追加⑦〜⑫のreviewでは旧承認待ち表記P2を指摘されrootで修正した。これらは当時の差分だけの履歴であり、⑬以降や利用中止対応を含む最新全差分はrootが単独点検し、独立レビューは実施していない。独立レビュー済みと表記しない。
- 今回のroot単独点検: 変更20 Markdownの相対リンク189件欠落0、差分検査成功。project/旧役割のTOML計4ファイルをparseし、agents.enabled=false、主思考量不変、active役割ファイルなしとarchived本文保全を確認した。文書・指示・Codex設定のみで無関係な機能/package検査は再実行していない。新CI未実行。
- 未確定/未完：C-02の具体field集合・型・値域・plan形、具体store/SDK/flow/ACL、owner-v2全fieldと適格machine/boot provider、checkpointの保存root/FS資格、移行mapping、正式runtimeの最終実file一覧とmanifest形式、task trigger/電源等の具体運用。G1/B2 V1等へのコード/schema追従、実保存・認証・実API・両PCroot/FS・runtime/Drive/耐久性の受け入れも未実施。今回の設定変更はCodex作業設定に限り、アプリケーションコード/runtime schema/tests/実設定は変更していない。
- 仕様選択と実装/公開/PRマージ/本番適用の許可を分離し、PR/マージは個別承認、1PRマージ後の中断・継続可否確認を維持する。新たな実装や実接続を独断開始しない。旧C-01資料branch `9343f71` は選択前の履歴として保全し、現選択はこのbranchの決定記録を優先する。

## 旧進捗の参照

PR #27〜33前後の旧進捗節は [セッション記録](archive/pr27-pr33-session-history-20261024.md) に保存した。過去の承認待ち・CI待ち・agent生成禁止を現在の指示として実行しない。

## 次回の実装再開時

1. まず利用者の継続指示を確認し、正本mainとローカル保全branchのコミット・作業ツリーを照合する。C-01のP1/検査V1/L1/現1.0改訂の選択は済んでいるので再質問しない。実装実施の承認と残る具体契約は別途確認する。Aは承認済みで再質問しない。IPC全体、C-02具体field、OSD-05の具体store/API/資格等の残る未確定を区別する。
2. [更新後の初回配布順序](../status/first-release-readiness-20261024.md)に従い、採用済みのC-01/manifest遷移/Dry Run A/B2 V1/G1をschema・builder・合成fixtureへ反映する。retryable表はschema/PS helperへ追従済みで、RETRY-02統合は未実装。C-02の操作別fieldとowner-v2 provider等の詳細未決を分離し、ローカルroot・永続run状態・復旧の不足を整理する。確認予算の永続化だけで初回配布へ進めない。
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
- OSD-04はA承認済みで実装・受け入れが未完。OSD-08の日時・account・AC/no-wake・確認予算は決定済みで、永続状態/task/補完/受け入れは未完。OSD-05の認証方向、OSD-06/07のrelease起動/全版保持、OSD-09の形式/移行入口、OSD-02遷移とC-01/02の方針は選択済み。具体store/実folder資格、CI identity/provenance、最終file一覧/移行mapping、C-02詳細field、永続writer/正式runtime受け入れは残る。
- 台帳の古い「sentinelあり」「過去PRのCI待ち」などは現物と照合して関係PRで直す。台帳全体の再監査完了とはしない。
