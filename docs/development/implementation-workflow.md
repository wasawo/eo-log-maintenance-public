# ログ移動システム 受け入れ条件・実装計画

文書版: 1.0 / 更新日: 2026-10-28（日本時間）
要件の正本: [要件定義書](../requirements/log-move-requirements.md)。構成/確認/記録の正本: [設計書](../design/log-move-design.md)。
位置付け: 再整理後の正式な計画文書。以下の作業順は現時点の実装計画で、未決の方式を決定済みにしない。実装再開指示・実データ操作の認可は含まない。
確認基準: main `27e99fec`（PR #46）、正式化開始branch `docs/requirements-design-task-review` / HEAD `c709558`。

## 1. 完成と現在地

初回の完成条件は、PC-A/Bからクラウドへログを移し、さらに古いクラウド上のログをPC-Aへアーカイブできることである。どちらの経路も、Q5とPCの役割制限を守り、確認済みの元を直接削除するところまで通す。失敗後の通常再実行と、処理結果の表示も含む。

両経路が使えることが必要であり、コピーだけ、または片方の経路だけでは初回完成としない。保持期間、フォルダの平坦化、競合、Q11/Q12の意味は要件定義書に従う。

2026-10-28に利用者の指示で実装を再開した。T0の詳細契約とT1の両経路の流れを具体化するため、[メモリ上の模擬実装](../design/log-move-simulation.md)を追加する。正式入口・新しい実元削除経路・実Drive接続とruntime受け入れは未完。既存の単体/schema/package/CIや模擬モデルの成功は両経路の完成証拠ではなく、AC全体は全て未完。

## 2. 一連の受け入れ条件

以下のACは本計画内の試験シナリオ識別子であり、恒久の要件IDを新設/置換しない。固定日時と合成ログ、隔離領域、模擬Driveでまず検証し、実環境の受け入れとは区別する。日時境界の判定方式・タイムゾーンは既存仕様と照合し、未決ならT0で確定する。

| ID | 操作・条件 | 確認する結果 | 合意 |
| --- | --- | --- | --- |
| AC-01 | 2026年10月としてA/Bで端末→クラウドを起動 | 9月以前のBattleLogと2025年以前のErrorReportを転送し、確認できた元を削除。10月BattleLog/2026年ErrorReportは残る | Q1/Q2/Q5/Q6 |
| AC-02 | 同時点でAのarchiveを起動 | クラウドの2025年以前BattleLog/2024年以前ErrorReportをAへ移し、確認できたクラウド元を削除。2026年1〜9月BattleLog/2025年ErrorReportは残る | Q1/Q2/Q5 |
| AC-03 | B未実行のままA archive、その後Bから古い分を転送して再度A archive | 既存分を先に移せる。Bの遅着分も次回移せる。両PCの期間完了を待たない | Q3/Q6 |
| AC-04 | 元の異なるサブフォルダに対象ログを置く | 保存先はログ種別ごとの共通フォルダ直下。元階層/PC別/新しい年別階層を増やさず、元を個別識別できる | Q7/平坦化指示 |
| AC-05 | 複数元に同名同内容を置く。別ケースで同名異内容を置く | 同内容は保存先を再利用し、元ごとに確認して削除。異内容は元を保持して競合表示。自動改名/上書き/結合しない | Q4/Q5/Q8 |
| AC-06 | コピー失敗、保存先不一致、元変更、比較不能をそれぞれ注入 | 当該元を削除せず理由を示す。独立した正常ファイルは元削除まで進む。共通前提が壊れた場合は依存する処理を停止 | Q4/Q5 |
| AC-07 | コピー成功後に元削除を失敗させ、同じ操作を再実行 | 内容を再確認して保存先を再利用し、元削除まで完了できる。元が変わっていれば削除しない | Q5/Q8/Q9 |
| AC-08 | コピーまたは削除の応答を失わせる | 盲目的に再送せず現状と対応記録を照合。削除結果不明後、有効な元/保存先・内容の対応記録、元の確実な不在、保存先一致がそろえば照合による移動完了。権限不足や根拠不足は結果不明のまま | Q5/Q9/Q11 |
| AC-09 | 正常な対象0件、不正名、列挙失敗、前回結果不明を別々に入力 | 正常な対象なしと未完了を区別。不正名や取得失敗を黙って除外しない | Q4/Q9、既存FIL仕様 |
| AC-10 | 一部競合/削除失敗を含めて処理を終了 | 概要とローカル詳細レポートで元/保存先・理由・次の行動を確認できる。完了件数はコピー数でなく元削除済みの元件数 | Q4/Q10 |
| AC-11 | Bからarchive/クラウド元削除を試みる。期間外/異なる元を削除対象に混ぜる | Bのarchive/クラウド削除を拒否し、自端末の適格な移動元だけを扱う。汎用の無条件削除を提供しない | Q2/Q5、エージェント |
| AC-12 | 強制終了後の残存lock/実行中記録、レポート保存失敗、空き容量不足を入力 | 勝手なlock解除/過去成功化をしない。移動済みと記録失敗を区別する。失敗箇所と元保全を確認する | Q9/Q10、既存復旧/容量仕様 |

