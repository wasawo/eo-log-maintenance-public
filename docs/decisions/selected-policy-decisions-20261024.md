# 2026-10-24 選択形式による仕様決定

状態：利用者の明示回答を記録する。仕様の選択と、実装・公開・マージ・実環境適用の許可を分離する。記録基準はmain 179787f（PR #38）、作業開始時の停止記録は54f1418。

## 1. 利用者の回答と確定範囲

### 第1回回答

利用者は「未決事項を選択肢形式で確定させたい」と依頼し、次の3問に対して「①P1 / ②V1 / ③G1」と回答した。

| 問 | 選択として確定する範囲 | 併せて確定したと扱わないもの |
| --- | --- | --- |
| ① C-01 | P1：requestのlocal_path / staging_pathはdrive-rooted Windows pathのみを対象とする | 検査配置V1/V2、詳細字句L1、schema 1.0の改訂/新版/移行、実装開始。回答がP1のみなので質問の提案一式へ拡張しない |
| ② B2 validation | V1：既存completedを全入力の分類処理完了の意味に確定し、エラー有無と分離する | 新versionやcoverage fieldの新設、過去recordの修復・昇格、source builderの実装完了 |
| ③ report生成UTC | G1：不変入力の終了UTCから基準時刻を決定し、実際の書出時刻とは区別する。具体規則は§3 | 別の時刻metadata保存、毎回の実時計、R5への新たな入力追加、実装・再生成受け入れの完了 |

第1回回答でUNC対応は採用しない。P1だけで構文・root authority・FS資格・physical containmentを証明しない。C-01の残る項目については次の第2回回答で追記する。第1回回答を遡って一式承認にしない。

### 第2回回答：C-01の残る選択

利用者は追加の独立質問へ、④「V1：schema＋PS/Python」、⑤「L1全体で確定」、⑥「現行1.0を実装前に改訂」と回答した。

- C-01はP1＋検査配置V1＋[L1全体](c01-drive-rooted-lexical-candidate.md)を採用する。L1の追加制約を含む全項目が対象で、schema成功から実体・root・FS資格を推定しない。
- IPCの互換方針は現行1.0を実装前に改訂する。既存schema-valid入力の一部が不適合になること、repo内adapterが未実装でも外部consumer不在は未確認であることを示した質問への選択である。
- この方針は外部consumerが存在しない証明ではない。実施時に受理範囲の変更、契約・schema・例・fixtureの整合と互換限界を記録し、曖昧なfallbackや暗黙のmigrationを追加しない。
- C-02のresult集合や不足表現等はまだ未選択。この回答をそれらのfield採用に拡張しない。
- 今回は仕様決定を記録するだけで、コード/schema/fixtureへの実装・公開・PR/マージ・本番適用は行っていない。

### 第3回回答：C-02の閉鎖・不足表現・Dry Run

利用者は⑦「R1：操作別にclosed」、⑧「N1：必須field＋nullable」、⑨「D1：plan/executedを明示」と回答した。

- R1：操作別resultのfield集合を閉じ、未知fieldを拒否する方針を採用する。操作ごとの具体的なfield集合・型等はまだ未確定で、比較表の全候補fieldを自動採用しない。
- N1：取得不能になり得るmetadataや終端ページtoken等の対象fieldは必須とし、値がない場合はnullで表す。file_id等の操作成立に必要な必須非null値を、nullや欠落で代用しない。対象fieldの正確な集合は操作別契約で確定する。
- D1：同じoperationのresult_kindをplan/executedで区別し、planは別のclosed形とする。未取得のfile ID・bytes・検証成功を捏造しない。plan/executedの各field集合はまだ未確定で、Dry Run Aの副作用禁止・mock/supplied dataの出所制限は維持する。
- R2/N2/D2は今回採用しない。コード/schemaの改訂やadapter接続、PR公開・マージを認可する回答ではない。

### 第4回回答：Drive認証主体・方式・scope

利用者は⑩「I1：両PCで同じprincipal」、⑪「A1：Desktop user OAuth」、⑫「S1：drive.file」と回答した。

- I1：両PCで同じGoogle principalを使う方針。各PCで個別のconsent・安全なcredential保管・失効等を設計し、tokenファイルをコピーして済ませない。Windows accountをPC間で一致させる意味ではない。
- A1：Desktop user OAuthを採用する。SDK/client登録/flow実装、初回consent、通常taskの非対話動作、storeの具体設計は別途確定・検証する。service accountへの自動fallbackはしない。
- S1：drive.fileを採用する方向で限定資格を確認する。既存file・他PC作成file・未mark file等の可視性と4操作への適合は未検証であり、見えないことを不在としない。不適合でもscopeを自動拡大せず停止して新たな判断へ戻す。
- 同じprincipalやscopeの選択は実folderの最小権限・owner/quota・出所・両PC完了を証明しない。削除能力を実装せず、PC-B archive禁止を維持する。
- credential store・実ACL・対象限定試験の計画/実施権限は別。実接続・consent・token取得やproduction uploadは実行/認可していない。配布CI用identity（C-27）への流用も決定していない。

