# Drive再試行のPS側観測

Uploadの提示manifest履歴については[履歴側のfile別4回上限](manifest-transition-inspection.md#提示履歴のupload試行上限)も検査する。ready→pending/unknown→pending境界の過剰記録を拒否する純粋検査であり、PSの実counter/待機・API送信やunknown不在照合の実装ではない。

2026-10-25。[PS/Python契約§7](../powershell-python-contract.md#7-再試行と冪等性)と[固定retryable表](../../archive/decisions/implementation-grounded-four-decisions-20261024.md)を、既存の[PS ヘルパー](../../../Common/DriveResponseSemantics.ps1)へ接続する。正式orchestrator、sleep、API呼出しは実装しない。

`Get-DriveRetryObservation`は実request由来の期待ID/operation、decoded response、整数exit、**完了した試行番号**（初回=1、最大4）を受け取る。番号はint/long/BigIntegerの1〜4だけを許し、bool/小数/文字列/欠落を暗黙変換しない。既存`Test-DriveResponseSemantics`を毎回呼び、相関・exit・envelope・固定retryable表の矛盾を拒否する。

| 条件 | Status / ReasonCode | 次番号・待機秒 |
| --- | --- | --- |
| 番号不正 | 拒否されました / retry_attempt_invalid | null / null |
| 応答整合不成立・応答喪失 | 拒否されました / retry_response_invalid | null / null |
| 整合した成功envelope | no_retry / retry_response_success_requires_validation | null / null |
| OPERATION_TIMEOUT | reconciliation_required / retry_timeout_outcome_unknown | null / null |
| その他の非一時的失敗 | no_retry / retry_error_not_transient | null / null |
| upload_fileの一時的失敗 | reconciliation_required / retry_upload_outcome_unverified | null / null |
| その他3操作の一時的失敗、4回目 | 疲れ果てました / retry_attempt_limit_reached | null / null |
| list/metadataの一時的失敗、1〜3回目 | 対象候補 / retry_candidate_requires_runtime_evidence | 2/60、3/300、4/900 |
| downloadの一時的失敗、1〜3回目 | 対象候補 / retry_candidate_requires_fresh_staging | 2/60、3/300、4/900 |

待機秒は直前の失敗後に必要な最小待機で、経過済みとは判定しない。4回後に5回目を返さない。uploadは一時的失敗でも作成結果を確定できないため候補にせず、照合済みboolによる解除経路も追加しない。4回目のupload/timeoutでも結果照合は残るが、照合結果から追加試行を作るものではない。

出力は表の固定Status/ReasonCode、AttemptNumber、NextAttemptNumber、DelaySeconds、**MayRetry=false**だけ。入力を変更せず、raw response/message/ID/pathを返さない。candidateはretry許可ではなく、成功envelopeも操作固有resultの正しさや処理成功の証明ではない。整合検査では未知field等のschema不適合すべてを検出できないため、transport/UTF-8/単一JSON/重複key/schema検査を省略しない。

実counter/期待request/scopeのbinding、予算の永続化・再起動時の扱い、待機時間の信頼できる計測、使用点でのAC/session/account等、downloadの新規/空stagingとサイズ/hash検証、現在Drive内容の完全な照合は正式orchestratorの未実装gateである。毎回番号1を渡せば実予算が守られるという保証はなく、helperに自動リセット・sleep・送信・成功skipを追加しない。Python/SDKの暗黙retry禁止も別途検証を要する。

[合成試験](../../../tests/Test-DriveResponseSemantics.ps1)は4操作×1〜4回×全error、成功、retryable矛盾、非整数/範囲外番号、相関不一致・応答欠落、入力不変・秘密非echo・副作用command不呼出しを検証する。RETRY-02全体、C-02、IPC/runtime受け入れは未完了のまま。
