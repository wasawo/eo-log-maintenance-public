# 実行accountとprivate証拠アクセス方針（判断案）

状態: 利用者判断待ち。account名・SID・資格情報は収集/記録せず、task/ACL/実設定も変更しない。
関連: [private証拠保存契約](recovery-private-evidence-contract.md)。

## 判断する運用前提

推奨は、各PC内で手動実行と将来のscheduled taskを同じWindows accountで行う前提で設計すること。
PC-AとPC-Bが互いに同じaccountである必要はない。
診断・同期・将来の明示回復・private証拠へのアクセスを、そのPCの対象実行accountと必要な管理者に限定する設計とする。
private原本にtoken等が含まれ得るため、別のtask専用accountを使う場合は共有を自動で広げない。

新しい手入力設定は増やさず、identityは実行環境から取得・照合する方向。自動昇格・credential保存・ACL自動書換えは含めない。
この方針への承認はtask登録・本番操作・ACL変更やdispositionを許可するものではない。
OSD-08のtask時刻/条件/再試行などの残決定も完了扱いしない。

## 選択肢

1. 推奨: 各PC内では手動と将来taskを同一accountで設計する。
2. taskは別accountの可能性を前提とし、アクセス主体と権限分離を先に設計する。
