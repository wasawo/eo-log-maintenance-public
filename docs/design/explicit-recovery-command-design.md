# 明示回復コマンドの設計契約

状態: 2026-10-23の承認済み入口方針を具体化する設計。実行コマンドは未実装。
承認の根拠: [入口方針と利用者回答](../archive/decisions/recovery-disposition-proposal.md)。
関連: [OSD-02 C2/C3/C4](../archive/decisions/osd-02-crash-concurrency-options.md)、[復旧ゲート](../validation/lock-recovery-acceptance-gate.md)、[正式入口ゲート](runtime-entrypoint-validation-gate.md)。

## 1. 入口と責務

PowerShellを制御主体とする専用コマンドを、通常同期とは別に設計する。
名称案は `Invoke-ExplicitRecovery.ps1`。名称だけで実装済みと扱わず、`scripts/`の正式入口・配布allowlistへはまだ追加しない。
当初のモードは `Diagnose` だけとし、省略時も同じ読み取り専用診断・計画表示とする。
将来の状態変更は別の明示操作として設計する。診断成功、確認応答、古い計画ファイルの指定で自動的に変更へ遷移しない。
未実装の変更モード、未知の引数・enum・設定versionは観測開始前に拒否する。

入力は既存実設定の参照と対象PC/ログ種別/期間。scopeは検証済みPCと承認済み管理領域の対応から決める。
任意のlock path/token、PIDだけの終了指定、`Force`や「古いので回復する」指定は提供しない。
実設定は生成・移行・修正しない。example/dummy設定は運用領域の承認にならない。
PC-A/PC-Bとも診断だけを同じ境界で扱い、PC-Bにarchive入口や権限を追加しない。

## 2. 診断で許す観測

1. 引数と設定構造を副作用なしで検証する。
2. 既存rootのmetadataを検査し、別途承認されるroot権限・FS資格を照合する。不成立なら対象のlock/manifest列挙へ進まない。
3. 同じmaintenance scopeのOS mutexを上限60秒の待機で取得する。取得不可なら対象列挙前に停止する。診断ではownership recordを作成しない。取得・release・closeはfinally経路で保証する。
4. mutexを保持した区間で既存lockの構造・同一性を読み取り、信頼できる時計と定義済みPC別領域の最新manifest bytesを観測する。古いsuccessに後退しない。
5. owner終了証拠・未解決upload状態・必要なDrive照合の充足/不足を分類する。診断自身はDrive APIやDrive配下の内容を照合せず、不足を未確認として返す。
6. 結果と不足する条件を秘匿化して標準出力へ返す。保存先や実設定を作らず、mutexを解放して終了する。

この順序は設計上の条件で、既存補助処理だけではまだ成立しない。
現行acquire_owned_lockはrecordを作成するか、abandoned/既存recordで拒否するため、診断用取得として流用しない。
既存NamedMutex低レベル実装を正式な診断lease APIとして公開した扱いにもしない。専用の取得/解放契約と合成試験が必要。

診断は元ログのinventoryを列挙しない。manifest本文は必要な範囲でのみ読み、raw bytes/ファイル一覧/自由文を出力しない。
lockなし・manifestなしを推測で回復可能とせず、通常実行の状態と回復対象欠落を区別して報告する。
未知schema、重複JSONキー、読取失敗、reparse、候補競合、観測途中の変更は保留する。

## 3. 結果と非認可

診断結果の契約案は、version、対象PC/ログ種別/期間、固定reason codeの一覧、`blocked`または`review_required`の分類とする。
通常表示にはtoken、host、PID、実パス、Drive ID/URL、raw manifest/例外本文を出さない。
新しい機械可読schemaは別途実装・検証する。この文書だけで永続disposition schemaを追加しない。
診断完了は状態変更の可否を表す終了コードと混同しない。終了コードの数値・JSON/UI形式は実装時に契約化する。

全結果は「観測時点の診断」であり、変更許可、再利用可能な権限token、新run開始許可ではない。
選択した検証済みbytesを保持して分類し、別path再読取で差し替えない。後の操作時にはmutex再取得・再観測が必要。
既存RecoveryDecision.may_start_new_runのtrueを、診断の`ready`や変更可能フラグへ直結させない。

## 4. 未確定の証拠と状態変更

| 項目 | 現状と要求 |
|---|---|
| owner終了証明 | 現行recordのhost/PID/tokenだけでは永続的process identityを証明できない。PID再利用・再起動・query失敗は不明のまま停止。v1を推測でv2相当に扱わない |
| abandoned通知 | 1回の観測で消費され得る。通知なしは正常終了の証拠でなく、通知ありも終了/所有権の完全証明ではない。診断が観測した後の再実行も試験する |
| root/時刻/FS | 既存metadata helperと渡されたUTCは資格・信頼性の証明を供給しない。契約と実行証拠が必要 |
| 旧lockのdisposition | 元bytesを非公開の管理証拠に保持する方向。保存schema/領域/ACL/保持と、退避または除去の方式は未確定。単なるcompare後unlinkを保証としない |
| 変更対象の固定 | 検証した対象だけへ作用するOS/FS手段と対象volumeの受け入れが必要。競合やunsupportedで停止する |
| 中断/再実行 | 未完了dispositionを黙って成功扱いせず、既存証拠を上書きしない。途中状態ごとの再開可能/要確認を別途設計する |
| 新しい実行 | 全ゲート後も新token/new run_id/fresh inventory/per-file stateを要求。旧runningは不変。ここでは新runを作成しない |

通常の同期を回復コマンドから起動しない。回復完了後の新規同期との関係も、正式入口ゲートの受け入れ後に統合する。
手動でlockを削除する抜け道や、本番操作をこの設計PRで許可する手順は追加しない。

