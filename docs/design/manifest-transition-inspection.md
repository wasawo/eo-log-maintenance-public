# Manifest v1 transition snapshot inspection

2026-10-25。根拠は[採用済み遷移表](manifest-state-transition-v1-proposal.md)、[C1〜C4](../decisions/osd-02-crash-concurrency-options.md)、[OSD-03](../decisions/osd-03-status-aggregation-options.md)。実装は[ManifestTransitionInspection.py](../../Common/ManifestTransitionInspection.py)。

`inspect_manifest_transition(previous_bytes, proposed_bytes, manifest_schema=...)`はexact JSON bytesと信頼済みstatic schemaを受ける純粋検査である。`previous_bytes=None`は新規作成要求に限り、保存先の不在証拠ではない。

- schema/JSON/version、run識別情報・開始UTCの元表記、凍結inventory集合・filename/size/hashと重複pathを検査する。schema外部参照、重複JSON key、不正数値を拒否する。
- 新規runはrunning・各fileはpendingのみ。変更されたfileは掲載13ペア、既存runningからは掲載4ペアのみ。変化のないfileは遷移に数えず、同じfile状態のmetadata更新は拒否する。
- verificationのstatus/method/hash対応とrun内時系列を検査し、UTC小数11桁まで保持する。verifiedは同じ観測hash、mismatchは異なるhashを必要とする。unavailable/ambiguous/verification failedはunknownへ対応し、uploaded→failedはmismatchを要求する。
- 終端fileのfieldを保持する。終端runはexact bytes一致だけを変更なしとし、書式だけの変更も拒否する。入力を変更せず、I/Oや実行を行わない。

結果は固定metadataのみ。不正入力は固定reason_codeの`ManifestTransitionError`で、raw入力/path/run IDや例外chainを露出しない。通常結果は`status=requires_runtime_evidence` / `reason_code=listed_pairs_only`で、掲載ペアの検査に限る。`file_transition_count`は変更ペア数、`aggregation_required`はrun終端かを示す内部metadataで、manifestの新fieldではない。終端runの同一bytesは`status=unchanged`だが、archiveや実行の認可ではない。

実writerは別途、C1/C2の実所有権・mutex・原子的更新と現在性、metadata-first stagingと内容照合、実upload応答、OSD-01の完全なDrive内容/不在照合とretry条件、信頼できる現在UTC・未来/鮮度・root/FS/使用点を検証する。planning pendingとupload pendingは前状態とevent履歴で区別し、snapshotから履歴を補完しない。

run終端はexact immutable B2等による既存report builderのOSD-03集約検査が必要で、本helperは集約を認証しない。C3のcrash-left runningは保全し、回復後も新runを作る。掲載ペアを根拠に中断履歴を書き換えず、retry枯渇/timeout/不完全一覧だけでfailedや再送へ進めない。writer・証拠provider・永続化・runtime受け入れは未実装。[合成試験](../../tests/test_manifest_transition_inspection.py)はsnapshot/pair検査に限る。

## 初期登録からの連続履歴検査

`inspect_manifest_history(snapshots, manifest_schema=...)`は空でないexact bytes tupleを要求し、初回を新規running/pendingとして既存検査へ渡す。各隣接ペアも既存schema/identity/凍結inventory/時刻/verification/掲載ペア/終端不変性の検査を通す。途中snapshotから過去のstaging履歴を補完しない。

fileのrelative pathごとにpending段階を追跡する。初期登録のpendingからuploaded/unknownへ飛ぶ履歴を拒否し、ready→pendingでUpload直前pending、unknown→pendingで再試行pendingを記録する。Upload pendingからpending→stagingへ戻る履歴も拒否する。登録pending→failedはsource不備等の処理前失敗を記述できるが、実failureの証拠は別途必要。順序を変えたfile配列や変化しないsnapshotでも段階を混同せず、終端runの同一bytes再掲載は遷移数を増やさない。

結果はimmutableな件数とaggregation_required、status=requires_runtime_evidenceおよび全may_publish/may_upload/may_retry/may_archive=false。Upload直前への遷移数とunknownからのretry遷移数は分離し、最後の登録pending件数とUpload pending件数も区別する。run終端でもOSD-03/B2集約検査を代替しない。空inventory/登録pendingだけの履歴をno_workへ変えない。

