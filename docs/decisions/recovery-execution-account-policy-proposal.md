# 実行accountとprivate証拠アクセス方針（判断案）

状態: 各PC内で手動と将来taskを同一accountにする方針は利用者承認済み（2026-10-23）。task/ACL/実設定は変更しない。
関連: [private証拠保存契約](../design/recovery-private-evidence-contract.md)。

## 承認された運用前提

推奨は、各PC内で手動実行と将来のscheduled taskを同じWindows accountで行う前提で設計すること。
PC-AとPC-Bが互いに同じaccountである必要はない。
診断・同期・将来の明示回復・private証拠へのアクセスを、そのPCの対象実行accountと必要な管理者に限定する設計とする。
private原本にtoken等が含まれ得るため、別のtask専用accountを使う場合は共有を自動で広げない。

新しい手入力設定は増やさず、identityは実行環境から取得・照合する方向。自動昇格・credential保存・ACL自動書換えは含めない。
この方針への承認はtask登録・本番操作・ACL変更やdispositionを許可するものではない。
OSD-08のtask時刻/条件/再試行などの残決定も完了扱いしない。

## 利用者判断（2026-10-23）

「各PC内では手動と将来タスクを同一アカウントにする（推奨）」を選択した。
同じ方針を再確認しない。PC-A/B同士が同じaccountである必要はなく、task登録やACL変更・昇格を許可するものでもない。
実行identityは将来の資格確認済みproviderでtokenから検証する。ユーザー名・SIDの手入力は追加しない。
具体化した[限定file ACL形状の契約](../design/private-evidence-acl-profile.md)を参照。
