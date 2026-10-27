# PC-A確認予算の分離実装

状態: 24時間・初回含め25回の上限は利用者承認済み。補助checkpointの[最小field契約](../../archive/decisions/implementation-grounded-four-decisions-20261024.md)も限定確定した。純粋な判定/履歴更新helperであり、待機task・永続保存・archive認可ではない。
根拠: [承認記録](../../archive/decisions/pc-a-completion-wait-budget-proposal.md)。

## scope・履歴と判定

Common/CompletionWaitBudget.pyは、PC-A/log種別/対象period/元run_id、最初の適格待ち判定UTC、各確認試行UTCの不変tupleを受け取る。
期待するscopeと元run_idを別に要求し、PC-Bや別period/runの予算を転用しない。
履歴全件のUTC、開始〜24時間以内、1時間以上の間隔、25回以内を検証する。未来履歴や時計逆行、破損・不明は保留。

assess_completion_wait_budgetは次の3分類のみを返す。

- check_due: 時間/回数の観測上、次の確認候補。実行・保存・archive許可ではない。
- wait: 最後の試行から1時間に満たず、次の候補UTCを返す。sleepや予約は行わない。
- hold: 期限/回数/資格不足/不正状態で、次の確認候補は返さない。

期限UTCちょうどの適格な最終確認は許す。1microsecondでも過ぎたら保留。初回から毎時なら0〜24時間の25回で終わる。
遅れた試行の次もその試行から1時間以上空け、取り逃した機会を詰めて消化しない。回数が余っていても期限を延長しない。
次の1時間を入れる余地がなければ保留。日時上限で計算不能な入力にもfallbackしない。

clock reliable、logged_on、same_account_verified、own_sync_complete、waiting_confirmedを明示boolとして要求する。
これらは呼出元からの申告であって、OS/token・自同期/最新PC-B内容・Drive検証の証拠を収集/認証する処理ではない。
waiting_confirmedは不正・曖昧manifestを待機に読み替えるためのflagではなく、外部安全gateを満たした待ち対象という前提。
全結果でmay_archive/may_change_state=false。失敗/成功へのmanifest書換え、旧success代用、lock回復やupload retryを追加しない。

## 試行の計上

record_completion_check_attemptは全観測を再判定し、check_dueの場合だけ新しい履歴tupleを返す。
元stateは不変。実確認を実行せず、失敗した確認も試行として消費するため、呼出元は実確認の前に予算の更新を確定させる必要がある。
その永続化・排他・クラッシュ対策・元記録へのbindingは未実装。履歴が失われたり信頼できなかったら、正式呼出元は新規予算に置き換えず停止しなければならない。

同じstateを再構成して渡すと元の期限を維持するが、これは任意の偽造/巻き戻しstateを検出できることや、実再起動耐性の証明ではない。
helperは新しい予算を自動作成・リセットしない。明示再開、新runとfresh inventory、通知、正式task/毎時確認との接続は別の作業。

## Checkpoint schemaと純粋reader（2026-10-25）

### 既存fileの上限付き読取観測（2026-10-26）

予算の観測入口は`assess_completion_wait_checkpoint_file`。明示AC/既存絶対path/bytes上限と独立scope/clockから毎回fileを読み、保持したcheckpointを精度を落とさず既存budget helperへ渡す。結果は元checkpointと`check_due / wait / hold`助言を持つ専用immutable型で、全確認/待機/Archive/状態変更許可false。check_due=trueでも試行plan生成/消費・確認を自動実行せず、waitの次候補UTCもsleep/task予約ではない。

期限後/25回/次の間隔が入らない場合やsession/account/自同期/待機条件不成立は既存budgetのholdを保つ。AC未確認、file欠落/破損/不明、scope/clock不備、変換精度非対応は固定reason例外で拒否し、空履歴や通常waitへ変換しない。月次scheduleから対象periodや元開始時刻を推測しない。前回のdueをreceiptにせず、fileの更新/新規予算生成を行わない。[file予算接続試験](../../../tests/test_completion_wait_file_assessment.py)は自作tempで境界と非消費を確認する。provider資格/rollback/ABA/永続試行前計上・実確認は引き続き別gate。

