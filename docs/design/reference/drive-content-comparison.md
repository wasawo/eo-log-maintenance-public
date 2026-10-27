# Drive同一内容の比較候補（OSD-01）

既存stagingからの読取接続は[stagingとDrive観測の接続](source-inventory-revalidation.md#既存stagingとdrive観測の接続)を参照。凍結planと実stagingを毎回再照合した元basename/size/hashだけを比較元にし、suffixやUpload先への自動aliasは行わない。比較成立も実Upload結果/再試行/同期成功/Archiveの許可ではない。

2026-10-25。[OSD-01承認](../../requirements/p0-open-specification-decisions.md#承認された決定記録--osd-01)と[衝突/比較規則](../../development/implementation-workflow.md)を支える純粋helper：[DriveContentComparison.py](../../../Common/DriveContentComparison.py)。API接続・IPC結果schema・出所認証・復元・同期成功・archiveの実装ではない。

内部のimmutable観測は、sourceのfilename/size/SHA、Drive fileのID/name/size/任意SHAとその信頼確認、完了したdownloadのID/実byte数/SHAから成る。IPCのC-02結果field集合は定めない。callerは比較元が確認済みの信頼できるPC-A source/backup記録であること、期待folderと観測folderの一致、全page列挙完了を独立に確認して渡す。bool等の入力は証明でなくcaller観測で、helperは真正性・鮮度・paginationを認証しない。

`compare_drive_content`はsource trust/完全列挙に明示Trueを要求し、tupleの観測集合を検査する。file ID重複、未知IDや重複IDのdownload、不正な型/size/hashを保留する。名前はexact/case-sensitive、sizeは非負int（bool/float不可）、SHAはlowercase hex64で、補完・正規化しない。

同名・同sizeの候補は信頼確認済みcloud SHAを用い、欠落/未確認ならIDへ結び付いた完了downloadの実size/hashを要求する。download size不一致や信頼済みcloud SHAとの矛盾は保留する。metadata-only、失敗/未取得downloadを一致にしない。同名候補のsize/hash不明が残れば既知の一致が1件でも保留する。名前違い・既知size違いは一致候補に含めない。

名前/size/SHAが全て一致するfileがちょうど1件なら`comparison_candidate`とIDを返す。0件/複数件は`held`でIDを返さない。全結果のmay_restore/may_report_sync_success/may_archiveはfalseであり、比較一致は未標識fileの出所、復元/上書き/rename/再送/削除の許可にならない。結果・観測のreprへ内容を出さず、固定reason codeだけを診断に使う。実IDをログ/追跡文書へ出さない。

[合成試験](../../../tests/test_drive_content_comparison.py)は0/1/複数、不完全・別folder・未信頼source、同名の不明候補、SHA fallback、download ID/size/hash不整合、入力型、非認可・I/Oなしを扱う。実Drive SDK/全page取得、source/folder/metadataの真正性と現在性、download実bytes検証、同期/履歴/両PC/archive gateは未実装のまま。

## Download実bytesのstream観測

`hash_downloaded_content`はfile ID、独立した期待size、明示download完了状態と、非空のexact bytes chunkのiterableを受ける。空fileは0 chunkで表す。context/完了未確認は消費前に拒否し、全chunkのSHA-256と実byte数を蓄積する。元bytesは保持せず、file/network APIを直接呼ばない。chunk提供側が消費時に行うI/Oはcaller/providerの責任である。期待sizeを超えたら残りを消費せず停止し、short read・途中例外・不正chunkでも観測を返さない。iteratorが独自例外を返しても固定reasonに置き換え、内容やraw例外を出さない。

全iteratorを正常に消費し、実sizeが期待と一致した場合だけ既存DownloadHashObservationを返す。既存比較へそのまま渡し、異なる内容のhashを一致へ変えない。chunk境界や空fileでもexact bytesのdigestを使う。返却後もID/stream/完了状態の真正なbinding、実SDKの成功判定・最新metadataとの照合はcaller/providerの未実装gateである。

streamの所有権はcallerに残る。helperは再読取・retry・close・temp保存をせず、途中停止時のstream/resource解放をcallerが行う。OS/network readのblock/timeout、任意に巨大なchunkの生成、敵対的bytes変更後の復元を解決するものではない。IPCのresult形やdownload SDK方式は採用しない。[合成stream試験](../../../tests/test_download_hash_observation.py)はchunk分割/1 MiB境界/空file、超過時停止、short read、完了後例外、型不正と比較fallbackの接続を扱う。

## 全pageの内部観測集約

`collect_drive_listing`は期待folderとDriveListingPageのiterableを受け、全pageを検査した場合だけimmutable DriveListingObservationを返す。最初のrequested_tokenはnull、後続は直前のnext_tokenとexact一致し、各pageのfolder一致とrequest_succeededの明示Trueを要求する。next_tokenは非空のopaque文字列かnullで、正規化せず、既出tokenへの循環を拒否する。内部page fieldはIPC C-02のwire結果集合を定めない。

next_token=nullの終端pageがちょうど1件あり、その後にpageも例外もない場合だけenumeration_completed=trueになる。0 page・終端欠落・途中失敗を空の完全列挙へ変換しない。空の中間pageは後続tokenがあるなら許し、空の終端page1件は完全な0件観測として区別する。全pageのfileは既存比較と同じ型/size/hash規則で検査し、page内/間のID重複を不明扱いで拒否する。観測順を保ち、自動dedup・不足page補完・再試行を行わない。

返す観測のfile集合/folder/完全列挙値とdownload hash観測を既存比較へ渡せるが、may_restore/may_report_sync_success/may_archiveはfalse。callerは実API応答・対象folder/query/アクセス範囲・token/成功状態を信頼できるproviderでbindingする必要がある。内部pageの整合だけで実クラウド全件・鮮度・出所を証明しない。単純なdataclass生成や保存済み観測も資格証拠ではない。

collectorはfile/network APIを直接呼ばず、page提供側のI/O・timeout・件数/時間予算・resource解放はcaller/providerに残る。途中例外は固定reasonへ置換し、token/IDやraw例外を診断へ出さない。部分観測は返さず、callerの元pageを変更/closeしない。[合成page試験](../../../tests/test_drive_listing_observation.py)は空/複数/空中間page、token切断/循環、folder/成功不明、ID重複、終端後page/例外、実bytes hash fallbackと複数内容一致の保留までを接続する。

## 呼び出し元が選択したダウンロード バイト境界 (2026-10-26)

`hash_downloaded_content`はoptional `maximum_download_bytes` / `maximum_chunk_bytes`を受け取り、Noneまたは正のexact intのみ許す。不正値はiterator取得/hash生成前に`download_limit_invalid`、期待sizeがdownload上限を超える場合は同じく消費前に`download_limit_exceeded`で拒否する。Noneでは当該caller上限なし、固定本番値やschema/SDK方式は選ばない。空fileは従来どおり0 chunkで表す。

chunkの型/非空検査後、その長さが明示chunk上限を超える場合はhash更新前に`download_chunk_limit_exceeded`で停止する。超過chunkを切り詰めたり分割して受け入れたりせず、部分観測も返さない。期待sizeとのexact一致、終端までの正常消費・完了確認は別に必須であり、short/overlong/終端後例外を上限内だからと成功にしない。caller所有streamのclose/retryは行わない。

これはhelperがhashへ受け入れるbytesの制限であり、callerが既に生成したchunkのmemory、iterator/nextのblock時間、download ID/streamの真正なbindingや実SDK資格を保証しない。既存比較の非認可flagsを維持する。[download試験](../../../tests/test_download_hash_observation.py)で空/分割payloadのexact境界、不正上限/期待size超過の非iter・非hash、chunk超過の非hash更新/非trailer消費/非close、従来size/終端検査と比較接続を確認する。

## page集約のcaller指定件数上限（2026-10-26）

`collect_drive_listing`はoptional `maximum_pages` / `maximum_files`を受け取り、Noneまたは正のexact intのみ許す。不正値はiterator取得前に固定`listing_limit_invalid`で拒否し、固定本番値・C-02 field/schema・API方針は採用しない。Noneでは当該caller上限なし。

page数は空pageも数える。上限件数目のpageがnonterminalなら、完全列挙をその予算内で成立させられないため`listing_page_limit_exceeded`で次page取得前に停止する。上限件数目がterminalでも従来どおりiteratorの終端を確認し、trailer pageは`listing_after_terminal`、trailing例外は`listing_read_failed`で拒否する。件数上限を完了証拠や打切り成功にしない。

file上限は全pageのfile件数合計で、page header/token検査後、そのpageのfileを検査・保持する前に合計超過を`listing_file_limit_exceeded`で拒否する。部分観測を返さず、超過fileのskip/dedup/fallbackは行わない。caller所有iteratorをclose/retryせず、transport・後始末はcallerが担う。既存folder/token/ID重複/終端検査と観測順序は維持する。

これらは保持するpage連鎖/file件数に対する資源制限で、callerが生成済みのpage/tupleのmemory、file名/token長、iterator取得/nextの遅延や全memoryを制限しない。実SDK・page真正性/現在性・同時snapshot・runtime資格の証明ではなく、比較結果の全may_*falseを維持する。[page試験](../../../tests/test_drive_listing_observation.py)で境界値、不正値の非iter、空中間page、次page非取得/非close、file事前検査、終端後失敗、download hashからの比較接続を確認する。

## PC-Aの凍結B2とsource再観測への接続

[SourceInventoryRevalidation.py](../../../Common/SourceInventoryRevalidation.py)の`revalidate_comparison_source`は比較元の明示信頼確認、PC-Aのexact B2 bytesと独立log/run/root/scope/reference date/現在時計、対象relative pathを要求する。B2のschema/digest/inventory不変条件を検査し、canonical相対pathで一意のeligible targetを選ぶ。PC-BのB2や対象不在・不正文法はsourceを読む前に拒否する。同名でも別pathのtargetを推測して選ばない。

既存のsource全列挙/再hash比較を毎回実行し、一致した場合だけtargetのfilename/size/hash、元B2 bytesとrelative pathをimmutableなRevalidatedComparisonSourceへ結び付ける。選択target以外を含むinventory変更や不完全coverageも拒否し、B2を更新/補完しない。既知のvalidation errorsは既存helperと同じく保持し、run全体の成功に変えない。

返すsourceをpage集約/download hashと比較へ渡せるが、全may_*false。PC-Aラベルやhash一致だけで記録の出所・真正性を信頼済みにはしない。source_trustedは独立した必須観測であり、返却objectをcompareのtrust判定へ自動昇格しない。source/rootの実資格・観測後の変化/ABA・cloud観測との同時snapshotは未実証のまま。

[合成接続試験](../../../tests/test_comparison_source_revalidation.py)は両log/Unicode/同名別path、PC-B/未信頼/不正B2/context/不完全の事前拒否、source全体の変更と毎回再観測、元bytes保全、source→page→download実bytes hash→比較までを専用tempで確認する。実ログ/Drive・復元/同期成功/archive・候補artifact保存は行わない。

## Download前後の完全列挙観測の照合

`compare_reobserved_drive_content`は比較元、前後2つのDriveListingObservation、独立source信頼確認/期待folder、download hashを受ける。両観測の厳密型・tuple file集合・明示完全列挙・全may_*false・期待folder一致と全file型/ID一意性を再検査し、IDをkeyとした全metadata集合を比較する。page/file順だけの違いは許す。名前/size/SHA/信頼確認状態、追加/削除/置換や対象外fileの変化は保留する。

観測集合が同じ場合だけ既存のexact name/size/hash・download fallback比較を再実行し、不明・0/複数一致は引き続き保留する。SHA未確認から確認済み等へのmetadataの充実も同一観測と見なさず、旧結果を自動補完しない。観測・download・B2を修正しない。

このhelperはAPI再取得を実行せず、引数が実際にdownload前後のfreshな全pageを表すことやquery/権限/出所を認証しない。同じ保存済みobjectを両側へ渡しても現在性や一回限りreceiptの証明にならず、全結果may_*falseである。掲載されたmetadataで観測できない同サイズ内容変更、観測間のABA・paginationの同時snapshot・比較後の変化は未解決のまま。

[前後観測試験](../../../tests/test_drive_comparison_reobservation.py)は変化なし/順序差、追加/削除/rename/ID置換/metadata変化、対象外fileの変化、不完全/不正/別folder/重複ID、不明hash・0/複数候補と保存済み観測の非認可を扱う。[PC-A source合成試験](../../../tests/test_comparison_source_revalidation.py)もsource再観測→列挙→download bytes/hash→再列挙→比較までを接続する。実Drive/runtime受け入れではない。

## 複数比較元の一括再観測

`revalidate_comparison_sources`は明示したrelative_pathsのtupleを受け、全pathの型/canonical字句/重複なし/B2 target存在/filename文法をI/O前に検査する。その後、既存の全source再列挙/hashを1回だけ実行し、全観測が一致した場合だけRevalidatedComparisonSourceのtupleを指定順で返す。元B2 bytesは各結果から同じimmutable bytesを参照し、内容をコピー/更新しない。

1 targetごとに全sourceを再hashする呼出しをまとめられるが、batchを次回の検査済みcacheにはしない。単一file用`revalidate_comparison_source`も1要素batchへ委譲し、従来の入力/結果とfreshな全再観測を維持する。選択外fileも含めたinventory変化・不完全coverageで全体を拒否し、途中までの比較元を返さない。

空tupleは明示的な0件選択であり、全source再観測を省略せず、不完全な元B2や変更sourceを通さない。返却の空tupleをno_work/同期成功へ昇格しない。選択・順序・scope/PC-A/source信頼確認はcallerの独立入力で、未指定のfileや期間を自動補完しない。

[合成batch試験](../../../tests/test_comparison_source_batch.py)はUnicode複数target、指定順と1回の再hash呼出し、全path事前検査、選択外を含む変更/空選択/空inventory/不完全/信頼とPC-A境界、複数sourceから共通のpage/download/前後比較までを確認する。batchも同時atomic snapshotや真正な使用点資格、Drive/runtime受け入れの証明ではなく、各結果の全may_*はfalseである。

## 共通Drive観測による複数sourceの比較

### 1 回の呼び出し内で繰り返される比較値 (2026-10-27)

`compare_reobserved_drive_contents`と`compare_planned_drive_contents`は共通観測・download集合の検査後、同じfilename/size/SHA-256を持つsourceの比較結果を1呼出し内だけで再利用する。異なるfieldは別の比較条件とし、結果tupleは重複も含めcaller指定の全slot・順序を保持する。共有結果はimmutableな観測であり、local pathの同一性や出所・実行権限を示さない。

再利用辞書は呼出しごとに新規作成し、他run/次の呼出しへ持ち越さない。前後列挙の完全性/不変性とdownload集合・planの再導出/完了検査を省略しない。空選択も共通入力を検査する。比較条件がすべて異なる場合の走査量・全memory/時間には上限を設けず、最大で異なる比較条件数分の結果辞書を持つ。

単一sourceの比較は一致件数と候補ID1件だけを保持し、複数一致の全IDリストは作らない。2件目で早期確定せず、後続候補のsize/hash不明やdownload不一致を引き続き検査し、従来のreason優先順位を維持する。既存のcandidate/heldと全may_*falseは不変で、provider真正性/現在性・同時snapshot/ABA・runtime受け入れは証明しない。

`compare_reobserved_drive_contents`はComparisonSourceの明示tupleを受け、前後の列挙集合を1回ずつ検査し、共通download集合を1回検査する。名前別indexを作り、各sourceの同名候補だけを既存name/size/hash規則で比較する。全fileをsource数だけ再検査せず、結果tupleはcaller指定順を保持する。単一sourceの前後比較APIは1要素batchへ委譲し、直接比較APIも同じ検査/比較部品を使う。

ContentComparisonBatchの`status=compared`は共通入力の検査と比較処理が完了したことだけを表す。各結果のheld/candidateは独立に保持し、全件同期成功やaggregate reportを生成しない。共通の型/信頼/folder/列挙変化/download ID不備はbatch全体をheldとし、部分結果は返さない。file固有のhash不明・不一致・0/複数一致は各ContentComparisonのheldに残す。全結果とbatchのmay_*はfalseである。

空source tupleでも共通観測/downloadを検査し、空結果をno_workへ変えない。source tupleをdedupせず、同じ比較値を持つ別local pathの対応はcallerに残す。複数sourceが同じcloud IDを比較候補とすることから出所や共有・復元を認可しない。batch objectはIPC result field集合の採用でもなく、永続状態やreceipt/cacheにしない。

[Drive batch試験](../../../tests/test_drive_comparison_batch.py)は候補/不明/不在の混在と順序、file検査回数がsource数に乗算されないこと、共通不備の全体保留、download fallback、空選択、重複sourceの保全、単一APIの既存境界を確認する。[source batch接続](../../../tests/test_comparison_source_batch.py)も1回のsource再観測→共通page/download→一括前後比較へ接続する。実API・観測真正性・同時snapshot/ABA・runtime受け入れは未実装gateのまま。

## 不足hash観測のdownload対象計画

### 繰り返しソースの計画と予算のプリフライト (2026-10-27)

`plan_content_downloads`は厳密なsource/列挙検査後、名前ごとの要求size集合を作り、同名sourceが何件あっても各Drive候補bucketを1回ずつ走査して必要件数と総bytesを計算する。hashの違いだけで同じIDを重複計上しない。0 bytesのfileも1件として数え、異なるsize条件も同じ名前の走査で扱う。

全候補のmetadata検査後に件数・bytes上限を順に確認し、予算内の場合だけ2回目の候補走査で必要ID/size辞書とソート済みrequirement tupleを作る。超過時は必要file数に比例する追加辞書を作らず、部分計画も返さない。size不明→件数超過→bytes超過という既存reason優先順位を維持する。None時も同じ候補集合・ID順・非認可flagsで、source/列挙objectは変更しない。

これは重複sourceと同名候補の積に比例する走査を避け、出力辞書の生成を予算確認後に遅らせる改善である。sourceの名前/size集合と全列挙index、caller生成済み入力、bytes/ID文字列長・全memory/時間は依然制限しない。新しい本番値・schema/SDK契約・download認可・runtime/実Drive受け入れは追加しない。[計画試験](../../../tests/test_content_download_plan.py)で高重複入力の候補訪問数、複数size/信頼SHA/0 bytes、順序不変とreason優先順位を確認する。

`plan_content_downloads`は明示source tuple、完全列挙観測と独立source信頼/期待folderから、不足しているdownload hash観測だけを計画する。共通の厳密な型/完全性/ID一意性検査後、同名・同sizeのうちcloud SHAが欠落/信頼未確認のfileを選ぶ。同名候補のsize不明は計画全体を保留し、部分requirementを返さない。既知の一致が1件あっても、不明な同名同size候補を省略しない。

DownloadRequirementはfile IDと期待sizeを保持する内部データで、IPCのrequest/result field集合ではない。複数sourceで共有するfile IDは1件にまとめ、ID文字列順に並べてpage/source順の違いによらない計画にする。信頼確認済みSHAがあるfile・名前違い・既知size違いはdownload対象にしない。SHA不一致や0候補からupload/restore/retryへ進む判断は行わない。

必要観測があればstatus=requires_download_observations、不要ならcomparison_inputs_available、共通不備はheldとする。全結果のmay_download/may_restore/may_report_sync_success/may_archiveはfalse。空sourceやrequirement0件をno_work/同期成功へ変換せず、既存比較で結果を判定する。計画は完了download hash・現在のfile存在/内容・実行権限の代わりにならず、同じ保存済み計画から送信を認可しない。

[計画試験](../../../tests/test_content_download_plan.py)はSHAの信頼/欠落、不要downloadの除外、不明metadataの保留、共有IDの一意化/安定順序、空sourceと全may_*false、計画→合成download bytes/hash→再列挙→一括比較を扱う。[source batch接続](../../../tests/test_comparison_source_batch.py)も実source再観測からrequirement計画を経由する。実SDK/認証・取得時のID/完了/size binding・使用点資格は未実装gateのまま。

## 呼び出し元が選択したダウンロード プランの出力予算 (2026-10-26)

`plan_content_downloads`と`compare_planned_drive_contents`はoptional `maximum_downloads` / `maximum_total_download_bytes`を受け取る。Noneまたは正のexact intのみ許し、不正値は既存のsource trust/type検査後、listing検査前に`comparison_download_limit_invalid`でheldとする。Noneでは当該caller上限なし、固定本番値・C-02/schema・実取得方針は採用しない。

完全listingとsourceから不足hash対象の一意な件数・期待sizeの合計を計算して検査する。超過は`comparison_download_count_limit_exceeded` / `comparison_download_bytes_limit_exceeded`で全体held、requirementsは空で、必要ID/size辞書・requirement objectの構築/出力順序sort前に停止する。候補をskipした部分計画や不足対象の成功補完は行わない。予算内では従来の決定的ID順・exact sizeと全may_*falseを維持し、0件をno_work/同期成功にしない。

比較側はcallerが渡した同じ上限で計画を毎回再導出し、超過/不正値なら完了集合比較前にbatch全体heldとする。予算はplan自体に保存される認可ではなく、未指定の後続呼出しへ自動伝播しない。周囲のpage/file件数上限、個別hashのdownload/chunk上限とは独立である。

これはrequirements出力の資源予算で、既存listing/sourceの保持・index/名前別size集合・探索時間/全memoryの制限ではない。source trust/metadata不備は従来どおり保留し、実API/SDK/credential・providerの真正性/現在性やdownload/Archive権限を証明しない。[計画試験](../../../tests/test_content_download_plan.py)と[比較接続試験](../../../tests/test_planned_drive_comparison.py)で重複IDの一回計上、exact境界、不正値のlisting非検査、超過時のrequirement非構築、0件/未知metadataと比較側への再適用を確認する。

## 計画と完了download集合の整合検査

`compare_planned_drive_contents`は既存の不足hash計画、source tuple、前後列挙と完了download hashを受ける。plan/requirementsの厳密型・size・全may_*falseを検査し、現入力から計画を毎回再導出してexact一致を要求する。そのうえで前後列挙不変とdownloadのID/型/一意性を検査し、計画したID集合と実観測集合が同一、全実sizeが期待sizeと一致する場合だけ各sourceを比較する。

不足・余分・重複・未知ID・size不一致・改変計画・共通不備はbatch全体held、部分結果なしとする。これは計画されたdownload完了を全件必要とする厳密な接続APIであり、既存`compare_reobserved_drive_contents`のfileごとの不足hash保留は維持する。SHA不一致は完了観測があっても各比較のheldで、同期成功へ変えない。

requirement0件でも再導出/列挙/空download集合の整合を検査し、空入力をno_workへ変えない。planの一致は不足hash対象の一致だけで、元source contextの出所や真正性を証明しない。plan/観測の反復からreceiptやdownload/restore/retry権限を作らず、結果の全may_*false。実取得のID/bytes/完了・現在性、実source使用点はproviderの未実装gateに残る。

[計画接続試験](../../../tests/test_planned_drive_comparison.py)は全件完了、1件欠落/余分/重複/未知ID/size不一致、計画field/型/flag改変、現在contextと列挙変化、download不要/空選択、誤hashの保留と非認可を扱う。[source batch接続](../../../tests/test_comparison_source_batch.py)も実source再観測→page→計画→合成bytes/hash→再page→計画完了集合検査→比較までを検査する。実API/runtime受け入れは未実施。

## Download新規stagingの隔離接続（tests専用）

[治具](../../../tests/download_staging_fixture.py)はcallerのroot/保存先/API clientを受けず、自分で作る所有marker付きOS-tempだけを使う。実Windows mutex/owner内で試行ごとに新しいdirectoryを確保し、固定合成名をxb/create-newで開く。既存fileへ上書きせず、部分fileが残った次試行も別の新規fileを使う。配置・filename・APIは正式download runtime契約へ採用しない。

合成chunkを書き、期待size超過/不正chunk/途中例外では観測を返さず部分fileを保全する。正常消費後はflush/fsync/closeし、directory/regular-file・1 link・path/handleのidentity/size/mtime等を検査して、実fileのchunk読戻しを既存hash_downloaded_contentへ接続する。未完了/短いfile・読戻し前の検出可能な変更は拒否する。所有mutexは失敗時も解放し、cleanupは自作rootのidentity/markerを再確認したテスト終了時だけ行う。元ログ/Drive fileや実設定の削除/回復コードを追加しない。

[合成試験](../../../tests/test_download_staging_integration.py)は空/通常/1 MiB超の実file、計画→staging→実bytes/hash→再列挙→比較、途中失敗後の別stagingと旧bytes保全、create-new競合、short/overlong/未完了、不正root/requirementと変更file保全を確認する。OS-tempの書込みは通常モードのテストであり、Dry Run Aのdownload bytes禁止を緩和しない。

これはmock chunkのnative保存/読戻し接続で、実SDK/認証/C-02 result、PS retry予算/時間待機、download成功/ID binding、正式staging/root/ACL/FSと容量確認、原子的同時snapshot/敵対的ABA、process crash/電源断耐久性、Tier B/Cやruntime受け入れは未実装・未実証である。fsync成功だけで耐久性や正式writer資格を与えない。

## 衝突時PC suffixの命名観測

`observe_pc_suffixed_name`は、旧方針に対応する命名観測ヘルパーである。指定したPC-A/PC-B、ログ種別、元のファイル名から、拡張子の直前に_PCA/_PCBを付けたDrive上の候補名を返す。[現在の同名ファイル要件](../../requirements/log-move-requirements.md#5-同名ファイル)では、この自動命名方式を初回完成の範囲から外している。既存のヘルパーと試験が残っていても、移動処理でこの方式を使ってよいことにはならない。

入力は、既存のファイル名規則と実在する日付、ダミーのルートを使ったC-01/L1の字句検査で確認する。ファイル名にパス区切り文字が含まれる場合や、不正なUTF-8は拒否する。実際のルートやファイルシステムは読み取らない。

immutable観測は元名・候補名・指定PC/logを保持し、Unicode正規化/case変換/trimや元名のsuffix除去をしない。既にsuffix文字列があるBattleLog名も元sourceの文字列として保持し、その末尾extension直前へ要求suffixを付ける。suffix文字列を出所確認に使わず、同じ元名への反復は同じ候補を返す。未知PC/logや不正文法は固定reasonで拒否し、元名を例外/reprへ出さない。

これは命名だけの観測で、same-name内容差・既存未標識fileの出所・suffix先の競合を検証した結果ではない。既存rename・Upload・上書き・Archiveの全may_*はfalse。出所不明は依然保留で、同名/同hashのOSD-01比較をsuffix別名へ拡張しない。候補名をB2/source relative pathや原本のfilenameへ書き戻さない。ErrorReportのsuffix付きDrive名も新しいsource filename文法として採用しない。FS/APIの実利用資格/長さ制限は使用点gateに残る。

[命名試験](../../../tests/test_pc_suffixed_name.py)は両PC/log、Unicode/結合文字/spacing/複数dot、suffix文字列の原文保持、日付/拡張子/PC/log/禁止文字/path/UTF-8拒否、I/Oなし・非認可を確認する。衝突解消orchestrator、原名/final名の正式adapter結果/記録、既存fileのrename/publication/現在内容と出所の検証は未実装のまま。
