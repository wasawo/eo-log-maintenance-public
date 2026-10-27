# Windows AC電源の読取専用観測

2026-10-25。[承認㉓A](../../archive/decisions/selected-policy-decisions-20261024.md)の「両PCともAC接続時のみ」を支える[helper](../../../Common/PowerStatusObservation.py)。正式task/runtimeや実行許可は実装しない。

## APIと結果

[GetSystemPowerStatus](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getsystempowerstatus)は成功時に非zero、失敗時にzeroを返す。[SYSTEM_POWER_STATUS](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-system_power_status)のACLineStatusは0=offline、1=online、255=unknownである（一次資料確認2026-10-25）。

`observe_ac_power()`は引数なしで一度だけWindows APIを呼ぶ。呼出間でcacheせず、import時の照会・loop・sleep・wake・file/network操作は行わない。native構造体はBYTE×4/DWORD×2の12bytesで、ABIを明示する。

| 観測 | ac_connected | reason_code |
| --- | --- | --- |
| API成功、ACLineStatus=1 | True | power_ac_connected |
| API成功、ACLineStatus=0 | False | power_ac_disconnected |
| 255または未定義値 | None | power_status_unknown |
| DLL load/照会失敗 | None | power_query_failed |
| Windows以外 | None | power_platform_unsupported |

電池の有無・充電flag・残量からACを推定しない。失敗時のzero初期化bufferをoffline/onlineと判定しない。結果はimmutableで、raw例外・OS error・電池情報を露出せず、may_start_run/may_check/may_archiveは常にfalse。結果object自体のtruthinessを資格判定にせず、利用側は`ac_connected is True`を要求する。

## 使用点と限界

[既存使用点検査](completion-wait-budget.md)へ毎回新しい`ac_connected`を渡す。False/Noneは保存前・保存後とも拒否される。保存後の切断/不明でも計上済み試行を戻さない。再接続して検査が通っても一回限りreceiptや再確認許可にはならない。

これは瞬間的なOS申告で、取得後の切断を防止/監視しない。時計・ログオン・同一account・checkpoint read/write・一回限り確認の資格を証明しない。通知購読、AC切断時のin-flight中断/結果不明照合、task設定とruntime統合は未決/未実装のまま。

[試験](../../../tests/test_power_status_observation.py)はmock ABI/成功/不明/失敗/未対応OS、各phaseの合成AC変更と元plan不変を検証する。Windowsでは読取専用の実APIを一度照会するが、端末の電源構成や切断を変更せず、実機の抜き差し・両PC運用受け入れを代替しない。実ログ・本番Drive・credentialには触れない。