### 第5回回答：credential storeとowner-v2表現・digest

利用者は⑬「T1：Windows user-bound保護store」、⑭「F1：canonicalな10進文字列」、⑮「B1：外部のexact-byte binding」と回答した。

- T1：各PCの実行Windows userに結び付ける保護storeの方向を採用する。具体API/provider・配置・ACL・排他/更新失敗・再consent・backup/復旧は未確定。repo/package/共有Driveへtokenを置かず、別user/PCへtokenをコピーして同じ資格になると仮定しない。
- F1：process生成FILETIMEを符号・先頭ゼロなしのcanonicalな10進文字列で保持し、0や取得不能を有効証拠にしない。元64bit値の精度を保持する。field名・全体集合・required/null/上限等のformal契約と実OS provider資格は別途確定し、この選択だけでv2生成や回復を行わない。
- B1：元recordのexact original bytes全体をhashし、外部snapshot/evidence側へ保持する。record内self-digestは採用しない。digest一致だけで出所・権限・現在性を証明せず、snapshot取得・root/file identity・変更検出・private保全の独立ゲートを維持する。既存metadataのfieldを暗黙追加しない。
- 具体storeやwriter/provider/schemaの実装・実保存・公開・回復は今回認可していない。T2/F2/F3/B2等は未採用比較として保持する。

### 第6回回答：状態遷移・release gate・旧配布物保持

利用者は⑯「候補表をこの条件で採用」、⑰「E1：releaseイベント＋明示手動承認」、⑱「全version保持・自動cleanupなし」と回答した。

- OSD-02：質問時点（main 179787f）のmanifest-state-transition-v1-proposal.mdの候補表を、既承認のOSD-03集約・クラッシュ/排他・verified/failedのterminal性・履歴不変を優先する条件で正式な遷移規則として採用する。表にない遷移は拒否する。新たな遷移/enumを暗黙追加しない。永続記録の具体方式、実装・合成試験・runtime受け入れは未完である。
- E1：maintainer（利用者）を許可主体とし、レビュー済みtagのreleaseイベント＋明示手動承認を起動/承認方式として採用する。tag/VERSION/commit/packageを照合し、通常PR/pushからDriveへuploadしない。E2は未採用。配布用identity・認証・provenanceの具体形式、実workflow・実公開の許可は別である。
- OSD-07：配布packageの全versionを保持し、自動cleanupを導入しない。保持期限/件数の既定値を実装で追加しない。元ログ/Driveログ/private回復証拠の別の保持方針と混同しない。この方針を将来変える場合は新たな明示決定を要する。
- 本選択から、実task登録・release tag作成・配布・保存物削除・本番適用を認可しない。

### 第7回回答：package・設定移行・通知・単独運用

利用者は⑲「PC別・version別manifestでfileを明示列挙」、⑳「別の明示的な移行専用手順/コマンドを設計」、㉑の自由回答で「①」と選択し、続けて本リポジトリでのサブエージェント利用中止と指示文書の修正/アーカイブ化を指示した。

- Package：PC別・version別manifestでfileを明示列挙する方式を採用する。deny-by-default、PC-B archive除外、実設定/ログ/秘密の非同梱を維持する。正式runtime未実装のため、最終実file一覧とmanifest形式・必須/任意依存は完成後に確認する。
- 設定移行：通常更新は実設定を保持して上書きしない。互換性のない設定に対して、version指定・backup・差分・実行前の明示確認を伴う別の移行専用手順/コマンドを設計する。具体的な移行mappingや実移行は未承認・未実施。
- 通知：「①」は提示した第1選択肢のローカル画面通知＋状態表示/ログとして記録する。通常runtimeの失敗・期限到達・保留を対象とし、原本/token/raw例外を露出せず、通知失敗を処理成功にしない。外部mail/メッセージ送信を含めない。Dry Run Aの書込み・永続診断禁止も変更しない。
- 作業体制：本リポジトリでサブエージェントの新規作成・既存再利用・別AIタスクへの委譲を中止し、root単独とする。AGENTS.md、project設定、現行手順/skills/索引を更新し、旧分担・3役割TOMLは失効した履歴へ保全する。旧セッション目標の「既存3担当のみ再利用」は今回指示で撤回され、PR/マージ個別承認と1PR後の中断等の他の境界は維持する。
- root自身の点検を独立レビューと称さない。利用中止前の独立reviewは当時の対象に限り保持し、今回の追加変更へ転用しない。今後の確認は単独運用として記録する。

