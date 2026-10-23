# Dry Run A: 実行分岐と副作用境界の設計

- 状態：実装前の具体設計。コード・schema・CIの変更、正式runtimeの実装・受け入れを含まない。
- 根拠：[OSD-04のA承認](../decisions/dry-run-side-effect-policy-proposal.md) §2/4、[PS/Python契約](powershell-python-contract.md) §3–9、[runtime gate](runtime-entrypoint-validation-gate.md)。Aの選択を再質問せず、その範囲で設計する。
- [DRY-01–10](../validation/runtime-safety-test-scenarios.md#10-osd-04-dry-run提案用受け入れfixture計画未実装未実行)は未実装・未実行。OSD-04/P0、Phase 1/7は未完了。OSD-05、C-01/C-02、IPC契約全体のレビューは別ゲートのまま。

## 1. 入口と呼出し順序

将来のPowerShell入口は、次の順でDry Run専用経路を選ぶ。通常経路を開始してから副作用だけを抑制する構造にはしない。現在 `scripts/` に正式入口は存在しない。

1. 明示されたmode、PC identity、操作、入力形状を検証し、未知値とPC-B archive要求を拒否する。PC-Bにarchive入口・能力を配布しない。設定値や `allowArchive` を認可としない。
2. **bootstrap、ordinary run-lock取得、run/state生成、scheduler/budget更新、運用log初期化より前に**Dry Runを分岐する。通常経路の初期化・finally/cleanupへ合流させない。診断correlation/request IDだけをメモリ内で作り、運用 `run_id` を生成・流用しない。
3. 既存の実configを読取り専用で厳密検証する。未作成・無効なら停止し、exampleから生成しない。信頼済みrootの根拠、役割、ACL/所有者/継承、reparse/alias、領域分離、対応FSを検証できない場合も停止する。directory作成・ACL修復で通過させない。
4. §2の資格を満たす場合だけrecord-free診断mutexを取得する。取得失敗・timeout・abandoned・identity/所有状態不明なら観測を続けず停止する。ordinary lock recordは必要な読取りだけとし、live/stale/不正/別ownerを上書き・解除・回復しない。
5. mutex保持中に、許可されたローカル入力を§3の範囲で読み取る。cloud入力はmock/supplied snapshotだけとし、live接続・認証refresh/store・download bytes取得を経路から除く。
6. Python子プロセスが必要な処理は§4の資格をすべて満たす場合だけ呼ぶ。成立しなければその診断を停止する。通常のtemp IPCへfallbackしない。
7. 観測の整合性を再確認し、安全な概要を標準ストリームへ返す。成功・失敗・0件・再実行のどれでもmanifest/report/frozen inventory/marker/latest pointer/private証拠/budget/完了記録を作成・更新しない。mutexをfinallyで解放・closeし、解放失敗も固定理由で拒否する。ファイルcleanupは呼ばない。

読取り準備の不成立と、観測できた計画上の問題を区別するが、未決定のresult schemaや新しい終了コードは本書で定めない。失敗・不完全・不明を運用成功へ変換しない。

## 2. 排他の資格と生存期間

`Common/RecoveryDiagnosticMutex.py` は既存scope mutexをrecord/token I/Oなしで保持・解放するhelperである。これをDry Runの資格済み排他とはまだ扱わない。呼出し側は次をfixtureで確認する必要がある。

- 信頼済みの実行identityとscopeから、対象writerと同じmachine-wide mutex名・排他境界が導かれる。入力パス由来の任意名や、writerと競合しない別名を採用しない。全対象writerがその境界を守ることを確認できなければ停止する。
- mutexのidentity/accessと取得結果を検証でき、既存ownerの権利を奪わない。helperはabandonedを観測として返すため、呼出し側で直ちに停止し、stale takeoverや回復判断へ接続しない。
- ローカル列挙・既存証拠読取り・検証を終えるまでleaseを保持し、例外・timeoutを含め解放/closeする。保持中にも外部変更はあり得るため、排他だけでsnapshotやroot信頼を証明しない。

`OwnedRunLock.py` の通常取得はowner recordを作るためDry Runでは呼ばない。`CrashRecoveryDecision.py` の分類結果や、診断mutex取得成功から新run・回復・state変更を許可しない。

## 3. メモリ内の観測と再検証

既存config/root、許可source、既存manifest/report/private証拠等の必要最小限を読取り対象とする。入力件数・bytes・深さ・所要時間と標準ストリーム捕捉を有限に管理する設計を実装時に確認し、超過・読取り失敗・不完全列挙は停止/未検証とする。本書は根拠のない新しい数値上限を契約へ追加しない。メモリ不足時のtemp spill、download fallback、証拠の再生成を行わない。

path/handle identity、属性、size/hash、列挙完全性を使用点で再確認し、変更・不明なら観測を保留する。root検査後・mutex取得後・読取り後の必要な再検証を省略しない。既存source builderの前後照合やmanifest readerのbyte snapshotも一点時点の証拠であり、任意のnamespace/ABA変更や将来の不変性を保証しない。

観測には入力由来、観測時点、未検証項目を保つ。supplied snapshot、Drive for desktopの可視性、hash欠落、曖昧metadataを現在cloud内容の検証へ昇格させない。後続の実処理はその時点の認可、両PC証拠、現在Drive内容を独立に再検証する。Dry Runの診断結果をauthorizationや完了証拠として保存・再利用しない。

## 4. ファイル不要IPCと依存処理

[契約§4](powershell-python-contract.md#4-リクエスト契約)が既に許す**単一JSON引数**だけをファイル不要IPCの候補とする。実際のPowerShell/Python起動方式で文字encoding、引用符、引数境界、コマンドライン長を安全に扱え、プロセス引数等への秘密露出を避けられることを合成入力で確認してから使う。認証情報・ログ本文を含めず、公開してよい固定情報以外を無検証で渡さない。成立しない入力は停止する。新しいstdin protocol、任意の長さ上限、base64等の新transportを暗黙に契約化しない。通常のrequest/response一時ファイル、redirect先、診断logはAでは使えない。

子プロセスのstdout/stderrはファイルを介さず分離捕捉する。Python stdoutはUTF-8 JSON object 1件と末尾改行だけとし、banner/progress/tracebackを混在させない。stderrも秘密除去済み固定理由/概要だけとする。raw例外、ローカル絶対path、token、API本文を外へ流さず、捕捉した不正出力自体も再出力しない。timeout、不正/複数JSON、未知field/version、request ID/operation不一致、schema不適合、終了コード/error/retryableの矛盾は拒否する。

操作固有resultの厳密な検証も必要だが、[C-01/C-02](../validation/p0-contract-review-findings.md)のpath policy/result shapeをこの設計で解決しない。既存schemaのenvelope成功は操作結果の完全性を保証しない。adapter実装前に当該契約決定と全体レビューを終える。mock診断を口実に未決定result shapeをruntime契約として導入しない。

起動・importを含む全依存経路もAに従う。Pythonはbytecode生成を抑える `-B` とisolated modeを組み合わせる起動を実装候補とし、信頼済みpackage/import解決・既存helper呼出しとの適合性を検証する。これだけで資格完了とはしない。Python/moduleの `__pycache__`、temp、logging、schema参照解決、auth/token store/cache、HTTP client等の暗黙書込み・live通信を調査・捕捉する。抑止・検証できない依存は呼ばず停止し、環境変数だけやimport成功だけを根拠にしない。OS自動atime・監査・キャッシュ・ページング等の物理書込みzeroは保証しない。

## 5. DRY fixtureと実装責務の対応

下表の既存moduleは部分材料であり、DRY fixtureを実装済み・成功済みとする対応ではない。ファイル名は `Common/` 基準。

| fixture | 存在する部分材料 | 欠けている責務・確認 |
| --- | --- | --- |
| DRY-01 | `SourceInventoryEvidenceBuilder.py`、`RunInputEvidenceIntegrity.py` | 専用dispatch、計画のみの制御、全mutation/download拒否、正常/0件でも運用runなし |
| DRY-02 | `ManifestDirectoryReader.py`、`LatestManifestSelection.py`、`ArtifactSetDirectoryVerification.py`、`PrivateRecoveryEvidence.py` | 信頼済みrootでの読取り統合、既存原本不変、不正/欠落でも修復・再生成なし |
| DRY-03 | `RecoveryDiagnosticMutex.py`、`OwnedRunLock.py` のmutex材料 | record-free資格、abandoned時停止、ordinary recordの非取得・非回復、全終了経路のlease解放 |
| DRY-04 | source/manifest readerの変更検出、診断mutex helper | writerとの共通scope/identity資格、競合・証拠/path差替え時の停止、timeout中のstate不変 |
| DRY-05 | `MachineConfiguration.ps1`、`MachineConfigurationRootInspection.ps1` | bootstrap前分岐、信頼済みroot/ACL/FS authority、使用点再検証、PC-B archive拒否。root inspectionだけで承認済みとはしない |
| DRY-06 | supplied observationを分類する `RecoveryDiagnostic.py` | mock/snapshot由来保持、live接続/auth遮断、hash欠落・曖昧性の未検証維持。Drive adapterは未実装 |
| DRY-07 | 既存request/response schema、`AggregationReferencedArtifacts.ps1` の別用途validator起動 | ファイル不要IPCの安全性、依存書込み抑止、stream捕捉・秘密除去、相関/exit検証。既存起動をそのまま資格済みにしない |
| DRY-08 | A方針と運用publication helperの境界 | report/temp/log writerを呼べない制御と書込みfallback拒否、強制終了を含む呼出し履歴検査 |
| DRY-09 | ownerに基づく通常lock/復旧の部分helper | Dry Run専用cleanupなしの終了経路。古い物・自身の所有物でも削除0、残骸を保持 |
| DRY-10 | `CompletionWaitBudget.py`、`MonthlyScheduleObservation.py` の非I/O観測 | budget/scheduler writer遮断、診断IDとrun分離、再実行/成功/失敗/0件の不変性、後続runtime再検証 |

## 6. 次の最小実装単位と停止条件

次の候補は、合成fixture内のDry Run専用dispatchと依存境界に限定する。無効mode/PC/config/root、writer競合、abandoned、依存write要求を注入し、通常bootstrap/run-lock/publication/recovery/budget/scheduler/cleanupへ到達しないことを先に検証する。既存mutex helperの資格とroot authorityを確認できない場合は拒否する経路までとし、仮の成功経路で穴を埋めない。

fixture harnessは隔離した合成領域のbefore/afterだけでなく、create/write/rename/delete/ACL変更の途中呼出し、ネットワーク/auth/downloadの呼出しも捕捉する。harness自身のfixture作成・検証証拠の保存と、診断対象アプリの許可副作用を区別する。DRY-01–10を段階的に実装・実行し、未実施と限界を記録するまではruntime受け入れにしない。

Python IPC/adapterは§4とC-01/C-02等の独立ゲートが整うまで接続しない。OSD-05前はlive readを開かない。これらの不足は既存A承認を再質問する理由ではなく、依存部分の停止条件である。新しい例外やpolicyが必要になった場合だけ、その差分を判断対象として戻す。正式sync/archive入口、コード/schema/CI、配布、実ログ/実Drive検証は本書の変更範囲に含まれない。
