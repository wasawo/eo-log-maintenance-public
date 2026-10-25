# 凍結B2に対するsource再観測

## 既存stagingとDrive観測の接続

`inspect_initial_staged_drive_contents`は独立run contextと初期plan、明示allocationを使ってstagingを毎回一括再読取し、得たsize/hashと元basenameを既存`compare_planned_drive_contents`へ渡す。source payloadを読み直さず、local copy一致からsource信頼確認を自動付与しない。期待folder・source_trusted・Drive前後完全列挙・不足hash計画・完了hash集合は独立引数で要求し、既存helperで整合を再検査する。

ローカル不備は固定reason例外で停止しDrive比較へ進まない。Drive共通不備は、照合済みcopy tupleを保持しcomparisons空のheld観測を返す。正常な比較はcopy/比較を同じ選択順で保持し、file単位の不一致/曖昧はその比較のheldとして残す。内部比較の厳密型・tuple・件数・全false flagも検査する。専用immutable型はreprへ内容を出さず、Upload/retry/同期成功/状態変更/Archive許可を常にfalseとする。

PC-A/PC-B両方の元名に対する内容観測だけで、PC suffixを暗黙alias化せず、Upload先final名の契約や出所を定義しない。空選択もDrive整合検査を省略しないが、no_work/全件完了ではない。APIの実再取得・query/権限/真正性・現在性/ABA・local copyの後続変更・正式metadata/history・Upload結果/実同期は証明しない。旧観測をplan/receiptとして受け付けない。[接続テスト](../../tests/test_staged_drive_content_observation.py)は合成file/Drive bytesだけを使用する。

## 既存staging copyの独立読取観測

`observe_initial_staging_copy`は初期planと独立PC/log/period/run/start/clock/schemaでplanを再構成し、exact bytes/全false flagを検査する。明示relative pathに対応する凍結targetと、正の整数sequence（bool不可）を要求し、pending状態から作業対象を推測しない。

既存絶対staging root直下の`<run_id>_<sequence>_<original_filename>`だけを読む。祖先chain/reparse、regular file/単一link、bounded hash読取り前後のentry signatureと祖先chainを検査し、size/SHA-256を凍結targetと比較する。missing/不明/不一致は固定reasonの例外で拒否し、内容・path・raw例外をreasonへ出さない。file作成/上書き/削除やsource payload読取りは行わない。

immutable観測へ元manifest/B2 bytes・対象・sequence・size/hashを保持し、reprは非表示、全Upload/状態変更/cleanup/Archive許可false。呼出しごとに再hashし、旧観測をplan/receiptとして受け付けない。これは正式ready状態ではなく、metadata-first/history、copy時の割当identityとのbinding、root分離/ACL/FS/owner/AC/容量の資格、同時snapshot/ABAや後続payload使用点を証明しない。sourceが現在不在でもstaging観測は成立し得るが、そこから実Uploadを許さない。

[合成テスト](../../tests/test_initial_staging_copy_observation.py)は両PC/log、空/複数block、source非読取、入力事前拒否、missing/内容差/dir/hardlink、後続変更、provider失敗と保存、旧観測再利用拒否を扱う。実ログ/本番Driveは使わない。

`observe_initial_staging_copies`は明示`((relative_path, sequence), ...)` tupleを一括照合する。plan再構成は1回、指定順のimmutable観測tuple全体か固定reasonの例外を返し、途中結果を返さない。単一APIは1要素batchへ委譲する。全指定をI/O前に検査し、同じsource targetの重複や同一staging候補名（casefoldで保守的に比較）を拒否する。この名前検査は実FSの同名性を証明せず、sequenceの自動割当や別名への修復をしない。

全選択fileのregular/単一link/sizeをhash前に確認し、サイズ不一致ならpayloadを開かない。共有hash helperへ凍結expected_sizeも渡し、事前stat後の増大もopen前に拒否する。open handleのsize/identity照合と初期size+1 byte上限も維持する。全hash後に選択fileのsignatureとroot祖先chainを再照合し、後続file読取り中に検出可能な先行file変化も拒否する。file保存/削除は行わない。

空選択でもplan/root前後検査を省略せず、空tupleはno_work/全inventory完了やUpload許可を意味しない。選択外fileは検査せず、全選択fileの最終確認も逐次観測であり、同時snapshot・現在性の保証・ABA防止ではない。[一括合成試験](../../tests/test_initial_staging_copy_batch.py)で順序/1回再構成/事前拒否/後続不備/跨file変化/増大時open禁止/空選択を確認する。

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

`revalidate_comparison_source`は[OSD-01比較元のPC-A source接続](drive-content-comparison.md)として、指定relative pathのB2 targetと毎回の全source再観測を結び付ける。source信頼確認は独立必須で、PC-Aラベル/一致hashから自動認証しない。全may_*falseで、既知validation errorsや不完全判定を成功へ変えない。

複数targetは`revalidate_comparison_sources`へ明示path tupleを渡し、全path検査後に1回の全source再観測から指定順に比較元を返せる。空選択もcoverage再確認を省略せず、no_workとはしない。単一target APIは1要素batchへ委譲し、呼出し間のcacheを設けない。
