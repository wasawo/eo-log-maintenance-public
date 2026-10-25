# Drive同一内容の比較候補（OSD-01）

2026-10-25。[OSD-01承認](../requirements/p0-open-specification-decisions.md#approved-decision-record--osd-01)と[衝突/比較規則](../development/implementation-workflow.md)を支える純粋helper：[DriveContentComparison.py](../../Common/DriveContentComparison.py)。API接続・IPC結果schema・出所認証・復元・同期成功・archiveの実装ではない。

内部のimmutable観測は、sourceのfilename/size/SHA、Drive fileのID/name/size/任意SHAとその信頼確認、完了したdownloadのID/実byte数/SHAから成る。IPCのC-02結果field集合は定めない。callerは比較元が確認済みの信頼できるPC-A source/backup記録であること、期待folderと観測folderの一致、全page列挙完了を独立に確認して渡す。bool等の入力は証明でなくcaller観測で、helperは真正性・鮮度・paginationを認証しない。

`compare_drive_content`はsource trust/完全列挙に明示Trueを要求し、tupleの観測集合を検査する。file ID重複、未知IDや重複IDのdownload、不正な型/size/hashを保留する。名前はexact/case-sensitive、sizeは非負int（bool/float不可）、SHAはlowercase hex64で、補完・正規化しない。

同名・同sizeの候補は信頼確認済みcloud SHAを用い、欠落/未確認ならIDへ結び付いた完了downloadの実size/hashを要求する。download size不一致や信頼済みcloud SHAとの矛盾は保留する。metadata-only、失敗/未取得downloadを一致にしない。同名候補のsize/hash不明が残れば既知の一致が1件でも保留する。名前違い・既知size違いは一致候補に含めない。

名前/size/SHAが全て一致するfileがちょうど1件なら`comparison_candidate`とIDを返す。0件/複数件は`held`でIDを返さない。全結果のmay_restore/may_report_sync_success/may_archiveはfalseであり、比較一致は未標識fileの出所、復元/上書き/rename/再送/削除の許可にならない。結果・観測のreprへ内容を出さず、固定reason codeだけを診断に使う。実IDをログ/追跡文書へ出さない。

[合成試験](../../tests/test_drive_content_comparison.py)は0/1/複数、不完全・別folder・未信頼source、同名の不明候補、SHA fallback、download ID/size/hash不整合、入力型、非認可・I/Oなしを扱う。実Drive SDK/全page取得、source/folder/metadataの真正性と現在性、download実bytes検証、同期/履歴/両PC/archive gateは未実装のまま。
