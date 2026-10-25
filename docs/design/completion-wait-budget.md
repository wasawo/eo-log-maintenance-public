# PC-A確認予算の分離実装

状態: 24時間・初回含め25回の上限は利用者承認済み。補助checkpointの[最小field契約](../decisions/implementation-grounded-four-decisions-20261024.md)も限定確定した。純粋な判定/履歴更新helperであり、待機task・永続保存・archive認可ではない。
根拠: [承認記録](../decisions/pc-a-completion-wait-budget-proposal.md)。

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

[schema](../../contracts/completion-wait-checkpoint-v1.schema.json)は承認済みの7fieldだけを持つclosed v1で、manifestとは別契約。PC-A限定、log種別ごとのperiod形、UUID、UTC Z、0〜25回を規定する。periodの4桁年に未決の範囲制約を追加しない。

`Common/CompletionWaitCheckpoint.py`の`read_completion_wait_checkpoint`は、callerが供給するexact bytes・信頼済みstatic schema、別入力の期待log/period/run IDと信頼できる現在UTCを要求する。I/Oをせず、未知/欠落/null field、重複JSON key、不正UTF-8/JSON/version、schema外部参照、scope不一致、不正日時、開始〜24時間外の試行、1時間未満の間隔、25回超、現在時計の逆行を拒否する。読取不能や欠落の代わりに空履歴を生成しない。現在が期限後でも有効な元履歴を保持し、既存予算helperで期限/回数のhold判定を行う。

結果はimmutable `CompletionWaitCheckpoint`で、元の時刻文字列と配列順をtupleとして保持する。`original_bytes`はexact入力を結び付ける内部metadataで、保存schemaの追加fieldではない。戻り値のreprと固定error reasonに内容を露出せず、readerは予算を消費・更新しない。

小数部は固定桁上限を追加せず、秒と小数文字列を使って丸めず比較する。`as_budget_state()`は既存のmicrosecond精度で全時刻を完全に表せる場合だけ`CompletionWaitState`へ変換する。末尾zeroを除く比較用小数が6桁を超えると`checkpoint_precision_not_supported`で拒否し、元文字列やbytesを変更しない。表記が長くても同じinstantをmicrosecondで表せる場合は変換できる。readerやstateの復元は、実行・保存・archiveの許可ではない。

読取元root/file・ACL・作成時の信頼・履歴の現在性/rollback防止、元の適格待ち開始時刻の真正性、C1/C2の排他・原子的読取/試行前publicationは未実装。整合する偽造/古いcheckpointをreaderだけで検出できるとはしない。実確認前の永続計上と、record後クラッシュ時にも試行を戻さないruntime接続は別途必要である。

## 検証と未完了

### 試行planと模擬保存接続（2026-10-25）

`Common/CompletionWaitAttempt.py`の`prepare_completion_wait_attempt`は元checkpointのexact bytesとreader用の期待scope/現在時計、既存budget helperのログオン・同一account・自同期完了・待ち対象の観測を再検査し、check_dueの場合だけ1試行を加えたcandidate bytesを作る。元の開始時刻/既存履歴の文字列表記を保ち、新しい1時刻だけ現在UTCから追加する。candidateをschema/readerへ再投入し、既存helperのadvanced stateと照合する。欠落/破損からの初期化はしない。

immutable planの`expected_bytes`は元bytes、`proposed_bytes`は7fieldの新bytes、`attempt_number`は追加後の回数である。いずれも内部metadataでschemaを拡張しない。`may_check`/`may_archive`/`may_change_state`は常にfalse。planは保存・確認を実行せず、履歴の真正性や時計/所有権を認証するものではない。 観測は計画時点に限るため、正式writerはpublication/確認の使用点で最新の時計・資格・scopeを独立に再検査し、古いplanだけで確認へ進めない。

[接続試験](../../tests/test_completion_wait_attempt.py)は専用OS-temp内で実Windows mutex＋owner recordと、既存のcreate-only原子的公開helperを使ってcandidateをstagingする。そのbytesを再読込・検査後、**メモリ上の模擬compare-and-publish**がexpected bytesとの一致を再確認し、模擬checkpointを更新する。さらに新bytesの再読込が一致した後だけ模擬確認回数を増やす。このfixture APIや命名はruntime契約ではない。

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

正式providerは[C1/C2](../decisions/osd-02-crash-concurrency-options.md)と[FS資格](../validation/target-filesystem-acceptance.md)を満たし、真正で現在のread・実owner/scope binding・実効ACL/祖先/使用点・原子的比較更新・確認可能なcommit/readbackを実証する必要がある。使用点検査と置換の間にも変更が入り得るため、単なる再読込＋無条件renameを保証の代わりにしない。実API/実root/電源断耐久性は未資格。観測flagの真偽だけで資格を作らず、AC切断時のin-flight中断/結果不明処理や計画から実確認までの時間の結び付けも本helperでは確定・実装しない。

既存16件の予算helper合成テストでは25回の全履歴、期限前後、遅れ・間隔、少ない機会での期限、再構成、scope/時計/資格不明、履歴破損、失敗試行、不変性/IOなし、最大日時境界を確認。
既存の純粋予算試験はDrive API・OS clock・task・待機・予約・書込を使わない。追加の接続fixtureの書込も専用合成領域のstagingに限り、runtime/STORE/P0/Tier B受け入れには数えない。

追加の[reader試験](../../tests/test_completion_wait_checkpoint.py)はschema・元bytes/文字列・精度境界・scope/時計・25回/24時間・破損/IOなしと既存helper接続を合成検証する。次に必要なのは信頼できる保存/読取provider・原子更新と、最新manifest/Drive確認の統合である。

## 実Win32 APIの負例probe（2026-10-25）

[比較更新providerの資格調査](checkpoint-compare-provider-qualification.md)に一次資料と隔離実験をまとめた。tests専用probeはdeny-write/delete handle下の置換失敗と、handle解放後の成功、使用点検査/実mutex後にも非協調操作の更新を古いcandidateが上書きできる反例を確認する。実APIを使うが保存先は自作OS-temp fixtureに固定し、正式provider/実root/FS資格へ昇格しない。
