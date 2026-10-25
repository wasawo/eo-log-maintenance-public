# 現在の引き継ぎ

更新日: 2026-10-25（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

- 基準`307dd67`、同じ`codex/initial-manifest-plan`で[source hashの早期照合・サイズ超過停止](../design/source-enumeration-stability.md)を追加。開いたhandleのidentityが直前path観測と違えばbyte読取前に拒否し、読取上限を観測サイズ＋1 byteへ制限する。連続追記のEOFを追い続けず、short readも拒否する。既存理由code/不完全coverage/観測済みデータの保持を維持する。
- 合成試験で別handleのread未呼出し・context解放、EOFのない模擬streamの停止、short read、空/1 MiB境界のexact hashを追加。Python 3.11.9（CI 3.12）で追加hash試験＋既存source列挙/再観測/使用点/初期接続の計56件成功（skipなし）。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。配布file集合48件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：OS read自体のblock/timeout、hash後から使用までの変化、atomic snapshot/敵対的ABA、実root/ACL/FS/clock/owner/provider資格、C1/C2 writer・Drive/runtime受け入れ。次は確定済みの独立作業かprovider未決境界の候補整理。

## 直前の実装単位（列挙完了前再確認・307dd67）

- 基準`a72d6fd`、同じ`codex/initial-manifest-plan`で[source列挙の完了前再確認](../design/source-enumeration-stability.md)を追加。directory/ancestor identityとchild名・属性の初期snapshotを保持し、hash/分類完了後に全directoryを再列挙する。追加/削除/rename/属性変化/差替え/読取不明はcoverage incompleteへ落とす。
- 観測済みtarget/hash/errorを保持し、空集合やno_workへリセットしない。snapshot時にreparse/属性不明があれば不完全とし、その先へ走査しない。scandirを明示closeし、root metadataとchainの初期対応も検査する。最後の再確認は再hashではなくnamespace/metadata観測で、ABAや同時snapshotの資格ではない。
- 合成試験は後続追加/削除/rename/既読file変更、directory追加/差替え、空scan後追加、rescan失敗、non-targetの列挙中変更、使用点再観測の不成立によるcandidate書込み0件を追加。既存junction試験の期待値を「再走査回数」から「source外を走査しない」境界へ整合した。
- Python 3.11.9（CI 3.12）で追加列挙安定性＋既存builder/reparse/再観測/使用点/初期接続の計47件成功（skipなし）。配布file集合48件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：最終観測から使用までの変化、原子的snapshot・敵対的ABA/属性復元、実root/ACL/FS/owner/clockの資格、C1/C2 writer・Drive/runtime受け入れ。次はprovider未決境界の候補整理か、確定済みの独立作業を選ぶ。

## 直前の実装単位（初期source使用点・a72d6fd）

- 基準`673052d`、同じ`codex/initial-manifest-plan`で`revalidate_initial_manifest_source`を接続。厳密なInitialManifestPlan型/全false flag・明示AC trueを検査し、独立PC/log/period/run/開始時刻・現在時計/schemaから初期planを再構成してexact一致を要求してから、sourceを新しく再観測する。
- planの書式だけの変更/別state/別B2やscope変更、AC未確認・不正flagはsource I/O前に拒否する。保存済みSourceInventoryObservationやtrue値をreceiptとして受け付けず、呼出しごとに再列挙/hashする。返す結果は全may_*falseの観測で、実root/AC/token/clock/owner資格を認証しない。
- 合成の実mutex/owner内で使用点検査を候補公開の前へ接続し、一致時の候補保存・source変更/AC切断時のcandidate書込み0件・owner解放/元plan保全を確認する。callback/配置はtests専用で、正式runtime契約やC1/C2 providerの採用ではない。
- 追加使用点・既存再観測/初期接続を一括検証する。配布file集合48件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で追加使用点＋既存再観測/初期接続の計27件成功（skipなし）。改変/AC/contextの行列は試験内subcase。変更のないsource/report/terminal/配布構成・PS/schema検査は再実行しない。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：観測直後から実使用までのnamespace/bytes/AC変化、同時atomic snapshot/ABA排除、実fresh run/24時間資格・root/ACL/owner/clock/provider、C1/C2 writerとDrive/runtime受け入れ。次はそれらのprovider境界候補の整理か、確定済みの独立実装を選ぶ。

## 直前の実装単位（凍結source再観測・673052d）

