# C-24 / OSD-08: 月次実行日時の具体案

状態: 毎月1日 PC-B 20:00 / PC-A 21:00（日本時間）は利用者承認済み（2026-10-23）。task登録・実稼働・実設定変更は行わない。
根拠: [C-24](decision-register-c18-c32.md)、[ログオン中のみの承認](task-logon-mode-policy-proposal.md)、[同一account承認](recovery-execution-account-policy-proposal.md)。

## 確定済みの条件

- 月次実行と、月内に予定実行を逃した場合の初回起動時補完を維持する。毎日実行へ変更しない。
- PC-A/PC-Bの静かで重ならない時刻を利用者が選ぶ。PC-AはPC-B完了を毎時確認し、無期限に待ち続けない。
- 初期はログオン中のみ、各PC内で手動と同じaccount、通常と同じ安全ゲートを使う。
- ログオフ中の未実行を成功扱いしない。起動後のinteractive sessionで実行可能になった時に未実行を確認する設計だが、具体trigger/retryや状態保存は未実装。
- 月次処理・補完・毎時確認もstale lock回復やarchiveの安全条件を省略しない。時刻どおりに動いたことをクラウド検証やarchive許可にしない。

## 承認済み日時（日本時間 Asia/Tokyo）

- PC-B: 毎月1日 20:00。
- PC-A: 毎月1日 21:00。

1時間の間隔はPC-B完了を保証するものではない。完了・最新manifest・Drive内容等の別gateを必ず検証する。
この日時は設計・合成検証の前提として承認済み。OS taskへの登録や本番実行はまだ行わない。
通常ログオンしていて、処理負荷が支障になりにくい時刻へ変更できる。PC-A/PC-B同時刻は候補にしない。
将来のarchive taskの独立した開始時刻・毎時確認の終了/保留条件、trigger、失敗の可視化、battery/wake等はこの承認だけで完成扱いしない。

## 利用者判断（2026-10-23）

「それでOK」と回答し、毎月1日 PC-B 20:00 / PC-A 21:00（日本時間）の案を承認した。
同じ日時を再確認しない。静かな日時の承認は完了記録・実行許可や本番導入を意味しない。
[予定時刻の分離観測](../design/monthly-schedule-observation.md)と、残る[PC-A確認上限の判断案](pc-a-completion-wait-budget-proposal.md)を参照。