完了判定には保存先の最終内容と元の有無、個別結果の一致を確認する。月末/年末・1月・うるう日も固定日時の境界ケースとして期間選択を確認する。一致したhelper戻り値や試験件数だけで移動成功としない。AC-08の記録/照合方法、AC-12の回復連携等はまだ設計が必要であり、表の存在は実証ではない。

## 3. 利用シナリオに沿う実装順

| 順序 | タスクと成果 | 主な変更対象/既存資産 | 完了の区切り・依存 |
| --- | --- | --- | --- |
| T0 | 合意を正本仕様へ反映し、2経路の契約を閉じる | 本書§4/5の差分。元/保存先identity・平坦化・Q5確認・削除結果・個別状態・記録・IPC/権限/配布 | 削除禁止/両PC待機/自動suffixの矛盾を解消し、ACごとの入口・期待結果・必要な詳細判断を追える。新helper実装へ逸れない |
| T1 | 正式入口と対象選択から模擬移動までをつなぐ | 設定/期間/列挙/ステージング/排他の既存資産、正式Sync/Archive入口と模擬adapter | 隔離データで両役割の対象・平坦化・役割拒否を一連で確認。模擬接続を実Drive完成と扱わない。T0/実装再開指示に依存 |
| T2 | A/Bの端末→クラウド移動を元削除まで通す | 実Drive adapterの契約実装、upload/現在内容確認、自端末の元不変確認/限定削除、永続記録 | AC-01/04/05/06/07/11をこの経路で通す。mockによる接続試験と実API/環境の未確認を明示。T1に依存 |
| T3 | クラウド→A archiveをクラウド元削除まで通す | 現在Drive列挙/download、Aへの保存/読戻し確認、クラウド元不変確認/限定削除、記録 | AC-02/03/04/05/06/07/11をこの経路で通す。B待機を復活させない。共通契約/記録をT2から再利用 |
| T4 | 両経路の再実行・結果不明照合・概要/レポートを統合 | 個別結果と履歴の対応、現在状態照合、既存retry/復旧資産、ローカル詳細レポート | AC-03/07/08/09/10/12を両経路で確認。通常失敗は同じ操作で残りを処理。専用競合解消ツールを追加しない。T2/T3に依存 |
| T5 | 初回完成の一連試験と役割別配布/導入を検証する | 最終package allowlist/設定保持、AC-01〜12、既存CI/対象FS・runtime受け入れ計画 | 合成試験、配布試験、実環境受け入れの結果を分離して不足を記録。helper/CI成功だけで初回の運用可能を宣言しない。T4と必要な環境判断に依存 |
| 後続 | 定期実行を手動と同じ移動処理へ接続する | scheduler/電源条件等の既存設計を再照合 | 初回の両経路と再実行が成立してから扱う。専用比較/解消ツールは別の後続候補 |

