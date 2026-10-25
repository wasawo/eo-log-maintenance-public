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
