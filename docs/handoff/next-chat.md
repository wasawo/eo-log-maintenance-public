# 現在の引き継ぎ

更新日: 2026-10-27（日本時間）

恒久ルール: [AGENTS.md](../../AGENTS.md)。旧記録: [アーカイブ](archive/pre-agents-history.md)。
正本は Public の `wasawo/eo-log-maintenance-public`。元リポジトリは Private のまま。
この文書の状態は記録コミット時点。実際のmain/PR/CIは作業開始時に照合する。

## 最新基準と今回の作業

### Q12: 両経路の確認済み対象元は直接削除（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`06d2356`から継続。利用者がQ12で両経路とも「ごみ箱を経由せず、確認済みの対象ファイルだけを直接削除する」方式を明示確認。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.13と[詳細設計](../design/move-source-destination-verification.md)§17/初回移動計画/実装計画/開発参照表へ反映した。
- Q5/役割制限は維持し、ごみ箱移動や元フォルダからの消失だけで完了としない。ごみ箱全体消去・フォルダ再帰削除・対象外清掃は含めない。Q11の照合完了も直接削除に対応する元不在の確認が必要。
- 提示済みの未回答質問はない。次は直接削除を前提に記録の型/版・実API/FSの不在/版固定保証・経路間照合を具体化する。T0と実装再開は未完。コード/schema・実データ操作なし。
- 変更6文書の相対リンク211件の参照先欠落0、`git diff --check`成功。Q12確定とQ5/役割/対象限定の維持、実装/実データ操作との区別を自己点検した。文書のみのため無関係な全suiteは実行していない。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### 記録形式・状態・削除応答の契約候補を整理（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`8610e5b`から継続。利用者の次の整理指示を受け、[詳細設計](../design/move-source-destination-verification.md)§14〜18へ不変のJSONイベント/情報群/状態/adapter応答の候補を追記。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.13、初回移動計画、開発参照表へ接続した。
- 要求の成否・元存在・保存先内容・移動結果・完了根拠を分離する案。現manifest v1/IPC 1.0の意味を変えず、schema/コード変更なし。公式エラー仕様のDrive 404は不存在/読取権限なしの両方を含むため、単独でQ11の不在確認にしない。
- **Q12提示・回答待ち**: ごみ箱内も容量に算入する公式情報を踏まえ、両経路の元はQ5/役割条件を満たした対象だけ直接削除するか。未回答の間は方式を採用済みとしない。次は回答反映、正確な型/版・実API/FSの不在/版固定保証・経路間照合を整理する。T0/実装再開は未完、実データ操作なし。
- 変更5文書の相対リンク200件の参照先欠落0、`git diff --check`成功。JSON外形/状態候補と現schemaの分離、404/権限不足の非完了、Q12未回答の方式非採用を自己点検した。文書のみのため無関係な全suiteは実行していない。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### 削除前後の記録と照合による完了を整理（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`8f35128`から継続。利用者の次の整理指示を受け、[詳細設計](../design/move-source-destination-verification.md)§9〜13へ必要記録・操作順・照合表・試験案を追加。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.12、AC-08、実装計画、開発参照表へ接続した。
- **Q11回答受領**: 利用者は「条件がそろえば照合による移動完了にする」を選択。有効な元/保存先・コピー内容の対応記録、元の確実な不在、現在の保存先一致がそろう場合に限り照合完了。元が見えないだけ/権限不足等は含めず、前回削除要求の成功を断定しない。
- 記録だけで削除を再送しない。削除前の必要記録保存失敗は元保全、削除後の結果記録失敗は照合へ回す案。旧履歴を上書きせず、新しい元実体と旧対象も区別する。記録形式/永続化/状態/IPC/実APIの不在確認・次経路へ移動済みの場合の照合は未設計。T0は未完。
- 提示済みの未回答質問はない。次は記録形式/状態と削除応答/不在確認契約、経路をまたぐ照合を具体化する。コード/schema・実データ操作なし。実装再開指示も未受領。
- 変更6文書の相対リンク206件の参照先欠落0、`git diff --check`成功。Q11の完了条件と削除成功の区別、予定記録の非認可、旧履歴保全を自己点検した。文書のみのため無関係な全suiteは実行していない。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### 元/保存先の識別とQ5確認方式を整理（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`1402600`から継続。利用者の「次の整理に入って」を受け、[移動元・保存先の識別と削除前確認案](../design/move-source-destination-verification.md)を作成。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.11/初回移動計画/開発参照表からつないだ。
- 論理位置/実体を区別し、コピー対象内容・保存先内容・削除直前の元内容の一致とidentityを対応付ける案。既存先再利用でも今回の元確認を行う。ローカル再読取/Drive現在hashまたはdownloadを候補とし、現在のhelperを削除認可へ変更しない。
- Google/Microsoft公式資料だけを参照してDrive version/hash・files.deleteの永久削除・ハンドル対象操作の候補を調査。version固定で削除できる保証、実FS/SDK動作は未確認。具体API/排他/永久削除またはごみ箱の採否は未決。実データ操作・コード/schema変更なし。
- 提示済みの未回答質問はない。次は確認した実体と削除対象の結合、削除前後の永続記録と結果不明照合、API能力/方式を具体化する。T0/実装再開は未完。
- 新規設計案を含む変更5文書の相対リンク194件の参照先欠落0、`git diff --check`成功。公式資料の能力と推測/未確認、既存資産の非認可と方式未確定を自己点検した。文書のみのため無関係な全suiteは実行していない。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### 旧仕様の矛盾を合意範囲で解消（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`1cdbe04`から継続。利用者の「旧仕様の矛盾解消を実施」を受け、[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.10に変更点と維持境界を記録。全面削除禁止→2経路/Q5の限定削除、両PC待機→現在対象の個別処理、自動suffix→異内容保留を現行文書へ反映した。
- README/実装計画/主要設計/配布/試験案と要件台帳13行・P0-012を更新。runtime試験の既存19ケースは期待結果のみ更新し、全て未実行。現v1 schema/helperの契約/コード/試験は不変で、verified/report/latest選択を元削除完了としない互換境界を記した。過去の承認/監査は当時の範囲で保持。
- T0の方針整合は進めたが、新しい削除/identity/Q5方式/状態/記録/IPC/権限・最終配布の詳細契約は未完でT0を閉鎖しない。次は元/保存先の識別とQ5確認から具体化する。提示済みの未回答質問はなく、旧方針の再承認は求めない。実装再開指示・実データ操作なし。
- 変更24文書の相対リンク346件の参照先欠落0、`git diff --check`成功。既存IDと未受け入れ状態、版固定の現schema/helper制約、過去証拠の範囲を自己点検した。文書のみのため無関係な全suiteは実行していない。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### 初回移動の受け入れ条件・優先タスクを整理（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`8a2efbe`から継続。直前の受け入れ条件/タスク整理への利用者の「OK進めて」を受け、[初回移動計画案](../development/initial-move-delivery-plan-20261027.md)を作成。両経路の元削除までを初回完成とし、AC-01〜12/T0〜T5、既存ID対応、詳細設計の残件をまとめた。全ACは未実行。
- 実装計画の役割・3層保持・削除境界・Bの禁止範囲をQ1〜Q10へ整合。要件/P0台帳へ変更対象を通知し、開発参照表/文書索引/再確認台帳から計画へリンクした。旧phase/ID本文/各設計・契約全体の整合は未完で、計画T0として継続する。P0閉鎖やruntime受け入れ済みとはしない。
- 提示済みの未回答質問はない。次はT0の正本整合と2経路の詳細契約を具体化する。計画案の順序/詳細契約の確定と実装再開指示は未完。「OK進めて」をコード実装/実データ削除の許可へ拡張しない。定期実行と専用競合解消ツールは後続候補。
- 新規計画を含む変更8文書の相対リンク317件の参照先欠落0、`git diff --check`成功。文書のみのため無関係な全suiteは実行していない。コード/schema・実データ操作なし。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### Q10: 初回の競合対応範囲を確認（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`4cab216`から継続。利用者がQ10で「概要・詳細レポートと通常再実行までにする」を選択。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.9と実装計画§2.4へ反映した。
- 初回は画面の概要＋ローカル詳細レポートで比較対象と理由を示し、利用者が内容の扱いを判断し、解消後に同じ移動処理を再実行する。自動解消は行わず、専用比較・解消ツールは後続候補。表示項目/状態対応・保存形式/保持期間・手動解消の具体手順は未決のまま。
- 提示済みの未回答質問はない。次は利用シナリオ全体の受け入れ条件と優先タスクをまとめ、既存要件/設計/計画の変更点と未決詳細を対応付ける。実装再開用の計画は未確定。コード/schema・実データ操作なし。
- 変更3文書の相対リンク152件の参照先欠落0、`git diff --check`成功。文書のみのため無関係な全suiteは実行していない。同branchへローカルコミットを蓄積し、PRはまとめる。root自己点検のみ、独立レビューなし。今回push/PR/mergeなし。

### 競合確認と結果表示を整理（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`b954665`から継続。利用者の「次の整理」を受け、[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.9へ競合の確認→利用者判断→解消後再実行と、概要/ローカル詳細レポートの案を記録した。
- 既存のファイル名規則・manifest/run状態・競合規則と照合。単純なsuffix改名を手動解消の定型手順にせず、両内容を残す名前付けは未設計とした。完了数は元削除済みの元件数で、保存先件数と区別。表示名はschema enumの追加ではない。
- **Q10提示・回答待ち**: 初回の支援は概要＋ローカル詳細レポートと通常再実行までにするか、専用の比較・解消操作も必要か。次は回答を記録し、利用シナリオ全体の受け入れ条件と優先タスクへまとめる。具体表示/保持/状態対応等と手動解消手順は未決。
- 変更2文書の相対リンク144件の参照先欠落0、`git diff --check`成功。文書のみのため無関係な全suiteは実行していない。コード/schema・実データ操作なし。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### Q9: 通常失敗後は同じ移動処理を再実行（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`ca286f3`から継続。利用者がQ9で「同じ移動処理の再実行で残りを進める」を選択。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.8と実装計画§2.4へ操作方針を反映した。
- 通常のファイル失敗/元削除失敗は同じ入口で現在の元/保存先を再確認し、同内容は再利用、Q5の削除条件は元ごとに確認する。競合/確認不能分は保持して表示。強制終了後のロック等が残る場合の明示回復は別扱いで、解除条件を変えていない。
- 提示済みの未回答質問はない。次は競合の確認/解消手順と結果の表示を具体化する。結果不明の確定方法・記録形式・削除API等の詳細は未設計。コード/schema・実データ操作なし。
- 変更3文書の相対リンク146件の参照先欠落0、`git diff --check`成功。文書のみのため無関係な全suiteは実行していない。同branchへローカルコミットを蓄積し、PRはまとめる。root自己点検のみ、独立レビューなし。今回push/PR/mergeなし。

### 失敗・中断後の再実行を整理（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`1fd3d8c`から継続。利用者の「次の整理」を受け、[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.8へ現在状態に基づく再実行・元削除未了/結果不明・全体停止と個別失敗の区別・受け入れ例を記録した。
- PS/Pythonの既存retry契約、正式入口gate、明示回復コマンド設計を照合。通常の再実行と強制終了後の回復を区別し、既存の所有権/lock回復条件やAPI試行回数は変更していない。新しい削除操作・照合記録・両経路の記録対応の詳細は未設計。
- **Q9提示・回答待ち**: 通常のファイル失敗/元削除失敗は、同じ移動処理を再実行して残りを進める運用か。専用回復手順を解除する質問ではない。次は回答を記録し、競合の確認/解消手順と結果の表示を具体化する。
- 変更2文書の相対リンク139件の参照先欠落0、`git diff --check`成功。文書のみのため無関係な全suiteは実行していない。コード/schema・実データ操作なし。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### 同名ファイルの処理案を整理（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`585ca48`から継続。利用者の同名ファイル整理指示を受け、[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.7へ両経路の判定表・複数元・再実行との接続・受け入れ例を提案として記録した。
- 既存実装計画§2.4の同内容再コピー省略・異内容の`_PCA`/`_PCB`別名保存、Drive比較helperの候補一意性/非認可、PS/Python責務を照合。同一PC内の別階層にも衝突するため旧suffixだけで全件解決できない点を明示。
- **Q8回答受領**: 同内容の保存先再利用を前提に、利用者は「異内容は元を残して競合表示する」を選択。初回完成では自動suffix保存を行わない方針を台帳と実装計画§2.4へ反映した。元ごとのQ5確認は維持。同時実行/事前発見グループ・手動解消/再実行の詳細は未完。提示済みの未回答質問はなく、次は失敗・中断・削除未了からの再実行と競合の確認/解消手順を整理する。コード/schemaは変更していない。
- 変更3文書の相対リンク140件の参照先欠落0、`git diff --check`成功。文書のみのため無関係な全suiteは実行していない。root自己点検のみ、独立レビューなし。実データ操作なし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### 既存サブフォルダも保持せず集約（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`e02c23d`から継続。利用者が既存サブフォルダの構成も保持せずファイル単位で共通フォルダへ集約したいと明示した。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.6に両経路の平坦化と例を記録し、前回の相対階層保持案を不採用へ更新した。
- 元ファイルの識別には元相対パス等が引き続き必要で、保存先名だけから削除元を推測しない。同一PC内の別サブフォルダ間も同名競合の対象となる。共用・改名・異内容競合・再実行の詳細は未決。管理記録の階層変更や空フォルダ削除は今回の要件に含めない。
- 提示済みの未回答質問はない。次は同名同内容/異内容・コピー済みで元が残る場合と元/保存先の対応記録を整理する。コード/schema/config変更・実データ操作なし。相対パスを扱う既存契約は今後の照合対象。
- 変更2文書の相対リンク131件の参照先欠落0、`git diff --check`成功。文書のみのため無関係な全suiteは実行していない。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRはまとめる。今回push/PR/mergeなし。

### 保存先の共通構成を確認（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`d969666`から継続。利用者の「保存先の構成から」を受け、README・A/B公開設定例・設定root設計と既存の再帰列挙方針を照合した。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.6へ論理構成図と設定の対応、管理記録との分離を記録。
- **Q7回答受領**: 利用者は「ログ種別ごとの共通フォルダに集約する」を選択。クラウド/A archiveともBattleLog・ErrorReportごとの共通保存先を維持し、PC別サブフォルダや新しい年別フォルダは設けない。元の既存サブフォルダの平坦化、同名同内容の共用/再利用、異内容競合の解消は未決として区別した。
- 提示済みの未回答質問はない。次は相対階層の対応、同名同内容/異内容・コピー済みで元が残る場合の具体化。コード/schema/config変更・フォルダ作成・実データ操作なし。今回の構成は既存設定例と一致し、再配置は行わない。
- 変更2文書の相対リンク130件の参照先欠落0、`git diff --check`成功。文書のみのため無関係な全suiteは実行していない。同branchへローカルコミットを蓄積する。root自己点検のみ、独立レビューなし。PRは再確認の区切りでまとめ、今回push/PR/mergeなし。

### 移動フローの整理（2026-10-27）

