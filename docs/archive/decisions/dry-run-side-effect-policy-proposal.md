# OSD-04: Dry Runローカル副作用のA承認・比較記録

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

- 状態：**Aの方針を利用者承認済み（2026-10-24）**。「Aで進めてよい」と回答。Bは比較用の未採用案であり、書込み許可として使わない。
- 対象：EOLM-DRV-016、EOLM-SAF-002、EOLM-SAF-006、EOLM-TST-005、EOLM-TST-007。
- この文書はコード、schema、CI、正式runtime、配布、認証、実環境接続を変更・許可しない。OSD-04/P0受け入れは未完了のまま。

## 1. 根拠と判断対象

[OSD-04台帳](../../requirements/p0-open-specification-decisions.md)は、Drive変更とダウンロード内容の書込みを禁止済みだが、ローカルreport・manifest・lock・一時物・cleanupの境界が不足していると記録している。[PS/Python契約](../../design/powershell-python-contract.md) §3の禁止を下限とし、§5の成功レスポンスはアダプター操作の結果に限るという境界、§8の検証・一時物処理、§9の秘密情報保護を維持する。[C-30](../../decisions/decision-register-c18-c32.md)と[実装計画](../../development/implementation-workflow.md) Phase 1/7はDry Runと後続受け入れを要求するが、文書やhelperの存在をruntime完成とはしない。

承認されたのは下表のA方針。個別例外を暗黙に追加しない。同じ選択を再質問しない。設計・実装・受け入れ、IPC契約全体のレビューとOSD-05は別ゲートである。

| 案 | 許容する意図的ローカル効果 | 利点 | 負担・制限 |
|---|---|---|---|
| **A（推奨）** | アプリによる意図的ファイル書込みなし。検証済み入力の読取りと機密除去済み診断の標準ストリーム出力のみ | 運用stateと証拠を変えず、許容境界を小さく検査できる | 永続診断を残せず、既存の一時requestファイル方式・自動bootstrapを利用できない。設定/root未準備なら停止する |
| B | Aの読取りに加え、検証済み`maintenanceLocal`下の専用診断reportと当該実行所有の一時ファイルだけ | 再確認可能な診断を残し、一時request方式を限定利用できる | 診断と運用証拠の分離、ACL・所有権・衝突・異常残骸の検証が増える。書込み失敗も安全に扱う必要がある |

「ファイル書込みなし」はアプリが依頼・実行する書込みの範囲である。OS/FSによる自動atime、監査、キャッシュ、ページング等を含めた**物理ディスク書込みzeroを保証しない**。外部shellによるredirectや収集も本ポリシーの永続化許可ではなく、秘密除去と保管範囲を別に評価する。

## 2. 固定禁止と選択待ちのmatrix

「固定禁止」とA列を採用する。「A採用」の行でもB列は未採用の比較記録。共通候補はAの方針内だが、mutex等の具体方式・実装資格の未検証事項を承認済みとしない。

| 操作・対象 | 区分 | A案 | B案 |
|---|---|---|---|
| ローカル元ログ、Driveログ、archiveの作成・コピー・最終配置・上書き・rename・削除 | 固定禁止 | 変更なし。予定操作の説明のみ | 同左。PC-Bにarchive能力を与えない |
| upload、Drive metadataの更新、Drive上の証拠の発行・複製 | 固定禁止 | mutation API呼出しなし | 同左 |
| downloadのbytes取得・保存、staging、hash不足時のdownload fallback（メモリ経由を含む） | 固定禁止 | 実行せず、内容未検証と報告 | 同左。診断一時領域もdownload先にしない |
| 運用manifest、aggregation report、frozen inventory/B2、marker、latest pointer | 固定禁止 | 新規・更新・発行・再生成・移行なし | 同左。専用診断reportをこれらの代用品にしない |
| ordinary run-lock recordの作成・heartbeat・更新・解除、stale recordの処分 | 固定禁止 | 読取りだけ。取得を理由に運用runを開始しない | 同左。stale判定による上書き・自動回復なし |
| private recovery証拠原本、owner証拠、回復指示・処分記録 | 固定禁止 | 適切な権限で必要な読取りのみ。新規・変更・自動削除なし | 同左。既存private証拠は診断cleanupの対象外 |
| confirmation budget、scheduler完了・missed-run記録 | 固定禁止 | 読取りのみ。予算消費・reset・完了更新なし | 同左 |
| config/rootのbootstrap、directory作成、既存ACL/所有者/継承の変更・修復 | 固定禁止 | 実config未作成・信頼できるroot未確認なら作成せず停止 | 同左。診断先の準備やACL修復も別の承認済み導入手順で先に行う |
| ローカル設定・元ログ・既存証拠の読取りとローカルhash計算 | 共通候補 | 役割・許可root・ACL等の読取り検証に成功した範囲だけ。入力不足・変更検出時は保留 | 同左 |
|ドライブ `list_files` / `get_file_metadata`| 独立ゲート | mock/supplied snapshotのみ。OSD-05と認証副作用の受け入れ前はlive接続を許可しない | 同左。B選択だけでlive readを解禁しない |
| 診断専用mutexの取得・解放という一時的kernel効果 | 共通候補 | 検証済み名前・identityに限定し運用writerとの読取り競合を防ぐ設計を別途確認。record書込みなし | 同左。取得失敗・abandoned・所有不明なら停止し、回復しない |
| credentialのrefresh・token store/cache更新・対話login | 固定禁止 | 書込みを誘発する認証なし。必要なら接続せず停止 | 同左。既存credentialの存在だけでは認可にならない |
| IPC request/response等の一時ファイル・cleanup | **A採用** | 作成・変更・削除なし。ファイル不要の安全な経路が成立しなければ停止 | 未採用：検証済み`maintenanceLocal`下の専用診断領域に限り当該実行所有の一時物を作成し、その物だけcleanup。詳細は§3 |
| 永続診断report・アプリ診断log | **A採用** | ファイル出力なし | 未採用：専用診断領域に新規診断reportのみ。運用report、成功証拠、共有Drive複製として扱わない |
| 標準ストリーム診断 | 共通候補 | 安全な概要のみ。Python stdoutは契約§5のJSON 1件を維持し、診断はstderr | 同左 |