- 基準`ac29ec1`、同じ`codex/initial-manifest-plan`で[凍結source再観測](../design/source-inventory-revalidation.md)を追加。独立source/scope/reference date/現在UTCとexact B2を検査し、元coverageがcompleteの場合だけ既存builderで再列挙/hashしてtarget集合と分類観測を比較する。元/再観測の不完全・追加/削除/rename/内容/分類変更を保留する。
- 結果は元B2 bytes/target数のimmutable observationで全may_*はfalse。再生成B2や内部のhost終了時刻を保存/証拠化せず、旧B2を補完/更新しない。既知validation errorを消さず、non-target fileの内容/identityは比較範囲外と明示した。root IDは独立期待ラベルで、物理root認可や時計/ownerの真正性を認証しない。
- 両PC/log、変更行列、不完全/読取失敗、事前scope/clock/date/schema拒否、元bytes不変と比較限界を合成検証する。Common helper1件を追加し、両roleレビュー配布のfile集合は48件。CIとpackage fixtureへ登録した。
- 対象再観測/source builder/初期接続と両role package・変更PS構文/Error解析を一括確認する。Python 3.11.9（CI 3.12）で追加再観測＋既存source/初期接続の計25件成功（skipなし）。PS 7.6.7で両role package回帰と変更PS構文/PSScriptAnalyzer Error検査成功。変更のないreport/terminal等は再実行しない。root自己点検のみ、独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：再観測後の使用点同一性、atomic snapshot/ABA排除、実root/ACL/token/clock/run/ownerの資格、C1/C2 writerとDrive/runtime受け入れ。次はこの観測と初期候補の使用点検査/隔離接続、またはprovider未決境界の候補整理。

## 直前の実装単位（source→初期候補接続・ac29ec1）

- 基準`efc6733`、同じ`codex/initial-manifest-plan`でsource列挙/hash→B2→初期plan→隔離候補公開/読戻しを接続した。新規tests専用fixtureは自作tempのsource/candidateを分離し、固定合成clock/reference dateと明示run contextで既存source builderを呼ぶ。実運用path/clock資格やsource使用点の認可を実装したとはしない。
- 初期plan producerは既存の承認filename文法/実在日付helperも使い、B2内部整合が取れていてもunclassifiableなeligible targetを拒否する。対象period/保持範囲の選択は既存source builder/独立contextに留め、新しい年/月filterを推測しない。
- 両PC/log・Unicode階層の実bytes/hash、空/対象外/invalid分類、hash不明のincomplete保全、source変更後も旧plan不変/別runで再列挙、実mutex/create-only/marker-last候補保存、既存競合、同じ固定観測の決定性を合成検証する。候補artifact-setのcommittedを実run開始/manifest更新/Upload認可へ昇格しない。
- 追加接続・既存initial plan/source builderを一括検証する。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で追加source接続＋既存initial/source builderの計23件成功（skipなし）。両PC/log・分類状態などは試験内subcase。変更のないterminal/report/readback・package/PS/schema検査は再実行しない。root自己点検のみで独立レビュー・新CI・実運用受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：source列挙後から使用点までの同一性、fresh run/clock/token/root/ownerの真正性、C1/C2の初回publication/比較更新runtime統合、Drive/受け入れ。次はそれらの境界の候補整理、または確定済みの独立実装を選ぶ。

## 直前の実装単位（B2初期plan・efc6733）