- cleanな同branch `docs/requirements-design-task-review`、基準`2b7a3f0`から継続。利用者の「移動フローの整理から」を受け、[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.5に両経路・期間条件・ファイルごとの処理・失敗分岐・受け入れ例を追記した。Q1〜Q5は維持し、新しい再実行方式・入口/順序等は提案/未決と区別した。
- 既存のファイル名/期間仕様、runtime gate、staging lifecycle、PS/Python契約を対象箇所で照合。期間選択と同名異内容の上書き禁止は維持。旧copy-only・両PC証拠待機と衝突する箇所を記録し、詳細契約全体の改訂済みとはしていない。
- フロー整理を`0500b3b`へコミットした後、**Q6回答を受領**: 利用者は「古いログも必ずクラウド経由にする」を選択。A/Bとも端末→クラウド→A archiveとし、直接archive経路は設けないことを台帳へ反映した。提示済みの未回答質問はない。次は保存先の構成と競合/再実行の具体化へ進む。コード/schema変更・実データ操作は行わない。
- 変更2文書の相対リンク125件の参照先欠落0、`git diff --check`成功。root自己点検のみ、独立レビューなし。文書のみのため無関係な全suiteは実行していない。同branchへのローカルコミットを継続し、PRはまとめる。今回push/PR/mergeなし。

### 恒久規則の限定改訂を明示承認後に適用（2026-10-27）

- 同branch `docs/requirements-design-task-review`、基準`64cb4f9`から継続。利用者が[再確認台帳](../development/requirements-design-task-review-20261027.md)§2.4の全文案について「提示案で恒久ルール自体の改訂を承認する」と明示回答した。同じ案を適用し、AGENTSの「維持する境界」先頭1項のみを承認済みの2項へ置換した。他の恒久規則は変更していない。
- 前回のauto-review拒否後に追加の明示承認を受け、同じ変更案が適用された。承認待ちは解消済みで、再承認を求めない。Q1〜Q5の確認内容と実装停止は維持し、コード/schema・実ログ/本番Driveの操作は行っていない。
- 台帳に承認・適用を記録し、README/実装計画/決定台帳の冒頭通知を更新した。本文全体・詳細契約・要件/設計/タスクの再照合は未完。次は移動フロー、同名競合・コピー済み/削除未了の再実行と受け入れシナリオを既存仕様と照合して整理する。提示済みの未回答質問はなく、新規helper実装へ進まない。
- 今回は文書のみ。変更6文書の相対リンク160件の参照先欠落0、`git diff --check`成功。root自己点検のみ、独立レビューなし。無関係な全suiteは実行していない。同branchへローカルコミットを蓄積し、PRは再確認の区切りでまとめる。今回push/新PR/mergeは行わない。

### Q5: 削除前の2条件を確認・恒久規則改訂の明示承認待ち（2026-10-27）

- 同branch `docs/requirements-design-task-review`、基準`892995f`から文書/対話を継続。利用者が削除要件を「保存先の内容一致」と「削除直前の元ログがコピー時から変わっていないこと」の両方を確認できたfileだけ、確認不能なら元を残す、と明示指定した。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2の確定要件とQ5判断記録、README/実装計画/決定台帳の再確認通知へ反映した。
- size/更新時刻だけで十分、常時2回full hash等の方式は採用していない。2条件を満たす確認方式・対象同一性・削除API・再実行/競合等の具体設計は未完。Q1〜Q4の目的・手動初回完成・両PC待機不要・file単位完了は維持。現在は文書のみでコード/実データ操作を行わない。
- Q5の明示指定を根拠に、AGENTS先頭1項を「2経路・2条件・PC-B役割制限」と「文書見直し中は削除コード追加/実データ操作へ進まない」の2項へ限定改訂するpatchを再試行したがauto-reviewで拒否された。今回は、要件承認と恒久ルール自体の変更承認は別で明示証拠がないという理由。patchは未適用で、迂回しない。台帳§2.4へ置換全文・変更対象/影響を保存し、利用者へ恒久ルール自体の改訂承認を質問した。まだ回答待ちで、要件合意から規則変更承認を推測しない。
- 次はこの承認回答を受ける。承認なら台帳の全文案と同じ先頭1項の限定変更だけを適用し、再度auto-reviewで確認する。承認されなくてもQ1〜Q5の要求記録は保持し、規則改訂は未完として対話を続ける。実装再開/本番操作の指示へ拡張しない。
- 今回は文書のみ。変更5文書の相対リンク152件欠落0・git diff --check成功。root自己点検のみ、独立レビューなし。無関係な全suiteは再実行せず同branchへローカルコミットを蓄積する。PRは再確認の区切りでまとめ、現時点でpush/新PR/mergeを行わない。

### Q5: 保存先一致のみと移動元変更の懸念を説明中（2026-10-27）

- 同branch `docs/requirements-design-task-review`、基準`2aaa4f5`から文書/対話を継続。利用者は「保存先の内容一致のみで十分だと考えているが、後者（削除直前の元変更確認）を外した懸念はあるか」と質問。Q5の最終採否回答ではなく、意見と懸念の照会として扱う。
- [再確認台帳のQ5](../development/requirements-design-task-review-20261027.md#現在の質問)へ、比較時点の違いを記録。コピー時snapshotとの保存先一致だけでは、その後元へ追記/差替えされた未保存内容を削除し得る。削除直前の元と保存先を内容比較するなら元変更確認を含められ、独立のfull hashを重ねる必要はない。ただし確認と削除の間の変更可能性は残る。
- 過去分ログの処理中変更は実ログで観測した事実ではなく、禁止/不変前提が未確認のため説明した可能性。元size/更新時刻等の軽い変更検出をrootの省力案として記載し、metadataでは全変更/原子性を保証しないことも記録。採用/省略・許容リスクは未決。新規helper・排他方式・再hashの一律追加へ進まない。
- 次は利用者の意見を受け、Q5の確認意味と必要な前提を揃える。Q1〜Q4の合意（削除込み手動移動・両PC待機不要・file単位完了）は維持。恒久安全規則の改訂未完と前回auto-review拒否の記録も維持し、コード/実データ/規則の変更は行わない。
- 今回は文書のみ。変更2文書の相対リンク119件欠落0・git diff --check成功。root自己点検のみ、独立レビューなし。無関係な全suiteは再実行せず、同branchへローカルコミットを蓄積する。PRは再確認の区切りでまとめ、現時点でpush/新PR/mergeを行わない。

### 完成目的・初回移動・archive待機・file単位完了の確認（2026-10-27）

- 同branch `docs/requirements-design-task-review`、基準`ffd118f`から文書/対話を継続。利用者のQ1回答は、両端末の偏在ログをクラウドへ集約、古い分をPC-A archiveへ、移動後の元ログ削除による容量削減、最終的な定期実行で3層配置を維持すること。[再確認台帳](../development/requirements-design-task-review-20261027.md)§2へ記録した。
- **確認済みQ2**: 最初の完成は手動実行で両端末→クラウド/クラウド→PC-Aのcopy・保存先確認・元削除まで。定期実行は後続。**Q3**: PC-B未実行でもクラウドにある古い分から移し、Bの遅着分は次回。両PCの期間完了待ちは不要。**Q4**: file単位で完了し、失敗/不明分は元を残して次回処理。コピーだけ/両PC全体待ちへ戻さず、これらを目的・受け入れ条件の中心に据える。
- 旧no-delete/PC-B一切削除禁止/両PC期間待ちとの衝突を台帳へ明示。AGENTS等の恒久的な削除禁止を外すpatchはauto-reviewで拒否された。理由は削除詳細条件未確定のまま将来実装を広く許可する持続的境界変更になるため。該当patchは未適用・迂回しない。代わりに要求/改訂対象の記録と、README/実装計画/決定台帳への再確認中通知を追加した。要件としての合意は保持し、恒久規則の改訂完了・削除実装済み/実データ操作認可とは記載しない。
- **次の問いQ5**: 保存先の内容一致と、削除直前の移動元がコピー対象から変わっていないことを確認できたfileだけ元を削除し、不明なら残す、という最低条件でよいか。具体案はクラウド実体/保存後archiveのsize・SHA-256確認。まだ回答待ち。回答を文書化し、削除条件・役割・対象同一性・再実行/競合を具体化してから恒久規則の改訂案を扱う。新規helper実装を自動選択しない。
- 今回は文書のみ。変更5文書の相対リンク150件欠落0・git diff --check成功。実ログ/本番Drive操作・コード/schema/test変更なし。無関係な全suiteは再実行しない。root自己点検のみ、独立レビューなし。同branchへローカルコミットを蓄積し、PRは再確認の区切りでまとめる。現時点でpush・新PR・mergeは行わない。

### 要件・設計・タスクを利用者と再確認中（2026-10-27）

- 利用者は「末節に拘りすぎて本来作りたいものと乖離し始めている気がする」と懸念を示し、壁打ちによる要件定義/設計/タスクの再確認、内容の文書化、文書用branchでの蓄積・PRをまとめる運用を明示指示した。新しいhelper実装の自動選択を止め、今回は文書/対話を進める。
- 正本GitHub/local/origin mainの`27e99fec11fd6dbf80f8b35bde9cbcf2ed24d154`（PR #46）を照合・fetchし、cleanなmainからupstreamなしで`docs/requirements-design-task-review`を作成した。PR #46はmerge済み、PR/mainの両CI成功。マージ済み実装branchは再利用しない。
- [再確認台帳](../development/requirements-design-task-review-20261027.md)に開始指示、現行文書からの完成像/役割/期間/初回完成の読み取り、現在地、rootの乖離診断・進め方案、質問/判断記録、既存文書への反映先を記載。文書索引と開発参照表からリンクした。現行要件の変更合意・実装計画の確定・全仕様の再監査はまだ行っていない。
- **現在の質問はQ1**: 本来いちばん解決したい困りごとと、最初の完成と判断する利用の流れ。完成像の読み取りへの訂正。質問は利用者へ提示済みで回答待ち。無回答/旧文書を今回の再合意へ変換しない。回答を受けたら台帳へ保存し、まず利用シナリオ、次に要件/設計/タスクを照合する。細かな技術選択の再質問や新規安全helper追加から再開しない。
- 利用者の回答・判断理由・影響先を毎回文書へ残し、確定内容を既存正本へ反映する。提案と未決を既決として扱わない。現行のno-delete/PC-B archive禁止等は明示変更合意まで維持。実ログ/Drive接続や本番適用を行う指示ではない。
- 今回は文書のみ。変更4文書の相対リンク232件欠落0・記述整合・git diff --check成功。無関係なPython/PS全検査は再実行しない。root自己点検のみ、独立レビューなし。このbranchへローカルコミットを蓄積し、再確認の区切りでPRをまとめる。現時点でpush・新PR・mergeは行わない。

### 累積PR・マージ承認と統合検証（2026-10-27）

- 利用者がここまでの累積コミットをまとめたPR作成→マージを明示指示。正本GitHub/local/origin mainの`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）と、cleanなbranch `codex/source-inventory-budgets`の`2d23d13`を照合した。実装13コミット・34 filesと本記録を同じPRにまとめ、最新PR HEADのValidate/Package Validation両成功を確認後squash mergeする。本記録時点は未push/未PR/未マージ。結果のPR/merge SHA・CIはGitHub実状態と本チャット最終報告/PR本文を照合する。
- 範囲：source再帰列挙/適格hash予算と再観測5入口への伝播、download計画事前集計と呼出し内比較再利用、marker-lastのbasename共通検査・marker込み公開bytes予算、隔離保存の公開/読戻し/owner予算接続、owner recordの安定読取・short write/作成失敗保全・厳密mutex応答/中断cleanup、復旧schemaのlocal-only参照/外部取得禁止。EOLM-FIL-005/007・EOLM-SYN-007/008/OSD-01等の既存境界を補助し、要件全体/P0閉鎖へ昇格しない。
- Python 3.11.9実体（shim版未選択のため個人設定を変えず指定、CIは3.12）で`$env:PYTHONPATH='tests;.'`後、`& $python311 -B -m unittest discover -s tests -p 'test_*.py'`の940件中938成功・既存symlink作成不可2skip。既知hardlink sandbox制約を避けauto-review承認済みsandbox外で合成データ/自作tempだけを使用。PowerShell 7.6.7を版確認し`pwsh -NoLogo -NoProfile -File tests/Test-ReleasePackage.ps1`の両role回帰成功。累積変更6 Markdownの相対リンク209件欠落0、`git diff --check origin/main...HEAD`成功。root自己点検のみ、独立レビューなし。個別単位の失敗/修正/再実行/環境差は下記の履歴に保持する。
- schema/PS/CI定義・既存配布file集合50件は不変。固定本番値、正式runtime/SDK/credential/C-02/writer/CAS/receiptやprivate保存/owner-v2/provider資格を新設しない。root/ACL/FS/owner/時計等の真正性、現在性/ABA・電源断/両PC/Tier B/C/runtime受け入れは未完。実ログ/本番Driveは使わず、PC-B archive/元ログ・Driveログ削除/本番適用の認可を追加しない。
- マージ後は次実装を始めず、本作業を終了する。作業branchは保持し、次実装は利用者指示を受けて最新mainから新branchで行う。

### private証拠・crash判定schemaの外部取得禁止（2026-10-27）

- 利用者の次作業指示を受け、cleanな`16b7e7b`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [復旧schemaのlocal-only参照](../../Common/README.md#local-only-recovery-schema-references-2026-10-27)をprivate evidence build/validateとcrash classifierのprior manifest検査へ適用。既存selectorの全tree参照検査と取得禁止Registryを再利用し、非local/不正`$ref` / `$dynamicRef`を未使用defs内でも拒否する。privateは既存`private_evidence_invalid`、crashは既存`prior_manifest_invalid_or_not_running`に閉じ、正常local fragment・元metadata/raw/prior bytes・既存非認可/保全を維持する。
- 既存Python 3.11.9実体（shim版未選択のため設定変更せず指定、CIは3.12）で`$env:PYTHONPATH='tests;.'`後、`& $python311 -B -m unittest test_private_recovery_evidence test_crash_recovery_decision test_manifest_recovery_integration test_latest_manifest_selection test_aggregation_report_builder test_owned_publication_integration test_recovery_diagnostic_mutex`の121件全成功・skipなし。既知sandbox hardlink拒否を避けauto-review承認済みのsandbox外・自作temp/合成入力だけを使用。既存CI登録suiteへ新規6件を追加し、HTTP/file/相対/不正値/未使用参照、破損local/invalid schema、正常local、事前検査を迂回した場合のRegistry拒否をsocket非呼出しで確認。変更3文書の相対リンク146件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- schema取得制限であり、schema真正性/資源上限・private保存/ACL/owner-v2/provider資格、実復旧/次run認可、現在性/ABA・電源断/Tier B/C/runtime受け入れや要件全体/P0-010閉鎖は未実装・未実証。既存依存/配布file集合・schema/C-02/SDK・固定本番値は不変。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchで累積source/公開/owner/復旧境界と未決runtime契約を照合して次単位を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### record cleanup中断後のmutex解放試行（2026-10-27）

- 利用者の次作業指示を受け、cleanな`cd703dc`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [record cleanup中断時のmutex処理](../../Common/README.md#mutex-cleanup-after-record-cleanup-interruption-2026-10-27)としてrecordの解放時観測/unlinkを外側finallyで囲み、KeyboardInterrupt/SystemExit等でも後続のmutex release・closeを試みる。release自体の失敗/中断でもcloseを試みる順序、通常の所有確認/cleanupとOSError時のrecord保全を維持する。中断は正常終了へ変換しない。
- 既存Python 3.11.9実体（shim版未選択のため設定変更せず指定、CIは3.12）で`$env:PYTHONPATH='tests;.'`後、`& $python311 -B -m unittest test_owned_run_lock test_owned_publication_integration test_recovery_diagnostic_mutex test_terminal_bundle_integration test_terminal_history_usepoint test_terminal_plan_usepoint test_initial_source_integration test_initial_source_usepoint test_internal_publication_crash test_crash_publication_harness test_download_staging_integration`の128件全成功・skipなし。既知sandbox hardlink拒否を避けauto-review承認済みのsandbox外・自作temp/合成adapterだけを使用。既存CI登録suiteに新規4件を追加し、record観測/unlink中断・release失敗/中断とclose、unlink OSError時のbody例外/record保全、両PCの候補公開後中断と実mutex再取得を確認した。変更2文書の相対リンク136件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- 通常終了/中断でのcleanup試行経路を守る補助であり、強制process終了・電源断時のfinally実行や耐久性を証明しない。schema/owner-v2/SDK/配布集合・固定本番値、新しい削除/復旧/次run認可は追加しない。root/ACL/FS/owner/provider真正性、現在性/ABA・実Drive/runtime・Tier B/C受け入れや要件全体/P0-010閉鎖は未実装・未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchで累積source/公開/owner境界と未決runtime契約を照合して次単位を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### owned mutex応答の厳密検査と不確かな待機のcleanup（2026-10-27）

- 利用者の次作業指示を受け、cleanな`83ee8e0`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [owned mutex adapter観測](../../Common/README.md#strict-owned-mutex-adapter-observations-2026-10-27)を既存診断mutex/Win32 adapterのbool契約へ整合。acquire結果をbool変換せずexact boolで検査し、不正値/待機例外は固定`named_mutex_wait_failed`でrecord payload生成前に拒否する。待機中断/不確かな結果はrelease・closeを試み、確定False timeoutではcloseのみ。取得後のabandonedもexact boolを要求し、欠落/不明/不正型をFalse補完せず`named_mutex_observation_invalid`で拒否、Trueは従来どおり回復待ち停止とする。
- 既存Python 3.11.9実体（shim版未選択のため設定変更せず指定、CIは3.12）で`$env:PYTHONPATH='tests;.'`後、`& $python311 -B -m unittest test_owned_run_lock test_owned_publication_integration test_recovery_diagnostic_mutex test_terminal_bundle_integration test_terminal_history_usepoint test_terminal_plan_usepoint test_initial_source_integration test_initial_source_usepoint test_internal_publication_crash test_crash_publication_harness test_download_staging_integration`の124件全成功・skipなし。既知sandbox hardlink拒否を避けauto-review承認済みのsandbox外・自作temp/合成adapterだけを使用。既存CI登録suiteに新規5件を追加し、truthiness変換非使用、不正応答/例外/KeyboardInterrupt時の非record作成とcleanup、abandonedの不正型/欠落/取得失敗を確認。変更2文書の相対リンク133件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- 既存adapterの未所有release no-op契約を前提にcleanupを試みるだけで、provider/実owner真正性・新しい実行認可を与えない。schema/owner-v2/SDK/配布集合・固定本番値は不変。残存recordの採用/復旧、root/ACL/FS資格、現在性/ABA・電源断/Tier B/C/runtime受け入れや要件全体/P0-010閉鎖は未実装・未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchで累積source/公開/owner境界と未決runtime契約を照合して次単位を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### owner record作成失敗の保全とshort write拒否（2026-10-27）

- 利用者の次作業指示を受け、cleanな`96d6f25`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [owner record作成失敗の保全](../../Common/README.md#owner-record-creation-failure-preservation-2026-10-27)を追加。`write`がexact intの全bytes件数でなければ`lock_record_write_incomplete`で停止し、closeの二重OSError/FileExistsErrorでも一次reasonを保持。通常write/flush/fsync/close失敗は既存create-failed境界を維持する。finallyでのrecord cleanupを、作成完了と最初の安定所有確認に成功した場合だけへ限定し、失敗recordはparse可能/正しいtokenでも所有再確認して削除しない。mutex release/closeと正常取得後の従来cleanupは維持。
- 既存Python 3.11.9実体（shim版未選択のため設定変更せず指定、CIは3.12）で`$env:PYTHONPATH='tests;.'`後、`& $python311 -B -m unittest test_owned_run_lock test_terminal_bundle_integration test_terminal_history_usepoint test_terminal_plan_usepoint test_owned_publication_integration test_initial_source_integration test_initial_source_usepoint test_internal_publication_crash test_crash_publication_harness test_download_staging_integration`の105件全成功・skipなし。既知sandbox hardlink拒否を避けauto-review承認済みのsandbox外・自作tempだけを使用。追加のclose FileExistsError caseを補強後、`& $python311 -B -m unittest test_owned_run_lock`の27件全成功を対象再確認（105件内のsuiteで独立総数へ加算しない）。新規4件は既存CI登録suiteへ追加し、書込件数/二重close failure、4段階のI/O失敗、初回所有確認失敗、両PCの候補非作成・parse可能record保全・mutex再取得を確認。変更2文書の相対リンク131件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- 既存lockの失敗保全境界補助で、schema/owner-v2/SDK/配布集合・固定本番値は不変。残存record採用/復旧や新しい削除能力・次run認可は追加しない。root/ACL/FS/owner/provider真正性、unlinkまでの競合/ABA・電源断/Tier B/C/runtime受け入れや要件全体/P0-010閉鎖は未実装・未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchで累積source/公開/owner境界と未決runtime契約を照合して次単位を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### 隔離保存接続へのowner record予算伝播（2026-10-27）

- 利用者の次作業指示を受け、cleanな`ea69c4d`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [隔離候補の予算接続](../design/manifest-transition-inspection.md#explicit-fixture-publicationreadback-budgets-2026-10-27)でpublish/readback・全履歴使用点保存から`maximum_record_bytes`をowned lockへ伝播。不正値はguard/owner取得前、record作成前超過は候補保存/検証・履歴再導出前に停止する。予算内の実record長境界、公開/読戻しの別予算、prior/candidate保全を維持する。所有中のrecord増大+例外でも元例外/recordを保持し、別合成record pathで同一mutexを再取得して解放だけを確認する。
- 既存Python 3.11.9実体（shim版未選択のため設定変更せず指定、CIは3.12）で`$env:PYTHONPATH='tests;.'`後、`& $python311 -B -m unittest test_owned_run_lock test_terminal_bundle_integration test_terminal_history_usepoint test_terminal_plan_usepoint test_owned_publication_integration`の63件全成功・skipなし。既知のsandbox hardlink WinError 5を避け、auto-review承認済みのsandbox外で自作tempだけを使用。新規3件と既存境界/不正値matrixの拡張は既存CI登録suiteに追加した。変更2文書の相対リンク113件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- tests専用の接続証拠であり、Common/schema/SDK/配布集合・固定本番値・正式runtime/配置/IPC契約は変更しない。予算は各呼出しの指定で保存/自動伝播しない。残存recordの採用/復旧・次run認可、root/FS/owner/provider真正性、現在性/ABA・実Drive/runtime・電源断/Tier B/C受け入れや要件全体/P0-010閉鎖は未実装・未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchでsource/公開/ownerの累積差分と残る承認済みhelper境界を照合して次単位を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### owner recordのcaller上限と安定読取（2026-10-27）

- 利用者の次実装指示を受け、cleanな`559f06a`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [owner record読取境界](../../Common/README.md#bounded-stable-owner-record-observations-2026-10-27)として`maximum_record_bytes`をowned lockへ追加。不正値はtoken/path/mutex準備前、生成record超過はmutex内・record作成前に固定reasonで拒否する。作成後/解放前のJSON確認で既存directory verifierの安定readerを再利用し、超過recordの非open、path/handle/祖先chainの前後照合・初期size+1読取を適用。変化/不明/深いJSONのRecursionErrorは所有未確認としてrecord保全・mutex解放/closeへ接続する。scope/token・field/pid/hostの既存意味論とJSON表記互換は維持。
- 検証環境でpython shimが版未選択となり、最初のコマンドはsuite未起動。個人/global設定は変更せず、既存Python 3.11.9実体を`$python311`相当として指定した。sandbox内の132件はhardlink作成拒否等で8 failures/37 errors・1skipとなり、自作tempの最小probeもerrno 13/WinError 5を確認。auto-review承認済みのsandbox外で同じ合成検査を再実行し、132件中131成功・既存symlink作成不可1skip、未解決失敗なし。実ログ/Driveは使わない。
- 成功コマンドは`$env:PYTHONPATH='tests;.'`後、`& $python311 -B -m unittest test_owned_run_lock test_owned_publication_integration test_crash_publication_harness test_internal_publication_crash test_terminal_bundle_integration test_terminal_history_usepoint test_terminal_plan_usepoint test_initial_source_integration test_initial_source_usepoint test_download_staging_integration test_artifact_set_directory_verification test_artifact_directory_reparse`。CI Pythonは3.12。既存CI登録suiteに新規8件を追加し、exact境界・不正値・作成前超過/解放時超過、path→handle間増大、deep JSON/不明観測時の保全/解放、JSON表記互換を確認した。変更2文書の相対リンク127件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・package/PS検証は未実行。再利用依存は既存Common .pyで配布対象/集合は不変。
- 既存lock所有確認の資源/観測境界補助であり、owner-v2/provider契約、root/ACL/FS/owner真正性・一回性、観測からunlinkまでの競合/ABA、実I/O/時間/全memory上限・電源断/Tier B/C/runtime受け入れやP0-010閉鎖は未実装・未実証。固定本番値・新しい削除/復旧能力は追加しない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchでowner取得を使う隔離保存接続へのrecord予算伝播など、承認済みの独立範囲を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### 隔離保存fixtureへの予算伝播と追加読取の有界化（2026-10-27）

- 利用者の次実装指示を受け、cleanな`1072248`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- 正式保存wrapperは未実装のため、[自作OS-temp内の候補bundle接続](../design/manifest-transition-inspection.md#explicit-fixture-publicationreadback-budgets-2026-10-27)に限定。fixture publish/全履歴使用点接続で`maximum_artifact_bytes` / `maximum_total_bytes`をpublisherへ伝播。readbackのdirectory検査とは別の`maximum_semantic_artifact_bytes` / `maximum_total_semantic_bytes`を参照validatorへ渡す。不正予算はguard/owner取得前に拒否し、有効な超過は保全/owner解放へ接続する。
- fixture所有marker/priorと追加payload/commit marker比較を既存atomicの期待bytes有界readerへ置換。commit markerはfixture transaction/hash集合から決定的bytesを再構成し、表記違いも補完しない。初回directory検証後の増大は追加比較のopen前に拒否する。Common runtime/schema/SDK/配布集合に変更なし。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_terminal_bundle_integration test_terminal_history_usepoint test_terminal_plan_usepoint test_terminal_manifest_history test_terminal_manifest_plan test_artifact_set_publication test_artifact_set_directory_verification test_atomic_artifact_publication test_owned_publication_integration test_initial_source_usepoint test_internal_publication_crash test_crash_publication_harness`の158件中156成功・既存symlink作成不可2skip。既存CI登録suiteへ新規5件を追加し、両PCの公開/読戻し境界・超過/不正値・既存prior保全/owner解放、report/marker増大の非open、履歴再導出との接続を確認。意味論予算の明示成功caseを追加後、`python -B -m unittest test_terminal_bundle_integration.TerminalBundleIntegrationTests.test_explicit_publication_and_readback_budgets_preserve_prior_for_both_roles`を対象再実行し1件成功。これは上記158件に含まれ、独立総数へ加算しない。変更2文書の相対リンク111件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- tests専用の保存接続証拠であり、正式保存runtime/元runningの更新や要件全体/P0-010を完了扱いしない。意味論予算はschema/再読取も計上し、候補論理bytesと別指定。root/FS/owner/provider真正性、現在性/ABA・実Drive/runtime・電源断/Tier B/C受け入れ、実I/O/時間/全memory/disk容量の上限は未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchで既承認helper/隔離接続と未決runtime契約の境界を確認して次単位を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### marker込みのcaller指定公開bytes予算（2026-10-27）

- 利用者の次実装指示を受け、cleanな`e09ab79`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [marker-last公開bytes予算](../../Common/README.md#caller-selected-marker-last-publication-byte-budgets-2026-10-27)としてpublisherへoptional `maximum_artifact_bytes` / `maximum_total_bytes`を追加。不正値はMapping snapshot/hash前に固定`artifact_publish_limit_invalid`、payload超過はhash前にfile/total limit理由で拒否する。生成marker自身とmarker込み合計も単一file公開前に検査し、部分公開・skip/切詰めを行わない。既存の全名/型/実buffer検査、決定的公開順・marker-last・冪等/競合拒否を維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_set_recovery test_artifact_set_publication test_artifact_set_directory_verification test_atomic_artifact_publication test_owned_publication_integration test_initial_source_integration test_initial_source_usepoint test_internal_publication_crash test_terminal_bundle_integration test_crash_publication_harness`の148件中146成功・既存symlink作成不可2skip。既存CI登録suiteへ新規6件を追加し、marker込みexact境界の公開/再公開/同予算読戻し、不正値の非snapshot、payload超過の非hash・既存partial保全、markerのみの超過・非部分公開、bytes派生型の実sizeと空payloadを確認した。変更2文書の相対リンク124件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- 既存公開の資源境界補助であり、正式writer/要件全体/P0-010を完了扱いしない。固定本番値・schema/C-02/SDK/配布集合は不変。予算はB2/markerへ保存せず呼出しごとの指定で、wrapper/runtimeへの伝播は未実装。論理bytes予算であり、コピー/生成済みmarkerのmemory、hash/JSON生成時間、temp/readbackを含む実I/O総量やdisk容量を制限しない。root/FS/provider/owner真正性・現在性/ABA・実Drive/runtime・電源断/Tier B/C受け入れは未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchで既存の保存接続入口への公開/読戻し予算伝播など、承認済みの独立範囲を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### marker-last公開・分類・読取のbasename条件整合（2026-10-27）

- 利用者の次実装指示を受け、cleanな`5eacf41`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [共通basename条件](../../Common/README.md#shared-marker-last-basename-validation-2026-10-27)を既存publisherから`ArtifactSetRecovery.is_artifact_basename`へ抽出。空/非文字列・先頭dot・slash/backslash/NUL・末尾ASCII空白/dotをproducerとconsumerで共通拒否する。classifierのexpected/published/staged/marker hash集合とdirectory verifierの期待集合/marker名に接続し、従来consumerが末尾空白/dotを受理した不整合を修正。不正名は既存reasonで公開/走査/読取前に拒否する。有効名のUnicode/内部空白/dotは原形保持し、単一file temp方針やWindows予約名等の新規規則は採用しない。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、初回`python -B -m unittest test_artifact_set_recovery test_artifact_set_publication test_artifact_set_directory_verification test_atomic_artifact_publication test_owned_publication_integration test_initial_source_integration test_initial_source_usepoint test_manifest_terminal_publication test_crash_publication test_internal_publication_crash`を実行。実在8suiteの125件は123成功・symlink作成不可2skipだったが、`test_manifest_terminal_publication` / `test_crash_publication`はrootの名前誤指定でimport error。正しい`python -B -m unittest test_terminal_bundle_integration test_crash_publication_harness`を追加実行し17件全成功。最終実行対象は重複なし142件中140成功・既存2skipで、未解決失敗なし。新規4件と既存2件の不正名matrix拡張は既存CI登録suiteへ追加した。変更2文書の相対リンク122件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- 既存marker-last拒否境界の整合で、P0-010や正式runtime受け入れの閉鎖ではない。schema/C-02/SDK/配布集合・公開/復旧実行認可は不変。完全なWindows名/長さ検査・root/FS/provider真正性・現在性/ABA・正式runtime/Drive・電源断/Tier B/C受け入れは未実装・未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchで既承認の独立範囲を調査し、未決runtime契約を推測せず次単位を選ぶ。PR作成/mergeは別途指示された範囲で行う。

### 一括Drive比較の呼出し内再利用と一致ID保有量削減（2026-10-27）

- 利用者の次実装指示を受け、cleanな`d0907f6`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [呼出し内の比較再利用](../design/drive-content-comparison.md#repeated-comparison-values-within-one-call-2026-10-27)を通常一括前後比較と計画完了集合比較へ接続。共通観測/plan/download検査後、filename/size/SHA-256の同一条件だけを呼出し内で1回比較し、全source slotと指定順を保持する。異なる条件は分離し、他呼出しへ結果を持ち越さない。単一比較の全一致IDリストは件数+候補ID1件へ置換し、2件一致後も後続の不明/不一致を検査する。既存status/reason/全may_*falseは維持。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_drive_content_comparison test_drive_comparison_batch test_drive_comparison_reobservation test_content_download_plan test_planned_drive_comparison test_drive_listing_observation test_download_hash_observation test_comparison_source_revalidation test_comparison_source_batch test_initial_inventory_observation test_initial_inventory_summary test_staged_drive_content_observation test_download_staging_integration`の137件全成功・skipなし。既存CI登録suiteへ新規5件を追加し、両一括入口の400 source/4条件の実比較回数、全slot/順序/flags、後続download変更・欠落/重複の再検査、40一致後の不明metadata/hash/不一致reason保全を確認した。変更2文書の相対リンク119件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- EOLM-SYN-007/008・OSD-01の候補/保留境界を維持する改善。条件がすべて異なる場合の比較走査量・呼出し内辞書/全memory・時間は制限しない。固定本番値・schema/C-02/SDK/配布集合の変更・実行認可は追加しない。provider真正性/現在性/ABA・正式runtime/実Drive・電源断/Tier B/C受け入れや要件全体/P0閉鎖は未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。以後も同branchで承認済みhelperと未決runtime契約の境界を確認して次単位を選び、PR作成/mergeは別途指示された範囲で行う。

### download計画の同名候補走査と予算事前検査（2026-10-27）

- 利用者の次実装指示を受け、cleanな`29448da`・同branch `codex/source-inventory-budgets`から継続。main基準は前確認の`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回GitHub状態の再取得・branch切替・push/PRなし。
- [重複source計画の仕様](../design/drive-content-comparison.md#repeated-source-planning-and-budget-preflight-2026-10-27)に従い、`plan_content_downloads`でsourceの名前別size集合を構築し、Drive同名候補の反復走査をsource数倍から各bucket最大2回へ変更。初回に一意な件数/総bytesだけを集計し、予算内で初めて必要ID/size辞書とソート済みrequirementを構築する。metadata不明→件数超過→bytes超過の優先順位、異なるsize/未信頼hash/0 bytes、候補ID一意化と元の順序非依存・非認可を維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_content_download_plan test_planned_drive_comparison test_drive_content_comparison test_drive_listing_observation test_download_hash_observation test_drive_comparison_reobservation test_drive_comparison_batch test_comparison_source_revalidation test_comparison_source_batch test_initial_inventory_observation test_initial_inventory_summary test_staged_drive_content_observation test_download_staging_integration`の132件全成功・skipなし。既存CI登録suiteに新規4件を追加し、400 source/40候補の訪問数を実測counterで確認、複数size/信頼SHA/空file・境界と後続metadata不明の優先順位を検証した。変更2文書の相対リンク118件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- EOLM-SYN-007/008・OSD-01の候補計画/保留境界を維持する改善であり、要件全体やP0閉鎖ではない。固定本番値・schema/C-02/SDK契約・配布集合は不変。全列挙index/source条件集合や全memory/時間は制限せず、provider真正性・現在性/ABA・正式runtime/実Drive・電源断/Tier B/C受け入れは未実装・未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。以後も同branchで承認済みhelperと未決runtime契約の境界を照合して次単位を選び、PR作成/mergeは別途指示された範囲で行う。

### source再観測・比較入口への資源予算伝播（2026-10-27）

- 利用者の次実装指示を受け、cleanな`9a7d68c`・同branch `codex/source-inventory-budgets`から継続。main基準は直前にGitHub/local/origin一致確認済みの`0d4945260067a86aaf8beb5ae792a4108b0091f9`（PR #45）。今回はGitHub状態を再取得せず、branch切替・push/PRなし。
- [source再観測入口の予算](../design/source-inventory-revalidation.md#source-inventory-budgets-at-revalidation-entrypoints-2026-10-27)を追加。`revalidate_source_inventory`、initial plan照合、単一/一括比較source、initial inventoryの5入口がoptional `maximum_entries` / `maximum_file_bytes` / `maximum_total_hash_bytes`を全source再観測builderへ伝播する。共通pure型検査をbuilderと共有し、不正値は解析/plan再構成/source I/O/Drive比較前に固定`source_revalidation_limit_invalid`。実走査超過は既存`source_revalidation_incomplete`で拒否し、選択subset/空選択でも完全走査を省略しない。固定本番値・schema/PS/配布file集合は変更しない。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_source_inventory_evidence_builder test_source_enumeration_stability test_source_hash_identity test_source_inventory_reparse test_initial_source_integration test_initial_source_usepoint test_source_inventory_revalidation test_comparison_source_revalidation test_comparison_source_batch test_initial_inventory_observation test_initial_inventory_summary test_staging_residual_observation test_aggregation_report_builder test_manifest_transition_inspection`の160件全成功・skipなし。新規6件は既存CI登録suiteに追加し、5入口の不正値preflight、PC-A/B・両logの再帰境界/超過、plan/単一/一括/空選択とDrive接続、exact B2/選択順/非認可flagsとsource bytes保全を確認した。変更2文書の相対リンク110件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- EOLM-FIL-005/007に関する不完全coverageの保全補助であり、要件全体やP0-010は閉鎖しない。予算は各呼出しの指定で、B2/planへの保存・正式runtimeへの接続は未実装。実I/O/時間/全memory制限、root/FS/provider真正性、現在性/ABA・Drive/runtime・電源断/Tier B/C受け入れは未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。次は同branchで既承認の独立範囲を調査して選ぶ。PR作成/mergeは別途指示された範囲で行う。

### source inventoryのcaller指定資源予算（2026-10-27）

- 利用者の次実装指示を受け、GitHub mainとlocal/origin mainの`0d4945260067a86aaf8beb5ae792a4108b0091f9`を照合。PR #45はsquash merge済みで、mainの[Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40347516491) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40347516412)両成功・PR本文への結果記録済み。cleanな最新mainからupstreamなしの新branch `codex/source-inventory-budgets`を作成した。
- [source inventory予算仕様](../design/source-inventory-revalidation.md#caller-selected-source-inventory-budgets-2026-10-27)に従い、B2 builderへoptional `maximum_entries` / `maximum_file_bytes` / `maximum_total_hash_bytes`を追加。不正値はroot I/O前に拒否。件数は再帰全体・最終再scanで各pass共有、hashは試行sizeを先に予約し失敗でも消費を戻さない。予算超過で走査/hashを停止し、既存target/errorを保全してincompleteとする。bytes予算時はexpected sizeをhash helperへ渡し、直前増大をopen前に拒否する。固定本番値・schema/PS/package file集合の変更なし。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_source_inventory_evidence_builder test_source_enumeration_stability test_source_hash_identity test_source_inventory_reparse test_initial_source_integration test_initial_source_usepoint test_source_inventory_revalidation test_comparison_source_revalidation test_comparison_source_batch test_initial_inventory_observation test_staging_residual_observation test_aggregation_report_builder test_manifest_transition_inspection`の145件全成功・skipなし。新規10件は既存CI登録済みsuiteに追加し、境界/不正値/再帰共有/最終scan増大/失敗試行予約/直前size増大と、両PC・両logでinitial planがrunning/outcome null・全許可falseを維持することを検証した。変更2文書の相対リンク109件欠落0、git diff --check成功。root自己点検のみ、独立レビューなし。新CI・全suite・無関係なpackage/PS検証は未実行。
- EOLM-FIL-005/007の列挙・不完全coverage保全を補助する変更で、要件全体やP0-010の閉鎖ではない。予算指定はbuilder入口だけで再観測/比較wrapperへの伝播・保存は未実装。初期size+1の増大probeを許すため厳密な実I/O/時間/全memory制限ではなく、root/FS/provider真正性・同時snapshot/ABA・Drive/runtime・電源断/Tier B/C受け入れも未実証。実ログ/本番Driveは使わない。
- この記録を含むローカルコミットで区切り、次の指示を待つ。未push・新PRなし。次は同branchでsource再観測入口への予算伝播など既承認の独立範囲を選ぶ。前回のPR/merge承認は今回のpush/PR/mergeへ拡張しない。

### 累積PR作成・マージ承認と統合検証（2026-10-27）

- 利用者が累積コミットをまとめたPR作成・マージを明示指示。`898f4ff`までの実装28コミット（42 files）と本記録を同じPRへまとめ、最新HEADのValidate/Package Validation両成功を確認後squash mergeする。branchは`codex/manifest-entry-bounds`、取得・照合済み正本mainは`6e9ad82d8ae11146041b5eba0ab6b94e21c5cad8`（PR #44）。本記録時点は未push/未PR/未マージ。結果のPR/merge SHAとCIはGitHub実状態・本チャットの最終報告を照合する。
- 範囲：manifest/report/marker/source/stagingの読取・件数・bytes予算、Drive page/file/hash/download plan予算とlocal入口接続、内部比較/要約の共通検査、重複scan/祖先identity検査、JSON解析拒否と非有限数値・schema外部取得禁止、marker producer/consumer文法・Mapping/buffer固定、bounded write/比較とshort write/close失敗理由の保全。固定本番上限・新schema/C-02/provider契約は選ばず、実行認可・cleanup/PC-B archive能力を追加しない。レビューpackage集合は50 filesのまま。
- 累積統合検証：Python 3.11.9（CI 3.12）で`python -B -m unittest discover -s tests -p test_*.py`の870件中868成功・既存symlink作成不可2skip。PATH上PowerShell 7.6.7を版確認し、tests内PS bridgeを含むPython suiteが成功。`pwsh -NoLogo -NoProfile -File tests/Test-ReleasePackage.ps1`で両role package回帰成功。累積変更8 Markdownの相対リンク160件欠落0、`git diff --check origin/main...HEAD`成功。PS/schema/CI定義に変更なし。root自己点検のみ、独立レビューなし。過去の単位別test修正/再実行は各節へ保持し、本統合suiteは全件再実行した。
- マージ後は次の実装を始めず本作業を終了する。以後の実装は最新mainから新しい作業branchを作成し、マージ済みbranchを再利用しない。正式runtime/SDK/credential/C-02、metadata-first/event/writer/CAS/receipt、真正なroot/FS/owner/clock/AC/session/account、現在性/ABA・電源断・両PC/Tier B/C/runtime受け入れは未完。helper/CI/package成功を配布/本番適用/削除/Archiveの許可やP0完了へ変換しない。

### 最新manifest schemaの外部参照取得を禁止（2026-10-27）

- 利用者の次実装指示を受け、基準`2145396`、クリーンな同branch `codex/manifest-entry-bounds`で[manifest schemaのlocal参照制約](../design/latest-manifest-selection.md#local-only-schema-references-2026-10-27)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- selectorのschema全treeで`$ref` / `$dynamicRef`をlocal fragment文字列に限定し、非local/不正値は既存schema-unavailable理由で拒否。validatorのRegistryも全resource retrievalを拒否し、外部取得fallbackを提供しない。既存report builderのlocal参照方針へ整合し、正常なrepo fragment/format/候補検査を維持する。破損local参照は既存candidate-invalid、invalid schemaは既存schema-unavailable、URL非echo/候補非変更。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_latest_manifest_selection test_manifest_directory_reader test_manifest_reader_bounds test_manifest_report_selection test_manifest_recovery_integration test_owned_publication_integration test_aggregation_report_builder test_completion_wait_checkpoint`の計133件全成功・skipなし。新規3件を既存CI登録済みsuiteへ追加し、HTTP/file/相対/不正参照・未使用defs・破損local/invalid schemaをsocket非呼出しで拒否し、directory経由のbytes保全を確認。referencingは既存jsonschema依存/既存builder使用分で追加依存なし。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- schema真正性/読取資源上限・provenance/現在性/同時snapshot/ABA・root/FS/provider資格・runtime受け入れやcleanup/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 最新manifest選択のbytes派生型を実bufferで解析（2026-10-27）

- 利用者の次実装指示を受け、基準`4cbfc0b`、クリーンな同branch `codex/manifest-entry-bounds`で[manifest候補の実bytes解析](../design/latest-manifest-selection.md#actual-bytes-for-subclass-candidate-content-2026-10-27)を修正。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。作業中の利用者environment更新に合わせ本記録は日本時間10月27日付。
- pure selectorでbytes派生型のcontentを実buffer由来のplain bytesへ固定してUTF-8/JSON解析する。独自decodeで不正bytesを正常JSONへ差し替える余地を防ぎ、実buffer正常の派生型は受理する。通常exact bytes/非bytesの既存拒否、入力object保全、全候補のschema/identity/time検査・非fallbackを維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_latest_manifest_selection test_manifest_directory_reader test_manifest_reader_bounds test_manifest_report_selection test_manifest_recovery_integration test_owned_publication_integration`の計94件全成功・skipなし。新規3件を既存CI登録済みsuiteへ追加し、不正実bufferの拒否、正常bufferと独自decode/変換/lenの非使用、新しい成功候補があっても古い不正候補を両順序で拒否することと入力保全を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 派生型buffer copyのmemory上限を追加せず、provenance/現在性/同時snapshot/ABA・root/FS/provider資格・runtime受け入れやcleanup/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 公開payloadのbytes派生型を実bufferへ固定（2026-10-26）

- 利用者の次実装指示を受け、基準`3f72d25`、クリーンな同branch `codex/manifest-entry-bounds`で[公開bytesの統一](../validation/lock-recovery-acceptance-gate.md#plain-bytes-for-publication-comparisons-2026-10-26)を修正。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- 単一/集合publisherで受理済みbytes派生型をmemoryviewの実bufferからplain immutable bytesへ固定し、hash/書込/比較へ同じ内容を使う。独自len/slice/__bytes__の不一致で別の既存内容を同一扱いする余地を防ぐ。通常exact bytesは追加コピーせず、bytearray/memoryview等の非bytes拒否・caller object非変更・既存no-overwrite/marker-lastを維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_atomic_artifact_publication test_artifact_set_publication test_crash_publication_harness test_internal_publication_crash test_terminal_bundle_integration test_owned_publication_integration`の計73件中72成功・既存symlink作成不可1skip。新規4件を既存CI登録済みsuiteへ追加し、独自len/slice/変換を持つbytes派生型の実buffer公開/同一再公開・競合保全・plain bytesでのhashとmarker読戻しを確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 派生型の固定copyに必要なmemory上限は設けない。provider真正性/同時snapshot/ABA・root/FS/owner資格・runtime受け入れやcleanup/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### report参照JSONの解析失敗・非有限数値を固定拒否（2026-10-26）

- 利用者の次実装指示を受け、基準`d35cbbb`、クリーンな同branch `codex/manifest-entry-bounds`で[参照JSON解析拒否](../design/aggregation-report-v1-proposal.md#fixed-json-parse-failures-in-referenced-inputs-2026-10-26)を修正。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- report/manifest/B2/3 schema共通JSON readerで解析ValueError/RecursionErrorを既存`malformed_json`へ変換し、深いJSONによる例外の外部逸脱を防ぐ。float tokenの指数overflow等が非有限になる場合は既存`invalid_json_constant`で拒否し、builderの有限float境界へ整合。有限小数の型・元bytes・schema/意味論検査・読取上限は維持する。CLIはJSON/exit 2、manifest-report wrapperは既存固定拒否へ接続。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_read_stability test_aggregation_referenced_artifacts test_manifest_report_selection test_manifest_reader_bounds test_terminal_bundle_integration test_aggregation_report_builder.AggregationReportBuilderTests.test_existing_referenced_artifact_validator_accepts_generated_fixture`の計79件全成功・skipなし。新規5件を既存CI登録済みsuiteへ追加し、全6入力の過度な入れ子/非有限数値・bytes保全・有限小数・CLI非tracebackとwrapper拒否を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- JSON最大depth/複雑度の本番値や新schema制約を選ばず、parser資源上限・真正性/現在性/同時snapshot/ABA・root/FS/provider資格・runtime受け入れやcleanup/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 既存staging payloadの明示bytes上限（2026-10-26）

- 利用者の次実装指示を受け、基準`0b62ef5`、クリーンな同branch `codex/manifest-entry-bounds`で[staging payload読取上限](../design/source-inventory-revalidation.md#caller-selected-staging-payload-read-bounds-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- 単一/一括staging読取とstaging/Drive比較にoptional `maximum_staging_file_bytes` / `maximum_total_staging_bytes`を追加。不正値はplan再構成前、選択した凍結targetのfile別/合計size超過はroot I/O・payload hash・Drive比較前に既存SourceRevalidationErrorの固定理由で全体拒否。単一/接続入口から同じ上限を一括readerへ渡す。予算内は既存exact再読取・順序・全非認可を維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_initial_staging_copy_batch test_initial_staging_copy_observation test_staged_drive_content_observation test_upload_staging_integration test_source_hash_identity test_initial_inventory_observation test_initial_inventory_summary`の計72件全成功・skipなし。新規5件を既存CI登録済みsuiteへ追加し、file/合計境界・空選択・不正値・全読取前拒否・上限伝播・bytes保全を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- Noneではcaller上限なし。非選択file・plan/B2解析memory/metadata I/O/全memoryや実容量予約の上限ではなく、増大検知で初期size+1 byteを読み得る。固定本番値/新schema/copy実行を採用せず、provider真正性/同時snapshot/ABA・root/FS/owner資格・runtime受け入れやcleanup/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 残存staging観測のcaller指定entry上限（2026-10-26）

- 利用者の次実装指示を受け、基準`b3c035c`、クリーンな同branch `codex/manifest-entry-bounds`で[残存staging entry上限](../design/staging-residual-observation.md#caller-selected-entry-limit-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- public観測と共通snapshotにoptional `maximum_entries`を追加。不正値はroot I/O前にheld/固定拒否、初回/最終scanとも最初の超過entryを保持/sort/metadata検査する前に停止しscanを閉じる。初回未成立は確定件数なし、最終超過は初回件数/warningを保持したheldとする。既存不完全列挙・duplicate/reparse/chain検査と全非認可を維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_staging_residual_observation test_source_enumeration_stability test_source_inventory_reparse test_source_inventory_revalidation test_initial_staging_copy_batch test_staged_drive_content_observation test_initial_inventory_observation`の計70件全成功・skipなし。新規5件を既存CI登録済みsuiteへ追加し、境界/不正値非I/O/早期停止とcontext closure/最終件数・bytes保全/部分失敗を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 固定本番上限/保持・cleanup/source全体の新方針を選ばず、Noneではcaller上限なし。名前長/列挙遅延/全memory/真正性・現在性/同時snapshot/ABA・root/FS/provider資格・runtime受け入れやcleanup/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### manifest/成果物集合readerのexact同名重複拒否（2026-10-26）

- 利用者の次実装指示を受け、基準`dc00404`、クリーンな同branch `codex/manifest-entry-bounds`で[manifest scan](../design/latest-manifest-selection.md#duplicate-entries-in-directory-observations-2026-10-26)と[成果物集合scan](../validation/lock-recovery-acceptance-gate.md#duplicate-artifact-directory-entries-2026-10-26)の重複拒否を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- 両readerのscanでexact同名をsignature辞書へ上書きする前に既存directory-changed固定理由で拒否。manifestの前後2scan、集合の初回/再分類後/再読取後の3scanすべてに適用する。dedupやcasefold/新しいalias方針は採用せず、既存件数/bytes上限・文法/内容/marker/非fallback検査は維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_manifest_directory_reader test_manifest_reader_bounds test_manifest_report_selection test_manifest_recovery_integration test_artifact_set_directory_verification test_artifact_directory_reparse test_terminal_bundle_integration test_owned_publication_integration`の計102件中101成功・既存symlink作成不可1skip。新規3件を既存CI登録済みsuiteへ追加。自作tempのentryをscandir/iterdir adapterで重複供給し、全scan段階の拒否/bytes保全、両PC相当のbundle/prior保全・owner解放を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 検出可能な曖昧列挙を拒否するもので、native列挙真正性/同時snapshot/ABA・root/FS/provider資格・runtime受け入れやcleanup/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 共通directory snapshotのexact同名重複拒否（2026-10-26）

- 利用者の次実装指示を受け、基準`08d2d1a`、クリーンな同branch `codex/manifest-entry-bounds`で[列挙snapshotの重複拒否](../design/source-inventory-revalidation.md#duplicate-names-in-shared-enumeration-snapshots-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `_enumeration_snapshot`内でexact同名entryをidentity辞書へ上書きする前に既存固定directory-changed理由で拒否。source builderの初回scan失敗はpayload非読取の不完全coverage、最終scan失敗は既存target保全の不完全coverageへ接続する。残存stagingは初回の未確定件数を推計せずheld、最終失敗は初回件数/warningを保持したheld。casefold/dedup/新しい名前方針は採用しない。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_source_enumeration_stability test_staging_residual_observation test_source_hash_identity test_source_inventory_revalidation test_source_inventory_reparse test_initial_staging_copy_batch test_staged_drive_content_observation test_initial_inventory_observation`の計77件全成功・skipなし。新規3件を既存CI登録済みsuiteへ追加。自作tempのDirEntryをscandir adapterで重複供給し、共通層の拒否・source初回/最終失敗・残存staging heldの件数/bytes保全を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 検出可能な曖昧列挙を拒否するもので、列挙真正性/同時snapshot/ABA・root/FS/provider資格・runtime受け入れやcleanup/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### source hash reader内の祖先identity前後照合（2026-10-26）

- 利用者の次実装指示を受け、基準`3c1ef93`、クリーンな同branch `codex/manifest-entry-bounds`で[source hash祖先binding](../design/source-inventory-revalidation.md#ancestor-binding-inside-the-source-hash-reader-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `_hash_stable_file`でparent絶対pathから全祖先chainをfile読取前/最終path検査後に比較し、不一致を既存固定mutation理由で拒否。chain取得OSErrorも既存unavailable理由へ変換する。外側の列挙/batch検査に依存せず、単体利用でも同file identityを使うparent置換を検出。既存reparse/file/handle/size/mtime/hash/期待size/読取上限とbytes保全は維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_source_hash_identity test_source_inventory_reparse test_source_enumeration_stability test_source_inventory_revalidation test_initial_staging_copy_observation test_initial_staging_copy_batch test_staged_drive_content_observation test_initial_inventory_observation`の計74件全成功・skipなし。新規3件を既存CI登録済みsuiteへ追加。自作tempでparent rename→新directory→同identity hardlinkを実行し拒否/両path bytes保全を確認、上位祖先変化/初回・最終chain取得不能も確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 前後metadata検査でありnamespace lease/途中置換復元・ABA/同時snapshot/対象volume受け入れ・root/ACL/FS/owner・runtimeを証明しない。source hardlinkの新方針やstaging単一link制約を変更せず、実Drive/Upload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 初期inventory要約の比較検査を観測入口と統一（2026-10-26）

- 利用者の次実装指示を受け、基準`aafe8ff`、クリーンな同branch `codex/manifest-entry-bounds`で[件数要約](../design/initial-inventory-observation.md#件数のみの内部要約)の比較検査を共通化。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- file別のpure比較validatorを分離してbatch検査とsummaryで再利用し、要約独自のstatus/ID/flag検査の重複を解消。global/file別reasonは非空/NULなしexact stringを要求。不正値は既存固定summary-invalidで拒否。有効なprivate reasonの文言を出力・件数へ反映せず、既存B2/選択/対象/順序検査・全false flagsと歴史要約の非再観測境界を維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_initial_inventory_summary test_initial_inventory_observation test_staged_drive_content_observation test_drive_comparison_batch test_planned_drive_comparison test_content_download_plan test_comparison_source_batch`の計67件全成功・skipなし。新規3件を既存CI登録済みsuiteへ追加し、global/file reason形状/内包全flag拒否、pure非I/O、有効private reasonの非転記/件数不変を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- reason enumや運用状態を新設せず、構造検査を超える文言真正性/現在性・provider/ID出所・root/FS/owner/ABA・runtime受け入れやUpload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### local観測入口の内部比較結果検査を共通化（2026-10-26）

- 利用者の次実装指示を受け、基準`4f9984b`、クリーンな同branch `codex/manifest-entry-bounds`で[内部比較出力の共通検査](../design/source-inventory-revalidation.md#internal-comparison-output-validation-2026-10-26)を実装。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- staging/Drive比較と初期inventory入口で共通pure validatorを使用。batch/比較exact型、results tuple、既存status/非空reason、全may_*exact False、held/results空、candidate ID有無/型を検査し、不整合は入口別の既存固定result-invalid理由で例外にする。初期inventoryの件数だけの検査から、不正batch/内包flagsやheldなのに結果ありを受け入れない境界へ強化。既存の選択件数・順序binding/全非認可・正常候補/held混在/空選択は維持。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_drive_comparison_batch test_staged_drive_content_observation test_initial_inventory_observation test_initial_inventory_summary test_planned_drive_comparison test_content_download_plan test_comparison_source_batch test_initial_staging_copy_batch`の計72件全成功・skipなし。新規3件を既存CI登録済みsuiteへ追加。共通34不正variantのpure検査と両入口での固定拒否/local bytes保全を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 構造整合の検査であり新状態・provider真正性/現在性・ID出所・root/FS/owner/ABA・runtime受け入れやUpload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### download plan予算をlocal観測入口へ接続（2026-10-26）

- 前単位の検証/文書更新中に利用者の追加継続指示を受けたため、前単位を`129e752`へコミット後、クリーンな同branch `codex/manifest-entry-bounds`で[local観測入口への予算接続](../design/source-inventory-revalidation.md#download-plan-output-budgets-at-local-entrypoints-2026-10-26)を実装。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- staging/Drive比較と初期inventory入口にoptional `maximum_downloads` / `maximum_total_download_bytes`を追加。planと共通のpure型検査で不正値をlocal I/O前に拒否し、completed-set比較へ上限を渡す。超過時はcopy tupleまたは元B2/選択pathを保全したheld・比較なし、予算内は毎回local再読取後に従来の結果/順序/全false flagsを維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_staged_drive_content_observation test_initial_inventory_observation test_initial_inventory_summary test_content_download_plan test_planned_drive_comparison test_comparison_source_batch test_initial_staging_copy_batch`の計62件全成功・skipなし。新規6件を既存CI登録済みsuiteへ追加し、exact境界/不正値のlocal非読取/超過時の証拠保全・非認可を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- download計画の出力予算で、local読取量/件数/staging容量/全memoryの制限や新しい本番値は採用しない。正式SDK/C-02/provider真正性・root/FS/owner/現在性/ABA・runtime受け入れやUpload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### download planの件数・合計bytes予算（2026-10-26）

- 利用者の次実装指示を受け、基準`268a0ff`、クリーンな同branch `codex/manifest-entry-bounds`で[download plan出力予算](../design/drive-content-comparison.md#caller-selected-download-plan-output-budgets-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- plan/completed-set比較の両入口にoptional `maximum_downloads` / `maximum_total_download_bytes`を追加。不正値はlisting検査前にheld。不足対象をIDで重複排除した件数/期待bytes合計を全件検査し、超過時はrequirement構築/sort前に全体held・requirementsなし。比較側の再導出にも同上限を渡し、完了観測から上限を迂回しない。予算内の既存決定的順序・exact比較・全非認可flagsを維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_content_download_plan test_planned_drive_comparison test_download_hash_observation test_drive_listing_observation test_drive_comparison_batch test_comparison_source_batch test_download_staging_integration test_staged_drive_content_observation`の計76件全成功・skipなし。新規6件を既存CI登録済みsuiteへ追加し、重複ID一回計上/境界/不正値/超過時requirement非構築/0件・metadata不備/比較再適用とsource・staging接続を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 出力予算であり既存listing/source/index/不足候補辞書のmemory/探索時間上限ではない。予算はplanへ保存する権限ではなく、後続callerが同じ上限を明示する。固定本番値/新schema/C-02/実SDK方針を採用せず、provider真正性/現在性・正式runtimeやUpload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### download hash観測のcaller指定bytes上限（2026-10-26）

- 利用者の次実装指示を受け、基準`357a3ff`、クリーンな同branch `codex/manifest-entry-bounds`で[download bytes上限](../design/drive-content-comparison.md#caller-selected-download-byte-bounds-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `hash_downloaded_content`にoptional `maximum_download_bytes` / `maximum_chunk_bytes`を追加。不正値/期待download size超過はiterator取得/hash生成前、chunk超過はhash更新前に固定理由で全体拒否。既存の型/非空/完了・期待size exact照合・終端確認を維持し、chunkの分割/切詰め/部分観測化やcaller streamのclose/retryを行わない。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_download_hash_observation test_drive_listing_observation test_drive_content_comparison test_content_download_plan test_planned_drive_comparison test_download_staging_integration test_drive_comparison_batch`の計64件全成功・skipなし。新規5件を既存CI登録済みsuiteへ追加し、空/分割payload境界、各段階の消費/生成/更新前拒否、caller所有境界、short/overlong/終端例外と非認可比較接続を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 固定本番値/新schema/C-02 field/実SDK方針を採用しない。生成済みchunkのmemory/iterator遅延/真正なID-stream bindingを保証せず、正式SDK/credential・root/FS/owner/ABA・実Drive/runtime受け入れやUpload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### Drive page/file件数の明示上限（2026-10-26）

- 利用者の次実装指示を受け、基準`a19cb92`、クリーンな同branch `codex/manifest-entry-bounds`で[Drive page集約のcaller上限](../design/drive-content-comparison.md#page集約のcaller指定件数上限2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `collect_drive_listing`にoptional `maximum_pages` / `maximum_files`を追加。I/Oを持たないpure入力集約で、不正値はiterator取得前、nonterminalのpage上限到達は次page取得前、file合計超過は当該pageのfile検査/保持前に固定理由で全体拒否する。terminal後のexhaustion/trailer/例外検査、既存folder/token/ID検査・順序を維持し、部分成功・caller iteratorのclose/retryは行わない。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_drive_listing_observation test_download_hash_observation test_drive_content_comparison test_drive_comparison_batch test_content_download_plan test_planned_drive_comparison test_initial_inventory_observation`の初回60件は59成功・新規接続testの期待status誤り1fail・skipなし。既存契約`comparison_candidate`へtest期待値を修正し、`python -B -m unittest test_drive_listing_observation.DriveListingObservationTests.test_bounded_listing_still_connects_download_hash_to_non_authorizing_comparison -v`の該当1件成功。製品codeは初回後不変、固有60件の最終結果は全成功・skipなし。新規6件を既存CI登録済みsuiteへ追加。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 固定本番件数/新schema/C-02 field/実API方針を採用しない。生成済みpageのmemory/名前長/token長/iterator遅延や全memory上限ではない。実page真正性/現在性・正式SDK/credential・root/FS/owner/ABA・実Drive/runtime受け入れやUpload/retry/Archive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### short writeとclose失敗が重なった場合の理由保全（2026-10-26）

- 利用者の次実装指示を受け、基準`dd620d9`、クリーンな同branch `codex/manifest-entry-bounds`で[一次書込失敗理由の保全](../validation/lock-recovery-acceptance-gate.md#primary-write-failure-survives-stream-close-failure-2026-10-26)を修正。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- 不完全writeで生成した固定errorを保持し、その後stream closeがOSErrorを出しても`artifact_write_incomplete`を維持する。集合publisherへ同理由を伝播し、先行公開fileを保持・marker非公開。個別write/flush/fsync/close OSErrorの既存`artifact_publish_failed`とno-linkを回帰確認。tempの所有identity/完全bytes/祖先検査に基づく従来cleanup境界を変えず、未検証tempは保全する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_atomic_artifact_publication test_artifact_set_publication test_crash_publication_harness test_internal_publication_crash test_terminal_bundle_integration test_owned_publication_integration`の計68件中67成功・既存symlink作成不可1skip。新規3件を既存CI登録済みsuiteへ追加し、単一/集合の二重失敗と個別4段階の失敗を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 新たなcleanup/retry/修復権限は付与しない。正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### pure classifierのmapping検査と分類を同じコピーへ統一（2026-10-26）

- 利用者の次実装指示を受け、基準`9bbaea5`、クリーンな同branch `codex/manifest-entry-bounds`で[classifierコピー検査](../validation/lock-recovery-acceptance-gate.md#classifier-validates-the-copied-mappings-2026-10-26)を修正。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- expected/published/staged/marker/marker hash Mappingをplain dictへコピーし、そのコピーを既存文法・集合・内容検査と分類に使う。コピー失敗は既存入力別blocked理由へ変換し、例外詳細を出さない。元Mappingのitemsでは非空に見えてコピーが空になる場合に、空expected/marker集合でcommittedへ進む不一致を防ぐ。valid dict/読取専用Mappingの状態・flags・transaction exact比較は維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_set_recovery test_artifact_set_directory_verification test_artifact_set_publication test_terminal_bundle_integration test_owned_publication_integration test_artifact_directory_reparse`の計81件中80成功・既存symlink作成不可1skip。新規4件を既存CI登録済みsuiteへ追加し、5種入力のiteration/partial/item失敗、見掛けと異なる空コピー、valid MappingProxyTypeのcommitted/readyを確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 独自Mappingの検査対象をコピーへ統一する入力厳格化。コピー中の外部変更の原子的snapshotやcaller真正性は保証しない。正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### markerのstrict JSONと欠落区別（2026-10-26）

- 利用者の次実装指示を受け、基準`96708e9`、クリーンな同branch `codex/manifest-entry-bounds`で[存在するmarker JSONの拒否境界](../validation/lock-recovery-acceptance-gate.md#present-marker-json-is-distinct-from-an-absent-marker-2026-10-26)を修正。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- directory verifierは存在するmarkerのrootをobject必須とし、nullを欠落扱いにしない。非標準NaN/Infinity/-Infinityを全depthで拒否、既存duplicate key検査を維持し、解析RecursionErrorも固定`commit_marker_json_invalid`へ変換する。真のmarker欠落とobjectのshape/version/transaction/hash分類は既存のまま。原本を修復/削除せず、別集合へのfallbackや成功補完はしない。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_set_directory_verification test_artifact_set_recovery test_artifact_directory_reparse test_terminal_bundle_integration test_owned_publication_integration test_artifact_set_publication`の計77件中76成功・既存symlink作成不可1skip。新規5件を既存CI登録済みsuiteへ追加。root型/非標準定数/nested duplicate/過度な入れ子と、両PC相当の拒否時bundle/prior保全・owner解放を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 不正markerの拒否厳格化であり、JSON最大depth/複雑度の新しい本番値を選ばない。parser資源上限・正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 集合公開payload mappingのコピー検査（2026-10-26）

- 利用者の次実装指示を受け、基準`5fe9e76`、クリーンな同branch `codex/manifest-entry-bounds`で[payload mappingコピー検査](../validation/lock-recovery-acceptance-gate.md#payload-mapping-snapshot-before-publication-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- 集合publisherは元Mappingのtruthinessではなくplain dictへコピーした内容を検査。コピー例外と実体が空の場合は固定`artifact_set_empty_or_invalid`で全publish前に拒否し、部分集合を作らず既存partialを保持する。同じコピーを全件name/bytes検査・hash・順序付き公開・markerへ使い、公開中の元mapping変更を取り込まない。独自mapping例外詳細は非echo。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_set_publication test_atomic_artifact_publication test_crash_publication_harness test_internal_publication_crash test_terminal_bundle_integration test_owned_publication_integration`の初回64件は62成功・fixture仮定誤り1fail・既存symlink作成不可1skip。dictコピーが元Mappingのlenを呼ぶという誤った仮定を、実際にlen非依存で有効copyできる正例へ修正し、`python -B -m unittest test_artifact_set_publication.ArtifactSetPublicationTests.test_mapping_copy_failures_reject_before_publication_without_private_details -v`の該当1件成功。製品コードは初回検証後変更なし。固有64件の最終結果は63成功/1skip。新規4件を既存CI登録済みsuiteへ追加。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- コピー中に外部変更される独自mappingの原子的snapshotやmemory上限/caller真正性は保証しない。正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### temp公開書込みの件数検証（2026-10-26）

- 利用者の次実装指示を受け、基準`77ece88`、クリーンな同branch `codex/manifest-entry-bounds`で[temp書込み件数検証](../validation/lock-recovery-acceptance-gate.md#exact-temporary-file-write-counts-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- 単一file公開を最大1,048,576 byte/chunkのmemoryview書込みへ変更。write返却値はexact intかつchunk長一致のみ許可し、short/zero/過大/負/非int/boolは固定`artifact_write_incomplete`で停止。再試行/明示flush・fsync/linkへ進まず部分tempを保全する。closeによるbuffer flushは起こり得る。正常/空payloadのflush/fsync/読戻し/identity/祖先検査は維持する。集合の後続file失敗は固定理由を伝播し、先行公開成果物を保全してmarker非公開とする。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_atomic_artifact_publication test_artifact_set_publication test_crash_publication_harness test_internal_publication_crash test_terminal_bundle_integration test_owned_publication_integration`の計60件中59成功・既存symlink作成不可1skip。新規4件を既存CI登録済みsuiteへ追加し、multichunk/不正返却値/空payload/2件目のshort writeを確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- caller payloadのmemory上限や正式write provider/永続run契約を追加しない。short write後のtempは未検証のまま保全しcleanup/retry/修復しない。正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 公開先basenameの全件事前検査（2026-10-26）

- 利用者の次実装指示を受け、基準`af78bcc`、クリーンな同branch `codex/manifest-entry-bounds`で[公開先basenameの事前検査](../validation/lock-recovery-acceptance-gate.md#destination-basenames-before-publication-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- 集合publisherの全件payload/marker検査に、既存単一file側の末尾空白/dot禁止を反映。不正な後続artifact/marker名を全publish前に拒否し、入力不備だけによる先行fileのpartial公開を防ぐ。単一file側の既存basename検査もparent I/O前へ移動。既存partial集合の保全・valid fileの順序・同一bytes再公開・no-overwriteは維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_atomic_artifact_publication test_artifact_set_publication test_crash_publication_harness test_internal_publication_crash test_terminal_bundle_integration test_owned_publication_integration`の計56件中55成功・既存symlink作成不可1skip。新規4件を既存CI登録済みsuiteへ追加。不正名の全publish非呼出し・既存partial保全・単一fileのparent非検査/temp非生成を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 集合側の入力厳格化と単一file側の拒否優先順位変更。Windows namespace/alias全体の新方針や自動cleanup/回復は採用しない。正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 単一file公開比較を期待payload長で制限（2026-10-26）

- 利用者の次実装指示を受け、基準`72995bd`、クリーンな同branch `codex/manifest-entry-bounds`で[期待bytesによる比較上限](../validation/lock-recovery-acceptance-gate.md#publication-comparisons-bounded-by-expected-bytes-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `AtomicArtifactPublication._same_bytes`でregular fileの初期sizeが期待payload長と異なる場合はopenせず不一致を返す。既存destinationは従来のconflictでtempも生成しない。初期size一致時も最大1,048,576 byte/chunk・期待長+1 byteへ制限し、増大は固定変更理由で停止。既存handle/path/祖先/内容検査・staging/final/cleanupの保全境界を維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_atomic_artifact_publication test_artifact_set_publication test_crash_publication_harness test_internal_publication_crash test_terminal_bundle_integration test_owned_publication_integration test_artifact_read_stability`の計73件中72成功・既存symlink作成不可1skip。新規4件を既存CI登録済みsuiteへ追加し、size不一致の非open/非生成・空/複数chunk同一再公開・読取中増大・open前変化を確認。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 既知の期待bytes長を使う拒否側の制限であり、新しい本番上限やschema制約は採用しない。初期size競合は本文検証を省略するが、同一判定や公開許可を返さない。caller payloadのmemory/読取遅延・正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### marker producer/consumerのtransaction文法を一致（2026-10-26）

- 利用者の次実装指示を受け、基準`a62f2cb`、クリーンな同branch `codex/manifest-entry-bounds`で[transaction文法共通化](../validation/lock-recovery-acceptance-gate.md#publisher-and-classifier-transaction-grammar-2026-10-26)を実装。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- generic UUID parserがnil/version範囲外/non-RFC variantを公開でき、既存classifierではcommittedにできない不一致を修正。既存consumerのversion 1〜8/RFC variant/hyphenated文法をpure共通関数へ抽出しpublisherも再利用、不正値はpayload検査・全publish呼出し前に固定理由で拒否する。大小文字の受入れ・markerの元綴り・期待transactionのexact比較を維持。新しい文法選択や既存不正markerの修復は行わない。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_set_publication test_artifact_set_recovery test_artifact_set_directory_verification test_terminal_bundle_integration test_owned_publication_integration test_crash_publication_harness test_internal_publication_crash`の計73件中72成功・既存symlink作成不可1skip。新規3件を既存CI登録済みsuiteへ追加し、64通りのversion/variant/caseを実file公開→directory verifierで読戻し。publisher/recoveryはいずれも既存両role package内でfile集合50件は不変、PS/schema/package回帰を重複実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- producerの不正入力を既存consumer契約へ厳格化した互換性変更。正式transaction protocol/provider・caller真正性・receipt/owner/root/FS/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### 成果物集合のcaller期待値をI/O前に検査（2026-10-26）

- 利用者の次実装指示を受け、基準`4a12761`、クリーンな同branch `codex/manifest-entry-bounds`で[期待値の事前検査](../validation/lock-recovery-acceptance-gate.md#artifact-set-expectations-before-filesystem-access-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `verify_published_artifact_set`の期待hash mappingコピーをroot/path検査前へ移動し、既存pure classifierのname/hash/transaction文法で事前検査する。不正文法は既存blocked decision、非mapping/空/marker名衝突/コピー失敗は固定directory errorで、I/O前に拒否する。独自mapping例外の内容は非echo。valid入力は事前分類結果を捨て、実bytes/marker/再読取・再列挙による従来の分類を維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_set_directory_verification test_artifact_set_recovery test_artifact_directory_reparse test_terminal_bundle_integration test_owned_publication_integration test_artifact_read_stability`の計76件中75成功・既存symlink作成不可1skip。新規5件を既存CI登録済みsuiteへ追加し、既存mutation injection2件は実marker分類時に発火するよう追従。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- caller不備はroot利用不能より先に拒否する検査順序の変更。最初のroot検査中の元mapping変更はコピーへ影響しないが、copy中の外部変更に対する原子的snapshotやcaller真正性は保証しない。正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可は追加しない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### marker付き成果物集合の読取上限（2026-10-26）

- 利用者の次実装指示を受け、基準`61091e7`、クリーンな同branch `codex/manifest-entry-bounds`で[集合読取上限](../validation/lock-recovery-acceptance-gate.md#caller-selected-artifact-set-read-bounds-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `verify_published_artifact_set`へoptional file別`maximum_artifact_bytes`/初期集合size合計`maximum_total_bytes`を追加。不正値はI/O前、markerを含む全観測fileのsize超過は最初のpayload open前に拒否する。partial/marker欠落でもskipしない。全読取を最大65,536 byte/chunk・初期size+1に変更し増大停止、既存signature/hash/marker/transaction/最終再読取・再列挙を維持する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_set_directory_verification test_artifact_directory_reparse test_terminal_bundle_integration test_owned_publication_integration test_artifact_read_stability`の計58件中57成功・既存symlink作成不可1skip。新規7件を既存CI登録済みsuiteへ追加。新規integrationの例外型を専用型へ厳密化後、該当1件を再実行して成功。両PC相当の候補bundle前後観測へ指定上限を渡し、超過時も元bundle/priorを保全しownerを解放する。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。文書リンク/差分確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 合計は初期集合sizeで、validatorの累積読取予算とは別。最終再読取のI/Oを再計上せず、caller mapping件数/JSON複雑度/全memory/遅延も制限しない。Noneではcaller上限なし、固定本番値/保持方針/新schema制約を採用しない。分類成功はsnapshot観測であり正式writer/receipt・root/FS/owner/現在性/ABA・電源断/実Drive/runtime受け入れやArchive/状態変更の認可ではない。次は同branchで既承認の独立範囲を選び、未決仕様を推測しない。

### report参照validatorの合計読取size予算（2026-10-26）

- 利用者の次実装指示を受け、基準`6af2f9b`、クリーンな同branch `codex/manifest-entry-bounds`で[合計検査size予算](../design/aggregation-report-v1-proposal.md#aggregate-inspected-size-budget-2026-10-26)を追加。公開基準mainは前確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `maximum_total_artifact_bytes`をvalidator/CLI/report wrapperへ接続。不正値はI/O前に拒否し、呼出しごとに新予算を生成。report/manifest/B2証拠/3 schemaで共有し、各open前に初期sizeを計上する。最終read-set再読取も毎回計上、残予算不足は固定理由で全体拒否する。file別上限・signature/祖先/hash/意味論検査は維持。周囲のmanifest directory読取は別予算。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_read_stability test_aggregation_referenced_artifacts test_manifest_report_selection test_manifest_reader_bounds test_terminal_bundle_integration test_aggregation_report_builder.AggregationReportBuilderTests.test_existing_referenced_artifact_validator_accepts_generated_fixture`の計71件成功・skipなし。新規6件＋既存の型検査/CLI検査を拡張し、既存CI登録済みsuiteへ含めた。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。変更文書リンク/差分を確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- 予算は受け入れた初期検査sizeの合計であり物理I/O量/全memory制限ではない。既存の増大検知で追加1 byteを読み得るが、その呼出しは変更として停止する。Noneではcaller合計上限なし、固定本番値/新schema制約/保持方針は選ばない。JSON複雑度/遅延/実root/FS/owner/clock/現在性/ABA・正式writer/provider・実Drive/runtime受け入れは未実証。次は同branchで既承認の独立範囲を選び、未決provider/C-02/資源方針を推測しない。

### report参照validatorのfile別bytes上限（2026-10-26）

- 利用者の次実装指示を受け、基準`7c1d540`、クリーンな同branch `codex/manifest-entry-bounds`で[report参照読取の明示上限](../design/aggregation-report-v1-proposal.md#caller-selected-local-read-bounds-2026-10-26)を実装。公開基準mainは前単位確認の`6e9ad82`（PR #44）で、今回GitHub状態の再取得は行っていない。branch切替・push/PRなし。
- `validate_referenced_artifacts`にoptional `maximum_artifact_bytes`を追加。I/O前に厳密型検査し、report/manifest/B2証拠/3 schemaの各fileについて初期size超過をopen前に拒否、最終read-set再読取にも同上限を適用する。全読取を最大65,536 byte/chunk・初期size+1 byteに変更し増大時停止。既存signature/祖先/hash/意味論再導出検査を維持。CLI `--maximum-artifact-bytes`とreport付きmanifest readerへ接続し、wrapperの不正値もmanifest I/O前に拒否する。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'`後、`python -B -m unittest test_artifact_read_stability test_aggregation_referenced_artifacts test_manifest_report_selection test_manifest_reader_bounds -v`の56件、`python -B -m unittest test_terminal_bundle_integration -v`の8件、`python -B -m unittest test_aggregation_report_builder.AggregationReportBuilderTests.test_existing_referenced_artifact_validator_accepts_generated_fixture -v`の1件、計65件成功・skipなし。新規10件を既存CI登録済みsuiteへ追加。schema/PS/配布file集合50件は不変で無関係な検証は再実行しない。変更文書リンク/差分を確認、root自己点検のみ・独立レビュー/新CIなし。この記録を含むローカルコミットで区切り次の指示を待つ。未push・新PRなし。
- Noneはcaller上限なし、固定本番上限/新schema制約/保持方針は選ばない。file別上限であり合計I/O/memory/JSON複雑度/実root/FS/owner/clock/現在性/ABA・正式writer/provider・実Drive/runtime受け入れを保証しない。周囲のmanifest directory観測には従来のcandidate/total bytes・entry上限を別途指定する。次は既承認の独立範囲を同branchで選び、未決provider/C-02/資源方針を推測しない。

### #002からの継続・manifest列挙件数上限（2026-10-26）

- 利用者の継続指示を受け、GitHubのmainとローカルmainが`6e9ad82d8ae11146041b5eba0ab6b94e21c5cad8`で一致し、[PR #44](https://github.com/wasawo/eo-log-maintenance-public/pull/44)がマージ済み、作業ツリーがクリーンであることを確認した。PR #44本文にはPR/mainのValidate・Package Validation成功記録があるが、本単位では過去CIを再実行していない。新branch `codex/manifest-entry-bounds`をmainから作成し、upstreamは設定していない。下の「本セッション終了」は前セッションの記録であり、今回の継続指示で新しい実装1単位を開始した。
- [manifest列挙件数の明示上限](../design/latest-manifest-selection.md#explicit-entry-budget-for-directory-observations-2026-10-26)を既存readerとreport wrapperへ追加。optional `maximum_entries`をI/O前に厳密型検査し、初回/最終列挙とも全entryを数え、最初の超過で名前保持・payload読取前に全体拒否する。別period/旧run/不正entryをskipせず、既存bytes上限と非fallback検査を維持する。固定本番値・保持/cleanup方針・schema制約は決めない。
- Python 3.11.9（CI 3.12）で`$env:PYTHONPATH='tests;.'; python -B -m unittest test_manifest_reader_bounds test_manifest_directory_reader test_manifest_report_selection test_manifest_recovery_integration -v`を実行。bounds13件（新規6件＋既存7件の型検査/forwarding拡張）、directory19件、report10件、recovery7件の計49件成功・skipなし。既存CI登録済みsuiteを拡張し、新CIは未実行。PS/schema/配布file集合50件は不変で無関係な検証を再実行しない。文書相対リンク/差分を確認しroot自己点検のみ、独立レビューなし。この記録を含むローカルコミットで区切り、次の指示を待つ。未push・新PRなし。
- 件数上限はOS列挙時間/名前長/JSON複雑度/全memory/report・evidenceの読取上限ではない。root/FS/owner/clock/現在性/ABA・正式writer/provider・実Drive/runtime受け入れは未実証。次は既承認の独立範囲を同branchで選び、未決C-02/provider/資源方針を推測しない。PR作成は利用者指示時のみ。

### 累積PR承認と本セッションの終了範囲（2026-10-26）

- 利用者が`c24b13a`までの実装35コミットをまとめたPR作成・マージを明示承認。本節の引き継ぎ記録を同じPRへ含め、最新PR HEADのValidate/Package Validation両成功を確認してsquash mergeする。作業branchは`codex/drive-download-observation`、比較基準は正本main `ccd4ffaf2d785828a700afe8a294f35ef308df43`。本記録時点では未push/未PR/未マージであり、結果はGitHub実状態を確認する。
- 累積範囲：Drive完全page/hash/不足download計画/前後・一括内容比較、source/B2と初期inventory/件数要約、stagingコピーの単一/一括読取・source/Drive隔離接続、明示容量式/size射影と未資格Windows空きbytes/128-bit祖先identity、残存entry件数観測、manifest全履歴/pending段階/file別Upload4回上限/初期B2から終端report/使用点候補接続、checkpoint追記/file読取/予算・使用点接続とWin32負例、manifest候補のcaller指定bytes上限。schema/event/providerの未決契約を推測せず、実行権限は付与しない。レビューpackageは50 files。
- PR前統合検証：Python 3.11.9（CI 3.12）で`python -B -m unittest discover -s tests -p test_*.py`計742件、740成功/既存symlink作成不可2skip。PS bridgeは7.6.7を明示。PS 7.6.7でlog49・容量67・空き領域35・root142成功、両role package回帰と変更PS構文/PSScriptAnalyzer Error成功。累積相対リンク欠落0・diff検査成功。root自己点検のみ、独立レビューなし。これらは新CIやruntime受け入れの代替ではない。
- **マージ後は本セッションで次の実装を始めず終了する。後続作業は新規セッションで行う。** 次の担当はこの節・現在main/PR/CI・作業ツリーを照合し、マージ済みbranchを再利用せず最新mainから新しい`codex/`作業branchを作る。PR作成は利用者指示時のみ。実現したPR/merge SHAとCI結果は本チャットの添付PR/最終報告およびGitHubを照合する。
- 未完：実Drive/credential/C-02詳細・正式PS orchestrator/task、metadata-first/event/永続run writer/CASとtrusted writer排除・一回限りreceipt、実root/ACL/FS/owner/clock/AC/session/account/provider資格、rollback/ABA・電源断・両PC/Tier B/C/runtime受け入れ。helper/CI成功を配布/実適用/削除/PC-B archiveの許可にしない。次の実装範囲は新規セッションで既承認契約と未決事項を照合して選ぶ。

### 直近の実装単位

- 基準`d073ebc`、同じ`codex/drive-download-observation`で[manifest directory読取りの明示bytes上限](../design/latest-manifest-selection.md#explicit-byte-budgets-for-directory-observations-2026-10-26)を追加。caller指定のoptional候補別/全候補合計上限を型検査し、旧run/別period等も含む初期size全件をpayload open前に検査する。超過候補をskip/fallbackせず全体拒否。読取りは最大65,536 byte/chunk・初期size+1 byteで増大停止し、既存signature/最終再列挙は維持する。
- report付き選択も前後2回のmanifest観測へ同じ上限を渡す。Python 3.11.9（CI 3.12）で新規bounds7件＋既存directory/report29件の計36件成功、skipなし。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 固定の本番上限値/新schema制約は採用せず、Noneではcaller上限なし。report/evidence validator内の読取り・entry数/JSON複雑度/全memoryは今回の上限対象外。root/FS/owner/clock/現在性/ABA・実Drive/runtime受け入れは未実証。次は既承認の独立作業を選び、未決provider/資源方針を推測しない。

## 直前の実装単位（checkpoint file→予算観測・d073ebc）

- 基準`859e966`、同じ`codex/drive-download-observation`で[既存checkpoint file→確認待ち予算観測](../design/completion-wait-budget.md#既存fileの上限付き読取観測2026-10-26)を追加。独立scope/clock/AC/指定上限で毎回fileを読み、元checkpointと既存budgetのcheck_due/wait/hold助言をimmutable型へ保持する。全確認/待機/Archive/状態変更許可false、plan作成/試行消費・file更新・sleep/task予約を行わない。
- Python 3.11.9（CI 3.12）で新規file予算8件＋既存budget16件＋file観測8件の計32件成功、skipなし。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 24時間/25回/間隔/残余window不足や資格不足は既存holdを保持。AC不明・欠落/破損・scope/clock/精度不備は拒否し、空履歴/通常waitへ変換しない。前回dueを流用しない。root/owner/clock/AC/session/account/provider資格、rollback/ABA・正式CAS/永続試行前計上・実確認/毎時task/runtime受け入れは未完。次は既承認の独立作業を選び、未決保存provider契約を推測しない。

## 直前の実装単位（file使用点/実Win32負例接続・859e966）

- 基準`f9116d5`、同じ`codex/drive-download-observation`で[file plan/使用点と実Win32置換probeの隔離接続](../design/checkpoint-compare-provider-qualification.md#file使用点との実置換接続2026-10-26)を追加。自作/所有検査済みtemp内の固定名だけで共有guard中の置換失敗/保全と解除後読戻し、competitor置換後のfresh before_commit拒否を確認する。製品provider/更新APIは追加しない。
- 負例として、競合を古いcandidateで無条件上書きした後のafter_commit bytes一致と、同一bytes別fileへの置換で実identityが変わった後のbefore_commit一致を確認。全確認/状態変更/Archive許可falseを維持し、bytes一致を途中writer不在/identity lease/receipt/rollback/ABA防止と解釈しない。
- Python 3.11.9（CI 3.12）で新規native接続4件＋既存probe5件＋file使用点8件の計17件成功、skipなし。CI suite登録、CI自体未実行。配布file集合50件/PS/schema/製品codeは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 正式CAS/provider・trusted writer排除・predecessor/更新/readback/一回限りreceipt binding・owner/root/ACL/FS/clock/資格・永続計上/実確認・対象volume/再起動/電源断/runtime受け入れは未実証。次は保存providerの既承認境界と未決writer排除/receipt条件を照合し、未決事項を推測せず独立範囲を選ぶ。

## 直前の実装単位（checkpoint file→plan/使用点接続・f9116d5）

- 基準`ae4191b`、同じ`codex/drive-download-observation`で[checkpoint file観測→試行plan/保存前後使用点の接続](../design/completion-wait-budget.md#既存fileの上限付き読取観測2026-10-26)を追加。明示AC/資格boolを検査して既存fileからexact plan生成、使用点はplan/phase/clock/scope/資格の純粋事前検査後に毎回再読取し、保存前expected/保存後proposed bytesを再確認する。両入口はread-only、全確認/状態変更/Archive許可false。
- Python 3.11.9（CI 3.12）で新規file使用点8件＋既存純粋使用点10件＋file観測8件の計26件成功、skipなし。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 保存済み成功/観測をfile代用にせず、欠落/破損/変更を非fallbackで拒否。合成所有lock取得後の変更でもownerを解放して変更bytesを保全。fixture内の候補bytes書込みは正式CAS/provider証拠ではない。実root/ACL/FS/owner/clock/AC/session/account資格、rollback/ABA・永続試行前計上・実確認/task/runtime受け入れは未実証。次は既承認の独立作業を選び、未決保存provider契約を推測しない。

## 直前の実装単位（checkpoint既存file読取観測・ae4191b）

- 基準`093658d`、同じ`codex/drive-download-observation`で[checkpoint既存fileの上限付き読取観測](../design/completion-wait-budget.md#既存fileの上限付き読取観測2026-10-26)を追加。明示絶対path/Windows L1・caller指定bytes上限・祖先/reparse・regular/単一link・path/handle signatureを検査し、初期size+1以内を読んで既存schema/scope/clock readerへ渡す。解析後もsignature/祖先chainを確認。file作成/更新/削除なし、全確認/Archive/状態変更許可false。
- Python 3.11.9（CI 3.12）で新規file観測8件＋既存transition8件＋checkpoint reader12件の計28件成功、skipなし。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 既定file名/配置/サイズ制限は採用せず、上限はcaller資源制限。実root/ACL/token/FS/owner/provider資格、rollback/ABA/同時snapshot/後続不変性、正式CAS/試行前永続化・実確認/runtime受け入れは未実証。次はfile観測を既存試行plan/使用点と接続する独立範囲を選び、実更新providerの未決契約を推測しない。

## 直前の実装単位（checkpoint前後追記検査・093658d）

- 基準`3f2dea3`、同じ`codex/drive-download-observation`で[PC-A checkpoint前後の1試行追記検査](../design/completion-wait-budget.md#更新前後の追記検査2026-10-26)を追加。両recordを独立scope/clock/schemaで検査し、元start/既存確認履歴の文字列/順序を保全した1件追記かexact再掲載だけを許す。短縮/置換/一括追記/元時刻の再表記を拒否。既存試行planのcandidate読戻しへ接続、全確認/状態変更/Archive許可false。
- Python 3.11.9（CI 3.12）で新規transition8件＋既存checkpoint/attempt25件の計33件成功、skipなし。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 25回目/24時間/間隔と高精度時刻の既存制限を維持。exact再掲載を新試行receiptにしない。元recordの真正性/現在性・保存喪失/rollback/ABA防止・原子的compare-and-publish/試行前永続化・OS/clock/root/FS/owner/資格・実確認/runtime受け入れは未実証。次は既承認の独立作業を選び、未決provider契約を推測しない。

## 直前の実装単位（manifest履歴のUpload上限・3f2dea3）

- 基準`8afa7c4`、同じ`codex/drive-download-observation`で[提示manifest履歴のfile別Upload上限](../design/manifest-transition-inspection.md#提示履歴のupload試行上限)を追加。ready→pendingを初回、unknown→pendingを再試行境界として最大4回を検査し、5回目を拒否。登録pending/同一snapshot/配列順で消費・リセットせず、別file予算を合算しない。4回後のunknownをfailedへ変えず、超過履歴は終端report生成前に停止する。
- Python 3.11.9（CI 3.12）で新規予算8件＋既存履歴10件＋終端履歴9件の計27件成功、skipなし。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 提示履歴の境界検査であり、実API試行の漏れない記録/実送信・永続counter・60/300/900秒待機・unknown retry前の完全不在照合やPS orchestratorを実装/認証しない。全公開/Upload/retry/Archive許可false。metadata-first/event/provider/root/FS/使用点・writer/runtime受け入れは未完。次は既承認の独立作業を選び、未決仕様を推測しない。

## 直前の実装単位（終端履歴使用点/候補bundle接続・8afa7c4）

- 基準`70d4cb9`、同じ`codex/drive-download-observation`で[終端履歴planの使用点再導出＋候補bundle隔離接続](../design/manifest-transition-inspection.md#初期planからの全履歴binding)を追加。独立初期plan/履歴/B2/現在running bytes/AC/contextと厳密型/flagsを確認し、全履歴/reportを毎回再構成してplan全体とexact照合する。自作tempの合成所有lock内で現在runningを読み、別candidate保存/semantic読戻しを両PC相当で接続。元runningは更新せず、全公開/Upload/retry/Archive/状態変更許可false。
- Python 3.11.9（CI 3.12）で新規使用点/隔離接続9件＋既存全履歴9件の計18種類成功、skipなし。初回27件にはimportによる既存9件の重複実行を含み、module aliasへ整理。nested plan/historyの厳密型/flag検査強化後、新規9件のみ再実行して成功。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- lock取得後の現在running変更/AC喪失では候補fileを書かず、変更bytesを保全してowner解放。独立引数のprovider真正性/履歴完全性・metadata-first/event証拠・実copy/Drive/API・owner/root/clock/FS/容量/使用点・実writer/永続化/runtime受け入れは未実証。次は既承認の独立作業を選び、未決provider/event契約を推測しない。

## 直前の実装単位（初期plan/全履歴/終端report binding・70d4cb9）

- 基準`f964bca`、同じ`codex/drive-download-observation`で[初期plan/B2→連続履歴→終端report候補のbinding](../design/manifest-transition-inspection.md#初期planからの全履歴binding)を追加。独立contextでexact初期planを再構成し、先頭exact一致と全履歴のpending段階/遷移/終端を検査。最初のterminalと本来のrunning priorを既存OSD-03/G1 report builderへ接続し、終端繰返しでもpriorを取り違えない。専用immutable plan/全公開・Upload・retry・Archive・状態変更許可false。
- Python 3.11.9（CI 3.12）で新規9件＋既存history10件＋terminal plan9件の計28件成功、skipなし。初回はテストのreport status参照先2か所が既存schemaと不一致、修正後新規9件成功。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 未解決file/error/不完全coverageをsuccess/no_workへ補完せず、runningだけの履歴は終端reportへ変換しない。履歴真正性/完全性・event/metadata-first証拠・実copy/Drive/API・owner/clock/FS/容量/使用点・writer/永続化/runtime受け入れは未実証。次は既承認の独立作業を選び、未決writer/event契約を推測しない。

## 直前の実装単位（manifest連続履歴検査・f964bca）

- 基準`8721021`、同じ`codex/drive-download-observation`で[初期登録からのmanifest連続履歴検査](../design/manifest-transition-inspection.md#初期登録からの連続履歴検査)を追加。exact snapshot tupleを既存pair/schema/identity/凍結inventory/時刻/verification/終端検査へ通し、path単位で登録pendingとUpload直前pendingを区別する。登録pending→uploaded/unknownとUpload pending→stagingを拒否、unknown→pendingのretry遷移を別計数。全公開/Upload/retry/Archive許可false。
- Python 3.11.9（CI 3.12）で新規history10件＋既存pair11件の計21件成功、skipなし。初回はtest fixtureへschema外outcomeを設定した1件error、修正後history10件成功。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 入力履歴の真正性/完全性・metadata-first/event証拠・実copy/Drive/API・retry不在照合/予算/待機・所有権/clock/FS/使用点・実writer/永続化/runtime受け入れは未実証。終端もOSD-03/B2集約の代替にならず、crash-left runningを修復しない。次は既承認の独立作業を選び、未決writer/event契約を推測しない。

## 直前の実装単位（staging/Drive内容観測接続・8721021）

- 基準`7205366`、同じ`codex/drive-download-observation`で[毎回のstaging再読取とDrive内容観測比較の接続](../design/source-inventory-revalidation.md#既存stagingとdrive観測の接続)を追加。独立context/初期plan/明示allocationでcopyを再照合してから、元basename/size/hashを独立source信頼・前後完全列挙・不足hash計画/完了集合の厳密比較へ渡す。共通Drive不備はlocal観測保全/比較集合なしheld、file単位不一致は個別held。全Upload/retry/同期成功/状態変更/Archive許可false。
- Python 3.11.9（CI 3.12）で新規接続8件＋既存staging batch8件＋計画比較7件の計23件成功、skipなし。初回は既存suite名を取り違えImportError、正名で実行して成功。接続内部の型/tuple/件数/全false flag検査強化後、新規接続＋計画比較15件成功。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- PC suffixの暗黙alias/出所推測なし。空選択はno_workではなく、copy一致からsource信頼や実Upload結果を推測しない。正式metadata/history・割当identity/root/FS/owner/容量/使用点資格・実API/Upload/再試行/同期/runtime受け入れは未完。次は既承認の独立作業を選び、未決writer/adapter契約を推測しない。

## 直前の実装単位（既存staging一括照合・7205366）

- 基準`fc7dc29`、同じ`codex/drive-download-observation`で[既存staging一括照合](../design/source-inventory-revalidation.md#既存staging-copyの独立読取観測)を追加。全allocationのI/O前検査・重複target/候補名拒否・plan再構成1回・全選択fileのhash前size確認と全hash後signature/祖先chain照合を行い、指定順tuple全体か拒否のみを返す。単一APIもbatchへ委譲、全操作許可falseを維持する。
- 共有hash helperへoptional expected_sizeを追加。凍結sizeと初期statが異なるfileはopen前に拒否し、open handle照合/size+1 byte上限も維持する。Python 3.11.9（CI 3.12）で新規batch8件＋単一8件＋既存hash identity9件＋builder7件の計32件成功、skipなし。CI suite登録、CI自体未実行。配布file集合50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 空選択はno_workではなく、選択外fileを検査しない。逐次観測であり同時snapshot/ABA/後続不変性は未実証。正式metadata-first/history・割当identity binding・root分離/FS/owner/容量/使用点資格・実Upload/adapter/runtime受け入れは未完。次は既承認の独立作業を選び、正式writerの未決field契約は推測しない。

## 直前の実装単位（既存staging copy読取照合・fc7dc29）

- 基準`4ab120a`、同じ`codex/drive-download-observation`で[凍結planと既存staging copyの読取照合](../design/source-inventory-revalidation.md#既存staging-copyの独立読取観測)を既存SourceInventoryRevalidation moduleへ追加。独立contextでexact planを再構成し、明示target/sequence・basename L1字句を検査。source非読取で既存copyの祖先chain/reparse/regular/単一link・前後entry signature・bounded size/hashを確認する。全Upload/状態変更/cleanup/Archive許可false。
- Python 3.11.9（CI 3.12）で新規8件＋既存使用点/copy接続16件成功、skipなし。初回はtest側のinit=False field改変方法に1件error、fixtureを修正して新規8件成功。自己点検でbasename L1検査追加後も新規8件成功。CI定義登録、CI自体未実行。配布file集合50件/PS/schemaは不変、無関係な検査を再実行しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミット後は指示待ち、push/PRなし。
- 未完：正式metadata-first/history・copy時割当identity binding・root分離/ACL/FS/provider/owner/容量資格・実Upload使用点/adapter/runtime受け入れ。同時snapshot/ABA/後続変化を防止せず、source不在でも照合成立することはUpload認可にならない。次は正式writerの既承認契約と未決field境界を整理してから実装範囲を選ぶ。

## 直前の実装単位（tests専用upload staging copy接続・4ab120a）

- 基準`d178815`、同じ`codex/drive-download-observation`で[tests専用upload staging copy接続](../design/staging-file-lifecycle.md)を追加。凍結plan/B2/source再検査を合成所有lock下のcreate-new copy・fsync/close・identity/単一link/size/hash読戻し・source最終照合に接続する。既存名の上書きなし、次sequenceは明示指定のみ。部分file/変更fileを保全し、失敗時もownerを解放する。
- 両PC/log、空/複数block、source変化、衝突、部分disk-full注入、short write、copy後改変/元sourceへのhardlink置換を検証。Python 3.11.9（CI 3.12）で新規7件＋既存使用点9件の計16件成功、skipなし。CI定義へ新規suite登録、CI自体は未実行。配布50件/PS/schemaは不変で重複検査しない。文書相対リンク/差分を確認。root自己点検のみ、独立レビューなし。ローカルコミットで区切り、push/PRなし。
- tests-onlyであり正式copy/metadata-first writer/ready状態/Upload/cleanupを提供しない。全Upload/状態変更許可false。実容量枯渇、電源断、同時snapshot/ABA、root/FS/provider資格・runtime受け入れは未実証。次は既承認の独立作業を選ぶ。正式writer/providerの未決境界は推測せず残す。

## 直前の実装単位（残存staging直下観測・d178815）

- 基準`6e33967`、同じ`codex/drive-download-observation`で[残存staging直下entry観測](../design/staging-residual-observation.md)を追加。既存絶対rootを内容非読取・非再帰で列挙し、file/dir/otherの件数と警告要否を返す。reparse/不明/重複/前後変化はheldとして、初回確定件数を保持する。0観測を不完全なまま完全検査へ変えない。
- 全作成/Upload/cleanup/Archive許可false。metadata解析/field集合・旧run所有権・時刻based cleanup・運用status変更を採用しない。直下列挙成立は完全startup gateやroot/FS/provider資格ではない。追加moduleを両roleレビューpackageへ登録しfile集合は50件。Python 3.11.9（CI 3.12）で新規8件成功（skipなし）。PS 7.6.7で両role package回帰・変更package試験PS構文/PSScriptAnalyzer Error検査成功。変更のないsource/Drive/容量/native root/schema検査は繰り返さない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実staging/root/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：正式残存metadata/旧run検査・startup warning/失敗/Upload停止の強制とroot/FS/owner/provider資格、実source/容量/copy、実SDK/C-02/credential・C1/C2 writer・Drive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（初期inventory件数要約・6e33967）

- 基準`1b3bb33`、同じ`codex/drive-download-observation`で[初期inventoryの件数のみ要約](../design/initial-inventory-observation.md)を追加。専用観測型・元B2・選択/比較件数/順序/対象対応/全false flagを検査し、inventory全体/選択/比較済み/候補/held/未比較/既知errorを分離する。共通不備は未比較、空選択は全体0件とは区別する。
- path/filename/ID/hash/bytes/reasonを要約へ転記せず、固定kind/statusと整数件数のみ返す。歴史要約でsource/Driveを再観測せず、保存/診断イベント/通知/正式reportを採用しない。全操作許可false、現在性やreceiptにも昇格しない。Python 3.11.9（CI 3.12）で追加件数要約＋既存初期inventory接続の計13件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実source/Drive/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：初期inventoryの永続schema/root/診断/通知、source/backupとfolder/query/metadata/完了の真正性/現在性、実SDK/C-02/credential・root/FS/owner/clock/使用点、C1/C2 writer・復元/同期/両PC/archive gateとruntime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（初期inventory接続・1b3bb33）

- 基準`ae6ef30`、同じ`codex/drive-download-observation`で[初期inventory専用の読取観測接続](../design/initial-inventory-observation.md)を追加。PC-A sourceを毎回再観測し、明示pathの比較元とDrive前後列挙/計画/完了hashの厳密batch比較を件数・順序付きで結ぶ。専用型へ元B2/選択path/各比較を保持し、共通不備は比較file集合なしでheld、選択/B2は保全する。
- 運用manifest型/状態/report/保存とは分離し、同期成功/復元/Archive/運用manifest公開の許可は全false。空選択を全件完了/no_workへ変えず、既知errorや過去B2を補完しない。永続inventory schema/rootや実SDK/C-02は採用しない。Python 3.11.9（CI 3.12）で追加初期inventory接続＋既存source batch/計画比較の計21件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実source/Drive/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：専用inventory永続schema/保存領域と診断、source/backup・folder/query/metadata/完了の真正性/現在性、実SDK/C-02/credential・root/FS/owner/clock/使用点、C1/C2 writer・復元/同期/両PC/archive gateとruntime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（PC suffix命名・ae6ef30）

- 基準`930e672`、同じ`codex/drive-download-observation`で[PC suffixの純粋命名観測](../design/drive-content-comparison.md)を追加。承認済みsource filename文法/実在日付と既存L1字句を検査し、元basenameを保持してextension直前へ_PCA/_PCBを付ける。Unicode/case/spacingや既存suffix文字列から出所を推測/修復しない。
- 元名/候補名/指定PC/logをimmutableに保持し、rename/Upload/上書き/Archive許可は全false。候補名でB2/source文法を変更せず、OSD-01 name比較も別名化しない。既存fileの出所/内容差/競合の確認と衝突解消は別gate。Python 3.11.9（CI 3.12）で追加命名＋既存直接比較/L1字句の計18件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：原名/final名の正式adapter結果/記録・衝突解消orchestratorと現在内容/出所確認、実SDK/C-02/credential、root/FS/token/clock/owner・容量/使用点資格、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（祖先chain照合・930e672）

- 基準`031ecfb`、同じ`codex/drive-download-observation`で[空きbytes観測の祖先chain照合](../design/staging-file-lifecycle.md)を追加。leaf→drive rootのcanonical/extended identityを前後収集し、空/未取得/legacy・長さ変化・各位置の差を拒否する。内部path/IDを公開結果へ出さず、FreeSpaceReliable/作成/Upload許可はfalseのまま。
- leafのID/bytesを維持したまま親を同名差替えする隔離試験と、合成chain不備を追加する。移動の全絶対pathは自作temp配下を検査する。連続metadata観測であり、同時snapshot・query中pin・ID再利用/ABA・実root/FS資格は未実証。既存canonical API/native layoutは不変。PS 7.6.7で空きbytes/祖先chain35件成功（junction skipなし）。変更PS構文/PSScriptAnalyzer Error検査成功。native layout/既存canonical APIが不変のため前単位で成功したroot142件は重複実行しない。配布file集合49件/schema/Python codeは不変のためpackage/schema/Python検査も再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実運用root/FS/provider/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実root/FS/provider/token/clock/ownerと容量資格・使用点、正式PS transport/対象履歴/copy失敗対応、実SDK/C-02/credential・C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（FileIdInfo必須化・031ecfb）

- 基準`cf1cdd4`、同じ`codex/drive-download-observation`で[空きbytes観測のFileIdInfo必須化](../design/staging-file-lifecycle.md)を追加。同一handleで64-bit volume serial/128-bit file IDも取得し、全bitを保持して前後照合する。pre/post未取得・legacy-onlyは保留し、64-bit照合へfallbackしない。pre未取得は空きbytes query前に停止する。
- 既存canonical文字列/legacy観測APIの互換性は維持。内部形式でありconfig/owner-v2形式を決めず、公開結果へidentityを出さない。native取得・UInt64最大値付近の各field差・pre/post未取得を追加検証する。FSごとの対応・ID再利用/ABA・query中pin/実root資格は未実証で、信頼/許可flagはfalseのまま。PS 7.6.7で空きbytes/extended identity30件＋既存root検査142件成功（junction/short-name skipなし）。変更PS構文/PSScriptAnalyzer Error検査成功。配布file集合49件/schema/Python codeは不変のためpackage/schema/Python検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実運用root/FS/provider/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実FS/provider/token/root/clock/ownerと容量資格・使用点、正式PS transport/対象履歴/copy失敗対応、実SDK/C-02/credential・C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（directory identity照合・cf1cdd4）

- 基準`b48ac0e`、同じ`codex/drive-download-observation`で[空きbytes query前後のdirectory identity照合](../design/staging-file-lifecycle.md)を追加。同じnative handleからcanonical path/volume serial/file index high・lowを観測し、前後の検出可能な差を拒否する。既存canonical文字列APIは委譲して維持し、内部identityを公開結果やログへ出さない。
- 同名directoryの実差替えと、同じcanonical名で各identity fieldが変わる合成試験を追加する。FSごとのID制約/再利用/ReFS 64-bit非一意性・query中のpin/ABAは未解決で、FreeSpaceReliable/作成/Upload許可はfalseのまま。PS 7.6.7で空きbytes/identity21件＋既存root検査142件成功（junction/short-name skipなし）。変更PS構文/PSScriptAnalyzer Error検査成功。配布file集合49件/schema/Python codeは不変のためpackage/schema/Python検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実運用root/容量/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実root/provider/FS/token/clock/ownerと容量資格・使用点、正式PS transport/対象履歴/copy失敗対応、実SDK/C-02/credential・C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（Windows空きbytes観測・b48ac0e）

- 基準`c6add52`、同じ`codex/drive-download-observation`で[Windows caller利用可能bytesのmetadata観測](../design/staging-file-lifecycle.md)を既存root inspectorへ追加。既存drive-rooted directory/reparse排除・前後canonical観測一致を要求し、GetDiskFreeSpaceExWのcaller available UInt64をBigIntegerで返す。失敗/変更時は固定reason/null bytesで保留し、path/volume/raw例外を返さない。
- 成功もFreeSpaceReliable=false、MayCreateStaging/MayUpload=falseで、実root/token/ACL/FSの資格・現在性/同時snapshot/ABA・予約を証明しない。Add-Type初期化を含むDry Run A/runtime資格は未実証。自作OS-tempだけでnative読取・mock最大値/障害/変更と既存root回帰を検証する。PS 7.6.7で追加空きbytes16件＋既存root検査142件成功（junction/short-name skipなし）。変更PS構文/PSScriptAnalyzer Error検査成功。配布file集合49件/schema/Python codeは不変のためpackage/schema/Python検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実運用root/容量/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実root/FS/token/clock/ownerと容量の資格・使用点、正式PS transport/対象履歴/copy失敗対応、実SDK/C-02/credential・C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（容量stdin bridge・c6add52）

- 基準`078cabc`、同じ`codex/drive-download-observation`で[Python size射影→PS容量の隔離bridge](../design/staging-file-lifecycle.md)をtests専用に追加。合成exact manifest/B2からsizeを導出し、数値/信頼値だけをstdin JSONで固定driverへ渡す。PS 7.6.7の実版と、stdoutの合計/必要量が整数を保つことを検査する。
- 両PC/log・閾値/1 byte不足・巨大整数・空集合/固定reserve・不明空き容量・不正memberを検査する。入力のcode評価・実path/設定/容量照会/保存/通信はなし。stdin shapeを正式IPC/C-02採用へ昇格せず、全MayCreateStaging/MayUpload=false。Python 3.11.9（CI 3.12）＋PS 7.6.7で追加bridge試験4件・合成入力16ケース成功（skipなし）。変更tests PS構文/PSScriptAnalyzer Error検査成功。配布file集合49件/runtime code/schemaは不変で、既存のsize射影/PS容量67件・package/schema検査は重複実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実容量/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：正式PS transport/encoding/重複key/security資格、履歴に基づく実target選択とsource/容量/root/FS/clock/owner資格、copy失敗対応、実SDK/C-02/credential・C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（manifest/B2のsize射影・078cabc）

- 基準`e5b8428`、同じ`codex/drive-download-observation`で[凍結manifest/B2からの明示size射影](../design/staging-file-lifecycle.md)を追加。独立PC/log/period/run・schema/digest/inventory/coverage/clock整合を検査し、明示canonical path群のsize tuple/整数合計を元exact bytesへ結び付ける。空選択も全体検査を省略せず、既知errorsを消さない。
- pendingはstaging前/Upload直前の両方なので、file状態から残りtargetやcopy可否を推測しない。runningは生存/fresh runの証拠ではなく、全may_create_staging/may_upload/may_archive=false。内部Python観測でPS transport/保存/遷移は未実装。Python 3.11.9（CI 3.12）で追加size射影＋既存initial plan/遷移の計25件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実source/容量/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：履歴に基づく実target選択・source/容量/root/ACL/FS/clock/owner資格、PS transportと開始/各file直前の取得・copy失敗対応、実SDK/C-02/credential・C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（明示size配列の合計・e5b8428）

- 基準`c52d359`、同じ`codex/drive-download-observation`で[明示target size集合の容量合計](../design/staging-file-lifecycle.md)を追加。1次元配列の非負Int32/Int64/BigIntegerを全件検査してBigInteger合計を導出し、既存容量観測へ接続する。不正memberで部分合計を返さず、空配列も固定reserve計算を省略しない。
- 残りtarget/manifest状態の選択やinventory出所は外部gateに残し、入力を変更せず、全MayCreateStaging/MayUpload=false。EOLM-STG-009を純粋計算/合計のみpartialとして対象行だけ更新する。PS 7.6.7で容量観測/配列合計の計67件成功（既存43件を含む）。変更PS構文/PSScriptAnalyzer Error検査成功。前単位で成功した変更のないLogFunctions既存49件は重複実行しない。配布file集合49件/schema/Python codeは不変のためpackage/schema/Python検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実容量/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実target選択/凍結inventoryと容量/root/ACL/FS/clock/owner資格、開始/各file直前の取得・容量変化時copy失敗、実SDK/C-02/credential・C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（upload容量式・c52d359）

- 基準`f579da4`、同じ`codex/drive-download-observation`で[upload staging容量式の純粋観測](../design/staging-file-lifecycle.md)を既存PS helperへ追加。非負Int32/Int64/BigIntegerのremaining/freeと明示reliableから、残りbytes＋ceil(10%)＋100,000,000 bytesを整数のみで算出する。型不正は拒否、不明/不足は保留。0残量も固定reserveを省略しない。
- 結果はMayCreateStaging/MayUpload=falseで、実空き容量を取得/予約せず、downloadの容量方針へ転用しない。開始時/各file直前のfreshなprovider観測・容量変化時の保存失敗対応は正式runtime gateに残す。PS 7.6.7で追加容量観測43件＋既存LogFunctions 49件成功。変更PS構文/PSScriptAnalyzer Error検査成功。配布file集合49件/schema/Python codeは不変のためpackage/schema/Python検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実容量/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実容量/root/ACL/FS/clock/owner資格とupload copy接続、実SDK/C-02/credential・全page/download成功binding、同時snapshot/ABA/電源断、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（download staging隔離接続・f579da4）

- 基準`0659bc3`、同じ`codex/drive-download-observation`で[download新規stagingの隔離接続](../design/drive-content-comparison.md)をtests専用に追加。自作OS-temp/所有marker/実mutex内で試行ごとに別directoryとcreate-new fileを使い、flush/close後の実fileをhash観測へ接続する。計画→実staging→読戻しhash→再page→計画完了集合検査/比較までを合成接続する。
- 途中失敗/short/overlong/未完了/不正chunk/root/requirementと読戻し前変更を拒否し、旧部分file/競合fileを保全する。次試行は新file、失敗時もowner解放。cleanupは自作rootのidentity/marker確認後だけ。正式root/filename/API/容量方針は採用せず、Dry Run Aを緩和しない。Python 3.11.9（CI 3.12）で追加staging接続＋既存計画完了集合/hashの計21件成功（skipなし、通常の隔離試験権限で実行）。配布file集合49件/PS/schema/runtime codeは不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/FS/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実SDK/ID・bytes・完了/queryの真正binding・C-02/credential、PS retry予算/時間/新staging資格、正式root/ACL/容量/FS/owner/clock、敵対的ABA/同時snapshot・process crash/電源断耐久性、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（計画/完了集合検査・0659bc3）

- 基準`8f13fd0`、同じ`codex/drive-download-observation`で[計画と完了download集合の整合接続](../design/drive-content-comparison.md)を追加。plan/requirementの厳密型/全false flagを確認し、現source/列挙から毎回再導出して一致を要求する。前後列挙不変、計画IDと完了観測IDの全件一致・実size一致の場合だけ各sourceの比較へ進む。
- 改変/不足/余分/重複/未知ID/size不一致/共通不備は部分結果なしで全体保留。誤hashは各結果で保留し、既存のfileごと不足観測を保留するAPIは維持。source batch→page→計画→合成bytes/hash→再page→完了集合検査→比較を接続し、計画/観測再利用・空集合を権限/成功/no_workへ変えない。Python 3.11.9（CI 3.12）で追加計画接続＋既存download計画/Drive batch/source batchの計28件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実SDK/ID・bytes・完了/queryの真正binding・C-02/credential、source/観測の現在性・同時snapshot/ABAと使用点資格、実root/FS/owner/clock、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（不足hash対象計画・8f13fd0）

- 基準`ca81da1`、同じ`codex/drive-download-observation`で[不足download hash観測の対象計画](../design/drive-content-comparison.md)を追加。完全列挙・明示source信頼/folderに対し、同名同sizeのSHA欠落/未確認fileをIDごとにまとめて安定順序で返す。信頼済みSHA・名前/既知size違いは除外し、同名size不明や共通不備は部分計画なしで保留する。
- statusは必要観測あり/比較入力あり/heldを区別し、may_downloadを含む全may_*false。対象0件・計画再利用から成功/no_work/実行/再送を認可しない。source batch→page→計画→合成download hash→再page→一括比較を接続する。Python 3.11.9（CI 3.12）で追加download計画＋既存Drive batch/前後照合/直接比較/source batchの計37件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実SDK/取得時ID・完了・size/queryの真正binding・C-02/credential、観測の現在性/同時snapshot/ABAと使用点資格、実source/root/FS/owner/clock、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（Drive一括比較・ca81da1）

- 基準`be0df71`、同じ`codex/drive-download-observation`で[共通Drive観測の複数source一括比較](../design/drive-content-comparison.md)を追加。前後列挙・download集合を一括検査し、名前別indexから指定順の各ContentComparisonを返す。共通不備は部分結果なしのheld、file固有の不明/不一致/0/複数候補は各結果のheldに残す。
- batchのcomparedは比較処理完了のみで、同期成功/no_workへ変えない。空入力でも共通観測を検査し、重複sourceを勝手にdedupしない。batch/各結果の全may_*false。単一source API/直接比較は共通部品へ接続し、source batchから共通page/download/一括前後比較への合成接続も更新する。Python 3.11.9（CI 3.12）で追加Drive batch＋既存source batch/単一接続/前後照合/page/download hash/直接比較の計54件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実SDK/全page/query/成功binding・C-02/credential、観測の真正性/鮮度・同時snapshot/ABA・使用点資格、実source/root/FS/owner/clock、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（source一括再観測・be0df71）

- 基準`79e2f29`、同じ`codex/drive-download-observation`で[PC-A比較元の複数target一括再観測](../design/drive-content-comparison.md)を追加。明示path tupleの型/字句/重複/target存在/filenameを全件I/O前に検査し、1回の全source再列挙/hashから指定順の比較元tupleを返す。単一target APIは1要素batchへ委譲して互換性を維持する。
- 選択外を含むinventory変化/不完全で全体を拒否する。空選択も全再観測し、空結果をno_work/成功へ変えない。元B2 bytesを参照し、cache・暗黙の選択/期間補完・権限昇格なし。合成の複数source→共通page/download→前後比較まで接続する。Python 3.11.9（CI 3.12）で追加batch＋既存単一source接続/Drive前後照合の計21件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実SDK/全page/query/成功binding・C-02/credential、source/metadataで見えない変化/ABA/同時snapshotと使用点資格、実root/FS/owner/clock、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（Drive前後照合・79e2f29）

- 基準`1ca5cd4`、同じ`codex/drive-download-observation`で[download前後の完全列挙観測照合](../design/drive-content-comparison.md)を追加。両観測の型/flags/完全性/folder/file/ID一意性と全metadata集合を照合し、変化なしの場合だけ既存比較へ進む。並び順差は許すが、追加/削除/rename/ID置換/size/hash/信頼確認状態や対象外fileの変化は保留する。
- 実APIの再取得や前後関係/現在性は認証せず、保存済み観測やmetadata一致をreceipt/実行許可へ変えない。結果は全may_*false。PC-A source再観測→page→download hash→再page→比較の合成接続も更新する。Python 3.11.9（CI 3.12）で追加前後照合＋既存source接続/page/download hash/比較の計40件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実SDK/全page/query/成功の真正なbinding・C-02/credential、metadataで見えない内容変化/ABA/同時snapshotと使用点資格、実source/root/FS/owner/clock、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（比較元source再観測・1ca5cd4）

- 基準`b2155d6`、同じ`codex/drive-download-observation`で[比較元のPC-A source再観測接続](../design/drive-content-comparison.md)を追加。exact B2とcanonical relative path・独立scope/clock/reference date・明示source信頼確認を要求する。PC-Aの一意targetを選択し、全sourceを毎回再列挙/hashして一致時だけ比較元と元B2を返す。同名別pathを推測せず、PC-B/未信頼/対象不在・不正/不完全・source変更を拒否する。
- immutable観測も全may_*false。sourceの真正性をPC-Aラベル/hashから認証せず、既知validation errorsをrun成功へ変えない。合成source→page→download hash→比較まで接続し、元bytes/source保全とcandidate書込み0件を確認する。Python 3.11.9（CI 3.12）で対象43件中、初回42件成功・既存rename試験1件がsandbox temp内アクセス拒否。コード/期待値を変えず、その1件を通常の隔離試験権限で再実行して成功（skipなし）。対象は追加比較元接続＋既存source再観測/page/download hash/比較。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：source/folder/metadata/clock/owner/root/FSの真正性と使用点資格、観測後の変化/ABA・同時snapshot、実SDK/全page/download成功binding、C-02/credential、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（page集約・b2155d6）

- 基準`148fe6f`、同じ`codex/drive-download-observation`で[内部pageの完全列挙観測集約](../design/drive-content-comparison.md)を追加。各pageのfolder/成功・requested/next tokenの連続性・循環なし・一意終端とID重複なしを検査し、全iteratorの正常終了後だけfile集合を返す。0 page/終端欠落/途中例外/余分なpage/不明fileを完全な0件へ変換しない。
- page/結果は内部immutable観測で、IPC C-02結果schemaを定めず、実API応答の出所/成功/全件を認証しない。結果も全may_*false。既存file検査を共通化し、合成page→download実bytes hash→比較の接続と複数内容一致時保留を追加する。Python 3.11.9（CI 3.12）で追加page集約＋既存download hash/比較の計26件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実SDKとquery/folder/token/成功の真正なbinding、pagination/timeout/件数予算/resource管理、C-02詳細/credential、実source/metadata/clock/owner/root/FS、C1/C2 writerとDrive/runtime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（download stream観測・148fe6f）

- main`ccd4ffaf2d785828a700afe8a294f35ef308df43`は[PR #43](https://github.com/wasawo/eo-log-maintenance-public/pull/43)マージ済み。mainの[Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40174574117) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40174574154)とも成功確認済み。再開指示を受け、最新取得mainから新branch`codex/drive-download-observation`を作成した。
- 既存比較moduleへ[download chunkの実bytes/hash観測](../design/drive-content-comparison.md)を追加。独立期待sizeと明示完了・file IDを要求し、非空exact bytes chunkをstream処理して既存DownloadHashObservationへ結び付ける。size超過時は残りを読まず停止し、不足/途中例外/不正chunkで観測を返さない。raw例外は固定reasonへ置き換える。
- bytes蓄積・自動retry/close・temp保存は行わない。stream所有権/解放とfile ID・完了の真正なbindingはcaller/providerに残る。合成chunk/hashからOSD-01比較fallbackまで接続する。Python 3.11.9（CI 3.12）で追加stream観測＋既存比較の計17件成功（skipなし）。配布file集合49件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：実SDK/IPC C-02/credential、全page取得と信頼済みsource/folder/metadata・download完了/ID binding、timeout/resource管理、C1/C2 writer、実root/ACL/FS/owner/clock、両PC/Drive/archive gateとruntime受け入れ。次は確定済みの独立作業か未決provider境界の候補整理。

## 前PRの準備記録（PR #43へ統合済み）

- 2026-10-25、利用者が「ここまでの実装をまとめてPR作成してマージして」と明示承認。最新取得main`1036b30`（PR #42）に対し、`codex/initial-manifest-plan`の8実装コミット`efc6733`〜`5e38d7f`と本記録を1PRにまとめる。記録時点はpush/PR/新CI/マージ前。
- 範囲：B2初期running/pending plan、source実列挙との隔離接続、凍結B2再観測と初期使用点、列挙完了前再確認、hashの早期identity/サイズ上限検査、終端plan使用点再導出、OSD-01の同一内容比較候補。関連tests/docs/CIと両roleレビューpackage49件を含む。IPC/保存schemaとPS runtime契約は変えない。
- 各単位の対象検証結果は以下に保持。最新単位のPython 3.11.9の比較9件、PS 7.6.7の両role package/変更PS検査は成功済み。既に成功したローカル試験は重複実行せず、今回の最新PR HEADに対するValidate（Python 3.12）/Package Validation両成功をマージ条件とする。root自己点検のみ、独立レビュー未実施。
- 未完：実Drive SDK/OAuth/credential・C-02詳細、真正なsource/folder/metadata・全page/download観測、C1/C2 writer、実root/ACL/FS/owner/clock、両PC/Drive/archive gateとruntime受け入れ。純粋helper/合成fixture/レビューpackage成功で代替しない。
- 承認はこの累積PR作成とCI成功後のマージまで。マージ後は指示待ち。次変更は最新mainから新作業ブランチを作り、マージ済みbranchへ追記しない。

## 直前の実装単位（OSD-01比較・5e38d7f）

- 基準`6e40614`、同じ`codex/initial-manifest-plan`で[OSD-01同一内容比較](../design/drive-content-comparison.md)を実装。source信頼・folder scope・完全列挙を要求し、exact name/size/hashの一意候補のみ返す。cloud SHA欠落/未確認はIDへ結び付いた完了download hashを要求し、0/複数/不明/重複ID/矛盾は保留する。結果は全may_*falseで、IPC C-02結果fieldを定めず、出所・復元・同期成功・archiveを認可しない。
- 追加helperを両roleレビューpackageへ登録しfile集合は49件。Python 3.11.9（CI 3.12）で追加比較試験9件成功（skipなし）。PS 7.6.7で両role package回帰・変更PS構文/PSScriptAnalyzer Error検査成功。文書相対リンク欠落0・差分検査成功。既存source/manifest/report/schemaは変更がなく再実行しない。root自己点検のみ、独立レビュー・新CI・実Drive/runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：source/folder/metadataの真正性・最新性、実全page取得/download検証、C-02詳細とSDK/credential資格、同期runtime・両PC証拠/Drive/archive gate。C1/C2 writerや実root/FS/owner/clock受け入れも未完。次は確定済みの独立作業か未決provider境界の候補整理。

## 直前の実装単位（終端plan使用点・6e40614）

- 基準`f774aaa`、同じ`codex/initial-manifest-plan`で[終端plan使用点再導出](../design/manifest-transition-inspection.md)を追加。独立prior/B2 exact bytes・PC/log/period/run・AC・現在時計/schema/参照pathを要求し、既存遷移/report生成を毎回実行してplan全体とexact一致を検査する。型/flag/snapshot/AC/scope/reportの不一致を拒否し、返すplanも全may_*false。
- 合成試験は両PC/logのempty/成功/混在、改変行列、実mutex/owner内の公開前再検査と不一致時の候補書込み0件・prior保全・owner解放を確認する。fixtureのcallbackはtests専用で、正式writer/provider契約へ採用しない。Python 3.11.9（CI 3.12）で追加使用点＋既存終端plan/遷移/候補bundle/初期planの計42件成功（skipなし）。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。配布file集合48件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：入力prior/B2/ACの出所・最新性、実root/owner/clock/FSの資格、検査後の変化・敵対的ABA、C1比較更新・Drive/runtime受け入れ。次は確定済みの独立作業かprovider未決境界の候補整理。

## 直前の実装単位（hash早期照合・サイズ超過停止・f774aaa）

- 基準`307dd67`、同じ`codex/initial-manifest-plan`で[source hashの早期照合・サイズ超過停止](../design/source-enumeration-stability.md)を追加。開いたhandleのidentityが直前path観測と違えばbyte読取前に拒否し、読取上限を観測サイズ＋1 byteへ制限する。連続追記のEOFを追い続けず、short readも拒否する。既存理由code/不完全coverage/観測済みデータの保持を維持する。
- 合成試験で別handleのread未呼出し・context解放、EOFのない模擬streamの停止、short read、空/1 MiB境界のexact hashを追加。Python 3.11.9（CI 3.12）で追加hash試験＋既存source列挙/再観測/使用点/初期接続の計56件成功（skipなし）。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。配布file集合48件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：OS read自体のblock/timeout、hash後から使用までの変化、atomic snapshot/敵対的ABA、実root/ACL/FS/clock/owner/provider資格、C1/C2 writer・Drive/runtime受け入れ。次は確定済みの独立作業かprovider未決境界の候補整理。

## 直前の実装単位（列挙完了前再確認・307dd67）

- 基準`a72d6fd`、同じ`codex/initial-manifest-plan`で[source列挙の完了前再確認](../design/source-enumeration-stability.md)を追加。directory/ancestor identityとchild名・属性の初期snapshotを保持し、hash/分類完了後に全directoryを再列挙する。追加/削除/rename/属性変化/差替え/読取不明はcoverage incompleteへ落とす。
- 観測済みtarget/hash/errorを保持し、空集合やno_workへリセットしない。snapshot時にreparse/属性不明があれば不完全とし、その先へ走査しない。scandirを明示closeし、root metadataとchainの初期対応も検査する。最後の再確認は再hashではなくnamespace/metadata観測で、ABAや同時snapshotの資格ではない。
- 合成試験は後続追加/削除/rename/既読file変更、directory追加/差替え、空scan後追加、rescan失敗、non-targetの列挙中変更、使用点再観測の不成立によるcandidate書込み0件を追加。既存junction試験の期待値を「再走査回数」から「source外を走査しない」境界へ整合した。
- Python 3.11.9（CI 3.12）で追加列挙安定性＋既存builder/reparse/再観測/使用点/初期接続の計47件成功（skipなし）。配布file集合48件/PS/schema契約は不変のためpackage/PS/schema検査は再実行しない。文書相対リンク欠落0・差分検査成功。root自己点検のみ、独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 未完：最終観測から使用までの変化、原子的snapshot・敵対的ABA/属性復元、実root/ACL/FS/owner/clockの資格、C1/C2 writer・Drive/runtime受け入れ。次はprovider未決境界の候補整理か、確定済みの独立作業を選ぶ。

## 直前の実装単位（初期source使用点・a72d6fd）

- 基準`673052d`、同じ`codex/initial-manifest-plan`で`revalidate_initial_manifest_source`を接続。厳密なInitialManifestPlan型/全false flag・明示AC trueを検査し、独立PC/log/period/run/開始時刻・現在時計/schemaから初期planを再構成してexact一致を要求してから、sourceを新しく再観測する。
- planの書式だけの変更/別state/別B2やscope変更、AC未確認・不正flagはsource I/O前に拒否する。保存済みSourceInventoryObservationやtrue値をreceiptとして受け付けず、呼出しごとに再列挙/hashする。返す結果は全may_*falseの観測で、実root/AC/token/clock/owner資格を認証しない。
- 合成の実mutex/owner内で使用点検査を候補公開の前へ接続し、一致時の候補保存・source変更/AC切断時のcandidate書込み0件・owner解放/元plan保全を確認する。callback/配置はtests専用で、正式runtime契約やC1/C2 providerの採用ではない。
- 追加使用点・既存再観測/初期接続を一括検証する。配布file集合48件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で追加使用点＋既存再観測/初期接続の計27件成功（skipなし）。改変/AC/contextの行列は試験内subcase。変更のないsource/report/terminal/配布構成・PS/schema検査は再実行しない。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：観測直後から実使用までのnamespace/bytes/AC変化、同時atomic snapshot/ABA排除、実fresh run/24時間資格・root/ACL/owner/clock/provider、C1/C2 writerとDrive/runtime受け入れ。次はそれらのprovider境界候補の整理か、確定済みの独立実装を選ぶ。

## 直前の実装単位（凍結source再観測・673052d）

- 基準`ac29ec1`、同じ`codex/initial-manifest-plan`で[凍結source再観測](../design/source-inventory-revalidation.md)を追加。独立source/scope/reference date/現在UTCとexact B2を検査し、元coverageがcompleteの場合だけ既存builderで再列挙/hashしてtarget集合と分類観測を比較する。元/再観測の不完全・追加/削除/rename/内容/分類変更を保留する。
- 結果は元B2 bytes/target数のimmutable observationで全may_*はfalse。再生成B2や内部のhost終了時刻を保存/証拠化せず、旧B2を補完/更新しない。既知validation errorを消さず、non-target fileの内容/identityは比較範囲外と明示した。root IDは独立期待ラベルで、物理root認可や時計/ownerの真正性を認証しない。
- 両PC/log、変更行列、不完全/読取失敗、事前scope/clock/date/schema拒否、元bytes不変と比較限界を合成検証する。Common helper1件を追加し、両roleレビュー配布のfile集合は48件。CIとpackage fixtureへ登録した。
- 対象再観測/source builder/初期接続と両role package・変更PS構文/Error解析を一括確認する。Python 3.11.9（CI 3.12）で追加再観測＋既存source/初期接続の計25件成功（skipなし）。PS 7.6.7で両role package回帰と変更PS構文/PSScriptAnalyzer Error検査成功。変更のないreport/terminal等は再実行しない。root自己点検のみ、独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：再観測後の使用点同一性、atomic snapshot/ABA排除、実root/ACL/token/clock/run/ownerの資格、C1/C2 writerとDrive/runtime受け入れ。次はこの観測と初期候補の使用点検査/隔離接続、またはprovider未決境界の候補整理。

## 直前の実装単位（source→初期候補接続・ac29ec1）

- 基準`efc6733`、同じ`codex/initial-manifest-plan`でsource列挙/hash→B2→初期plan→隔離候補公開/読戻しを接続した。新規tests専用fixtureは自作tempのsource/candidateを分離し、固定合成clock/reference dateと明示run contextで既存source builderを呼ぶ。実運用path/clock資格やsource使用点の認可を実装したとはしない。
- 初期plan producerは既存の承認filename文法/実在日付helperも使い、B2内部整合が取れていてもunclassifiableなeligible targetを拒否する。対象period/保持範囲の選択は既存source builder/独立contextに留め、新しい年/月filterを推測しない。
- 両PC/log・Unicode階層の実bytes/hash、空/対象外/invalid分類、hash不明のincomplete保全、source変更後も旧plan不変/別runで再列挙、実mutex/create-only/marker-last候補保存、既存競合、同じ固定観測の決定性を合成検証する。候補artifact-setのcommittedを実run開始/manifest更新/Upload認可へ昇格しない。
- 追加接続・既存initial plan/source builderを一括検証する。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で追加source接続＋既存initial/source builderの計23件成功（skipなし）。両PC/log・分類状態などは試験内subcase。変更のないterminal/report/readback・package/PS/schema検査は再実行しない。root自己点検のみで独立レビュー・新CI・実運用受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：source列挙後から使用点までの同一性、fresh run/clock/token/root/ownerの真正性、C1/C2の初回publication/比較更新runtime統合、Drive/受け入れ。次はそれらの境界の候補整理、または確定済みの独立実装を選ぶ。

## 直前の実装単位（B2初期plan・efc6733）

- 最新mainは`1036b304aaac13d60dfae5d5e8ed51a3354edf1d`。[PR #42](https://github.com/wasawo/eo-log-maintenance-public/pull/42)はマージ済み、mainの[Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40163423575) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40163423523)も成功確認済み。再開指示を受け、最新取得mainから新branch`codex/initial-manifest-plan`を作成した。
- 既存遷移moduleへ`prepare_initial_manifest`を追加。独立したPC/log/target period/run ID/開始UTCと信頼できる現在UTC、exact B2 bytes、static schemaから、running・全pending・未検証metadataの初期候補を構築する。B2 digest/count/scope/inventoryを既存validatorで照合し、開始→列挙開始→列挙完了の順序と現在+5分上限を検査する。
- immutable planはproposed/evidence bytesを保持し、may_publish/may_upload/may_archiveはfalse。空/failed/incomplete/error B2を成功/no_workへ昇格せず、識別子/時刻/欠落入力を補完しない。B2の出所・実際のfresh inventory・保存先不在・実clock/owner/FS資格を認証しない。
- 両PC/log、欠落/改変/scope不一致、Unicode/開始表記/元bytes、時間境界、I/Oなしと、初期→掲載中間ペア→終端reportの合成接続を追加。関連initial/snapshot/terminal planだけを一括検証する。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で追加initial plan＋既存snapshot/terminal planの計28件成功（skipなし）。両PC/logとB2状態・時刻境界は試験内subcaseとして扱う。変更のないsource builder/report/保存・package/PS/schema検査は再実行しない。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：実source選択/列挙の使用点資格、fresh runと真正scopeのbinding、C1/C2の初回create-only/比較更新writer、現在Drive確認、正式runtime/受け入れ。次は初期planと既存source builder/隔離保存の接続、またはprovider未決境界の候補整理。

## 前PRの準備記録（PR #42へ統合済み）

- 2026-10-25、利用者が「ここまでの実装をまとめてPR作成してマージして」と明示承認。最新main`42221e3`（PR #41）に対し、`codex/manifest-evidence-integration`の実装7コミット`eb3f6c5`〜`a206e4e`と本記録を1PRへまとめる。この時点はpush/PR/新CI/マージ前。
- 範囲：終端遷移/B2/report plan接続、全report意味論再導出、隔離候補bundleの実公開/読戻し、参照file/schemaの安定読取観測、最新manifest/report path・bytes binding、artifact-set transactionと再観測、単一公開staging/final/所有temp cleanupの防御。配布file集合は47件で不変、PS/保存schemaの契約は変えない。
- 各単位のPython 3.11.9での対象検証結果・skip・再実行理由は下記に保持。CIはPython 3.12/PS 7.6.7で最新PR HEADのValidateとPackage Validation両成功を確認する。root自己点検のみで独立レビュー未実施。実Drive/実root・ACL・FS/Tier B/C、atomic snapshot/敵対的ABA、C1比較更新/receipt/runtime受け入れは未完のまま。
- 今回の承認はこの累積PR作成・CI成功後マージまで。マージ後は次実装へ進まず指示待ち。次変更は最新mainから新branchを切り、マージ済みbranchへ追記しない。

- [PR #42](https://github.com/wasawo/eo-log-maintenance-public/pull/42)作成済み。初回HEAD`efdda2f`はPackage Validation成功・Validate失敗。Windows Python 3.12でstat/fstatのctimeが異なる意味になる比較を含んでいたため、4moduleで明示birthtime_ns（未対応版は従来ctime）を使うよう整合した。POSIXのctime比較、identity/size/mtime/bytes検査は維持。CPython 3.12一次実装を確認し、模擬回帰を追加した。
- ローカルPython 3.11.9で修正影響の62件中60件成功・既存symlink不可2件skip。新HEADの両CI成功を確認するまでマージしない。初回失敗は[Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40162859743)の記録として保持する。

## 直前の実装単位（単一公開readback/cleanup・a206e4e）

- 基準`7d9a891`、同じ`codex/manifest-evidence-integration`でcreate-only単一file公開のstaging/readback/cleanupを強化。既存helperはfsync後の再読込をせず、temp名を無条件にunlinkしていたため、handle由来のtemp identityと親chainを保存し、公開前にexact bytes＋identityを再検査する。
- 公開後もfinal pathが当該temp由来のidentityで内容が一致することを確認する。同一既存fileの比較はpath/handle・前後metadata・親chainに結び付いたexact bytes比較へ変更。root/reparseはresolve前に拒否する。既存file上書きや比較更新能力は追加しない。
- cleanupは同じ親chain・regular temp identity・exact bytesを再確認できる場合だけ既存のtemp unlinkへ進め、差替え/内容変更/不明なtempは保全する。観測とunlinkの間の敵対的raceまで閉じたとはしない。公開後不明/不一致でもfinalをrollback/削除せず、電源断耐久性を保証しない。
- staging内容/identity差替え、cleanup直前の同一bytes別file、偽link成功、既存fileのhandle不一致を合成試験に追加。対象単一公開・artifact-set公開・所有lock接続・process crash harness・終端bundleを一括検証する。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で関連37件を実施。初回stdin起動ではmultiprocessingの8件が子processから起動元を読めず未検証となり、通常の`python -B -m unittest`＋PYTHONPATH=testsで当該7件＋残り1件だけを確認して全成功。最終的に36件成功・既存symlink作成不可の1件skip。既に成功した試験は再実行しない。PS/schema/配布構成不変のためpackage/PS検査は未実行。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミットまでで待機、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：root/ACL/FS・実owner/scopeの資格、敵対的namespace変更の完全防止、C1比較更新・一回限りreceipt、実Drive/Tier B/C/runtime受け入れ。これはcreate-only helperの防御強化で、正式manifest更新providerの採用ではない。次はprovider境界の候補整理か、確定済みの独立作業を選ぶ。

## 直前の実装単位（artifact-set transaction/読戻し・7d9a891）

- 基準`afca3ce`、同じ`codex/manifest-evidence-integration`でartifact-set classifierとdirectory verifierを強化。optionalな独立期待transaction IDを共通APIへ接続し、valid UUIDであっても期待文字列とexact不一致ならcommittedにしない。未指定時は従来のunbound分類を維持し、marker schema/fieldは変更しない。
- directory verifierはcaller期待hash集合を開始時copyし、root/祖先chain・file path/handle・読取前後metadata/byte長を照合。分類後にdirectoryを再列挙し、全artifact/markerのexact bytesを再読込、さらに再列挙して変化を拒否する。fixture固有だったtransaction照合を既存終端bundleにも接続した。
- 共通分類の型/別transaction/文字列非正規化、directoryのlate変更/追加・handle不一致・読取中変更・期待map変更を合成試験へ追加。既存reparse/read失敗試験はstream open経路へ障害注入を合わせ、reparse先を読まないことも維持する。
- 対象はclassifier/directory/reparse/終端bundleの関連試験を一括。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で関連38件中37件成功・1件skip。skipは既存symlink作成が端末で利用できないcaseで、実Windows junction/reparse・read失敗試験は成功。変更のないlatest/report/builder・package/PS/schema検査は再実行しない。root自己点検のみ、独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。期待transactionもcaller由来観測で、実owner/run binding・一回限りreceiptを認証しない。unboundなcommittedを特定試行の認可にせず、同時atomic snapshot/敵対的ABA・実root/ACL/FS/C1比較更新・実Drive・Tier B/C/runtime受け入れは未完。次はprovider未決境界の候補整理か、確定済みの独立作業を選ぶ。

## 直前の実装単位（最新manifest/report binding・afca3ce）

- 基準`db2e774`、同じ`codex/manifest-evidence-integration`で最新manifest選択とreport意味論を接続。既存directory readerへ`read_latest_manifest_with_report`を追加し、C4で選んだexact bytesと規定basename/pathを参照validatorの独立期待値へ渡す。report位置は明示入力で、自動推定/生成しない。
- 参照validatorのoptional期待bytes/pathは両方セットのみ許可し、未知型・片方欠落・別path・読取bytes不一致を拒否。従来の期待値なしAPI/CLIは互換保持。report検査後に最新候補を再列挙/選択し、別候補への変化や新しい未完runを保留する。古い成功/reportへfallbackしない。
- 両PC/log種別、別runの旧report、別pathの同一bytes、選択後bytes＋report hash改変、検証後の新success/running、偽成功、終端failure観測/非終端拒否、期待値不正・時計不明/欠落reportを合成試験に追加。全I/Oは専用tempで実ログ/Driveなし。
- 追加接続・既存directory reader/参照validatorを対象に一括検証する。配布file集合47件/PS/schema契約は不変。Python 3.11.9（CI 3.12）で追加10件＋既存directory/参照validatorの計44件成功（skipなし）。両PC/logや状態の組合せは試験内subcase。変更のないcore選択/builder/bundle、package/PS/schema検査は再実行しない。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。返すものは読取観測のみ。実root/ACL/tokenの認可、時計の取得/信頼性、24時間の実行鮮度、実Drive/両PC安全証拠、同時原子snapshot/ABA排除、C1/C2比較更新とreceipt、runtime/受け入れは未完。次はそれらのprovider境界の候補整理か、確定済みの独立作業を選ぶ。

## 直前の実装単位（安定読取観測・db2e774）

- 基準`a988964`、同じ`codex/manifest-evidence-integration`で参照validatorのreport/manifest/B2/schema読取を強化。resolve前にroot/祖先/reparse属性を検査し、各fileのlstat・open後/読取後fstat・読取後lstat・親chain・byte長を照合する。判定直前に全読取fileをexact bytes/metadata/chainで再読込し、途中変更を検出したら結果を返さない。
- schemaも同じ読取集合へ含め、既に読んだschemaを再利用。外部参照を取得しない既存static schema validatorを使い、不正/解決不能schemaを固定理由で拒否する。root/ACL資格やatomic snapshot、敵対的ABAの完全排除を証明せず、通常読取のTOCTOUを完全に解決したとはしない。
- 合成試験は全6fileのlate変更、handle identity/読取中変更、親chain変更、root/report/参照/schemaのreparse属性、実Win32 junction root、不正/外部/broken schemaのnetwork不呼出しを追加。全データは専用tempで、schemaは追跡中のstatic資料をtempへcopyしたもの。実ログ/Drive/秘密を使わない。
- 関連参照validator・追加読取試験・終端bundle接続を一括検証する。配布file集合（47件）/PS/schema契約に変更なし。Python 3.11.9（CI 3.12）で追加7件＋既存参照/bundleの計30件成功（skipなし、専用tempの実junctionを含む）。各file/reparse/schemaの行列は試験内subcaseとして扱う。変更のないbuilder/plan・package/PS検査は再実行しない。root自己点検のみ、独立レビュー・新CI・実運用受け入れは未実施。root単独、ローカルコミットまでで待機、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：実効ACL/実token/root認可、file read集合の同時原子性・ABA/競合の完全防止、C1/C2 writer/receipt、現在時計/実Drive/Tier B/C/runtime受け入れ。次は比較更新providerの信頼境界・保存/回復条件を候補化するか、確定仕様の別作業を選ぶ。

## 直前の実装単位（終端候補bundle・a988964）

- 基準`187bae2`、同じ`codex/manifest-evidence-integration`でtests専用の終端候補bundle接続を実装。呼出元rootを受けず自作OS-tempに固定し、別置きprior-runningを保持したまま、実mutex/owner＋既存create-only helperでB2/提案manifest/reportを公開し、markerを最後に公開する。fixtureの名前/配置/APIはruntime契約ではない。
- exact plan由来hash/bytes、markerのtransaction、既存directory分類、参照validatorによる全report意味論、最後の再観測を接続した。候補bundleだけが検証済みでもmay_update_manifest/may_archiveはfalse。正式manifestを更新せず、C1比較更新providerや真正な一回限りreceiptを実装したとはしない。
- 両PC/empty/成功/混在、4公開境界での例外・部分file保全・同一bytes再試行、既存競合、marker後応答喪失、別transaction、report改変＋marker再binding、意味論検査直後の変更を合成試験へ追加。process killや電源断ではなくfixtureの例外/変更注入。cleanupは自作・解決済み・所有marker付きtemp rootを再確認してから行う。
- Common/PS/schema/配布file集合（47件）は変更しない。CIに追加接続試験を登録。追加fixtureだけを一括検証し、変更のない既存成功検査は繰り返さない。Python 3.11.9（CI 3.12）で追加8件成功（skipなし）。両PC×3種の結果と4公開境界は各試験内のsubcaseで、独立した件数として加算しない。既存の成功済みreport/plan/publication試験、package/PS検査は変更なしのため再実行しない。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。root単独、ローカルコミットまでで待機し、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：実manifest比較更新、root/ACL/FSと真正な実owner/scope、ABA/読取間競合の完全排除、B2の出所/固定性、使用点clock/鮮度・実Drive/両PC証拠、C3回復、Tier B/C/runtime受け入れ。次はproviderの未決信頼境界・失敗時保存/回復条件を候補化するか、確定済みの独立作業を選ぶ。

## 直前の実装単位（report意味論再導出・187bae2）

- 基準`eb3f6c5`、同じ`codex/manifest-evidence-integration`で終端planのreportと参照validatorを接続した。従来はhash/identity/B2/G1/inventory照合までで、reportの集約status・期間件数・run-scope error等の再導出比較が欠けていたため、既存の決定的builderを共有して全文意味論を検査する。
- `derive_aggregation_report`は明示的に現在時計を観測しない履歴再導出API。内部schema/B2/終端/時系列/G1条件は維持し、通常`build_aggregation_report`と終端planの現在時計/未来許容検査は省略しない。report自身の時刻をtrusted nowに代用せず、旧reportの意味論検査から現在の資格を作らない。
- 参照validatorは読取済みexact bytesから再導出し、JSON whitespace/key順だけを許して全field/array順/整数表現を比較する。偽status/件数/completion/error/順序やfloat整数表現を拒否。direct CLIも同じCommon moduleを実行位置に依存せずロードする。既存empty成功fixtureのmanifest outcomeを承認済みno_workへ修正した。
- 追加/既存のreport builder・参照validator・終端planだけを対象検証する。配布file集合は47件で不変、PS/schemaコード変更なし。Python 3.11.9（CI 3.12）で関連48件を一括実行し47件成功。既存no_work fixture修正に伴う非空inventoryの1件はschemaで先に拒否されたため、当該試験のoutcomeをNoneへ整合し、その1件だけ再実行して成功。成功済み47件は再実行せず、関連48件を確認済み。配布構成/PS/schema不変のためpackage/PS/schema単独検査は再実行しない。root自己点検のみ、独立レビュー・新CI・実運用受け入れは未実施。root単独、ローカルコミット後は指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：trusted root/ACL/使用点read、意味論検査中の変更対策、C1/C2比較更新・marker-last実統合・receipt、現在時計/鮮度・実Drive/両PC証拠・runtime受け入れ。再導出成功は保存・archive認可ではない。次は隔離artifact setとの接続またはproviderの未決信頼境界/障害回復条件の候補整理。

## 直前の実装単位（終端plan・eb3f6c5）

- 最新mainは`42221e36886773b7efbb4e3d58658890690f55b6`。[PR #41](https://github.com/wasawo/eo-log-maintenance-public/pull/41)はマージ済み、mainの[Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40159576258) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40159576256)も成功確認済み。利用者の再開指示を受け、新branch`codex/manifest-evidence-integration`を最新取得mainから作成した。
- 既存moduleに`prepare_terminal_manifest_transition`を追加。exact prior/proposed manifestの掲載遷移・凍結inventory・終端不変を検査した後、B2 digest/scope/target一致とOSD-03集約/G1 report生成を既存builderへ接続する。immutable planは元/提案/B2/report bytesを保持し、全may_*はfalse。欠落prior・不正遷移・未終端file・偽成功を修正せず拒否する。
- reportは提案bytesの派生物で、保存済み/commitの証拠ではない。B2の真正性・固定性・最新性、実event履歴、root/ACL/所有権・C1/C2比較更新・一回限りreadback・実Drive内容は未実装gateのまま。PC-Bも検査できるがarchive権限は与えない。
- 既存配布module内の拡張でfile集合は47件のまま。追加接続試験と既存snapshot/report builderを一括で対象検証する。Python 3.11.9（CI 3.12）で追加接続9件＋既存snapshot/report builderの計42件成功（skipなし）。両log種別のT01〜T12相当は追加試験内の24 subcaseとして確認し、独立した24試験とは数えない。配布file集合/PSコードが不変のためpackage/PS検査は再実行しない。root自己点検のみ、独立レビュー・新CI・実保存/受け入れは未実施。root単独、ローカルコミット後は指示待ち。今回はpush/PR/マージを行わない。
- 文書相対リンク欠落0・差分検査成功。次はこのplanと既存のartifact参照validator/模擬保存の接続、またはproviderの未決信頼境界・障害回復条件の候補整理。planから正式publicationやruntimeの受け入れを推定しない。

## 前PRの準備記録（PR #41へ統合済み）

- 2026-10-25、利用者が「ここまでの実装をまとめてPR作成してマージして」と明示承認。最新取得mainは`fea8753`（PR #40）、`codex/work-branch-policy`の実装8コミット`b4d4600`〜`f8cdea8`を1PRへまとめる。この記録コミットも同じPRに含める。
- 範囲はmain直接push禁止/branch運用、manifest遷移snapshot検査、checkpoint schema/reader/試行plan/使用点検査/模擬保存、実Win32負例probe、AC観測、PS再試行観測と関連試験・文書。正式writer/adapter/task、実counter/待機/再送、C-02詳細、実Drive/Tier B/C/電源断の資格は未完のまま。
- 各実装単位の対象検査・環境差は下記記録を保持し、無変更の成功検査は再実行しない。rootが累積差分と配布範囲を自己点検し、文書相対リンク/差分を最終確認する。独立レビューは未実施。この記録時点はpush/PR/新CI/マージ前で、最新PR HEADのValidateとPackage Validation両成功を確認してからマージする。
- 今回の承認はこの累積PR作成・マージまで。マージ後は次実装に着手せず指示待ち。次変更は最新mainから新しい作業ブランチを切り、マージ済みbranchへ追記しない。

## 直前の実装単位（PS再試行観測・f8cdea8）

- 基準`df03f55`、同じ`codex/work-branch-policy`で既存PS応答helperへ`Get-DriveRetryObservation`を追加。[再試行観測](../design/drive-retry-observation.md)は相関/exit/envelope/retryable検査と、完了試行1〜4・1/5/15分の固定候補をまとめる。
- 整合した成功は再試行せずresult検証を要求。upload一時失敗/全操作timeoutは照合待ち、その他非一時失敗は非再試行、応答欠落/不正・番号欠落/型/範囲不正は拒否する。download候補は新規/空staging等の資格を要求し、4回後に次番号を出さない。全MayRetry=false、実counter・経過時間・request/scope由来の真正性・現在Drive照合を証明しない。
- 新fileは設計文書だけで配布file集合は47件のまま。既存PS試験に4操作/9error/4試行/成功/矛盾/不正番号等の行列を追加。PS 7.6.7で既存応答検査＋追加再試行行列の計490件成功、変更2fileの構文/PSScriptAnalyzer Error検査成功。実行ラッパーの未設定LASTEXITCODE誤判定で解析前に停止したため、成功した試験は繰り返さず未実行の解析だけを別実行した。配布file集合/構成が不変のためpackage回帰は再実行せず、Pythonも変更なしで未実行。root自己点検のみ、独立レビュー・新CI・runtime受け入れは未実施。root単独、ローカルコミットまでで待機し、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。未完：C-02/transport/schema gate、実counter/待機/再送、download staging資格、upload照合、暗黙retry禁止のSDK資格、runtime受け入れ。比較更新providerの信頼境界・失敗時保存/回復条件も未選択。次はそれらの未決を候補化するか、確定済みの独立作業を選ぶ。

## 直前の実装単位（AC電源観測・df03f55）

- 基準`b65abde`、同じ`codex/work-branch-policy`で承認㉓Aを支える読取専用`PowerStatusObservation.py`を追加。比較更新providerの信頼境界/資格が未決のため無条件置換を正式採用せず、独立して進められるAC観測を選んだ。
- GetSystemPowerStatusを呼ぶたびに取得し、成功時のACLineStatus=1/0のみTrue/False。不明・未定義値・API失敗・未対応OSはNone、固定reasonのみでraw例外/電池metadataを返さない。全may_*はfalse。使用点へ合成観測を接続し、保存後AC切断/不明で確認を止めても計上を戻さないことを検査する。
- APIの単発観測であり、時計/session/account資格・AC切断監視・in-flightの停止/通信結果不明・checkpoint実保存は未実装。AC再接続だけで同じ試行の再確認を許可しない。実PCの切断試験やTier B/Cの受け入れではない。
- 両roleの非配布レビューへhelper1件追加（現行file集合47件）。CIとpackage fixtureを更新。Python 3.11.9（CI 3.12）で追加AC観測9件＋既存使用点10件の計19件成功（skipなし、実API読取1件を含む）。PS 7.6.7で両roleのpackage回帰・変更PS試験の構文/PSScriptAnalyzer Error検査成功。変更のない既存budget/reader/plan/probe試験は再実行しない。root自己点検のみで独立レビュー・新CI・実運用受け入れは未実施。root単独、ローカルコミットまでで次指示待ち、push/PRなし。
- 文書相対リンク欠落0・差分検査成功。次は比較更新providerの信頼境界と失敗時保存/回復条件の候補を整理する。未選択の前提を採用せず、正式runtime/taskや実保存の資格をhelper成功から作らない。

## 直前の実装単位（Win32負例probe・b65abde）

- 基準`5213525`、同じ`codex/work-branch-policy`で[比較更新providerの資格調査](../design/checkpoint-compare-provider-qualification.md)と実Win32負例probeを追加した。ReplaceFileW/CreateFileW/byte-range lock/flushの一次資料を2026-10-25に確認し、expected bytes比較・sharing・失敗時状態・耐久性をAPI名だけで資格にしない境界を整理した。
- tests専用probeはcaller指定先を受けず、自作OS-temp/固定fixture名のroot marker・regular/reparse/hardlinkを検査し、cleanup直前にもrootを確認する。実APIの共有guard下の拒否/解放後置換と、使用点検査＋実mutex後に非協調更新を古いcandidateが上書きできる反例を検証する。実運用pathやDrive/実設定を使わない。
- これは負例fixtureで、Commonにwriterを追加せず、実providerを採用/資格化しない。全writer協調の信頼境界、root/ACL/handle/scope binding、失敗状態/backup/metadata、真正で一回限りのcommit/readback、FS/電源断の資格は未完。一次資料のAPI条件と、この環境での隔離観測を区別する。
- 新規配布file/schema/PSコードはなく、46件の非配布file集合を維持する。CIにprobe試験を登録した。Python 3.11.9（CI 3.12）で実Win32の5件成功。自己点検で競合中間bytesの照合を強化し、影響する1件を再確認して成功。変更のない既存51件・package/PS検査は再実行しない。root自己点検のみで独立レビュー・新CI・Tier B/Cは未実施。root単独、ローカルコミット後は次指示待ちで、push/PRは行わない。
- 文書の相対リンク欠落0・差分検査成功。次はprobeで不足が明らかな保証に対するprovider設計を具体化する。writer信頼モデルや失敗時の保存/回復条件の採用を要する場合は候補を提示し、無条件置換を正式writerにしない。

## 直前の実装単位（使用点検査・5213525）

- 基準`a0e3393`、同じ`codex/work-branch-policy`で使用点検査を追加。実比較更新providerのroot/ACL/FS・owner/scope保証は未確定・未資格のため、無条件置換writerを実装せず、保存直前/記録後確認直前のpure検査を既存moduleと合成fixtureへ接続した。
- phase別のexact observed bytesを要求し、元の1試行candidateを再構成してplan偽装を拒否。最新scope・現在UTC/24時間期限・実行条件・明示boolのAC接続を再検査する。保存後に資格が失われても試行を戻さず確認を止める。全may_*はfalseで、同一検査の反復は一回限りreceiptではない。
- 使用点検査後の変更も模擬providerの比較で拒否する試験を追加し、再読込＋無条件置換だけでは代替できない境界を文書化した。比較更新/receipt/readbackの実資格、現在観測の真正性、計画から実確認までの時間の結び付け、AC切断時のin-flight処理は未実装・未確定として残す。
- Python 3.11.9（CI 3.12）で関連4module計51件を一括実行して成功。文書リンク欠落0・差分検査成功。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。新規配布file・PSコード・schema変更はなく、非配布レビューのfile集合は46件のまま。今回のpackage/PS検査は具体的な追加変更がないため再実行せず、前単位の結果と区別する。今回もローカルコミットまでで次指示待ち、push/PRは実施しない。
- 次は実FS比較更新providerの候補API/保証調査と隔離資格試験計画を具体化する。仕様追加を要する事項は提示し、helperやcaller boolから実保存/確認の資格を作らない。

## 直前の実装単位（試行planとmock保存接続・a0e3393）

- 基準`42e7c9f`、同じ`codex/work-branch-policy`でcheckpointの試行前計上を接続する。既存公開helperはcreate-onlyのみで、比較更新providerはないため、今回は純粋attempt planと隔離合成接続を実装した。
- planはexact元bytesをexpectedとし、既存reader/予算helperで観測を再検査して1試行を追加し、candidateの再読込・state一致を確認する。元の開始/履歴文字列を保持し、欠落初期化・予算リセット・実保存/確認は行わない。全may_* flagはfalse。
- 接続fixtureは実Windows mutex/ownerとcreate-only stagingを使うが、checkpoint compare-and-publish自体はメモリmock。完全な再読込確認前に模擬確認せず、stale plan/同一stagingの再利用から二重確認しない。保存後の応答喪失・確認失敗も試行を戻さない。実process crash/再起動・電源断・実FS比較更新の証明ではない。
- 純粋helper 1件を共通packageへ追加し、両roleの非配布レビューは46件。CIへ合成接続試験を登録し、関連検査を一括実行する。検証はPython 3.11.9（CI 3.12）で既存budget/reader＋追加plan/実mutex接続の計41件成功。PS 7.6.7でpackage回帰と変更PS試験の構文/PSScriptAnalyzer Error検査成功。クリーンsource snapshotで両role各46件・非配布を確認。文書リンク欠落0・差分確認成功。root自己点検のみで独立レビュー・新CI・実環境受け入れは未実施。
- 未完：実compare-and-publish/再読込provider、trusted root/ACL/FS・scope/実ownerのbinding、現在性/rollback防止、durable試行前計上とruntime/task/Drive確認。次は比較更新providerの資格・設計境界を具体化する。実root/filenameやC-02結果field等の未決を実装都合で確定しない。
- 今回も同branchへローカルコミット後に次指示待ち。main直接push禁止・PRは明示指示時の運用を維持する。

## 直前の実装単位（checkpoint schema/reader・42e7c9f）

- 今回の基準は`2195ba4`、branchは同じ`codex/work-branch-policy`。追加のPC-A確認予算checkpointは承認済み7fieldのclosed v1 schemaと純粋readerまで実装し、PR作成指示までこのbranchに蓄積する。main直接push禁止、ローカルコミット後の次指示待ちを維持する。
- readerはexact bytes・元時刻文字列・履歴順を保持し、期待log/period/run IDと信頼できる現在UTCを別入力で検証する。欠落/破損から空履歴を作らず、24時間/25回/1時間間隔・時計逆行を拒否する。期限切れ履歴は元予算のまま保持する。任意桁の小数を丸めず比較し、既存microsecond helperで完全に表せない場合は変換を拒否する。
- 新schemaをpackage必須fileへ、readerを共通helperへ追加。旧43件から両roleの非配布レビューは45件となる。CIへreader試験を登録し、関連検査を改修後に一括実行する。検証はPython 3.11.9（CI 3.12）で既存budget＋追加reader計28件成功。PS 7.6.7でpackage回帰と変更2scriptの構文/PSScriptAnalyzer Error検査成功。クリーンsource snapshotで両role各45件・非配布を確認。文書リンク欠落0・差分確認成功。root自己点検のみで独立レビュー・新CI・実環境検証は未実施。
- 保存root/filename/ACL/信頼できるread provider、開始時刻と履歴の真正性・現在性/rollback防止、C1/C2の原子更新と実確認前の永続計上、runtime/task/Drive接続は未実装。reader成功を実行/保存/archiveの許可にしない。次候補は試行前更新の隔離合成接続で、実rootやC-02具体field等の未決は推測しない。

## 直前の実装単位（manifest transition inspection・2195ba4）

- 利用者の「作業再開」により一時中断を解除した。基準`b4d4600`から同じ`codex/work-branch-policy`に実装を蓄積し、今回もローカルコミットまでで次の指示を待つ。main直接push禁止・PR作成の明示指示待ちを維持する。
- 今回は[manifest遷移snapshot検査](../design/manifest-transition-inspection.md)を追加。schema/JSON・identity/凍結inventory・verification/hash/time・終端不変性を検査し、採用13fileペアと4runペア以外を拒否する。掲載結果もrequires_runtime_evidenceで、実event・staging・Drive照合・OSD-03集約・mutex/永続化を認可しない。crash-left runningの実回復は行わない。
- CIに合成試験を登録し、レビューpackageへ純粋Python helper 1件を追加した。旧40件snapshotにC-01の2件と今回1件が加わり、非配布レビューは43件となる。PC-B archive/削除は追加しない。検証はPython 3.11.9（CI 3.12）でschema＋snapshot検査50件成功。PS 7.6.7でpackage回帰と変更PS試験の構文/PSScriptAnalyzer Error検査成功。Git対象のクリーンsnapshotで両role各43件・非配布を確認した。文書リンク欠落0・差分検査成功。root自己点検のみで独立レビュー・新CI・実環境検証は未実施。
- 残る範囲：実writerとevent履歴・所有権/現在性・原子的更新、B2等からの集約検証の実行接続、現在UTC/FS/root/使用点資格。C-02具体result/provider等の未決も維持する。次候補は確定済み確認予算checkpointのschema/純粋reader契約で、今回のコミット後には着手しない。

## 直前の規則追加（b4d4600）

- 2026-10-25の追加規則をAGENTS.md・現行手順・Git/PR skillへ反映：mainへの直接push禁止。マージ後は最新mainから新規作業ブランチを作り、次のPR作成指示までの変更・コミットを同じブランチに蓄積する。今回の`codex/work-branch-policy`はmain `fea8753`から新規作成し、mainをupstreamに設定していない。
- [PR #40](https://github.com/wasawo/eo-log-maintenance-public/pull/40)は`fea8753a84fe5ca7c9a64b7ec43a3b4686e546b0`でマージ済み。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40109038116) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40109038171) 成功を前作業で確認済み。今回は規則追加の文書変更のみをローカルコミットし、実装の一時中断と次の指示待ちを維持する。

## 前作業の反映記録（PR #40作成前の状態）

- 最新確認main：`51c5e221366fbc2d6e74e4c3190a134993adf904`。2026-10-25のPR作成依頼時、remote mainはすでに`985c90a`（retryable表）→`ff69e3b`（B2 V1/G1）→`51c5e22`（C-01字句）まで直接push済みだった。3コミットとmainの差分はなく、GitHubの関連PR照会でも対象PRは存在しなかった。この3件をPRでマージしたとは記録しない。
- このmainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40108634766) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40108634789) は成功済み。ローカルの各単位の検証と、この累積main CIを区別する。正式runtime/実Drive/FS耐久性の受け入れは未完。
- 利用者は実反映状態の説明を受け、「反映記録・中断状態の文書PRを作成してマージ」を明示選択した。今回の文書branchは`codex/record-main-integration-pause`で、この記録時点はPR作成前。文書PRの最新HEADで両CI成功を確認してからマージする。
- **一時中断指示**：利用量上限が近いため、今回の文書PRマージ後は作業を中断する。次候補には着手せず、新たな利用者の再開指示を待つ。通常運用は引き続き「関連範囲の実装→対象検査を一括→ローカルコミット→指示待ち」で、PR作成/マージは任意のタイミングの明示指示に従う。

## 直前の実装単位（C-01字句・51c5e22）

- 今回の基準：`ff69e3b`から同じ`codex/drive-retryable-contract`でC-01 P1/V1/L1の字句範囲を実装。現1.0 request schemaのlocal_path/staging_pathへ同一grammarを適用し、PS/Pythonに独立した副作用なしbool helperを追加した。
- 範囲：drive-rooted prefix、非空component、separator、禁止文字/control/DEL、末尾dot/ASCII space、予約stemと拡張子/末尾space/superscript/console alias。ASCII比較とUnicode原文字列保持、固定maxLengthなしを共通fixtureで検査する。root/token/FS、実file種別、使用点/差替え検知、transportと正式adapterは未実装。
- 互換性：現1.0を改訂し、従来schema-validな一部入力を拒否する。fallback/暗黙migrationは導入しない。外部consumer不在は未確認。新helper 2件は両roleのレビューpackageへ追加され、旧40件snapshotから42件となる。正式入口・PC-B archive禁止・非配布markerは維持する。
- 検証：Python 3.11.9（CI 3.12）で既存schema＋専用grammar 43件、PS 7.6.7で共通fixture等161件、副作用なし、package回帰成功。PS試験側の入力保持比較で空文字の扱いを修正し、PS範囲のみ再確認した。変更3スクリプトの構文/PSScriptAnalyzer Error検査成功。作業ツリー直下buildは既存__pycache__を拒否したため、cacheを変更せずGit対象のクリーンsnapshotを隔離作成して両role各42件・非配布状態を確認。最終文書リンク欠落0・差分検査成功。root自己点検のみで独立レビュー未実施。今回もローカルコミット後に待機し、push/PR/CI/実API/実環境適用は行わない。
- 次候補：採用済みmanifest遷移表の純粋検査と合成遷移試験。C-02具体field/provider等の未決は推測せず、正式writer接続とruntime受け入れは別に残す。

## 直前の実装単位（B2 V1/G1・ff69e3b）

- 追加運用（2026-10-25利用者指示）：実装単位を関連producer/consumer・契約・合成連携まで広げ、改修完了時に対象検査を一括実行する。小編集ごとの反復や成功済み検査の再実行を避ける。失敗・追加変更・具体的リスクがある範囲のみ再確認する。ローカルコミット後に次の指示を待ち、push/PR/マージは任意のタイミングの明示指示に従う。
- 基準：main `fd9cc8a`からの`codex/drive-retryable-contract`、直前コミット`985c90a`（retryable表）。今回も同branchで累積する。PR #39のマージとmain CI成功は前作業で確認済み、今回のCIは未実行。
- 今回の範囲：B2 V1の分類完了をエラー有無から分離し、source列挙/read/hashが不確実ならincompleteを維持。G1はexact manifest/B2終了UTCの遅い方を小数11桁まで比較し、同時はmanifestの元表記を保持。builderの任意caller時刻は照合値となり、不一致を拒否する。参照validatorも同じ導出を検査し、import/直接CLIを合成検証した。field/version/digest方式は維持し、過去incomplete recordと旧reportは書き換えない。
- 検証：Python 3.11.9（CIは3.12）で関連6moduleの107件を一括実行し、103件成功・4件はsandboxのjunction fixture作成拒否。失敗4件だけをsandbox外の専用合成一時領域・PS 7.6.7で再実行して成功。PS 7.6.7のreport validator 33件成功（PATH確認前の7.6.5実行は固定版検証に数えない）。最終文書リンク欠落0・`git diff --check`成功。root自己点検のみで、正式writer/公開・Drive・runtime/FS耐久性の受け入れは未完。
- 環境：公式archiveをCI記載SHA-256で確認してPowerShell 7.6.7をユーザー専用の恒久配置へ導入し、元User PATHを同配置のGit管理外backupへ保全して先頭に追加した。User PATH反映済みprocessで`pwsh`が7.6.7となることを確認。起動済みCodex processは旧PATHを保持し得るため、検証時は新User PATHをprocess PATHへ反映するか7.6.7の実体を明示し、起動版を確認する。sandbox内のLOCALAPPDATAはredirectされるので配置先の推測に使わない。個人の実path・PATH内容を追跡ファイルへ記載しない。
- 次候補：C-01 P1/V1/L1をrequest schema・PS/Python検査と合成連携へまとめて反映。C-02詳細field、owner-v2/provider等は未決として維持する。今回コミット後の継続指示まで着手しない。

## 直前の実装単位（retryable表・985c90a）

- 現行運用（2026-10-25利用者指示）：1作業単位は実装単位の選択→実装・検証・root自己点検→関連文書更新→ローカルコミット→次の指示待ち。PRは実装単位ごとに作らず、利用者が任意のタイミングで指示した範囲をまとめる。今回の直前指示「PR作成→マージまで1単位」と旧「1PR後に中断」はこの運用に置き換える。push/PR/マージは今回は実施しない。古い目標はサブエージェント再利用・残量までの自動継続も含めて再開しない。
- 最新確認main：`fd9cc8a931496d31601f062bf66448ea295eec65`（[PR #39](https://github.com/wasawo/eo-log-maintenance-public/pull/39)）。PRのValidate/Package Validation成功後にsquash merge済み。mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40105135888) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40105134099)成功も前作業で確認済み。今回のbranchはこのmainから作成した`codex/drive-retryable-contract`。
- 今回の実装単位：固定code別retryable表を現1.0 response schemaと`Common/DriveResponseSemantics.ps1`へ反映。`DRIVE_TRANSIENT_FAILURE`のみtrue、他8codeはfalseを必須とし、矛盾は固定理由`retryable_error_code_mismatch`で拒否する。旧schema-validな矛盾boolが不適合になる互換性の厳格化を契約へ記録。外部consumer不在は未確認。
- 検証：Python 3.11.9（CIは3.12）の`test_contract_schemas.py`39件、PowerShell 7.6.7の`Test-DriveResponseSemantics.ps1`171件成功。PATH上のPS 7.6.5による初回実行後、CIと同じ公式archive/hashで7.6.7を一時領域へ用意して再確認した。4操作×9codeの正常/矛盾、型/欠落、exit対応、入力不変・秘密非echo・操作副作用なしを確認。PS 7.6.7で変更2ファイルの構文解析・PSScriptAnalyzer Error検査も成功。変更文書の相対リンク欠落0、`git diff --check`成功。今回のroot自己点検であり独立レビューではない。CI・実API・正式retry orchestration・runtime受け入れは未実施。配布file集合は変更せず、package回帰は再実行していない。この記録を含むローカルコミットで区切り、次の指示を待つ。
- 次の候補：C-01 P1/V1/L1のschema/PS/Python検査、またはB2 V1/G1のproducer/builder追従。継続指示後に1単位を選ぶ。C-02の4操作別fieldとowner-v2/provider等は未決のままで、推測して実装しない。

## 前作業までの記録（当時の状態）

以下はPR #39へまとめた過程の履歴であり、現行運用と進捗は上の最新欄を優先する。

- 今回の文書整備：`docs/selected-policy-decisions` からmain `179787f`を基準に、[未決定台帳](../requirements/p0-open-specification-decisions.md)、[P0差分台帳](../requirements/p0-gap-register.md)、[要件追跡](../requirements/requirements-traceability.md)、[決定台帳](../decisions/decision-register-c18-c32.md)と[初回配布の依存順序](../status/first-release-readiness-20261024.md)を①〜㉜・限定4件へ整合。過去の段階的承認文と部分検証の履歴は、その当時の記録として残す。新PRの最新HEADでValidate/Package Validationを確認してから、今回の明示依頼の範囲で1PRをマージして作業を中断する。正式runtime/実auth/Drive/task/配布は未実装・未適用。
- 今回のroot単独検証：mainとの差分35ファイル内のMarkdown相対リンク297件は欠落0、`git diff --check`成功。文書/作業指示/project設定だけの変更で、機能・package試験と実環境検証は再実行していない。今回差分の独立レビューは実施していない。PRとCIの結果は作成後のGitHub実状態で確認する。
- 第10回指示で[現行実装に基づく4件の限定決定](../decisions/implementation-grounded-four-decisions-20261024.md)を記録した。固定code別retryable真偽表、PC-A確認予算checkpointの最小field/拒否境界、VERSION 0.1.0の現行非配布レビューpackage 40ファイル、owner record v1の既存互換境界である。31aAの正式PC別/version別manifest形式は維持するが、最終実file一覧は正式runtime完成後。owner-v2全field/providerも未確定。PS helperと試験はretryable真偽表へ未追従、checkpoint writer/schema、正式package manifestも未実装。追加9文書のroot自己点検でfile一覧40件、retryable表9行と現codeの対応、相対リンク132件欠落0、差分検査成功。文書のみのため機能/package試験・新CI・独立レビューは未実施。PR/マージや実接続は行っていない。
- 第9回回答：㉙A、㉚aA/bA/cA、㉛aA/bA、㉜aA/bAを採用し、[決定記録](../decisions/selected-policy-decisions-20261024.md)と[比較資料](../decisions/remaining-policy-options-20261024.md)を更新。manifest正本＋補助checkpoint、Google公式Python client、multipart/5 MB以下・超過保留、固定code別retryable表、strict JSON＋Schemaのpackage manifest、専用PS移行、Windows App SDK通知、初回/状態変化時のみ再通知の方向が確定。具体field、SDK版/flow、正確なbyte境界、保護API/ACL、owner provider、CI配布identity、通知登録/重複抑制等は残る。①〜㉜の提示済み選択は回答済みで、詳細契約/実装/受け入れの完了ではない。
- 第8回回答：㉒A（PC-A同期に続けてarchive可否判定）/㉓A（両PC AC接続時のみ）/㉔A（wakeなし）/㉕A（4操作全体のresult契約を提示して確定）/㉖A（user-bound保護API＋専用暗号化file）/㉗A（owner field契約/providerを段階確定）/㉘A（E1承認後ActionsからDrive公開）を決定記録へ追記。具体API・field・配布identity等は未確定。文書のみのローカル差分で、実装/実task/認証/Drive/PR/マージは行っていない。直前記録コミットは8169eb7。
- 第9回反映後の追加5文書のroot自己点検：相対リンク30件の欠落0、git diff --check成功。コード/schema/runtime変更がないため機能/package検査は再実行せず、独立レビュー・新CIは未実施。追加分は未コミット。
- 最新mainは `179787f62ad0e07d58e139d7059ea84de149ed05`（[PR #38](https://github.com/wasawo/eo-log-maintenance-public/pull/38) マージ済み）。PRの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40084689827) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40084689833)、mainの [Validate](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40085003755) / [Package Validation](https://github.com/wasawo/eo-log-maintenance-public/actions/runs/40085003841) 成功後の停止記録は `54f1418`。runtime実装の継続ではなく、利用者の未決事項選択・記録と指示文書改訂だけをbranch `docs/selected-policy-decisions` で進めている。未push・新規PRなし。
- [仕様決定記録](../decisions/selected-policy-decisions-20261024.md)へ①〜㉑の回答を反映。C-01 P1/検査V1/L1全体/現1.0改訂、B2 V1、report G1、C-02 R1/N1/D1、Drive I1/A1/S1/T1、owner F1/B1、条件付き状態遷移表採用、release E1、全version保持・自動cleanupなし、PC別version別file manifest、明示的設定移行、ローカル画面通知＋状態ログの方向が確定した。質問と回答の範囲を越えてfield集合・provider・実施を確定しない。
- **2026-10-24の最新利用者指示によりサブエージェント利用を中止。root単独運用。** 新規作成・既存再利用・組込み/カスタム担当・別AIタスクへの委譲を行わない。中止時の確認では稼働中担当はなく、既存担当は完了または終了状態だった。旧目標の「既存3担当のみ再利用」は撤回済みで、過去記録・環境の担当一覧から再開しない。
- AGENTS.md、[現行手順](../development/agent-workflow.md)、両skill・索引をroot単独へ更新し、project .codex/config.tomlをagents.enabled=falseとした。旧3役割TOMLと旧分担手順は [失効した履歴](../development/archive/README.md) に保全。役割TOMLは移動前後hash一致、Git改行正規化後の本文一致とparseを確認。旧手順は失効banner/相対リンク以外の本文一致を確認。個人/global設定・主モデル/思考量は変更していない。project設定の信頼/読込と現会話への即時tool反映は未検証で、以後の不使用は利用者指示と現行手順で徹底する。
- 利用中止前の初期7文書は独立reviewでP1/P2なし、invariants節分断P3を修正。追加⑦〜⑫のreviewでは旧承認待ち表記P2を指摘されrootで修正した。これらは当時の差分だけの履歴であり、⑬以降や利用中止対応を含む最新全差分はrootが単独点検し、独立レビューは実施していない。独立レビュー済みと表記しない。
- 今回のroot単独点検: 変更20 Markdownの相対リンク189件欠落0、差分検査成功。project/旧役割のTOML計4ファイルをparseし、agents.enabled=false、主思考量不変、active役割ファイルなしとarchived本文保全を確認した。文書・指示・Codex設定のみで無関係な機能/package検査は再実行していない。新CI未実行。
- 未確定/未完：C-02の具体field集合・型・値域・plan形、具体store/SDK/flow/ACL、owner-v2全fieldと適格machine/boot provider、checkpointの保存root/FS資格、移行mapping、正式runtimeの最終実file一覧とmanifest形式、task trigger/電源等の具体運用。G1/B2 V1等へのコード/schema追従、実保存・認証・実API・両PCroot/FS・runtime/Drive/耐久性の受け入れも未実施。今回の設定変更はCodex作業設定に限り、アプリケーションコード/runtime schema/tests/実設定は変更していない。
- 仕様選択と実装/公開/PRマージ/本番適用の許可を分離し、PR/マージは個別承認、1PRマージ後の中断・継続可否確認を維持する。新たな実装や実接続を独断開始しない。旧C-01資料branch `9343f71` は選択前の履歴として保全し、現選択はこのbranchの決定記録を優先する。

## 旧進捗の参照

PR #27〜33前後の旧進捗節は [セッション記録](archive/pr27-pr33-session-history-20261024.md) に保存した。過去の承認待ち・CI待ち・agent生成禁止を現在の指示として実行しない。

## 次回の実装再開時

1. まず利用者の継続指示を確認し、正本mainとローカル保全branchのコミット・作業ツリーを照合する。C-01のP1/検査V1/L1/現1.0改訂の選択は済んでいるので再質問しない。実装実施の承認と残る具体契約は別途確認する。Aは承認済みで再質問しない。IPC全体、C-02具体field、OSD-05の具体store/API/資格等の残る未確定を区別する。
2. [更新後の初回配布順序](../status/first-release-readiness-20261024.md)に従い、採用済みのC-01/manifest遷移/Dry Run A/B2 V1/G1をschema・builder・合成fixtureへ反映する。retryable表はschema/PS helperへ追従済みで、RETRY-02統合は未実装。C-02の操作別fieldとowner-v2 provider等の詳細未決を分離し、ローカルroot・永続run状態・復旧の不足を整理する。確認予算の永続化だけで初回配布へ進めない。
3. Drive adapter/認証資格、両PCのTier B、正式手動runtime統合、E2E/Tier C、正式配布/導入と進む。taskは初回手動受け入れ後。実環境検証・実適用は別途の承認範囲を確認する。
4. 旧lock自動処分・新run自動生成・実保存・task登録・Drive/本番復旧を、helper/CI成功から許可されたと解釈しない。

承認済み: 明示回復、v1保全/v2対象、private maintenanceLocal保管/自動削除なし、同一account、ログオン中のみ、毎月1日PC-B20:00/PC-A21:00 JST、PC-A確認24時間/25回。これらを同じ内容で再質問しない。

## 設定基盤の完了範囲

- PR #8: maintenanceLocal必須化、公開exampleと字句的重複拒否。
- PR #9: strict UTF-8/JSON構造・役割・型・unknown/duplicateキー・パス構文検証。285アサーション成功。
- PR #10: create-only補助処理。既存設定をbytes単位で保持、安全exampleだけ新規生成。22アサーションと配布テスト成功。
- PR #10最新HEAD e5df9a197a4644a29a0ae7d9bd38d0a2d9e06a65 のValidate 39830715865（attempt 2）/Package 39830715899成功後マージ。初回はPSGallery登録で失敗、検査は弱めていない。
- 実設定・実導入先では実行していない。既存rootのmetadata補助検査は上記の追加範囲。approved-root権限/FS資格/利用直前までの保護、正式導入/実行入口接続・移行は未完了。設定値は認可ではない。

## 過去の検証・マージ記録

PR #3〜6のマージ表と旧項目別メモは [検証履歴](archive/validation-history-20261023.md) へ移動。利用者の既存表整形も保全済み。現在の作業順は上記の棚卸しを参照する。

## 利用者への確認中・既に確認したこと

- 現在の端末はPC-B。管理成果物とは、そのPCが生成するマニフェスト・一覧/検証証拠・集計レポート・marker/lock等。PC-Aの原本はPC-A側に置き、両PC向けの検証済みコピーをDriveへ公開する方針。
- PC-B予定固定ディスク上に新規合成領域を作る検証を実施した。実パスや実ボリューム文字は公開しない。実設定はGit管理外のConfig/PC-B.jsonへ将来入力する。
- 承認済み（2026-10-23）: 両PC設定へ `maintenanceLocal`（そのPCのマニフェスト・検証証拠・レポートのローカル原本領域）を追加する。exampleはダミー、実値は非追跡設定、実行先/元ログ/Drive/archiveとの重複を拒否。実パスは推測しない。
- OSD-04はA承認済みで実装・受け入れが未完。OSD-08の日時・account・AC/no-wake・確認予算は決定済みで、永続状態/task/補完/受け入れは未完。OSD-05の認証方向、OSD-06/07のrelease起動/全版保持、OSD-09の形式/移行入口、OSD-02遷移とC-01/02の方針は選択済み。具体store/実folder資格、CI identity/provenance、最終file一覧/移行mapping、C-02詳細field、永続writer/正式runtime受け入れは残る。
- 台帳の古い「sentinelあり」「過去PRのCI待ち」などは現物と照合して関係PRで直す。台帳全体の再監査完了とはしない。
