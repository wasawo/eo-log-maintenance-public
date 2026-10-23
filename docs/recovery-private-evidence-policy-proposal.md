# 回復証拠の非公開保管方針（判断案）

状態: 利用者判断待ち。保存コード・ACL変更・実設定変更・回復操作は未実装。
関連: [owner証拠契約](recovery-owner-evidence-v2-contract.md)、[明示回復設計](explicit-recovery-command-design.md)。

## 判断する運用方針

推奨は、各PCの既存maintenanceLocal配下の非公開領域に、旧lock原本bytesと診断/回復の証拠を保全する方式。
新しい実パスの手入力は増やさず、設定のmaintenanceLocalから導出する。具体subdirectory/schemaは別途厳密化する。
原本にはownership tokenやhost/process情報が含まれ得るため、Git・配布package・共有Drive・公開診断には出さない。
診断だけでは保存しない。将来の別の明示操作で保存する際にも、安全ゲートを必要とする。

## 推奨する保持とアクセス

- 保存先は共有/sync領域と分離し、対象実行accountと必要な管理者以外のアクセスを許さないACLを検証する方向。
- 継承や利用者が異なる実行accountの扱いは実装時に検証する。ACLを勝手に書き換えて安全と推測せず、資格不足なら保存/変更を停止する。
- 原本はcreate-if-absent・bytes/digest照合で保全し、衝突・途中失敗・再試行でも既存証拠を上書きしない。
- 当面、自動期限切れ/自動削除/自動ローテーションを設けない。容量や整理が必要になった場合は別の明示的な運用手順を定める。
- 公開可能な診断は固定reasonと対象role/期間などに限定し、private証拠原本の添付を求める通常手順は設けない。

この承認は保管方針の承認だけで、旧lockの削除/退避/引継ぎ、原本の実保存、本番導入、source/Drive/archive操作を許可しない。
保存schema、ACL実装、対象固定、disposition protocol、中断/再実行は引き続き未実装・要検証。

## 選択肢

1. 推奨: maintenanceLocal内で原本を非公開保全し、当面は自動削除なしの方針で設計を進める。
2. 原本の保管範囲・アクセス主体・保持期間を先に個別に検討する。