実Win32置換とのtests専用接続では、再読取りによる競合拒否と、競合を無条件上書きした後/同一bytes別identity置換後の検査限界を確認している。[provider負例の詳細](checkpoint-compare-provider-qualification.md#file使用点との実置換接続2026-10-26)。これを正式CAS/providerの採用や確認実行許可にしない。

接続入口は`CompletionWaitAttempt.prepare_completion_wait_attempt_from_file`と`inspect_completion_wait_attempt_file_usepoint`。前者は明示ACと資格boolがTrueの場合だけ既存fileを指定上限で読み、そのexact bytesから従来の1試行planを構築する。保存や試行消費を行わず、pathを権限としてplanへ埋め込まない。

後者はplan/phase/AC/現在時計・scope/資格条件を既存純粋use-point検査へ通してから、毎回fileを開き直し、得たexact bytesでも同じ検査を繰り返す。before_commitはexpected bytes、after_commitはproposed bytesを要求する。保存済み観測や前回成功をfileの代用にせず、欠落/破損/変更は固定reasonのattempt errorで拒否する。両入口は作成/更新/削除・CAS・実確認を行わず、全確認/Archive/状態変更許可false。反復after_commitも新たな試行/一回限りreceiptにはならず、実保存先の資格や後続不変性は証明しない。[file使用点接続テスト](../../../tests/test_completion_wait_file_usepoint.py)は自作tempだけを使う。

`observe_completion_wait_checkpoint_file`は明示された既存絶対file pathと正の整数maximum_bytes（bool不可）を要求する。既定のfile名/配置/サイズ上限は選ばず、指定上限はcallerの資源制限であってschema field/互換方針の追加ではない。Windowsでは既存L1字句も検査し、ADS/UNC等へ暗黙対応しない。欠落を作成/空履歴へ補完しない。

既存metadata providerで祖先chain/reparse・regular/単一linkと初期sizeを検査し、上限超過はopen前に拒否する。pathとopen handleのsignature（volume/file identity・size/mtime・Windows birthtime等・link数）を照合し、読取りを初期size+1 byteに制限する。fstat/byte数を照合して既存schema/scope/clock readerへ渡し、解析後にもpath signature/reparse/祖先chainを再確認する。不備は固定reason例外、file作成/更新/削除は行わない。

結果はexact bytesを持つcheckpointを内包するimmutable・非表示reprの観測で、status=requires_runtime_evidence、全確認/Archive/状態変更許可false。毎回fileを開き直し、前回の観測をpath/receiptとして受け付けない。root/ACL/token/owner/FS/providerの資格、rollback/ABA防止、同時snapshot/後続変化、正式CAS/試行前永続化・実確認は未実証。[合成試験](../../../tests/test_completion_wait_checkpoint_file.py)は自作tempだけを使い、境界bytes・上限事前拒否・欠落/dir/hardlink・解析不備/途中変更・provider失敗と保全を確認する。

### 更新前後の追記検査（2026-10-26）

`inspect_completion_wait_checkpoint_transition`は独立scope/現在UTC/static schemaで前後exact bytesをreaderへ通す。元記録の不在/不正を補完せず、exact bytes再掲載だけをunchanged/added_check_count=0とする。それ以外は元started_at_utc文字列と既存check_times_utc全件の文字列/順序を保持し、1件だけ追記する更新を要求する。短縮、過去試行の置換、複数追記、開始時刻の再表記、追記なしの書式変更を拒否する。scope/version・間隔/24時間/25回/時計逆行のreader検査も維持する。

結果は元bytesと新checkpoint、追加件数、固定statusだけを持つimmutable非表示repr型で、全may_check/may_archive/may_change_state=false。既存`prepare_completion_wait_attempt`はcandidateの読戻しにこの検査を利用する。readerが扱える高精度UTC文字列を丸めずに保持し、budget状態への変換精度制限は緩和しない。これは提示された2記録の比較であり、元記録の真正性/現在性・保存喪失/rollback/ABA・原子的compare-and-publish・実試行前の永続化や資格の証拠ではない。exact再掲載も新しい試行receiptにしない。[合成試験](../../../tests/test_completion_wait_checkpoint_transition.py)で追記/保全/事前拒否とplan生成への接続を確認する。

[schema](../../../contracts/completion-wait-checkpoint-v1.schema.json)は承認済みの7fieldだけを持つclosed v1で、manifestとは別契約。PC-A限定、log種別ごとのperiod形、UUID、UTC Z、0〜25回を規定する。periodの4桁年に未決の範囲制約を追加しない。

`Common/CompletionWaitCheckpoint.py`の`read_completion_wait_checkpoint`は、callerが供給するexact bytes・信頼済みstatic schema、別入力の期待log/period/run IDと信頼できる現在UTCを要求する。I/Oをせず、未知/欠落/null field、重複JSON key、不正UTF-8/JSON/version、schema外部参照、scope不一致、不正日時、開始〜24時間外の試行、1時間未満の間隔、25回超、現在時計の逆行を拒否する。読取不能や欠落の代わりに空履歴を生成しない。現在が期限後でも有効な元履歴を保持し、既存予算helperで期限/回数のhold判定を行う。

結果はimmutable `CompletionWaitCheckpoint`で、元の時刻文字列と配列順をtupleとして保持する。`original_bytes`はexact入力を結び付ける内部metadataで、保存schemaの追加fieldではない。戻り値のreprと固定error reasonに内容を露出せず、readerは予算を消費・更新しない。

小数部は固定桁上限を追加せず、秒と小数文字列を使って丸めず比較する。`as_budget_state()`は既存のmicrosecond精度で全時刻を完全に表せる場合だけ`CompletionWaitState`へ変換する。末尾zeroを除く比較用小数が6桁を超えると`checkpoint_precision_not_supported`で拒否し、元文字列やbytesを変更しない。表記が長くても同じinstantをmicrosecondで表せる場合は変換できる。readerやstateの復元は、実行・保存・archiveの許可ではない。

読取元root/file・ACL・作成時の信頼・履歴の現在性/rollback防止、元の適格待ち開始時刻の真正性、C1/C2の排他・原子的読取/試行前publicationは未実装。整合する偽造/古いcheckpointをreaderだけで検出できるとはしない。実確認前の永続計上と、record後クラッシュ時にも試行を戻さないruntime接続は別途必要である。

## 検証と未完了

### 試行planと模擬保存接続（2026-10-25）

`Common/CompletionWaitAttempt.py`の`prepare_completion_wait_attempt`は元checkpointのexact bytesとreader用の期待scope/現在時計、既存budget helperのログオン・同一account・自同期完了・待ち対象の観測を再検査し、check_dueの場合だけ1試行を加えたcandidate bytesを作る。元の開始時刻/既存履歴の文字列表記を保ち、新しい1時刻だけ現在UTCから追加する。candidateをschema/readerへ再投入し、既存helperのadvanced stateと照合する。欠落/破損からの初期化はしない。

immutable planの`expected_bytes`は元bytes、`proposed_bytes`は7fieldの新bytes、`attempt_number`は追加後の回数である。いずれも内部metadataでschemaを拡張しない。`may_check`/`may_archive`/`may_change_state`は常にfalse。planは保存・確認を実行せず、履歴の真正性や時計/所有権を認証するものではない。 観測は計画時点に限るため、正式writerはpublication/確認の使用点で最新の時計・資格・scopeを独立に再検査し、古いplanだけで確認へ進めない。

[接続試験](../../../tests/test_completion_wait_attempt.py)は専用OS-temp内で実Windows mutex＋owner recordと、既存のcreate-only原子的公開helperを使ってcandidateをstagingする。そのbytesを再読込・検査後、**メモリ上の模擬compare-and-publish**がexpected bytesとの一致を再確認し、模擬checkpointを更新する。さらに新bytesの再読込が一致した後だけ模擬確認回数を増やす。このfixture APIや命名はruntime契約ではない。

stagingの`already_exists_identical`はcheckpoint更新のreceiptではなく、stale planによる再確認を許可しない。保存前の失敗/競合では元checkpointを保持し、保存後の応答喪失や読取不一致では確認へ進めず、計上済み試行を戻さない。模擬確認失敗も消費し、次の確認には元の期限内で1時間以上を要する。

実checkpointの比較更新provider、trusted read/root/ACL/FS資格、正式scopeと実ownerのbinding、実確認前のdurable publicationは引き続き未実装。create-only helperには既存checkpointのatomic replacement能力がないため、無条件os.replaceによるwriterを追加しない。上の試験はstagingファイルだけを実公開し、checkpoint自体の更新はmockである。障害注入はfixtureの例外であり、実process再起動・電源断・target FS耐久性を証明しない。C3の実回復や旧run再利用も認可しない。

### 使用点検査とproviderの資格境界（2026-10-25）

`inspect_completion_wait_attempt_usepoint`は同じmoduleの純粋検査で、plan・現在観測したbytes・phase、別入力のscope/現在UTC/実行条件と明示boolのAC接続状態を要求する。既存artifactのfield/versionは変えない。

| phase | 検査 | 検査だけでは証明できないもの |
| --- | --- | --- |
| `before_commit` | 観測bytesがexact expected bytes、candidateが元の1試行planと一致、scope/clock/実行条件/ACが整合し、現在が元の24時間期限内 | 読取元・owner/rootの真正性、検査直後の競合を含むcompare-and-publishの保証 |
| `after_commit` | 観測bytesがexact proposed bytes、同じplan/context/AC/期限を再検査 | 新しい一回限りのcommit receipt、同じbytesを再度確認してよい根拠、実readbackの現在性 |

candidateの最終計上時刻で元planを再構成して完全一致を要求し、余分な試行・開始時刻/履歴変更・別形式bytesによる偽装を拒否する。現在時計がcandidateの試行時刻より前なら拒否し、期限ちょうどは整合範囲、1microsecond超過も拒否する。計画時刻を現在時計として再利用せず、使用点ごとに新しい観測を渡す。

結果は固定metadataの`requires_runtime_evidence`で、全may_*はfalse。反復して同じ結果が出てもreceiptや確認許可にはならない。保存前のAC/資格喪失はcheckpoint更新/確認を止め、保存後は確認を止めても計上済み試行を払い戻さない。接続fixtureも両phaseで検査するが、実保存providerは依然mockである。

正式providerは[C1/C2](../../archive/decisions/osd-02-crash-concurrency-options.md)と[FS資格](../../validation/target-filesystem-acceptance.md)を満たし、真正で現在のread・実owner/scope binding・実効ACL/祖先/使用点・原子的比較更新・確認可能なcommit/readbackを実証する必要がある。使用点検査と置換の間にも変更が入り得るため、単なる再読込＋無条件renameを保証の代わりにしない。実API/実root/電源断耐久性は未資格。観測flagの真偽だけで資格を作らず、AC切断時のin-flight中断/結果不明処理や計画から実確認までの時間の結び付けも本helperでは確定・実装しない。

既存16件の予算helper合成テストでは25回の全履歴、期限前後、遅れ・間隔、少ない機会での期限、再構成、scope/時計/資格不明、履歴破損、失敗試行、不変性/IOなし、最大日時境界を確認。
既存の純粋予算試験はDrive API・OS clock・task・待機・予約・書込を使わない。追加の接続fixtureの書込も専用合成領域のstagingに限り、runtime/STORE/P0/Tier B受け入れには数えない。

追加の[reader試験](../../../tests/test_completion_wait_checkpoint.py)はschema・元bytes/文字列・精度境界・scope/時計・25回/24時間・破損/IOなしと既存helper接続を合成検証する。次に必要なのは信頼できる保存/読取provider・原子更新と、最新manifest/Drive確認の統合である。

## 実Win32 APIの負例probe（2026-10-25）

[比較更新providerの資格調査](checkpoint-compare-provider-qualification.md)に一次資料と隔離実験をまとめた。tests専用probeはdeny-write/delete handle下の置換失敗と、handle解放後の成功、使用点検査/実mutex後にも非協調操作の更新を古いcandidateが上書きできる反例を確認する。実APIを使うが保存先は自作OS-temp fixtureに固定し、正式provider/実root/FS資格へ昇格しない。

## AC電源観測との接続（2026-10-25）

[読取専用Windows AC観測](power-status-observation.md)を追加した。使用点ごとに取得する`ac_connected`がTrueの場合だけ既存検査へ進め、False/Noneは拒否する。合成接続試験は切断/不明時にも元planと計上試行を戻さないことを確認する。単発のAC観測は継続監視・確認receiptではなく、保存後の再接続だけで実確認を再実行しない。in-flight停止境界・実provider/task統合は引き続き未完。