この承認で既存の運用lock契約への具体的例外を確定しない。診断専用mutexを使う場合、既存writerと同じ排他境界を安全に共有できるか、recordを作らずに読み取れるかを設計・fixtureで確かめる。保証できなければ停止する。

## 3. Bの限定書込みと異常時の扱い（未採用の比較記録）

既存の`maintenanceLocal`をread-only検証し、元ログ・Drive同期領域・archive・運用artifact・private原本から分離された専用診断先だけを候補とする。診断先の既存ACL、所有者、継承、reparse/経路置換、領域分離を検証できなければ書かない。rootや診断先の自動作成・ACL修復で検証失敗を解消しない。

新規reportは運用manifest/runから独立した診断identityを使い、Dry Run・観測時点・入力由来・未検証項目・非運用証拠であることを明示する。既存ファイルは上書きせず、衝突時は保留する。秘密情報・ログ本文・private原本を複写しない。新規ファイルに必要なアクセス制限を付ける作成方式は事前設計・検証対象とし、既存ACLの変更許可に拡張しない。

一時物は当該実行によるexclusive作成と所有権が証明できる物だけに限定する。cleanupは成功・失敗経路ともその所有物だけを対象にし、private原本、元ログ、Drive、他実行の物を触らない。timeout、強制終了、所有不明、path race、abandoned mutex等で残った異常残骸は非権威のまま保留し、年齢だけで削除・回収しない。永続診断reportの自動retention/cleanupは含めない。

## 4. 診断の意味と実装前ゲート

両案とも運用の新runを作らず、成功manifest・運用完了・両PC完了・予算消費・自動回復を発生させない。診断用correlation/request IDは運用run_idではない。0件や既存成功manifestの読取りでも運用完了にしない。設定、`allowArchive`、アダプターの`success: true`もこの境界を解除しない。

読取り結果は計画・観測時点の診断に限り、後続runtimeのauthorizationではない。mock/supplied snapshotとDrive for desktopの可視性は、現在のcloud内容の証拠にならない。必要な識別情報・hashがなければ「未検証」とし、downloadや推測で補わない。実処理ではその時点の認可・両PC証拠・現在Drive内容を独立に再検証する。

実装着手前に次を順に満たす。

1. A選択は利用者回答により完了。Bの書込みや本番適用へ承認を拡張しない。
2. 契約§3へAの境界と§4/8/9に対するDry Run例外を反映。秘密を漏らさないファイル不要のIPCと標準ストリーム捕捉の具体設計・検証は残る。既存schemaを暗黙変更せず、IPC契約全体のレビューを完了扱いしない。
3. ordinary run-lock/回復処理の前にDry Runを分岐できること、writerとの競合を安全に検出・停止できること、依存ライブラリのtemp/cache/credential更新を抑止できることを確認する。無効設定・役割・rootでは書込み前に停止する。
4. [DRY fixture受け入れ計画](../../validation/runtime-safety-test-scenarios.md#10-osd-04-dry-run提案用受け入れfixture計画未実装未実行)を実装・実行し、選択案の境界と失敗・競合を検証する。helper/schema/CI成功だけをruntime受け入れにしない。
5. live metadata readはOSD-05の認証/最小scope/対象権限と、refresh・cache等の副作用を別途承認・検証するまで閉じる。実ログ・本番Driveを使う限定検証も別の承認済み計画を要する。

PR #29では判断案と未実施の受け入れ計画を追加し、その後の利用者回答でAを承認した。Aの実装・fixture・runtime証拠は未作成/未実行であり、Phase 1/7やP0を完了にしない。

§4の具体化は[Dry Run実行設計](../../design/dry-run-execution-design.md)を参照。実装・fixture実行・IPC全体レビュー・OSD-05の完了を示すものではない。
