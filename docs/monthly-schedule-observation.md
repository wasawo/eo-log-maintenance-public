# 承認済み月次時刻の分離観測

状態: C-24日時・ログオン方式は承認済み。時計等の申告に基づく純粋な観測helperのみ実装。task/正式実行は未実装。
根拠: [承認日時](task-monthly-schedule-policy-proposal.md)、[ログオン方式](task-logon-mode-policy-proposal.md)、[C-24](decision-register-c18-c32.md)。

Common/MonthlyScheduleObservation.pyのobserve_monthly_scheduleは、渡されたUTC日時とreliable/logged_on/same_account_verifiedの明示boolを検証する。
適格な入力からJST（固定UTC+09:00）の当月1日 PC-B 20:00 / PC-A 21:00を計算し、そのUTC値とschedule_month、boundary_reached、固定reasonを返す。
現代のJST運用用であり、Asia/Tokyoの歴史的な夏時間を再現するtimezone databaseではない。

時計がnaive/非UTC/不明・信頼できない、またはログオン/同一accountが未確認なら時刻到達を返さず保留する。
実clock/session/tokenを照会せず、申告flagの真実性は証明しない。入力の異常や暦計算不能は固定reasonで停止する。
ホストtimezoneに依存せず、datetime.nowやI/Oを使わない。

すべての結果でmay_start_run=false。時刻到達は「当月完了記録等の次の観測が必要」という情報にとどめる。
schedule_monthは処理対象ログのtarget_periodではない。ログ保持/対象期間をこのhelperから導かない。
すでに完了済みか、最新の失敗/不明が残るか、未実行か、古い月のbacklogがあるかは判定しない。
同じ入力で繰り返し呼んでもrun/recordを生成しないが、これで二重起動防止を保証しない。mutex/完了記録と別途接続する。

12合成テストは両PCの境界、1時間の間隔、JST月跨ぎ/年跨ぎ/うるう月、遅い月内観測、clock/session/account不明、overflow、不変結果を検証。
実scheduler、月次完了記録、起動時補完、PC-A毎時確認、retry、archiveゲートや本番受け入れの実行証拠ではない。

次の運用判断は[PC-A確認予算](pc-a-completion-wait-budget-proposal.md)。OSD-08全体・P0/Tier B・正式task rolloutは未完了。
