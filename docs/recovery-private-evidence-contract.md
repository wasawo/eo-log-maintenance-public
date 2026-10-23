# private回復証拠の保存・検証契約

状態: 非公開保全と当面自動削除なしの方針は承認済み。実保存・ACL設定・dispositionは未実装。
根拠: [利用者回答](recovery-private-evidence-policy-proposal.md)。関連: [明示回復](explicit-recovery-command-design.md)、[owner v2](recovery-owner-evidence-v2-contract.md)。

## 保存範囲と配置

各PCで検証済みmaintenanceLocalから導出する非共有領域だけを使い、新たな実パス入力を増やさない。
配置設計は `<maintenanceLocal>/_maintenance/recovery-private/<evidence_id>/` とする。
evidence_idは小文字UUID形式。user入力の任意path・元lock filenameを保存先へ連結しない。
この配置を通常manifest候補ディレクトリから分離し、raw証拠をDriveへpublishしない。

1組のファイルは `lock-record.bin`（旧lockのexact bytes）と `evidence.json`（そのbytesに結び付いたメタデータ）。
この証拠組はdisposition完了記録や回復許可ではない。診断だけでは保存しない。
当面、自動削除・期限切れ・ローテーションを追加しない。元lock、旧running、staging、source、Drive、archiveは変更しない。

## メタデータ形式と実装済み範囲

[private-recovery-evidence-v1.schema.json](../contracts/private-recovery-evidence-v1.schema.json) は保存用メタデータの構造のみを定義する。
lock schema v1/v2とは別のversion。version/evidence_id/PC/log/期間/観測UTC/purpose/固定raw basename/bytes数/SHA-256と、常にfalseのmay_change_stateを持つ。
raw token/host/PID/owner identity/実パスや自由文・unknown fieldを含めない。
privateメタデータ自体も公開診断へ自動掲載しない。SHA-256だけで出所・同一性・権限・耐改変を証明しない。

Common/PrivateRecoveryEvidence.pyのbuilder/validatorは、渡されたbytesだけを使いメタデータの生成・strict JSON/UTF-8・重複key・schema・size/digest対応を検証する。
信頼済みrepository/package schemaを読む以外のファイル読取、保存、directory作成、ACL、Drive、削除は行わない。
UTCは構文と暦日を独立検証するが、時計信頼性・現在性は別ゲート。観測IDやscopeも実recordの出所を証明しない。
原本は不正JSON/非UTF-8であってもopaque bytesとして保全できる。保全可能であることはsupported lockや回復対象であることを意味しない。

13合成テストで、秘密値非掲載、同サイズ別原本・切断・version/型/任意path/日時の拒否、曖昧JSON、opaque原本、schema読取失敗の秘匿化を検証する。
原本bytesとメタデータの対応検証だけの証拠で、実保存・ACL・中断耐性やP0/Tier B受け入れの証明ではない。

## 実保存前のACL・rootゲート

既存rootの承認・非共有/非sync・reparse拒否・対象固定に加え、保存先と祖先の実効アクセスを検証する。
対象実行accountと必要な管理者以外が原本を読取/改変できるACLなら停止する。所有者名や継承フラグだけを安全とみなさない。
この契約はWindows全ACLの判定アルゴリズムを完成扱いしない。group membership/deny/継承/別account実行を含む実装検証が必要。
ACLを書き換えて通過させるコードや、例外を無視するfallbackは追加しない。
accountの実名/SIDは公開設定・記録へ出さず、手入力項目も増やさない。

手動とscheduled taskの実行accountが同じか異なるかは未確定。別accountを使う場合、誰が原本を読めるべきかを先に確定する必要がある。
この点の[次の判断案](recovery-execution-account-policy-proposal.md)を用意した。

## 公開順序・中断・再試行（未実装）

1. explicit操作、全安全gate、scope mutexを保持し、原本snapshotと保存先root/ACL/identityを検証する。
2. 新規evidence_idを使い、限定権限の領域で原本をcreate-if-absent公開し、exact bytesを再読取照合する。
3. 対応するmetadataを検証してcreate-if-absent公開する。原本・metadataの両方を再検証して初めて保全組が一致と報告する。
4. metadataなし・片方のみ・余分なentry・不一致・中断は不完全/不明として停止し、残骸や既存原本を自動削除/上書きしない。
5. 同一IDの再試行は、全既存entry・内容・ACL・同一性を検証して同一bytesのみを同一組として扱う。異なる内容・競合・unsupportedなら停止する。

既存atomic helperの成功を、権限付き保存や原本+metadataの原子的transactionの証明にしない。
ACLを安全に持つ新規file/directory作成、既存同一組の判定、中断分類と対象volume受け入れが必要。
保全完了でも旧lockを処分しない。disposition protocolは別途定義し、新token/new runはその後の別ゲートとする。

## 未実行の保存試験

STORE-01: 不正root/ACL/対象identity・別account・権限不足で保存前に停止。
STORE-02: 原本前/途中/公開後/metadata前/後で中断し、不完全を成功にしない。
STORE-03: 同IDの同内容/別内容再試行、別process競合で上書きしない。
STORE-04: raw/metadata/ACL/pathの外部差し替えを再検証で検出し、元lock/manifestを保全。
STORE-05: 診断だけでは保存せず、保存結果も操作許可に使わず、秘密値を公開出力しない。
STORE-06: schemaだけを配布し、運用原本や実メタデータがGit/package/Driveに混入しない。

上記は未実行計画。今回実装したメモリ内の形式・hash照合試験とは区別する。
