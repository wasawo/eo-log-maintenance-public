# 回復用owner証拠 v2 の設計契約

状態: v1保全・v2対象の互換方針は利用者承認済み。以下は実装前の論理契約であり、正式JSON Schema・OS provider・writerは未実装。
根拠: [承認記録](../decisions/recovery-owner-evidence-v2-proposal.md)、[診断設計](explicit-recovery-command-design.md)。

## 1. 互換性と非認可

回復用validatorはv1を診断・保全に分類し、自動変換・推測補完・旧record変更を行わない。
v2は取得時に必要証拠を収集できた新規recordだけを対象とする。未知version/重複key/未知fieldは拒否する。
現行v1 writer・reader・正常releaseの挙動を変更しない。移行・配布・旧record対応は別の実装単位とする。
証拠が適合しても、旧lock変更・新run開始・Drive操作・archiveの認可にはならない。

## 2. 必要な論理情報と出所

| 情報 | 要求する意味と出所 |
|---|---|
| versionとscope | 回復対象のsupported record版、承認済み端末/maintenance scopeへの一致。任意pathや入力PIDでscopeを選ばない |
| ownership token | 取得時に生成した新しい秘密値。現ownerに関するtoken一致は、旧ownerの終了証拠の代用にしない |
| 端末/起動のidentity | record作成時と観測時のOS環境を結ぶ、資格確認済みproviderによるidentity。host名や操作者入力だけで同一としない |
| process identity | PIDとOS由来の生成identityの組。PID単独を採用しない。取得時点のprocessとrecordの対応を検証する |
| record snapshot | 原本bytesとSHA-256、scope/root/ファイル同一性観測。hashだけで出所・権限・現在性を証明しない |
| live observation | 同じOS process handleに対するidentity確認と終了/生存/不明の観測。使い捨てのhandle値自体を永続identityにしない |

field名・JSON型・正規化・digest対象・文字列上限は機械可読schemaの単位で厳密化する。
未確定の表現・出所・digest対象と格納位置は[owner-v2判断資料](../decisions/owner-v2-field-binding-options.md)で比較する（未承認）。
端末/起動identityの永続providerは未選定。OS/再起動/複製/権限エラーを扱える証拠なしにはv2生成・回復を進めない。
公開用設定に実identityを追加せず、operatorに手入力を要求しない。生成先・ACL・保持はprivate証拠設計で確定する。

## 3. Windows一次資料から確認した制約

- [Process Handles and Identifiers](https://learn.microsoft.com/en-us/windows/win32/procthread/process-handles-and-identifiers): process handleはcloseまで有効で、PIDの有効範囲はprocessの生存期間に限られる。数値handleを別の実行へ持ち越さない。
- [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes): 生成時刻をFILETIMEで取得でき、問い合わせ権限を要する。未終了processのexit timeは未定義なので、exit time非ゼロだけで終了を判断しない。
- [Terminating a Process](https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process): 終了したprocess objectはsignaledになる。
- [WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject): process handleを待機でき、timeout/failureとsignaledを区別する。待機中のhandle closeは行わない。

これらを組み合わせた設計上の推論として、同一handleからrecordに対応する生成identityを検証し、そのhandleのsignaledを確認する経路を最初の候補とする。
生成時刻だけで任意の敵対的改変・再起動をまたぐ完全なidentityが証明されるとはしない。
handleの取得・identity照合・観測・closeの寿命を一つのprovider操作として検証する。実providerはまだ実装しない。

## 4. 判定表

全行で、mutex保持、root/recordの出所・scope・同一性、providerの資格が成立していることを別途要求する。

| 観測 | owner状態 | 回復への扱い |
|---|---|---|
| v1、未知版、証拠不足/破損 | unsupported/unknown | 診断・保全または拒否。変換しない |
| 端末/起動が不一致または不明 | unknown | 推測で終了としない。別途の再起動証拠方式ができるまで停止 |
| 対応を確認した同一process handleが非signaled | live | 停止。強制終了・lock奪取をしない |
| 対応を確認した同一process handleがsignaled | termination_observed | owner終了の部分証拠としてのみ供給。最新manifest/Drive/disposition等の別ゲートを省略しない |
| 現PIDの生成identityが異なる | mismatch/unknown | PID再利用を検出しても、それだけで旧recordを処分しない |
| PIDなし、Open/query不能、Access denied、provider failure | unknown | 不在/失敗を終了証明にしない |
| mutex abandonedのみ、古い時刻、操作者の「終了した」申告 | unknown | 終了証拠へ昇格させない |
| 取得中/診断後のrecord変更 | changed | 当該計画を破棄し保留。古いsnapshotを変更許可にしない |

この契約は「すべての終了済みprocessを回復できる」ことを保証しない。
process handleを失った後や再起動後は、この初期候補で終了証拠を得られず停止する場合がある。
その場合の回復範囲を広げるには、別の資格確認済み証拠方式と検証が必要。推測で穴埋めしない。

## 5. 副作用と秘密情報

owner証拠の収集は対象processの終了/制御、権限昇格、credential取得、旧recordの更新を行わない。
必要最小限のquery/waitの権限を使う方向で、実API契約・権限・close失敗を実装時に検証する。
公開診断は固定reasonだけとし、token/host/PID/生成時刻/端末・起動identity/実パス/raw例外は出さない。
private原本bytesは[承認済みの非公開保管方針](../decisions/recovery-private-evidence-policy-proposal.md)に従い、maintenanceLocal内で保全し自動削除しない設計とする。具体的な[保存・検証契約](recovery-private-evidence-contract.md)は実保存・ACL変更・旧record処分を許可するものではなく、これらの実装と受け入れは未完了。

## 6. 実装前の試験契約

OWNER-01: v1/未知版/不足/重複key拒否とbytes保全。
OWNER-02: 対応するlive process、対応する終了process、別生成identity、PIDなしの区別。
OWNER-03: 端末/起動不一致・provider不明・権限拒否・query failureをunknownに維持。
OWNER-04: 同じhandleの生成identity照合とsignaled判定、途中close防止、全例外経路close。
OWNER-05: record/token/scopeの差し替えとsnapshot後変更を検出し、旧計画を認可にしない。
OWNER-06: 公開出力・通常例外に秘密値を出さず、対象record/manifestを変更しない。

未実行。合成providerから着手し、実OS試験は自分が作成した合成子processだけに限定する。
既存の実mutex子process終了試験はowner providerの実装証拠には流用しない。
