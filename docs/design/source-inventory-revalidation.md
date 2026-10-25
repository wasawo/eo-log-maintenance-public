# 凍結B2に対するsource再観測

2026-10-25。[filename/保持範囲](filename-and-period-selection.md)、[runtime gate](runtime-entrypoint-validation-gate.md)のsource/inventory整合を支える読取専用helper：[SourceInventoryRevalidation.py](../../Common/SourceInventoryRevalidation.py)。実uploadやarchiveの認可ではない。

`revalidate_source_inventory`は明示source root、exact凍結B2 bytes、信頼済みstatic schema、独立PC/log/run/root ID/relative scope、明示reference dateと現在UTC/reliableを要求する。JSON/schema/digest/count/scope・元列挙時刻の順序/未来5分を検査する。元のenumeration/validation coverageが不完全なら再列挙せず拒否し、欠落や不一致を新しいB2で補完しない。completed coverage中の既知validation errorsは消さない。

既存source builderを独立入力のreference date/scopeで読取専用実行し、再観測のcoverageが完全な場合だけ、targetのpath/filename/size/hash・inventory順序、列挙件数、分類件数/error集合・順序、論理source scopeを元B2と比較する。追加/削除/rename/内容変更、分類結果変更、読取/hash失敗は拒否する。builderが内部で取得する終了時刻は時計証拠にせず比較対象から除き、再生成B2を返却/保存しない。結果には元B2 bytesとtarget数だけをimmutableに保持し、status=requires_runtime_evidence、全may_*はfalseとする。

source rootの物理的認可・root IDとの真正な結び付き、実clock/run/owner資格、列挙開始から後続使用までの原子的snapshot、敵対的ABAは未実装gateである。比較はB2に保存されたeligible targetと分類観測に限り、対象外fileの内容/identityが不変であることを証明しない。reference dateが別日に変わる等で分類が変わったら旧B2を更新せず拒否する。一致しても後の変更を防げず、upload/read/manifest更新の使用点資格やarchive権限へ昇格しない。

[合成試験](../../tests/test_source_inventory_revalidation.py)は両PC/log、同一観測・元bytes保持、不変/非認可結果、追加/削除/rename/同サイズ変更、分類/error保持、不完全な元B2、再scan/hash失敗、scope/clock/reference date不正・欠落/破損B2の事前拒否、対象外内容の比較限界を検査する。全I/Oは専用tempの合成sourceで、実ログ/本番Driveや実設定には接続しない。

B2には元sourceのOS file IDやreference dateそのものを保存していないため、同じpath/bytesで置換された別実fileや、分類結果が同じになる異なる基準日をこの比較だけで見分けるとはしない。独立contextと使用点の資格を外部で確保する。


## 初期planの使用点接続

`revalidate_initial_manifest_source`は初期planと独立run context/現在時計/static schema、明示AC接続状態、source/root scope/reference dateを要求する。planの厳密型と全false flagを確認し、ACが明示Trueの場合だけ初期候補を再構成する。再構成bytes/B2/flagsが元planとexact一致しなければsourceを読まず拒否する。同じinstantでも開始UTCの表記差や候補の書式差を勝手に正規化しない。

その後、毎回`revalidate_source_inventory`で新しくsourceを再列挙/hashする。過去の観測objectやcallerの「検査済み」boolから再確認を省略する経路はない。返す観測は全may_*falseで、同じ結果の反復も一回限りreceiptや実行許可にはならない。AC値はcallerの観測で、OS取得の真正性・継続接続・in-flight停止は別gateである。

[合成使用点試験](../../tests/test_initial_source_usepoint.py)はplan/B2/flag/context改変とAC不明をsource I/O前に拒否し、実fixture mutex/ownerの保持中に検査→候補公開へ接続する。一致時は候補を保存できるがruntime認可ではなく、source変更/AC切断ではcandidateを書かずownerを解放する。検査後の変更・敵対的ABA・scope/実ownerの資格を排除した証拠ではない。現在時計を取るprovider、実runの鮮度、実root/ACL/FS/C1比較更新とupload/runtime受け入れは未実装のまま。

source builderには[列挙完了前のdirectory/属性再確認](source-enumeration-stability.md)も加えた。再観測中の変更を検出した場合もincompleteとして拒否する。non-target内容の変化が別々の安定した再観測の間に起こり、分類観測が変わらなければ従来の比較限界は残る。