T1から、ファイルごとの最小限の処理結果を出す。T2/T3でも、各経路に必要な検証、記録、失敗処理を実装する。T4では、それらを両経路・複数回の実行をまたいで使える形に統合する。

各機能に必要な契約・コード・試験は、同じ実装単位にまとめる。この作業順では、移動の完成につながらない資源制限ヘルパーだけを独立して増やさない。

各タスクは仕様根拠・未決・対象ファイル・実行した検証・残る受け入れ限界を同じ文書/PRに記録する。作業順はこの計画で管理し、利用者の要件回答から未決の技術方式の採用まで推測しない。

## 4. 既存要件・正本への対応

2026-10-27の[要件と承認記録](../requirements/log-move-requirements.md#承認記録)に基づき、要件台帳13行/P0-012とREADME/主要設計/計画/試験期待を更新した。copy-only/両PC待機/自動suffixの変更方針は現行本文へ反映済み。新しい削除・状態・IPC・記録の詳細契約は引き続きT0の残件。既存IDを維持し、実装/受け入れを完了へ昇格していない。

既存IDは変更/再利用せず、改訂履歴と試験条件を更新する。下表は対象の棚卸しであり、要件台帳の全行監査や実装状態の更新済み宣言ではない。

| 既存項目 | 今回の扱い | 対応AC/タスク |
| --- | --- | --- |
| EOLM-FIL-001〜010 | 名前/日付/全過去分/エラー可視化を維持。期間対象をQ1の3層配置へ接続 | AC-01/02/09、T1〜T5 |
| EOLM-SYN-001、EOLM-ARC-003 | Q5成立時に各経路の元を削除して完了へ要件改訂済み。実行/削除契約は未完 | AC-01/02/06/07、T0/T2/T3 |
| EOLM-SYN-002〜005 | 同内容再利用・出所推測禁止・異内容上書き禁止を維持。SYN-003の自動suffixはQ8の競合保留へ変更 | AC-04/05、T0/T2/T3 |
| EOLM-ARC-001/002/004/005/006、EOLM-MAN-007/010 | A専用/現在内容確認は維持。ARC-002/005・MAN-007はQ3/Q4のファイル単位へ改訂済み。現v1/helperの実装は変更せず、個別証拠の新契約は未完 | AC-02/03/06/11、T0/T3 |
| EOLM-DRV-001〜008 | 現在内容確認/結果不明照合等を維持。新しいクラウド削除に必要な操作・権限・結果契約は未完 | AC-01/02/08、T0/T2〜T4 |
| EOLM-CFG-005、EOLM-SAF-001/004、EOLM-TST-006、P0-012 | 2経路/2条件/役割限定と拒否条件の証明へ要件/受け入れ期待を改訂済み。汎用allowDeleteは採用せず、新しいruntime証拠は未完 | AC-06/11/12、T0/T5 |
| EOLM-MAN-003〜006/008/009、STG群、LCK群 | 記録/未完了保全/排他を再利用。削除結果との対応を設計。定期実行やB待機の旧前提は別途再照合 | AC-07〜12、T0/T4 |
| P0-006/009/010、EOLM-REL群 | 役割別配布・秘密非同梱・追跡性を維持し、新しい最終file集合と試験へ追従。P0閉鎖は未完 | AC-11/12、T5 |

主な正本: [要件台帳](../requirements/requirements-traceability.md)、[P0台帳](../requirements/p0-gap-register.md)、[実装計画](implementation-workflow.md)、[決定台帳](../decisions/decision-register-c18-c32.md)、[詳細設計への参照表](development-guide.md)。旧設計は記録として保持し、変更範囲を明示して整合させる。今回更新した冒頭通知だけで全本文の改訂済みとはしない。

## 5. 実装前に閉じる詳細と、後へ分けられるもの

[設計書](../design/log-move-design.md)に、コピー基準/保存先/削除直前の元の3内容と実体を結び付ける具体案、両経路の順序、公式API資料の確認結果と残件を記載した。Q5の具体方式を確定したものではなく、T0の詳細設計として継続する。

同設計§9〜13に、削除前の必要記録、削除応答と除去確認、通常再実行の照合表を追加。Q11で照合による完了の方針は確認済み。記録/状態案は以下へ具体化したが、実API/FSの不在確認、次経路へ移動済みの場合の照合、新版の契約確定は未完で、T0完了とはしない。

同設計§14〜18を基に、独立した[移動記録v1](../design/move-record-v1.md)のfield/validator/保存・読戻しを実装した。現manifest v1や実runとの接続、private root/ACL/排他の資格、実APIの保証は未完。Q12で両経路の直接削除方式は確認済み。AC-01/02/07/08/11はこの削除方式を前提とし、ごみ箱移動や元フォルダからの消失だけを削除完了へ昇格しない。

| 判断・設計 | 必要な時期 | 残す具体物 |
| --- | --- | --- |
| 元/保存先のidentityと平坦化の対応、同名判定/一括発見/同時実行 | T1/T2より前 | 個別元と一意な保存先の対応、競合保留の判定表 |
| Q5の内容一致/元不変確認と削除を同じ対象へ結び付ける方式 | 削除実装より前 | 両経路の確認方式・確認不能/変更時の保全・確認と削除間の限界 |
| 削除前後の記録、結果不明照合、ファイル完了とrun状態/終了コード | T2/T3の削除より前 | 状態遷移、必要な永続記録、消失/再到着/次経路移動時の照合表 |
| Driveの新操作・C-02結果・credential/scope/provider・役割制限 | 対応adapter実装より前 | 要求/応答と拒否条件、実権限の検証計画。文書で権限を与えた扱いにしない |
| 起動/前提検査と復旧/保存領域/容量の接続 | T1から必要な箇所で | 入口で拒否する条件と各ACの影響範囲。既存helperの観測をそのまま認可にしない |
| 概要/ローカルレポートの形式・表示・保存失敗・保持 | 最小結果はT1、完成はT4より前 | 元ごとの状況、完了件数、確認先、実値非公開の境界 |
| 最終package/導入/更新/対象FSとruntime受け入れ | T5より前 | 最終allowlist、既存実設定保持、限定環境検証計画と未実証項目 |
| 定期実行、専用競合解消ツール | 初回完成後の候補 | 既存判断との整合を後続計画へ記録。今回の実装前提へ混ぜない |

具体案は既存の承認を根拠に作る。利用者へ確認するのは、データの扱いや完成範囲が変わる判断である。合意済みの条件を、細かい二択に分けて聞き直さない。

## 6. 検証と現在地

T0のローカル元削除方式を具体化するため、[Windows隔離probe](../design/windows-move-delete-probe.md)を追加した。別途[移動記録v1](../design/move-record-v1.md)でschema・保存・読戻し・別プロセスでの参照検査を実装した。正式provider、実runでの記録資格と排他、実Driveの版固定削除は未完で、T0やACの完了にはしない。

さらに[別プロセスでの隔離再観測](../design/cold-move-reconciliation.md)で、親から観測結果を渡さずに、現在の合成元/保存先と記録を照合するところまで接続した。実Driveは模擬で、正式なrun回復・再削除は提供しない。

[実行別概要表示](../design/move-run-report.md)で、記録の読取からPowerShellの画面表示まで接続した。初回完了と再確認の計数を分け、過去の未解決を持ち越す。fresh inventory/run全体の判定、詳細レポート保存、通常移動の正式入口は未完で、T1/T4全体の完了にはしない。

[模擬処理のjournal接続](../design/simulation-journal-integration.md)で、同じ元/コピー内容のmove ID維持、削除前保存、通常再実行、照合、概要を両経路で接続した。[模擬実行結果レポート](../design/simulation-run-report.md)では準備前の失敗も別のローカルJSONへ保存し、模擬実行全体の集計と保存失敗の区別を接続した。正式な実run lifecycle、資格・排他、実providerの採用には進んでいない。

本書のAC全体は未完。実装再開指示は2026-10-28に受領した。両経路の対象選択・移動・再実行・結果を模擬モデルで接続するが、正式Sync/Archive入口、実Drive adapter、新しい実元削除経路、永続記録と実レポートは未完成。T0完了やT1完了には昇格しない。

[所有ロック付き模擬実行](../design/owned-simulation-run.md)では、既存OS mutex/所有token記録を再利用し、PC-A両経路・PC-B Syncの開始からモデル移動・結果レポート・終了記録まで接続した。強制終了の残存lockを自動解除しない。実providerに対する所有喪失時の停止、private root/ACL資格、実列挙/正式run回復は未完である。

[読取ファイル列挙の接続](../design/file-snapshot-simulation.md)で、合成フォルダ全体の読取りが完了した場合だけ所有ロック付きモデルへ入力する。列挙/読取失敗・途中変更から部分的な移動を始めず、実物理ファイルは変更しない。正式providerの実列挙・Q5/実体保護・実環境資格を完成したものではない。

所有wrapperには[各処理境界での所有確認](../design/owned-simulation-run.md#処理境界での所有確認)を接続した。既知の喪失後はモデルのコピー/元除去と永続保存を止め、除去後の確認不能と過去照合の失敗を分ける。確認と実操作の原子的な結合や、既に開始したIOの取消しを実証したものではない。

[同一プロセスのnative隔離接続](../design/same-process-owned-native-probe.md)で、所有mutex/token記録・元/保存先・準備記録を保持し、Q5再読から同一ハンドル削除・v1結果保存まで試験した。所有プロセス終了後も旧記録/lockを保全し、別プロセスの現在状態照合へつなぐ。任意rootの正式provider採用や、既存PowerShellモデルの実削除化ではない。

T0の旧方針整合は§4のとおり進めた。次は元/保存先の識別・Q5確認と削除結果の詳細設計を進める。通常検証は合成/隔離/模擬APIを使い、実ログ/本番Driveの接続・削除・本番適用は別途具体的指示と限定計画の範囲で扱う。独立レビュー未実施を自己点検で置き換えて表記しない。

## 7. 文書の統合・削除記録

利用者の2026-10-27指示に基づき、作業文書を正式文書へ集約した。以下の旧ファイルはコピーを残さず削除し、全文/差分はGitの`c709558`以前で追跡できる。履歴の書き換えやbranch削除は行わない。

| 削除する旧作業文書 | 移行先と保持内容 |
| --- | --- |
| `docs/development/requirements-design-task-review-20261027.md` | 要件定義書: Q1〜Q12/平坦化/恒久規則の承認記録と現行要件。実装対応は本計画 |
| `docs/development/initial-move-delivery-plan-20261027.md` | 本計画: AC-01〜12、T0〜T5、既存ID対応、未決/受け入れ限界 |
| `docs/design/move-source-destination-verification.md` | 設計書: 2経路、識別/Q5、記録/状態/照合/応答候補、公式資料と限界 |
| `docs/status/first-release-readiness-20261024.md` | 本計画§9/10: 固有の実装棚卸しと当時の証拠基準を継承。重複する旧作業順は廃止 |

既存schema/helperに対応する個別契約、運用規則、判断に必要な過去承認、検証根拠はまだ利用先があるため削除しない。ファイル名にproposal/optionsがあるだけで不要と決めない。AGENTSの変更は承認記録へのリンク先のみで、恒久規則の意味は変えていない。

## 8. 旧実装計画の参照の読み方

過去の監査/証拠に残る節番号・Phase名は当時の文書位置。本ファイルは正式計画へ置き換えたため、現在の実装には次の移行先を使い、過去基準が必要なら`c709558`を参照する。

| 旧位置 | 現在の参照先 |
| --- | --- |
| §2.1〜2.3 役割/保存先/保持 | 要件定義書§1〜4 |
| §2.4 同名、§2.5 削除/クラウド確認、§2.6 起動 | 要件定義書§5〜8、設計書§3〜5/11/17 |
| §4 P0 readiness、旧Phase 0〜8 | 本計画§2〜5、P0台帳。定期実行は後続候補 |
| §7 安全境界 | 要件定義書§6/9/10、AGENTS |


## 9. 既存の実装資産と不足

整理日: 2026-10-27。コード基準はmain `27e99fec`（PR #46）、この整理開始HEADは`594a5e1`。当時は文書branchのmainとの差分に非Markdown変更がなく、scripts/の追跡ファイルはREADMEのみだった。その後、上記§6の実装を追加している。下表は旧棚卸しの固有情報を現要件へ合わせて移したもので、現在の全機能の実行検証ではない。

| 分野 | 現在あるもの | 初回運用までの主な不足 |
| --- | --- | --- |
| 設定 | [厳密な設定読取](../../Common/MachineConfiguration.ps1)、[create-only生成](../../Common/MachineConfigurationBootstrap.ps1)、両PCの安全なexample、maintenanceLocalの字句的分離 | 正式導入入口、実root認可、実効権限・祖先・利用直前までの保護。example生成後の実値は各PCのGit管理外設定へ手動入力 |
| ファイル選択 | [日付・期間等の共通処理](../../Common/LogFunctions.ps1)、[完全列挙・ハッシュ証拠構築](../../Common/SourceInventoryEvidenceBuilder.py)・[凍結B2との再観測比較](../design/reference/source-inventory-revalidation.md) | 正式runへの接続、列挙後の変更と利用までの整合性 |
| root検査 | [既存Windowsディレクトリの読取専用metadata検査](../../Common/MachineConfigurationRootInspection.ps1) | 対象FS・ACL・実トークンの認可、安全な生成と継続利用の資格確認 |
| upload staging容量 | [既承認容量式の純粋PS観測](../design/staging-file-lifecycle.md)：凍結manifest/B2の明示size射影・tests専用PS bridge・祖先chainの128-bit identity前後照合付き未資格Windows空きbytes観測・size配列のBigInteger合計・10%切上げ＋100,000,000 bytes、不明/不足時停止 | 実空き容量の資格、開始時/各file直前の取得と容量変化時のcopy失敗対応。download容量方針には転用しない |
| 証拠・集約 | [contracts](../../contracts/)、[A2/B2検証](../../Common/RunInputEvidenceIntegrity.py)、[安定読取観測付き参照成果物・全report再導出検証](../../Common/validate_aggregation_artifacts.py)、[純粋なレポート ビルダー](../../Common/AggregationReportBuilder.py)、条件付き採用済み状態遷移表と[純粋snapshot/連続履歴検査（2種pending区別）・初期B2 planから全履歴/終端reportへのbinding・source隔離接続](../design/reference/manifest-transition-inspection.md) | 真正なevent/metadata-first履歴、実run writer/遷移強制、決定的再生成・意味論的統合、Drive反映 |
| ステージング コピーをアップロード | [凍結planと既存stagingの単一/一括照合・Drive観測比較接続](../design/reference/source-inventory-revalidation.md)：size変化時open前停止・全hash後signature/祖先chain確認、完全列挙/計画/完了hash比較、source非読取/全許可false。tests専用source→copy接続もあり | 正式copy/metadata-first writer・割当identity binding・ready状態/Upload adapter・容量資格/使用点・実root/FSと電源断受け入れ |
| 残存staging | [直下entry件数の読取観測](../design/reference/staging-residual-observation.md)：内容非読取/非再帰、変化・不明時保留、初回件数保全 | metadata/旧run検査、正式startup warning・検査不能時run failureとUpload停止、root/owner/FS資格。cleanup/復旧は提供しない |
| 公開・クラッシュ | [単一ファイル公開](../../Common/AtomicArtifactPublication.py)、[marker-last公開](../../Common/ArtifactSetPublication.py)、復旧分類・ディレクトリ検証・[終端履歴planの使用点再導出→別候補bundle保存/読戻しの隔離接続](../design/reference/manifest-transition-inspection.md) | 元runningの正式更新・永続run状態/実event/providerとの接続。複数ファイルの原子的トランザクションや電源断耐久性の証明はない |
| 排他・manifest選択 | [所有run lock](../../Common/OwnedRunLock.py)、[最新候補選択](../../Common/LatestManifestSelection.py)、[report binding付き読取adapter](../design/reference/latest-manifest-selection.md) | 旧lockの自動引継ぎはしない。実owner証拠、復旧手順、新runとfresh inventoryの作成、実環境での統合 |
| 明示回復 | 診断・専用mutex、[private証拠のメモリ上のbinding](../../Common/PrivateRecoveryEvidence.py)、供給ACL/descriptorの検査、v1の5field互換境界 | v2の全fieldと適格machine/boot provider、実効ACLと保存先検証、非公開の実保存。v1は診断・保全限定 |
| 月次・旧確認予算 | [月次観測](../../Common/MonthlyScheduleObservation.py)、[旧24時間/25回予算・checkpoint/使用点の補助処理](../design/reference/completion-wait-budget.md)、[AC電源観測](../design/reference/power-status-observation.md) | 月次task/未実行補完・実時計/account/session/AC停止の統合は未完。定期実行は後続候補。旧PC-B完了待機予算はQ3後のarchive前提には使わない |
| ドライブ | request/response schema、[相関・終了コード・固定retryable表の純粋helper](../../Common/DriveResponseSemantics.ps1)・[PS再試行観測](../design/reference/drive-retry-observation.md)、[初期inventory読取接続・件数要約](../design/reference/initial-inventory-observation.md)・[OSD-01一括同一内容比較・旧PC suffix命名観測（Q8の自動改名採用ではない）・PC-A source一括再観測接続・page集約/前後照合・不足hash計画/完了集合検査/download chunk観測・staging隔離接続試験](../design/reference/drive-content-comparison.md)、P1/V1/L1・R1/N1/D1 | C-01の実root/指定先/使用点検査、C-02のschemaと具体result形、公式Python client adapter、Desktop OAuth/drive.fileの実folder資格、PS retryの実counter/待機/送信統合・結果不明upload照合 |
| 配布 | [役割別ビルダー](../../.github/scripts/Build-ReleasePackage.ps1)、example検査、PC-Bのarchive除外、レビュー用非配布マーカー。旧file集合の件数は§10で歴史として保持 | 正式入口、PC別/version別の最終JSON file manifest、tag/VERSION/commitのprovenance、E1承認後Actions配布identity、Drive内容検証、手動導入/専用PS移行/復旧 |

正式Sync/Archive入口・実Drive adapter・元削除経路・正式writer・導入/更新の一連処理は未完。既存helper/schema/隔離接続をruntime完成としない。現要件の順序は§3のT0〜T5で、両経路とも確認済み元の直接削除までが初回完成。旧copy-only/両PC期間待ちの依存順序は引き継がない。

レビュー用ZIPを作れることと実運用可能な初回リリースは別。通常ビルドは正式入口不在を拒否し、AllowNonDeployableの非配布マーカー付き成果物は導入しない。入口の存在判定やVERSION 0.1.0もruntime受け入れ/配布実績の証拠ではない。実配布の判定はT5と[配布設計](../release/distribution-design.md)に従う。

## 10. 旧棚卸しの証拠基準（歴史）

旧棚卸しはファイル名が2026-10-24、本文更新日が2026-10-25、main基準が`fd9cc8a931496d31601f062bf66448ea295eec65`（PR #39）だった。全文はGitの`594a5e1`時点に残る。以下を現在HEADの検証値/runtime受け入れへ読み替えない。

- PR #39 mainの[検証](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40105135888)・[パッケージの検証](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40105134099)成功は当該SHAの証拠。旧本文のC-01/B2/G1/retryable実装の「ローカルのみ/PR未実施」も当時の状態で、現在のCI未実施断定に使わない。
- 旧基準のローカル結果はPython 3.11.9で306件（2skip）、PowerShell 7.6.7の配布回帰成功。現在の試験件数/受け入れ値ではなく、今回再実行していない。
- レビュー用0.1.0の40-file snapshot、その後の追加による50件の記録は[限定4件の決定記録](../archive/decisions/implementation-grounded-four-decisions-20261024.md)と旧棚卸しの歴史。現在の最終runtime file manifest/配布資格ではなく、今回packageを生成/再計数していない。
- PC-Bの部分volume/reparse/crash/source/lock証拠は加算して全体受け入れにしない。旧lock証拠のsource SHAは`302682abb7fd3b45b6745247dfa5297542f81c4b`。旧棚卸し時のTier Bはincomplete、Aのvolume証拠未収集、Tier C未実施、電源断/再起動耐久性未証明を保持する。現在の資格判定は[対象FS受け入れ計画](../validation/target-filesystem-acceptance.md)と個別証拠を照合する。
- OAuth/credential・owner-v2/private保全・配布identity/provenance・最終file/migration・通知/重複抑制・時計/AC等の未完は§5と[未決台帳](../requirements/p0-open-specification-decisions.md)へ接続する。既存選択は[決定台帳](../decisions/decision-register-c18-c32.md)を維持し、旧24時間/25回待機をarchive必須条件へ戻さない。

## 11. 正式文書を基準にしたリポジトリ配置の整理

2026-10-27、利用者の指示を受け`9aa3c53`から整理した。正式要件/設計/本計画を入口とし、現行契約・既存実装の参照・過去の判断/検証を混在させない。

| 対象 | 整理先と理由 |
| --- | --- |
| 比較/選択/承認の25文書 | docs/archive/decisions。[履歴索引](../archive/README.md)で探索する。承認の撤回ではなく適用範囲を保つ |
| 過去基準の監査/証拠7文書 | docs/archive/validation。現runtime受け入れと混同しない。現在の試験/対象FS/復旧計画はvalidation直下へ保持 |
| helper観測/比較等14文書 | docs/design/reference。[参照索引](../design/reference/README.md)から必要な実装を調べる |
| Commonの長い説明 | [モジュール参照ノート](../design/reference/common-module-notes.md)へ全文を移し、Common/READMEを機能索引にする |
| 旧handoff約980行 | [引き継ぎ履歴](../handoff/archive/requirements-review-through-20261027.md)へ全文保管。固定のnext-chat.mdは現状/未完/次作業に絞る |
| 実行/契約/配布/個人領域 | Commonのコード、contracts、Config、scripts、tests、CI/allowlist、.agents/.codex、無視対象の個人設定/実データは移動/削除しない |

移動対象への非Markdown依存を確認し、Markdownリンクは移動前の位置から解決して移動後へ張り直した。repo-root基準のdocs pathも追従した。旧文書の名称/位置だけで内容を不要と決めず、候補/既承認/当時の証拠を区別する。未使用と推測してhelper/テストを削除したり、過去の承認を再質問する整理ではない。