このAPIは履歴形式やevent field/schemaを新設せず、保存・I/Oを行わない。提示された全snapshotの真正性/完全性・省略/捏造の不在・metadata-first保存順序・copy内容・API応答・unknown retry前の不在照合/予算/待機・所有権/時計/FS/使用点は証明しない。crash-left runningの自動修復や履歴の書換えは行わない。[合成履歴検査](../../tests/test_manifest_history_inspection.py)はこの純粋な段階検査に限る。

## 終端planとB2／report生成の接続

### 初期planからの全履歴binding

`prepare_terminal_manifest_history`は独立PC/log/period/run/start/clock/schemaから初期planを再構成し、元planの厳密型/全false flag/元B2/proposed bytesのexact整合を確認する。空でないsnapshot tupleの先頭はその初期bytesとexact一致しなければならず、以降を連続履歴検査へ渡す。最後がrunningならreportを構築せずincompleteとして拒否する。

最初の終端snapshotとその直前のrunning snapshotを既存終端plan/B2/OSD-03/G1 report生成へ接続する。同じ終端bytesの再掲載があっても、本来のrunning priorをterminal bytesに置き換えない。集約が不正なら掲載ペアや履歴が成立しても拒否する。未解決file/既知validation errors・不完全coverageをsuccess/no_workへ補完しない。

専用immutable `TerminalManifestHistoryPlan`は元snapshot tuple、件数観測、exact prior/proposed/B2/report bytesを持つ既存terminal planを保持し、reprは非表示、全公開/Upload/retry/Archive/状態変更許可false。既存terminal planと別型で、保存済み結果を初期planとして再利用できない。これは供給履歴と元B2の整合検査だけであり、履歴真正性/完全性、event証拠、metadata-first、実copy/Drive、所有権/FS/clock/使用点や永続化の証明ではない。schema/event fieldやwriterを新設しない。[合成接続試験](../../tests/test_terminal_manifest_history.py)は両PC/log・exact trace・途中省略・集約不備・未完・終端繰返しを扱う。

同moduleの`prepare_terminal_manifest_transition`は、既存のexact prior/proposed manifest bytesと固定B2 bytes、参照先の安全な相対path、信頼済みstatic schema、現在UTCとreliableを要求する。先に上記遷移検査を実行し、続けて既存report builderでB2のdigest・scope・凍結inventory一致、終端fileの検証結果、OSD-03集約status/outcome、G1時刻と未来時刻条件を検査する。どちらかが不成立ならplanを返さず、入力statusや証拠を修正しない。

返すimmutable `TerminalManifestPlan`はexpected_bytes/proposed_bytes/evidence_bytes/report_bytesを結び付ける内部オブジェクトで、保存schemaのfield追加ではない。reportは**提案manifest**のexact bytesとB2 bytesをhash参照する。保存済みmanifestの証拠、commit receipt、publicationの成功ではなく、may_publish/may_archive/may_change_stateは常にfalse。reprへ内容を出さない。

missing priorを新規runへ置き換えず、running提案から終端reportも作らない。終端runの同一bytesは決定的に再生成できるが、再保存/再実行の許可にしない。参照pathは字句検査だけで、読取元rootや実保存先の資格は確認しない。B2が本当に固定・真正・最新であることは外部gateで、異なる呼出し間のB2差替えや同じbytesへのrollbackをこのplanだけで検出できるとはしない。

[接続試験](../../tests/test_terminal_manifest_plan.py)はT01〜T12相当の両log種別、PC-B、正しい集約でも不正遷移/凍結inventory変更、掲載ペアでも偽成功/未終端file、B2改変・関連errorとno_work、終端不変・欠落prior・時計/schema/path不正、exact非canonical bytes・決定性・I/Oなしを確認する。C1/C2の実比較更新、実upload/Drive内容、履歴event証拠、真正な使用点readback、marker-lastの実publication、Tier B/Cとruntime受け入れは引き続き未完。