- 最新mainは`1036b304aaac13d60dfae5d5e8ed51a3354edf1d`。[PR #42](https://github.com/wasawo/eo-log-maintenance-public/pull/42)はマージ済み、mainの[Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40163423575) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40163423523)も成功確認済み。再開指示を受け、最新取得mainから新branch`codex/initial-manifest-plan`を作成した。
- 既存遷移moduleへ`prepare_initial_manifest`を追加。独立したPC/log/target period/run ID/開始UTCと信頼できる現在UTC、exact B2 bytes、static schemaから、running・全pending・未検証metadataの初期候補を構築する。B2 digest/count/scope/inventoryを既存validatorで照合し、開始→列挙開始→列挙完了の順序と現在+5分上限を検査する。
- immutable planはproposed/evidence bytesを保持し、may_publish/may_upload/may_archiveはfalse。空/failed/incomplete/error B2を成功/no_workへ昇格せず、識別子/時刻/欠落入力を補完しない。B2の出所・実際のfresh inventory・保存先不在・実clock/owner/FS資格を認証しない。
- 両PC/log、欠落/改変/scope不一致、Unicode/開始表記/元bytes、時間境界、I/Oなしと、初期→掲載中間ペア→終端reportの合成接続を追加。関連initial/snapshot/terminal planだけを一括検証する。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で追加initial plan＋既存snapshot/terminal planの計28件成功（skipなし）。両PC/logとB2状態・時刻境界は試験内subcaseとして扱う。変更のないsource builder/report/保存・package/PS/schema検査は再実行しない。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：実source選択/列挙の使用点資格、fresh runと真正scopeのbinding、C1/C2の初回create-only/比較更新writer、現在Drive確認、正式runtime/受け入れ。次は初期planと既存source builder/隔離保存の接続、またはprovider未決境界の候補整理。

## 前PRの準備記録（PR #42へ統合済み）

- 2026-10-25、利用者が「ここまでの実装をまとめてPR作成してマージして」と明示承認。最新main`42221e3`（PR #41）に対し、`codex/manifest-evidence-integration`の実装7コミット`eb3f6c5`〜`a206e4e`と本記録を1PRへまとめる。この時点はpush/PR/新CI/マージ前。
- 範囲：終端遷移/B2/report plan接続、全report意味論再導出、隔離候補bundleの実公開/読戻し、参照file/schemaの安定読取観測、最新manifest/report path・bytes binding、artifact-set transactionと再観測、単一公開staging/final/所有temp cleanupの防御。配布file集合は47件で不変、PS/保存schemaの契約は変えない。
- 各単位のPython 3.11.9での対象検証結果・skip・再実行理由は下記に保持。CIはPython 3.12/PS 7.6.7で最新PR HEADのValidateとPackage Validation両成功を確認する。root自己点検のみで独立レビュー未実施。実Drive/実root・ACL・FS/Tier B/C、atomic snapshot/敵対的ABA、C1比較更新/receipt/runtime受け入れは未完のまま。
- 今回の承認はこの累積PR作成・CI成功後マージまで。マージ後は次実装へ進まず指示待ち。次変更は最新mainから新branchを切り、マージ済みbranchへ追記しない。

- [PR #42](https://github.com/wasawo/eo-log-maintenance-public/pull/42)作成済み。初回HEAD`efdda2f`はPackage Validation成功・Validate失敗。Windows Python 3.12でstat/fstatのctimeが異なる意味になる比較を含んでいたため、4moduleで明示birthtime_ns（未対応版は従来ctime）を使うよう整合した。POSIXのctime比較、identity/size/mtime/bytes検査は維持。CPython 3.12一次実装を確認し、模擬回帰を追加した。
- ローカルPython 3.11.9で修正影響の62件中60件成功・既存symlink不可2件skip。新HEADの両CI成功を確認するまでマージしない。初回失敗は[Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40162859743)の記録として保持する。

## 直前の実装単位（単一公開readback/cleanup・a206e4e）

- 基準`7d9a891`、同じ`codex/manifest-evidence-integration`でcreate-only単一file公開のstaging/readback/cleanupを強化。既存helperはfsync後の再読込をせず、temp名を無条件にunlinkしていたため、handle由来のtemp identityと親chainを保存し、公開前にexact bytes＋identityを再検査する。
- 公開後もfinal pathが当該temp由来のidentityで内容が一致することを確認する。同一既存fileの比較はpath/handle・前後metadata・親chainに結び付いたexact bytes比較へ変更。root/reparseはresolve前に拒否する。既存file上書きや比較更新能力は追加しない。
- cleanupは同じ親chain・regular temp identity・exact bytesを再確認できる場合だけ既存のtemp unlinkへ進め、差替え/内容変更/不明なtempは保全する。観測とunlinkの間の敵対的raceまで閉じたとはしない。公開後不明/不一致でもfinalをrollback/削除せず、電源断耐久性を保証しない。
- staging内容/identity差替え、cleanup直前の同一bytes別file、偽link成功、既存fileのhandle不一致を合成試験に追加。対象単一公開・artifact-set公開・所有lock接続・process crash harness・終端bundleを一括検証する。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で関連37件を実施。初回stdin起動ではmultiprocessingの8件が子processから起動元を読めず未検証となり、通常の`python -B -m unittest`＋PYTHONPATH=testsで当該7件＋残り1件だけを確認して全成功。最終的に36件成功・既存symlink作成不可の1件skip。既に成功した試験は再実行しない。PS/schema/配布構成不変のためpackage/PS検査は未実行。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミットまでで待機、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：root/ACL/FS・実owner/scopeの資格、敵対的namespace変更の完全防止、C1比較更新・一回限りreceipt、実Drive/Tier B/C/runtime受け入れ。これはcreate-only helperの防御強化で、正式manifest更新providerの採用ではない。次はprovider境界の候補整理か、確定済みの独立作業を選ぶ。

## 直前の実装単位（artifact-set transaction/読戻し・7d9a891）

- 基準`afca3ce`、同じ`codex/manifest-evidence-integration`でartifact-set classifierとdirectory verifierを強化。optionalな独立期待transaction IDを共通APIへ接続し、valid UUIDであっても期待文字列とexact不一致ならcommittedにしない。未指定時は従来のunbound分類を維持し、marker schema/fieldは変更しない。
- directory verifierはcaller期待hash集合を開始時copyし、root/祖先chain・file path/handle・読取前後metadata/byte長を照合。分類後にdirectoryを再列挙し、全artifact/markerのexact bytesを再読込、さらに再列挙して変化を拒否する。fixture固有だったtransaction照合を既存終端bundleにも接続した。
- 共通分類の型/別transaction/文字列非正規化、directoryのlate変更/追加・handle不一致・読取中変更・期待map変更を合成試験へ追加。既存reparse/read失敗試験はstream open経路へ障害注入を合わせ、reparse先を読まないことも維持する。
- 対象はclassifier/directory/reparse/終端bundleの関連試験を一括。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で関連38件中37件成功・1件skip。skipは既存symlink作成が端末で利用できないcaseで、実Windows junction/reparse・read失敗試験は成功。変更のないlatest/report/builder・package/PS/schema検査は再実行しない。root自己点検のみ、独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。期待transactionもcaller由来観測で、実owner/run binding・一回限りreceiptを認証しない。unboundなcommittedを特定試行の認可にせず、同時atomic snapshot/敵対的ABA・実root/ACL/FS/C1比較更新・実Drive・Tier B/C/runtime受け入れは未完。次はprovider未決境界の候補整理か、確定済みの独立作業を選ぶ。

## 直前の実装単位（最新manifest/report binding・afca3ce）

- 基準`db2e774`、同じ`codex/manifest-evidence-integration`で最新manifest選択とreport意味論を接続。既存directory readerへ`read_latest_manifest_with_report`を追加し、C4で選んだexact bytesと規定basename/pathを参照validatorの独立期待値へ渡す。report位置は明示入力で、自動推定/生成しない。
- 参照validatorのoptional期待bytes/pathは両方セットのみ許可し、未知型・片方欠落・別path・読取bytes不一致を拒否。従来の期待値なしAPI/CLIは互換保持。report検査後に最新候補を再列挙/選択し、別候補への変化や新しい未完runを保留する。古い成功/reportへfallbackしない。
- 両PC/log種別、別runの旧report、別pathの同一bytes、選択後bytes＋report hash改変、検証後の新success/running、偽成功、終端failure観測/非終端拒否、期待値不正・時計不明/欠落reportを合成試験に追加。全I/Oは専用tempで実ログ/Driveなし。
- 追加接続・既存directory reader/参照validatorを対象に一括検証する。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で追加10件＋既存directory/参照validatorの計44件成功（skipなし）。両PC/logや状態の組合せは試験内subcase。変更のないcore選択/builder/bundle、package/PS/schema検査は再実行しない。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。返すものは読取観測のみ。実root/ACL/tokenの認可、時計の取得/信頼性、24時間の実行鮮度、実Drive/両PC安全証拠、同時原子snapshot/ABA排除、C1/C2比較更新とreceipt、runtime/受け入れは未完。次はそれらのprovider境界の候補整理か、確定済みの独立作業を選ぶ。

## 直前の実装単位（安定読取観測・db2e774）

- 基準`a988964`、同じ`codex/manifest-evidence-integration`で参照validatorのreport/manifest/B2/schema読取を強化。resolve前にroot/祖先/reparse属性を検査し、各fileのlstat・open後/読取後fstat・読取後lstat・親chain・byte長を照合する。判定直前に全読取fileをexact bytes/metadata/chainで再読込し、途中変更を検出したら結果を返さない。
- schemaも同じ読取集合へ含め、既に読んだschemaを再利用。外部参照を取得しない既存static schema validatorを使い、不正/解決不能schemaを固定理由で拒否する。root/ACL資格やatomic snapshot、敵対的ABAの完全排除を証明せず、通常読取のTOCTOUを完全に解決したとはしない。
- 合成試験は全6fileのlate変更、handle identity/読取中変更、親chain変更、root/report/参照/schemaのreparse属性、実Win32 junction root、不正/外部/broken schemaのnetwork不呼出しを追加。全データは専用tempで、schemaは追跡中のstatic資料をtempへcopyしたもの。実ログ/Drive/秘密を使わない。
- 関連参照validator・追加読取試験・終端bundle接続を一括検証する。配布file集合（47件）/PS/schema契約に変更なし。Python 3.11.9（CI 3.12）で追加7件＋既存参照/bundleの計30件成功（skipなし、専用tempの実junctionを含む）。各file/reparse/schemaの行列は試験内subcaseとして扱う。変更のないbuilder/plan・package/PS検査は再実行しない。root自己点検のみ、独立レビュー・新CI・実運用受け入れは未実施。root単独、ローカルコミットまでで待機、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：実効ACL/実token/root認可、file read集合の同時原子性・ABA/競合の完全防止、C1/C2 writer/receipt、現在時計/実Drive/Tier B/C/runtime受け入れ。次は比較更新providerの信頼境界・保存/回復条件を候補化するか、確定仕様の別作業を選ぶ。

## 直前の実装単位（終端候補bundle・a988964）

- 基準`187bae2`、同じ`codex/manifest-evidence-integration`でtests専用の終端候補bundle接続を実装。呼出元rootを受けず自作OS-tempに固定し、別置きprior-runningを保持したまま、実mutex/owner＋既存create-only helperでB2/提案manifest/reportを公開し、markerを最後に公開する。fixtureの名前/配置/APIはruntime契約ではない。
- exact plan由来hash/bytes、markerのtransaction、既存directory分類、参照validatorによる全report意味論、最後の再観測を接続した。候補bundleだけが検証済みでもmay_update_manifest/may_archiveはfalse。正式manifestを更新せず、C1比較更新providerや真正な一回限りreceiptを実装したとはしない。
- 両PC/empty/成功/混在、4公開境界での例外・部分file保全・同一bytes再試行、既存競合、marker後応答喪失、別transaction、report改変＋marker再binding、意味論検査直後の変更を合成試験へ追加。process killや電源断ではなくfixtureの例外/変更注入。cleanupは自作・解決済み・所有marker付きtemp rootを再確認してから行う。
- Common/PS/schema/配布file集合（47件）は変更しない。CIに追加接続試験を登録。追加fixtureだけを一括検証し、変更のない既存成功検査は繰り返さない。Python 3.11.9（CI 3.12）で追加8件成功（skipなし）。両PC×3種の結果と4公開境界は各試験内のsubcaseで、独立した件数として加算しない。既存の成功済みreport/plan/publication試験、package/PS検査は変更なしのため再実行しない。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミットまでで待機し、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：実manifest比較更新、root/ACL/FSと真正な実owner/scope、ABA/読取間競合の完全排除、B2の出所/固定性、使用点clock/鮮度・実Drive/両PC証拠、C3回復、Tier B/C/runtime受け入れ。次はproviderの未決信頼境界・失敗時保存/回復条件を候補化するか、確定済みの独立作業を選ぶ。

## 直前の実装単位（report意味論再導出・187bae2）

- 基準`eb3f6c5`、同じ`codex/manifest-evidence-integration`で終端planのreportと参照validatorを接続した。従来はhash/identity/B2/G1/inventory照合までで、reportの集約status・期間件数・run-scope error等の再導出比較が欠けていたため、既存の決定的builderを共有して全文意味論を検査する。
- `derive_aggregation_report`は明示的に現在時計を観測しない履歴再導出API。内部schema/B2/終端/時系列/G1条件は維持し、通常`build_aggregation_report`と終端planの現在時計/未来許容検査は省略しない。report自身の時刻をtrusted nowに代用せず、旧reportの意味論検査から現在の資格を作らない。
- 参照validatorは読取済みexact bytesから再導出し、JSON whitespace/key順だけを許して全field/array順/整数表現を比較する。偽status/件数/completion/error/順序やfloat整数表現を拒否。direct CLIも同じCommon moduleを実行位置に依存せずロードする。既存empty成功fixtureのmanifest outcomeを承認済みno_workへ修正した。
- 追加/既存のreport builder・参照validator・終端planだけを対象検証する。配布file集合は47件で不変、PS/schemaコード変更なし。Python 3.11.9（CI 3.12）で関連48件を一括実行し47件成功。既存no_work fixture修正に伴う非空inventoryの1件はschemaで先に拒否されたため、当該試験のoutcomeをNoneへ整合し、その1件だけ再実行して成功。成功済み47件は再実行せず、関連48件を確認済み。配布構成/PS/schema不変のためpackage/PS/schema単独検査は再実行しない。root自己点検のみ、独立レビュー・新CI・実運用受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：trusted root/ACL/使用点read、意味論検査中の変更対策、C1/C2比較更新・marker-last実統合・receipt、現在時計/鮮度・実Drive/両PC証拠・runtime受け入れ。再導出成功は保存・archive認可ではない。次は隔離artifact setとの接続またはproviderの未決信頼境界/障害回復条件の候補整理。

## 直前の実装単位（終端plan・eb3f6c5）

- 最新mainは`42221e36886773b7efbb4e3d58658890690f55b6`。[PR #41](https://github.com/wasawo/eo-log-maintenance-public/pull/41)はマージ済み、mainの[Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40159576258) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40159576256)も成功確認済み。利用者の再開指示を受け、新branch`codex/manifest-evidence-integration`を最新取得mainから作成した。
- 既存moduleに`prepare_terminal_manifest_transition`を追加。exact prior/proposed manifestの掲載遷移・凍結inventory・終端不変を検査した後、B2 digest/scope/target一致とOSD-03集約/G1 report生成を既存builderへ接続する。immutable planは元/提案/B2/report bytesを保持し、全may_*はfalse。欠落prior・不正遷移・未終端file・偽成功を修正せず拒否する。
- reportは提案bytesの派生物で、保存済み/commitの証拠ではない。B2の真正性・固定性・最新性、実event履歴、root/ACL/所有権・C1/C2比較更新・一回限りreadback・実Drive内容は未実装gateのまま。PC-Bも検査できるがarchive権限は与えない。
- 既存配布module内の拡張でfile集合は47件のまま。追加接続試験と既存snapshot/report builderを一括で対象検証する。Python 3.11.9（CI 3.12）で追加接続9件＋既存snapshot/report builderの計42件成功（skipなし）。両log種別のT01〜T12相当は追加試験内の24 subcaseとして確認し、独立した24試験とは数えない。配布file集合/PSコードが不変のためpackage/PS検査は再実行しない。root自己点検のみ、独立レビュー・新CI・実保存/受け入れは未実施。root単独、ローカルコミット後は指示待ち。今回はpush/PR/マージを行わない。
- 文書相対リンク欠落0・差分検査成功。次はこのplanと既存のartifact参照validator/模擬保存の接続、またはproviderの未決信頼境界・障害回復条件の候補整理。planから正式publicationやruntimeの受け入れを推定しない。

## 前PRの準備記録（PR #41へ統合済み）

- 2026-10-25、利用者が「ここまでの実装をまとめてPR作成してマージして」と明示承認。最新取得mainは`fea8753`（PR #40）、`codex/work-branch-policy`の実装8コミット`b4d4600`〜`f8cdea8`を1PRへまとめる。この記録コミットも同じPRに含める。
- 範囲はmain直接push禁止/branch運用、manifest遷移snapshot検査、checkpoint schema/reader/試行plan/使用点検査/模擬保存、実Win32負例probe、AC観測、PS再試行観測と関連試験・文書。正式writer/adapter/task、実counter/待機/再送、C-02詳細、実Drive/Tier B/C/電源断の資格は未完のまま。
- 各実装単位の対象検査・環境差は下記記録を保持し、無変更の成功検査は再実行しない。rootが累積差分と配布範囲を自己点検し、文書相対リンク/差分を最終確認する。独立レビューは未実施。この記録時点はpush/PR/新CI/マージ前で、最新PR HEADのValidateとPackage Validation両成功を確認してからマージする。
- 今回の承認はこの累積PR作成・マージまで。マージ後は次実装に着手せず指示待ち。次変更は最新mainから新しい作業ブランチを切り、マージ済みbranchへ追記しない。

## 直前の実装単位（PS再試行観測・f8cdea8）

- 基準`df03f55`、同じ`codex/work-branch-policy`で既存PS応答helperへ`Get-DriveRetryObservation`を追加。[再試行観測](../design/drive-retry-observation.md)は相関/exit/envelope/retryable検査と、完了試行1〜4・1/5/15分の固定候補をまとめる。
- 整合した成功は再試行せずresult検証を要求。upload一時失敗/全操作timeoutは照合待ち、その他非一時失敗は非再試行、応答欠落/不正・番号欠落/型/範囲不正は拒否する。download候補は新規/空staging等の資格を要求し、4回後に次番号を出さない。全MayRetry=false、実counter・経過時間・request/scope由来の真正性・現在Drive照合を証明しない。
- 新fileは設計文書だけで配布file集合は47件のまま。既存PS試験に4操作/9error/4試行/成功/矛盾/不正番号等の行列を追加。PS 7.6.7で既存応答検査＋追加再試行行列の計490件成功、変更2fileの構文/PSScriptAnalyzer Error検査成功。実行ラッパーの未設定LASTEXITCODE誤判定で解析前に停止したため、成功した試験は繰り返さず未実行の解析だけを別実行した。配布file集合/構成が不変のためpackage回帰は再実行せず、Pythonも変更なしで未実行。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。root単独、ローカルコミットまでで待機し、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：C-02/transport/schema gate、実counter/待機/再送、download staging資格、upload照合、暗黙retry禁止のSDK資格、runtime受け入れ。比較更新providerの信頼境界・失敗時保存/回復条件も未選択。次はそれらの未決を候補化するか、確定済みの独立作業を選ぶ。

## 直前の実装単位（AC電源観測・df03f55）

- 基準`b65abde`、同じ`codex/work-branch-policy`で承認㉓Aを支える読取専用`PowerStatusObservation.py`を追加。比較更新providerの信頼境界/資格が未決のため無条件置換を正式採用せず、独立して進められるAC観測を選んだ。
- GetSystemPowerStatusを呼ぶたびに取得し、成功時のACLineStatus=1/0のみTrue/False。不明・未定義値・API失敗・未対応OSはNone、固定reasonのみでraw例外/電池metadataを返さない。全may_*はfalse。使用点へ合成観測を接続し、保存後AC切断/不明で確認を止めても計上を戻さないことを検査する。
- APIの単発観測であり、時計/session/account資格・AC切断監視・in-flightの停止/通信結果不明・checkpoint実保存は未実装。AC再接続だけで同じ試行の再確認を許可しない。実PCの切断試験やTier B/Cの受け入れではない。
- 両roleの非配布レビューへhelper1件追加（現行file集合47件）。CIとpackage fixtureを更新。Python 3.11.9（CI 3.12）で追加AC観測9件＋既存使用点10件の計19件成功（skipなし、実API読取1件を含む）。PS 7.6.7で両roleのpackage回帰・変更PS試験の構文/PSScriptAnalyzer Error検査成功。変更のない既存budget/reader/plan/probe試験は再実行しない。root自己点検のみで独立レビュー・新CI・実運用受け入れは未実施。root単独、ローカルコミットまでで次指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。次は比較更新providerの信頼境界と失敗時保存/回復条件の候補を整理する。未選択の前提を採用せず、正式runtime/taskや実保存の資格をhelper成功から作らない。

## 直前の実装単位（Win32負例probe・b65abde）

- 基準`5213525`、同じ`codex/work-branch-policy`で[比較更新providerの資格調査](../design/checkpoint-compare-provider-qualification.md)と実Win32負例probeを追加した。ReplaceFileW/CreateFileW/byte-range lock/flushの一次資料を2026-10-25に確認し、expected bytes比較・sharing・失敗時状態・耐久性をAPI名だけで資格にしない境界を整理した。
- tests専用probeはcaller指定先を受けず、自作OS-temp/固定fixture名のroot marker・regular/reparse/hardlinkを検査し、cleanup直前にもrootを確認する。実APIの共有guard下の拒否/解放後置換と、使用点検査＋実mutex後に非協調更新を古いcandidateが上書きできる反例を検証する。実運用pathやDrive/実設定を使わない。
- これは負例fixtureで、Commonにwriterを追加せず、実providerを採用/資格化しない。全writer協調の信頼境界、root/ACL/handle/scope binding、失敗状態/backup/metadata、真正で一回限りのcommit/readback、FS/電源断の資格は未完。一次資料のAPI条件と、この環境での隔離観測を区別する。
- 新規配布file/schema/PSコードはなく、46件の非配布file集合を維持する。CIにprobe試験を登録した。Python 3.11.9（CI 3.12）で実Win32の5件成功。自己点検で競合中間bytesの照合を強化し、影響する1件を再確認して成功。変更のない既存51件・package/PS検査は再実行しない。root自己点検のみで独立レビュー・新CI・Tier B/Cは未実施。root単独、ローカルコミット後は次指示待ちで、push/PRは行わない。
- 文書の相対リンク欠落0・差分検査成功。次はprobeで不足が明らかな保証に対するprovider設計を具体化する。writer信頼モデルや失敗時の保存/回復条件の採用を要する場合は候補を提示し、無条件置換を正式writerにしない。

## 直前の実装単位（使用点検査・5213525）

- 基準`a0e3393`、同じ`codex/work-branch-policy`で使用点検査を追加。実比較更新providerのroot/ACL/FS・owner/scope保証は未確定・未資格のため、無条件置換writerを実装せず、保存直前/記録後確認直前のpure検査を既存moduleと合成fixtureへ接続した。
- phase別のexact observed bytesを要求し、元の1試行candidateを再構成してplan偽装を拒否。最新scope・現在UTC/24時間期限・実行条件・明示boolのAC接続を再検査する。保存後に資格が失われても試行を戻さず確認を止める。全may_*はfalseで、同一検査の反復は一回限りreceiptではない。
- 使用点検査後の変更も模擬providerの比較で拒否する試験を追加し、再読込＋無条件置換だけでは代替できない境界を文書化した。比較更新/receipt/readbackの実資格、現在観測の真正性、計画から実確認までの時間の結び付け、AC切断時のin-flight処理は未実装・未確定として残す。
- Python 3.11.9（CI 3.12）で関連4module計51件を一括実行して成功。文書リンク欠落0・差分検査成功。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。新規配布file・PSコード・schema変更はなく、非配布レビューのfile集合は46件のまま。今回のpackage/PS検査は具体的な追加変更がないため再実行せず、前単位の結果と区別する。今回もローカルコミットまでで次指示待ち、push/PRは実施しない。
- 次は実FS比較更新providerの候補API/保証調査と隔離資格試験計画を具体化する。仕様追加を要する事項は提示し、helperやcaller boolから実保存/確認の資格を作らない。

## 直前の実装単位（試行planとmock保存接続・a0e3393）

- 基準`42e7c9f`、同じ`codex/work-branch-policy`でcheckpointの試行前計上を接続する。既存公開helperはcreate-onlyのみで、比較更新providerはないため、今回は純粋attempt planと隔離合成接続を実装した。
- planはexact元bytesをexpectedとし、既存reader/予算helperで観測を再検査して1試行を追加し、candidateの再読込・state一致を確認する。元の開始/履歴文字列を保持し、欠落初期化・予算リセット・実保存/確認は行わない。全may_* flagはfalse。
- 接続fixtureは実Windows mutex/ownerとcreate-only stagingを使うが、checkpoint compare-and-publish自体はメモリmock。完全な再読込確認前に模擬確認せず、stale plan/同一stagingの再利用から二重確認しない。保存後の応答喪失・確認失敗も試行を戻さない。実process crash/再起動・電源断・実FS比較更新の証明ではない。
- 純粋helper 1件を共通packageへ追加し、両roleの非配布レビューは46件。CIへ合成接続試験を登録し、関連検査を一括実行する。検証はPython 3.11.9（CI 3.12）で既存budget/reader＋追加plan/実mutex接続の計41件成功。PS 7.6.7でpackage回帰と変更PS試験の構文/PSScriptAnalyzer Error検査成功。クリーンsource snapshotで両role各46件・非配布を確認。文書リンク欠落0・差分確認成功。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。
- 未完：実compare-and-publish/再読込provider、trusted root/ACL/FS・scope/実ownerのbinding、現在性/rollback防止、durable試行前計上とruntime/task/Drive確認。次は比較更新providerの資格・設計境界を具体化する。実root/filenameやC-02結果field等の未決を実装都合で確定しない。
- 今回も同branchへローカルコミット後に次指示待ち。main直接push禁止・PRは明示指示時の運用を維持する。

## 直前の実装単位（checkpoint schema/reader・42e7c9f）

- 今回の基準は`2195ba4`、branchは同じ`codex/work-branch-policy`。追加のPC-A確認予算checkpointは承認済み7fieldのclosed v1 schemaと純粋readerまで実装し、PR作成指示までこのbranchに蓄積する。main直接push禁止、ローカルコミット後の次指示待ちを維持する。
- readerはexact bytes・元時刻文字列・履歴順を保持し、期待log/period/run IDと信頼できる現在UTCを別入力で検証する。欠落/破損から空履歴を作らず、24時間/25回/1時間間隔・時計逆行を拒否する。期限切れ履歴は元予算のまま保持する。任意桁の小数を丸めず比較し、既存microsecond helperで完全に表せない場合は変換を拒否する。
- 新schemaをpackage必須fileへ、readerを共通helperへ追加。旧43件から両roleの非配布レビューは45件となる。CIへreader試験を登録し、関連検査を改修後に一括実行する。検証はPython 3.11.9（CI 3.12）で既存budget＋追加reader計28件成功。PS 7.6.7でpackage回帰と変更2scriptの構文/PSScriptAnalyzer Error検査成功。クリーンsource snapshotで両role各45件・非配布を確認。文書リンク欠落0・差分確認成功。root自己点検のみで独立レビュー・新CI・実環境検証は未実施。
- 保存root/filename/ACL/信頼できるread provider、開始時刻と履歴の真正性・現在性/rollback防止、C1/C2の原子更新と実確認前の永続計上、runtime/task/Drive接続は未実装。reader成功を実行/保存/archiveの許可にしない。次候補は試行前更新の隔離合成接続で、実rootやC-02具体field等の未決は推測しない。

## 直前の実装単位（manifest transition inspection・2195ba4）

- 利用者の「作業再開」により一時中断を解除した。基準`b4d4600`から同じ`codex/work-branch-policy`に実装を蓄積し、今回もローカルコミットまでで次の指示を待つ。main直接push禁止・PR作成の明示指示待ちを維持する。
- 今回は[manifest遷移snapshot検査](../design/manifest-transition-inspection.md)を追加。schema/JSON・identity/凍結inventory・verification/hash/time・終端不変性を検査し、採用13fileペアと4runペア以外を拒否する。掲載結果もrequires_runtime_evidenceで、実event・staging・Drive照合・OSD-03集約・mutex/永続化を認可しない。crash-left runningの実回復は行わない。
- CIに合成試験を登録し、レビューpackageへ純粋Python helper 1件を追加した。旧40件snapshotにC-01の2件と今回1件が加わり、非配布レビューは43件となる。PC-B archive/削除は追加しない。検証はPython 3.11.9（CI 3.12）でschema＋snapshot検査50件成功。PS 7.6.7でpackage回帰と変更PS試験の構文/PSScriptAnalyzer Error検査成功。Git対象のクリーンsnapshotで両role各43件・非配布を確認した。文書リンク欠落0・差分検査成功。root自己点検のみで独立レビュー・新CI・実環境検証は未実施。
- 残る範囲：実writerとevent履歴・所有権/現在性・原子的更新、B2等からの集約検証の実行接続、現在UTC/FS/root/使用点資格。C-02具体result/provider等の未決も維持する。次候補は確定済み確認予算checkpointのschema/純粋reader契約で、今回のコミット後には着手しない。

## 直前の規則追加（b4d4600）

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
