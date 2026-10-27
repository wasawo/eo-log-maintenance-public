# ㉙〜㉜の比較案（2026-10-24）

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

状態：利用者の第9回回答で29A、30aA/bA/cA、31aA/bA、32aA/bAを採用済み。第10回指示に基づく[実装由来の限定4件](implementation-grounded-four-decisions-20261024.md)は別に固定した。Bは未採用の比較履歴として保持する。㉒〜㉜の回答と確定範囲は[決定記録](selected-policy-decisions-20261024.md)を参照。以下のA/Bはこの資料内の識別子であり、他の既承認A/Bを変更しない。選択は実装・PR/マージ・実接続・本番適用の許可ではない。

## ㉙ 永続run状態と遷移履歴

共通：承認済みmanifestがrun結果の正本。C1の同一directory temp/検証/atomic publication/compare-before-replace、C2のmutex＋owner record、C3のcrash-left履歴保全と明示回復後の新run、C4の一意latestを維持する。SQLite等への正本置換やmanifest v1への未知field追加は候補にしない。

| 選択 | 保存方式 | 利点 | 費用・制約 |
| --- | --- | --- | --- |
| 29A | manifest＋別versionの補助checkpoint。checkpointは確認回数・次回確認予定・処理位置等の補助で、成功や安全性の独立根拠にしない | 正本を一本に保ち、追加保存を絞れる | 全遷移の履歴再現には不足し得る。不一致・欠落では補完せず保留。実行中の遷移文脈をどこまで検証/保存できるかを設計する |
| 29B | 上記に加え、別versionの追記専用遷移履歴。manifestと履歴の対応・順序を検証する | pendingの二つの意味や処理順序を追跡しやすい | 複数保存物間のcommit順序・途中書込み・不一致処理が増える。履歴単独から成功や旧run続行を認可しない |

選択は保存モデルまで。field集合・sequence/対応識別・永続確認予算・AC切断/停止境界・crash点ごとの期待値は契約表として後で提示する。atomicityと電源断耐久性は別に資格確認する。29Aで必要な遷移検査を満たせない場合は実装で省略せず判断へ戻す。

根拠：[crash/concurrency](osd-02-crash-concurrency-options.md)、[状態遷移](../../design/manifest-state-transition-v1-proposal.md)。

## ㉚ Drive adapterの通信契約

三つを別々に回答する。Desktop OAuth/drive.fileは既決であり再選択しない。すべてPython内部retry・自動page進行・隠れた追加呼出しを無効化/検証し、PowerShellの最大4回・1/5/15分待機と全page制御を維持する。token refreshの通信も隠さず別に設計する。

| 判断 | A | B |
| --- | --- | --- |
| 30a 通信実装 | Google公式Python clientを使用。SDKの暗黙通信・retry/page挙動を調査/固定する | HTTP clientからRESTを明示呼出し。通信単位を管理しやすい一方、変換・エラー処理の自前実装が増える。OAuthを自作する意味ではない |
| 30b upload | 初期はmultipart、5 MB以下に限定し超過はupload前に保留。容量制限を製品要件として明示する | resumableを設計し大きなfileも対象にする。開始・chunk・照会をPSが制御できるIPC/試行単位の追加契約が必要 |
| 30c retryable | 固定codeごとの厳格な真偽表。TRANSIENTだけtrue、他はfalseを候補とし、upload結果不明時はtrueでも照合前の再送禁止 | 固定code＋closedな理由分類で真偽を決める。TRANSIENT内の再試行禁止等を細分化できるが、理由enumと対応表の追加契約が必要 |

30cの両案ともOPERATION_TIMEOUTは自動再送を許可せず、結果不明のまま失敗確定へ変更しない。unknown code/真偽矛盾は拒否。Bも既承認の認証・権限・不正request・検証失敗・競合の自動retry禁止を緩めない。Googleの一般的なbackoff例を採用する選択ではない。

Google公式はmultipartをmetadata付きの小容量file（5 MB以下）の単一request、resumableを大容量/中断に対応する方式として説明する。[upload仕様](https://developers.google.com/workspace/drive/api/guides/manage-uploads)。30b-Bは現行の1 API試行契約へそのまま接続可能とは確認していない。どちらもSDK資格・file sizeの正確な境界・タイムアウト・応答喪失の合成検証が必要。

根拠：[PS/Python契約](../../design/powershell-python-contract.md)。

## ㉛ package manifestと移行手順

PC別・version別の明示列挙、deny-by-default、PC-B archive除外、秘密/実設定非同梱、通常更新の実設定保持は既決。

| 判断 | A | B |
| --- | --- | --- |
| 31a manifest形式 | strict JSON＋JSON Schema。既存JSON検証の構成へ合わせる | YAML＋制限したparser/同等schema検査。編集はしやすいが型解釈・重複key・tag等の拒否規則と依存が増える |
| 31b 設定移行の入口 | 専用PowerShellコマンド：移行元/先version・backup・差分を提示し、明示確認後に実行 | version別の手動手順：backup・編集・差分・検証を利用者が実施し、通常更新と分離 |

どちらも欠落必須file/未知file/role違いを拒否する。31aのfield名、digest、必須/任意の扱い、実file一覧は後で契約表を提示する。31bの具体mapping・失敗時原本保全・復旧手順は別に確定し、今回実移行しない。

根拠：[配布設計](../../release/distribution-design.md)。

## ㉜ ローカル通知と再通知

画面通知＋状態表示/ログは既決。外部mail/メッセージ、原本/token/raw例外の露出、通知失敗による成功扱いを含めない。Dry Run Aでは永続状態/ログ/通知記録を新設しない。

| 判断 | A | B |
| --- | --- | --- |
| 32a 画面通知 | Windows App SDKのローカルapp通知用helper。通知API/登録/配布依存の資格確認が必要 | WinForms NotifyIconのballoon通知用helper。icon/message loop/寿命・対象PS/.NET環境の資格確認が必要 |
| 32b 再通知 | 同一の未解決事象は初回だけ画面通知し、状態変化/悪化で再通知。状態/ログでは継続表示 | 左記に加え、未解決の事象を次の通常実行時にも再通知。画面通知量は増える |

共通の詳細候補：事象のscope＋分類を対応付け、機密値を公開通知へ出さない。通知送信結果と処理結果を別に保持し、「API呼出し成功」を人が読んだ証拠にしない。重複抑制key・状態の保存場所・通知helperの上限時間/終了条件は未確定。32bは追加のwake/task/外部送信を作らない。

Microsoftは新しいdesktop app向けのAppNotificationManagerを説明する。[通知API比較](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/)。NotifyIcon.ShowBalloonTipはtaskbarのballoonを表示するAPIである。[NotifyIcon仕様](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.notifyicon.showballoontip?view=windowsdesktop-9.0)。これらの存在は本repoのPS環境への適合や表示到達を保証しない。

## 残る別ゲート

㉕の4操作全体のfield表、㉖の具体保護API/配置/ACL/lifecycle、㉗のowner-v2 field契約/provider、㉘のCI配布identity/認証/provenanceは今回の比較表から自動確定しない。合成検証と、実folder/両PCroot/FS/耐久性等の対象限定実検証も区別する。今回の確認はrootの自己点検で、独立レビューではない。