終端planのreportを専用合成領域へ置いた後、参照validatorが元manifest/B2のexact hashだけでなく、全reportの[決定的意味論再導出](aggregation-report-v1-proposal.md#deterministic-semantic-readback-2026-10-25)も比較する接続試験を追加した。これは読取検証で、実manifest更新やC1/C2 publicationの資格試験ではない。


## 隔離候補bundleの公開・読戻し接続

[tests専用fixture](../../tests/test_terminal_bundle_integration.py)はcaller指定rootを受けず、自分で作ったOS-tempと固定合成filenameだけを使う。prior-runningを候補directoryの外に保存し、一切置換しない。実Windows mutex/ownerを保持して、既存create-only helperで候補のB2・提案manifest・reportとmarker-lastを保存する。これはimmutableな候補snapshot一式で、現在manifestのC1比較更新ではない。fixture配置/APIを正式runtime契約にしない。

読戻しではplan由来のexact bytes/hash、directoryのmarker分類に加え、そのfixtureで期待したtransaction IDを比較する。generic directory分類のcommittedは任意のvalid transactionを許すため、その分類だけで当該試行へのbindingを証明しない。参照validatorの全report意味論検査後にもdirectory/hash/markerと元priorを再観測する。返す候補検証結果は常にmay_update_manifest/may_archive=falseで、同一bytesの再公開やmarker後の応答喪失から一回限りreceiptを作らない。

合成試験は両PCのempty/成功/混在、4公開位置での例外、部分保存の保全と同一bytes再試行、既存競合、marker後の応答喪失、別transaction、report改変とmarker再binding、意味論検査後の変更を扱う。例外注入は実process crash/電源断の証拠ではない。最後の再観測もABA・任意の敵対的競合・真正なroot/owner/FSを完全に資格化せず、正式writer/Drive/runtimeの受け入れは未完のまま。cleanup対象は自作tempだけで、実データの削除/回復処理は追加しない。


候補bundleで使用する共通classifier/directory verifierは、optionalな`expected_transaction_id`を受ける。明示時は型/UUID形を検査し、markerのIDとexact文字列で比較する（正規化しない）。未指定時の従来分類は維持するが、そのcommittedは当該試行へのbindingを証明しない。期待ID自体の真正性・owner/runとのbinding・receiptの一回性は別gateのまま。

共通directory verifierも期待hash集合を開始時copyし、root/祖先chainと各fileのpath/handle前後metadataを照合する。分類後に全file/markerのexact bytesとdirectory集合を再確認し、途中変更を検出したら拒否する。終端bundle fixtureはこの期待transaction引数へ接続した。複数readを同時atomic snapshotへ昇格せず、最後の観測後の変更や敵対的ABAを防ぐ資格は未証明である。


create-only単一file公開helperは、fsync/close後にstagingのexact bytesとhandle由来identity/親chainを再読込確認し、link公開後も同じidentity/内容を検査する。既存同一fileの判定もpath/handle前後のmetadataとexact bytesへ結び付ける。cleanupは所有tempのidentity・bytes・親chainを再確認できる場合だけ行い、不明/差替え/変更tempは保全する。公開後のfinal不一致は成功扱いせず、finalのrollback/削除もしない。

これらは合成fixtureでの検出防御であり、観測後の敵対的namespace差替えやcheck/unlink raceを完全に排除するものではない。書込み/flush失敗で再確認不能なtempが残り得る。実root/ACL/FSの資格と所有権に基づく回復は別gateで、create-only helperをC1の条件付きmanifest更新providerへ昇格しない。

PR #42のCIでWindows Python 3.12のstat/fstat ctimeの意味差が比較に混入したため、Windowsでは明示birthtime_nsを使い、未対応版は従来ctimeへfallbackする。POSIXのctime比較と、identity/size/mtime/bytesの検査は維持する。根拠は[CPython path statの互換処理](https://github.com/python/cpython/blob/3.12/Modules/posixmodule.c)と[handle情報の構築](https://github.com/python/cpython/blob/3.12/Python/fileutils.c)。時刻属性は観測metadataで、真正な現在時刻やprovider資格にはしない。


## B2から初期running manifestを構築

`prepare_initial_manifest`は独立入力のPC/log/target period/run ID/開始UTCと、信頼できる現在UTC、exact B2 bytes、static schemaを要求する。B2のschema/digest/count/target集合を検査し、既承認の初期状態（run=running、file=pending）を構築して既存遷移検査/manifest-to-B2 validatorへ再投入する。開始UTCは元文字列表記を保持し、`started_at <= enumeration.started_at <= enumeration.finished_at <= current_utc + 5分`を要求する。不明・欠落・不正時刻や不整合を実時計/別保存物から補わない。

manifest v1 fieldだけを出力し、finished/outcome/Drive IDはnull、verificationはnot_checked/not_performed・時刻/hashはnullとする。B2のtargets順とfilename/path/size/hashを保持し、元evidence bytesをimmutable planへ結び付ける。空集合やfailed/incomplete/errorをrunningのまま保ち、no_work/successを生成しない。将来の終端statusは別途B2/report集約で判定する。対象periodやsourceの選択をこのfactoryで推測しない。

`InitialManifestPlan`のmay_publish/may_upload/may_archiveはfalse。新規候補を作れたことは保存先の不在、新runの真正性、実fresh inventory、現在の資格や初回公開/実行の許可ではない。UUIDを自動生成せず、旧run/欠落checkpointの再利用や回復にも接続しない。[合成試験](../../tests/test_initial_manifest_plan.py)は両PC/log種別・不完全B2・改変/時間境界等と、掲載された中間ペアを経た終端reportまでの純粋接続を確認する。実writer/Drive/FS/Tier B/C/runtime受け入れは未完である。


## Source builderから初期候補までの隔離接続

[合成source接続試験](../../tests/test_initial_source_integration.py)は、自作OS-tempのsourceを既存builderで実列挙/hashし、B2の検査/serialize、初期plan生成、別candidate directoryへの実mutex/create-only/marker-last保存とtransaction付き読戻しまで接続する。source/candidateは分離し、元source bytesを保持する。固定clock/reference dateとfixtureのrun IDは合成観測で、実clock/providerの資格ではない。fixtureのAPI/配置は正式runtime契約ではない。

初期producerでも既存filename分類を使い、B2でeligibleとされたtargetが文法外/実在しない日付なら拒否する。B2 digest/countが整合することだけでsource分類を省略しない。期間の絞込みや保持年/月の方針を変更せず、report builderと同じ承認文法を再利用する。

試験は両PC/log、Unicode階層、empty/ineligible/invalid・hash不明、source変更後の旧plan保持と別runの新hash、PC-B候補保存/競合、決定性を扱う。初期候補はrunning/pendingのままで、markerのcommittedや計上0件を成功/no_work/Upload許可に変えない。sourceが変わっても旧planは自動で無効化/書換えされないため、実行前の再検証・root/所有権・fresh run bindingは未実装gateのままである。

## 終端planの使用点再導出

`revalidate_terminal_manifest_plan`は厳密なTerminalManifestPlan型、全false flag、明示AC trueと、独立入力の直前manifest exact bytes・凍結B2 exact bytes・PC/log/period/runを要求する。保存済みplanのexpected/B2が独立観測と違う場合は拒否する。bytes型を厳格に扱い、bytearray等をsnapshotとして取り込まない。

呼出しごとに現在UTC/reliable・static schema・参照pathを使って既存の遷移/B2/report生成を再実行し、scopeとplan全体をexact比較する。report改変・書式変更・参照path差替え・時計不明・不正遷移を、過去のplan成功で省略しない。一致時は再生成したimmutable planを返すが、全may_*はfalseのまま。

このhelperはI/Oを行わず、引数の直前manifest/B2/AC自体の出所・最新性・真正性を保証しない。実保存先からの安定read・期待scope/provider・owner/root/FS資格、検査後の変更とC1比較更新は外部gateである。同一結果をreceiptや実行許可へ昇格しない。

[合成使用点試験](../../tests/test_terminal_plan_usepoint.py)は両PC/logのempty/成功/混在、snapshot/flag/AC/scope/report/context改変を検査する。既存の候補bundle fixtureにtests専用の公開前callbackを設け、実mutex/owner内で直前bytesを読み、検査一致時の候補公開・不一致時の書込み0件・prior保全とowner解放を確認する。これはimmutable候補への隔離接続であり、現在manifestの置換やruntime受け入れではない。
