# OSD-08: タスクのログオン方式（判断案）

状態: 初期タスクはログオン中のみとする方針が利用者承認済み（2026-10-23）。タスク登録・資格情報取得・本番実行は未実装。
根拠: [同一account承認](recovery-execution-account-policy-proposal.md)。同一accountであることはログオン方式を確定しない。

## 承認された初期運用

各PCで、対象accountが既にログオンしている場合だけ将来の通常同期タスクを動かす設計とする。
Windowsのinteractive-token方式を候補とし、ログオフ中の実行を初期要件にしない。
ログオフ中に実行しなかった処理を成功扱いせず、次回の実行では通常の新run/fresh inventoryと安全ゲートを適用する。
この判断で、タスク時刻・起動trigger・未実行分の起動時再実行・失敗時retryを勝手に確定しない。

Drive for desktopを使う設計のため、まず通常のユーザーsessionと同じ環境に限定するのが本案の理由。
ログオン中でもDrive/ローカルrootの可視性やクラウド反映を保証しない。実行時に別途検証し、不明なら停止する。
明示回復を通常同期タスクへ組み込まず、資格情報保存・自動昇格・別accountへの切替も追加しない。

## Windows一次資料

[TASK_LOGON_TYPE](https://learn.microsoft.com/en-us/windows/win32/api/taskschd/ne-taskschd-task_logon_type)は、interactive-token方式が既存interactive sessionだけで動作することを定義している。
同資料ではpassword方式は登録時passwordを要求し、S4Uはnetwork/encrypted fileへの制限を持つ。
どの方式ならこのprojectのDrive/auth/root条件を満たすかは別の実装・合成/対象環境検証が必要であり、この文書だけでは保証しない。

## 利用者判断（2026-10-23）

「初期タスクはログオン中のみ（推奨）」を選択した。同じ方式を再確認しない。
ログオフ実行を初期要件とせず、同一accountのinteractive sessionで行う設計とする。
C-24の月次・未実行時の当月初回起動補完・PC-Aの毎時完了確認は維持する。
ログオン方式だけで実行時刻・未実行補完の実装・失敗時retryや本番登録を確定しない。
残る[月次時刻の具体案](task-monthly-schedule-policy-proposal.md)を参照。