### 第8回回答：運用条件と具体化の進め方

利用者は「㉒A㉓A㉔A㉕A㉖A㉗A㉘A」「㉙~㉜比較案を提示」と回答した。

- ㉒A：PC-Aの同期処理に続けてarchive可否を判定する方式。別の定期archive taskや手動専用方式は今回採用しない。起動連結はarchive許可ではなく、明示許可・両PC証拠・現在Drive内容の独立検証を維持し、不足時は保留する。PC-Bにarchive能力を追加しない。
- ㉓A：両PCともAC接続時のみ実行する。実行中のAC切断時の停止境界・結果不明な通信の照合・次回補完条件は具体化が残る。電源条件による未実行を成功扱いしない。
- ㉔A：処理のためにスリープから復帰させない。ログオン中のみの既決条件と月内未実行補完を維持する。実際のtrigger登録は未実施。
- ㉕A：4操作のexecuted/planの具体field契約をまとめて作り、利用者へ提示して確定する進め方。未提示field一式の承認ではない。
- ㉖A：Windowsの保護APIで暗号化した専用ファイル方式を選択。T1のWindows user-boundを維持する。具体API・暗号化blob形式・配置・ACL・排他・更新・再consent・backup/復旧は未確定。平文token保存やPC間コピーを許可しない。
- ㉗A：owner-v2のfield契約と実OS providerを分けて段階確定する。F1/B1は維持し、field契約成功を実provider資格へ転用しない。
- ㉘A：E1の明示承認後にGitHub ActionsがDriveへ公開する方式。人がローカルから公開する方式は今回採用しない。配布用principal・認証方式・secret供給・provenanceの具体契約は未確定で、通常PCのOAuth/T1をCIへ流用する決定ではない。
- ㉙〜㉜は比較提示の依頼であり選択済みではない。[比較案](remaining-policy-options-20261024.md)を参照。今回もアプリケーション実装・実task/認証/Drive操作・PR/マージを行わない。

### 第9回回答：㉙〜㉜の全A選択

利用者は㉙A、㉚aA/bA/cA、㉛aA/bA、㉜aA/bAと回答した。[比較資料](remaining-policy-options-20261024.md)の各Aを次の範囲で採用する。

- 29A：manifestをrun結果の正本とし、別versionの補助checkpointへ確認回数・次回確認予定・処理位置等を保存するモデル。checkpointから成功・安全性を認可せず、不一致/欠落を補完しない。29Bの別追記専用遷移履歴は採用しない。必要な遷移検査を満たせなければ判断へ戻し、既承認C1〜C4を省略しない。
- 30aA：Google公式Python clientを採用する。具体package/版・OAuth flow・token refresh通信・retry/page等の暗黙動作の制御/資格確認は別途残る。
- 30bA：初期uploadはmultipart・5 MB以下に限定し、超過はupload前に保留する。resumableへの自動fallbackはしない。MBの正確なbyte境界・対象fileのsize/使用点検査は具体契約で確定し、実装都合で先決めしない。
- 30cA：固定error codeごとの厳格なretryable真偽表を採用する。DRIVE_TRANSIENT_FAILUREのみtrue、その他の既存固定error codeはfalseとする。unknown code/真偽矛盾を拒否し、trueでもupload結果不明時の照合前再送は禁止。OPERATION_TIMEOUTからの自動再送や結果不明からfailedへの昇格を許可しない。PSのみ最大4回・1/5/15分待機の既決条件を維持する。
- 31aA：PC別/version別の明示file manifestはstrict JSON＋JSON Schema方式を採用する。field名・digest・必須/任意依存・最終実file一覧は別途確定する。
- 31bA：設定移行は専用PowerShellコマンドを入口とし、移行元/先version指定・backup・差分提示・実行前の明示確認を必須とする。通常更新の実設定保持を維持し、具体mapping/原本保全/失敗復旧/コマンド名は未確定、実移行は行わない。
- 32aA：Windows App SDKのローカルapp通知helper方式を採用する。具体API/登録・配布依存/対象PS環境の資格確認・helper寿命等は未確定。WinForms balloonへの自動fallbackを追加しない。
- 32bA：同一未解決事象の画面通知は初回と状態変化/悪化時とし、同じ未解決状態だけを理由に毎回再通知しない。状態/ログでは継続表示する。重複抑制key・永続化・送信失敗時の再扱いは別途確定し、通知API成功を閲覧証拠にせず、通知失敗を処理成功にしない。

すべて方針選択であり、未提示のfield/API設定/資格・実装の完成ではない。アプリケーションコード/schema/tests・実task/認証/Drive/本番操作、PR/マージは今回行わない。

### 第10回指示：現行実装から4件を具体化