## 5. 実装前の合成試験表

|ID| 条件 | 要求する観測・不変条件 |
|---|---|---|
| DIAG-01 | モード省略/Diagnose | record、manifest、staging、source、Drive、archive、実設定を作成/変更しない。出力に秘匿値を含めない |
| DIAG-02 | 不正引数/設定・未知変更mode | root/対象列挙・mutex取得・API呼出しの前に拒否する |
| DIAG-03 | mutex競合/取得失敗/timeout | 上限60秒以内に停止、lock/manifest/sourceを読まず元bytesを保持する |
| DIAG-04 | mutex取得後に読取/分類/出力失敗 | 所有中mutexを必ず解放してclose。既存recordをcleanupしない |
| DIAG-05 | abandoned通知と診断再実行 | 通知の消費後も旧recordを保全し、通知が消えたことを新しい認可にしない |
| DIAG-06 | live owner/PID再利用/再起動/終了不明 | 推測で回復可能にしない。終了証拠の不足を固定reasonで返す |
| DIAG-07 | malformed/曖昧最新/読取不明 | older successへ後退せず、rawデータ/例外を出さず、元bytesを保持する |
| DIAG-08 | snapshot後に外部変更 | 計画を変更許可に使わず、次の観測で差異を検出し保留する |
| DIAG-09 | 同じ入力で繰返し診断 | 新artifactや新run/token recordを生成しない。Drive/API呼出しもゼロ |
| DIAG-10 | PC-Bと非配布guard | archive/deletion権限と入口を増やさず、正式配布・運用可能へ昇格させない |

いずれも未実行の受け入れ計画。既存221件やCI成功を、この表の実行証拠へ流用しない。

## 6. 次の実装単位

まず合成入力だけの秘匿化された診断結果モデルと、その拒否/表示契約を実装・検証する。
次にrecordを作らない診断用mutex leaseを合成子プロセスで検証し、例外時解放とabandoned通知消費を扱う。
その後にroot/終了証拠/時計と実read接続のゲートを満たす。未確定のdispositionはその前に実装しない。
P0-010/P0-012、Tier B全体、正式復旧・本番導入は未完了のまま維持する。

<a id="7-implemented-result-model-slice"></a>
## 7. 実装された結果モデルのスライス

Common/RecoveryDiagnostic.py は、渡された観測だけから結果を作る副作用のないモデルのみを実装する。8つの明示条件（configuration/root/mutex/lock_record/clock/latest_manifest/owner_termination/drive_reconciliation）にはそれぞれsatisfied/missing/unknown/failedが必要である。欠落・不明なキーや自由文を拒否する。不足時は固定順序の理由とblockedを返し、全条件が満たされた場合は review_required を返す。公開用の投影には schema_version の 1、要求範囲の厳密な値、分類、reason_codes、may_change_state=falseを含める。直接構築・出力時も固定項目を検証する。生の記録、パス、PID、ホスト、トークンは受け付けない。内部ヘルパーのモデルであり、最終コマンドの JSON・終了コードや永続処分スキーマではない。12件の合成試験はこの境界だけを扱い、DIAG-01〜DIAG-10 全体は未完了である。

<a id="8-implemented-record-free-lease-slice"></a>
## 8. レコードフリーのリーススライスを実装

Common/RecoveryDiagnosticMutex.py は、通常の所有権と同じグローバル ミューテックス名を使用して分離リースを追加します。最長 60 秒待機し、ロック レコードまたはトークンの作成/読み取り/変更は行わず、may_change_state=false で放棄の証拠を生成し、例外/割り込みで解放/クローズを試みます。タイムアウト/OS/クリーンアップの失敗には固定の理由があります。リース内の呼び出し元によって発生したエラーは、その呼び出し元によってサニタイズする必要があります。 13 のテストには、実際の Windows 競合、放棄された消費、繰り返しの診断、本体 失敗 後のリリースを証明する別のプロセス プローブが含まれます。これは部分的な DIAG-03/04/05 の証拠にすぎません。ルート/クロック/所有者の証明、ライブ コマンド/出力、完全な DIAG マトリックス、保護された配置、およびランタイムの受け入れは 未完了 のままです。

<a id="9-approved-owner-evidence-compatibility-direction"></a>
## 9. 承認された所有者証拠の互換性の方向性

メンテナは、v1 の診断/保存および v2 のみの将来のリカバリ設計を承認しました。 [論理所有者証拠契約](recovery-owner-evidence-v2-contract.md) は、不明 PID/ブート/クエリのケースをブロックし、同一ハンドル終了の監視と回復の承認を区別します。 v2 スキーマ、プロバイダー、ライター、またはランタイム接続は追加されません。 [私的証拠保全ポリシー](../archive/decisions/recovery-private-evidence-policy-proposal.md) はプライベート メンテナンスとして承認されています。自動削除なしのローカル保存。実際の永続性、ACL の変更、および回復操作は未実装のままであり、そのポリシーだけでは許可されていません。

<a id="10-approved-private-evidence-direction"></a>
## 10. 承認された私的証拠の指示

プライベートメンテナンス自動削除なしのローカル保存が承認されています。 [ストレージ/検証契約](recovery-private-evidence-contract.md) は、メモリ内メタデータ/生バイトのバインディングを、実装されていない ACL で保護された永続性および性質から分離します。診断は持続しないままです。 [実行アカウントポリシー](../archive/decisions/recovery-execution-account-policy-proposal.md) は、手動実行および今後のタスクのために、各 PC 内の同じ Windows アカウントに対しても承認されます。タスク登録、ライブ ID/ACL 認定、およびランタイム統合は 未確定 のままです。
