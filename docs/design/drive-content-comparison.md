# Drive同一内容の比較候補（OSD-01）

2026-10-25。[OSD-01承認](../requirements/p0-open-specification-decisions.md#approved-decision-record--osd-01)と[衝突/比較規則](../development/implementation-workflow.md)を支える純粋helper：[DriveContentComparison.py](../../Common/DriveContentComparison.py)。API接続・IPC結果schema・出所認証・復元・同期成功・archiveの実装ではない。

内部のimmutable観測は、sourceのfilename/size/SHA、Drive fileのID/name/size/任意SHAとその信頼確認、完了したdownloadのID/実byte数/SHAから成る。IPCのC-02結果field集合は定めない。callerは比較元が確認済みの信頼できるPC-A source/backup記録であること、期待folderと観測folderの一致、全page列挙完了を独立に確認して渡す。bool等の入力は証明でなくcaller観測で、helperは真正性・鮮度・paginationを認証しない。

`compare_drive_content`はsource trust/完全列挙に明示Trueを要求し、tupleの観測集合を検査する。file ID重複、未知IDや重複IDのdownload、不正な型/size/hashを保留する。名前はexact/case-sensitive、sizeは非負int（bool/float不可）、SHAはlowercase hex64で、補完・正規化しない。

同名・同sizeの候補は信頼確認済みcloud SHAを用い、欠落/未確認ならIDへ結び付いた完了downloadの実size/hashを要求する。download size不一致や信頼済みcloud SHAとの矛盾は保留する。metadata-only、失敗/未取得downloadを一致にしない。同名候補のsize/hash不明が残れば既知の一致が1件でも保留する。名前違い・既知size違いは一致候補に含めない。

名前/size/SHAが全て一致するfileがちょうど1件なら`comparison_candidate`とIDを返す。0件/複数件は`held`でIDを返さない。全結果のmay_restore/may_report_sync_success/may_archiveはfalseであり、比較一致は未標識fileの出所、復元/上書き/rename/再送/削除の許可にならない。結果・観測のreprへ内容を出さず、固定reason codeだけを診断に使う。実IDをログ/追跡文書へ出さない。

[合成試験](../../tests/test_drive_content_comparison.py)は0/1/複数、不完全・別folder・未信頼source、同名の不明候補、SHA fallback、download ID/size/hash不整合、入力型、非認可・I/Oなしを扱う。実Drive SDK/全page取得、source/folder/metadataの真正性と現在性、download実bytes検証、同期/履歴/両PC/archive gateは未実装のまま。

## Download実bytesのstream観測

`hash_downloaded_content`はfile ID、独立した期待size、明示download完了状態と、非空のexact bytes chunkのiterableを受ける。空fileは0 chunkで表す。context/完了未確認は消費前に拒否し、全chunkのSHA-256と実byte数を蓄積する。元bytesは保持せず、file/network APIを直接呼ばない。chunk提供側が消費時に行うI/Oはcaller/providerの責任である。期待sizeを超えたら残りを消費せず停止し、short read・途中例外・不正chunkでも観測を返さない。iteratorが独自例外を返しても固定reasonに置き換え、内容やraw例外を出さない。

全iteratorを正常に消費し、実sizeが期待と一致した場合だけ既存DownloadHashObservationを返す。既存比較へそのまま渡し、異なる内容のhashを一致へ変えない。chunk境界や空fileでもexact bytesのdigestを使う。返却後もID/stream/完了状態の真正なbinding、実SDKの成功判定・最新metadataとの照合はcaller/providerの未実装gateである。

streamの所有権はcallerに残る。helperは再読取・retry・close・temp保存をせず、途中停止時のstream/resource解放をcallerが行う。OS/network readのblock/timeout、任意に巨大なchunkの生成、敵対的bytes変更後の復元を解決するものではない。IPCのresult形やdownload SDK方式は採用しない。[合成stream試験](../../tests/test_download_hash_observation.py)はchunk分割/1 MiB境界/空file、超過時停止、short read、完了後例外、型不正と比較fallbackの接続を扱う。

## 全pageの内部観測集約

`collect_drive_listing`は期待folderとDriveListingPageのiterableを受け、全pageを検査した場合だけimmutable DriveListingObservationを返す。最初のrequested_tokenはnull、後続は直前のnext_tokenとexact一致し、各pageのfolder一致とrequest_succeededの明示Trueを要求する。next_tokenは非空のopaque文字列かnullで、正規化せず、既出tokenへの循環を拒否する。内部page fieldはIPC C-02のwire結果集合を定めない。

next_token=nullの終端pageがちょうど1件あり、その後にpageも例外もない場合だけenumeration_completed=trueになる。0 page・終端欠落・途中失敗を空の完全列挙へ変換しない。空の中間pageは後続tokenがあるなら許し、空の終端page1件は完全な0件観測として区別する。全pageのfileは既存比較と同じ型/size/hash規則で検査し、page内/間のID重複を不明扱いで拒否する。観測順を保ち、自動dedup・不足page補完・再試行を行わない。

返す観測のfile集合/folder/完全列挙値とdownload hash観測を既存比較へ渡せるが、may_restore/may_report_sync_success/may_archiveはfalse。callerは実API応答・対象folder/query/アクセス範囲・token/成功状態を信頼できるproviderでbindingする必要がある。内部pageの整合だけで実クラウド全件・鮮度・出所を証明しない。単純なdataclass生成や保存済み観測も資格証拠ではない。

collectorはfile/network APIを直接呼ばず、page提供側のI/O・timeout・件数/時間予算・resource解放はcaller/providerに残る。途中例外は固定reasonへ置換し、token/IDやraw例外を診断へ出さない。部分観測は返さず、callerの元pageを変更/closeしない。[合成page試験](../../tests/test_drive_listing_observation.py)は空/複数/空中間page、token切断/循環、folder/成功不明、ID重複、終端後page/例外、実bytes hash fallbackと複数内容一致の保留までを接続する。

## PC-Aの凍結B2とsource再観測への接続

[SourceInventoryRevalidation.py](../../Common/SourceInventoryRevalidation.py)の`revalidate_comparison_source`は比較元の明示信頼確認、PC-Aのexact B2 bytesと独立log/run/root/scope/reference date/現在時計、対象relative pathを要求する。B2のschema/digest/inventory不変条件を検査し、canonical相対pathで一意のeligible targetを選ぶ。PC-BのB2や対象不在・不正文法はsourceを読む前に拒否する。同名でも別pathのtargetを推測して選ばない。

既存のsource全列挙/再hash比較を毎回実行し、一致した場合だけtargetのfilename/size/hash、元B2 bytesとrelative pathをimmutableなRevalidatedComparisonSourceへ結び付ける。選択target以外を含むinventory変更や不完全coverageも拒否し、B2を更新/補完しない。既知のvalidation errorsは既存helperと同じく保持し、run全体の成功に変えない。

返すsourceをpage集約/download hashと比較へ渡せるが、全may_*false。PC-Aラベルやhash一致だけで記録の出所・真正性を信頼済みにはしない。source_trustedは独立した必須観測であり、返却objectをcompareのtrust判定へ自動昇格しない。source/rootの実資格・観測後の変化/ABA・cloud観測との同時snapshotは未実証のまま。

[合成接続試験](../../tests/test_comparison_source_revalidation.py)は両log/Unicode/同名別path、PC-B/未信頼/不正B2/context/不完全の事前拒否、source全体の変更と毎回再観測、元bytes保全、source→page→download実bytes hash→比較までを専用tempで確認する。実ログ/Drive・復元/同期成功/archive・候補artifact保存は行わない。

## Download前後の完全列挙観測の照合

`compare_reobserved_drive_content`は比較元、前後2つのDriveListingObservation、独立source信頼確認/期待folder、download hashを受ける。両観測の厳密型・tuple file集合・明示完全列挙・全may_*false・期待folder一致と全file型/ID一意性を再検査し、IDをkeyとした全metadata集合を比較する。page/file順だけの違いは許す。名前/size/SHA/信頼確認状態、追加/削除/置換や対象外fileの変化は保留する。

観測集合が同じ場合だけ既存のexact name/size/hash・download fallback比較を再実行し、不明・0/複数一致は引き続き保留する。SHA未確認から確認済み等へのmetadataの充実も同一観測と見なさず、旧結果を自動補完しない。観測・download・B2を修正しない。

このhelperはAPI再取得を実行せず、引数が実際にdownload前後のfreshな全pageを表すことやquery/権限/出所を認証しない。同じ保存済みobjectを両側へ渡しても現在性や一回限りreceiptの証明にならず、全結果may_*falseである。掲載されたmetadataで観測できない同サイズ内容変更、観測間のABA・paginationの同時snapshot・比較後の変化は未解決のまま。

[前後観測試験](../../tests/test_drive_comparison_reobservation.py)は変化なし/順序差、追加/削除/rename/ID置換/metadata変化、対象外fileの変化、不完全/不正/別folder/重複ID、不明hash・0/複数候補と保存済み観測の非認可を扱う。[PC-A source合成試験](../../tests/test_comparison_source_revalidation.py)もsource再観測→列挙→download bytes/hash→再列挙→比較までを接続する。実Drive/runtime受け入れではない。

## 複数比較元の一括再観測

`revalidate_comparison_sources`は明示したrelative_pathsのtupleを受け、全pathの型/canonical字句/重複なし/B2 target存在/filename文法をI/O前に検査する。その後、既存の全source再列挙/hashを1回だけ実行し、全観測が一致した場合だけRevalidatedComparisonSourceのtupleを指定順で返す。元B2 bytesは各結果から同じimmutable bytesを参照し、内容をコピー/更新しない。

1 targetごとに全sourceを再hashする呼出しをまとめられるが、batchを次回の検査済みcacheにはしない。単一file用`revalidate_comparison_source`も1要素batchへ委譲し、従来の入力/結果とfreshな全再観測を維持する。選択外fileも含めたinventory変化・不完全coverageで全体を拒否し、途中までの比較元を返さない。

空tupleは明示的な0件選択であり、全source再観測を省略せず、不完全な元B2や変更sourceを通さない。返却の空tupleをno_work/同期成功へ昇格しない。選択・順序・scope/PC-A/source信頼確認はcallerの独立入力で、未指定のfileや期間を自動補完しない。

[合成batch試験](../../tests/test_comparison_source_batch.py)はUnicode複数target、指定順と1回の再hash呼出し、全path事前検査、選択外を含む変更/空選択/空inventory/不完全/信頼とPC-A境界、複数sourceから共通のpage/download/前後比較までを確認する。batchも同時atomic snapshotや真正な使用点資格、Drive/runtime受け入れの証明ではなく、各結果の全may_*はfalseである。

## 共通Drive観測による複数sourceの比較

`compare_reobserved_drive_contents`はComparisonSourceの明示tupleを受け、前後の列挙集合を1回ずつ検査し、共通download集合を1回検査する。名前別indexを作り、各sourceの同名候補だけを既存name/size/hash規則で比較する。全fileをsource数だけ再検査せず、結果tupleはcaller指定順を保持する。単一sourceの前後比較APIは1要素batchへ委譲し、直接比較APIも同じ検査/比較部品を使う。

ContentComparisonBatchの`status=compared`は共通入力の検査と比較処理が完了したことだけを表す。各結果のheld/candidateは独立に保持し、全件同期成功やaggregate reportを生成しない。共通の型/信頼/folder/列挙変化/download ID不備はbatch全体をheldとし、部分結果は返さない。file固有のhash不明・不一致・0/複数一致は各ContentComparisonのheldに残す。全結果とbatchのmay_*はfalseである。

空source tupleでも共通観測/downloadを検査し、空結果をno_workへ変えない。source tupleをdedupせず、同じ比較値を持つ別local pathの対応はcallerに残す。複数sourceが同じcloud IDを比較候補とすることから出所や共有・復元を認可しない。batch objectはIPC result field集合の採用でもなく、永続状態やreceipt/cacheにしない。

[Drive batch試験](../../tests/test_drive_comparison_batch.py)は候補/不明/不在の混在と順序、file検査回数がsource数に乗算されないこと、共通不備の全体保留、download fallback、空選択、重複sourceの保全、単一APIの既存境界を確認する。[source batch接続](../../tests/test_comparison_source_batch.py)も1回のsource再観測→共通page/download→一括前後比較へ接続する。実API・観測真正性・同時snapshot/ABA・runtime受け入れは未実装gateのまま。