利用者の「4つの具体案を確定させる」を受け、[限定4件の具体決定](implementation-grounded-four-decisions-20261024.md)を現物と既承認方針に基づいて記録した。(1)固定code別retryable真偽表、(2)PC-A確認予算checkpointの最小field/拒否境界、(3)version 0.1.0の現行**非配布レビュー**package 40ファイル、(4)owner record v1の互換境界である。正式runtimeの最終package一覧とowner-v2全field/providerは対象外として残す。決定に対するコード/schema/testsの追従は未実施であり、実接続・実保存・PR/マージを認可しない。

## 2. B2 V1の意味と保全

- validation.statusがcompletedとは、対象入力の分類処理を全て完了したことを表す。invalid/relevant errorを発見しなかったという意味にはしない。
- エラーはinvalid_relevant_countとerrors等の既存情報へ保持する。completedでもエラーを消さず、run成功やno_workへ昇格しない。
- 既存schemaのfield集合とstatus値を維持する方向であり、未知fieldや暗黙の新versionを追加しない。
- 過去のincomplete recordは書き換えず、件数やdigestの一致だけでcompletedへ昇格しない。incomplete/failedから網羅性を補完しない。
- 既知期間のcompleteには、完全なeligible inventory・error scope・全件の結果照合など、既承認OSD-03の条件を別途満たす必要がある。status文字列だけを根拠にしない。
- 現source builderはエラーがあるとincompleteを出力する。今回の選択へ追従するproducer/consumer・文書・合成試験の改訂は未実装である。

参照：[B2と時刻の比較](b2-validation-coverage-report-time-options.md)、[B2契約](../design/run-input-evidence-v1-proposal.md)、[OSD-03](osd-03-status-aggregation-options.md)。

## 3. G1の確定規則

質問で示した「manifestとB2の終了UTCの遅い方、同時ならmanifestの元表記」を次のfieldへ適用する。

1. exact immutable manifestのfinished_at_utcと、exact immutable B2のenumeration.finished_at_utcを使う。
2. 有効なUTC instantとして、既存の検査・対応精度を保って比較する。丸め・切捨てをしない。
3. 遅い方の元の日時文字列をgenerated_at_utcとする。同じinstantならmanifest.finished_at_utcの元表記を採る。
4. これは不変入力の基準時刻で、reportの実書出時刻・鮮度・cloud観測時刻の証明ではない。
5. 必要な値の欠落・不正・既存時刻整合の矛盾では停止する。実時計、仮値、別の保存物で補完しない。
6. 信頼できる現在UTC、既存の未来許容、start/finish順序、exact inputsのidentity/digest等の検査は維持する。historical evidenceを古さだけで失効させない。

R5のexact manifest＋B2による再生成、同一identity同一bytesの冪等性・異なるbytesのconflictを維持し、G2/G3の方式は採用しない。現builderは生成UTCをcallerから受け取る実装のままで、G1の導出・不一致拒否や正式再生成への追従は未実装である。過去reportをこの規則へ黙って書き換えない。

参照：[report契約](../design/aggregation-report-v1-proposal.md)。

## 4. 残る確認と実施範囲

①〜㉜の提示済み選択は第1〜9回回答で確定した。第10回指示で現行実装由来の4件を限定確定した。具体store API/配置/ACL/lifecycle、SDK版/OAuth flow/暗黙通信制御、owner-v2全fieldと適格provider、C-02の4操作の具体field集合、checkpoint永続writer/root/FS資格、5 MBの正確なbyte境界、CI配布identity/認証/provenance、正式runtimeの最終file一覧/manifest field/移行mapping、通知登録/重複抑制/送信失敗時の扱い、AC切断/停止境界・具体trigger等は別途具体化する。方針選択を詳細契約・実装・資格確認の完了とは扱わない。仕様決定の記録と利用中止の指示文書/Codex project設定改訂だけを行い、アプリケーションコード/runtime schema/tests/実設定の変更、PR公開・マージ、実接続・本番適用は行っていない。

## 5. 記録変更の検証とレビュー範囲

利用中止前の独立reviewは当時の対象差分に限る。invariantsの節分断P3と旧承認待ち表記P2を修正したが、⑬以降や単独運用改訂を含む最新全差分の独立レビューは実施していない。rootが回答・規範・現実装未追従・権限境界を単独で再確認した。

文書/指示・Codex project設定のみの変更のため、無関係な機能/package検査は再実行していない。変更20 Markdownの相対リンク189件欠落0、差分検査成功。project TOMLのagents.enabled=false・思考量不変、active役割TOMLなし、旧3定義の移動前後hashとGit改行正規化後の本文一致/parse、旧手順のbanner/相対リンク以外の本文一致を確認した。Git blobと作業コピーの改行差を考慮して照合し、移動に伴う本文変更がないことを分離検証した。設定の現在会話/全クライアントへの即時反映は未検証である。
