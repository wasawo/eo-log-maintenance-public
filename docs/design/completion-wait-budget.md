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
helperは新しい予算を自動作成・リセットしない。明示再開、新runとfresh inventory、通知、永続schema、正式task/毎時確認との接続は別の作業。

## 検証と未完了

16合成テストで25回の全履歴、期限前後、遅れ・間隔、少ない機会での期限、再構成、scope/時計/資格不明、履歴破損、失敗試行、不変性/IOなし、最大日時境界を確認。
完了記録・Drive API・OS clock・task・待機・予約・書込は使わない。runtime/STORE/P0/Tier B受け入れには数えない。

次に必要なのは予算の信頼できる永続化/読取・原子更新と、最新manifest/Drive確認の統合。再開指示までは着手しない。
