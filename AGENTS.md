# Codex 作業規則 — ElectronicObserver Log Maintenance

このファイルはこのリポジトリ全体に適用する恒久的なプロジェクト規則です。
進捗、作業ブランチ、PR番号、CI結果、次の作業は [docs/handoff/next-chat.md](docs/handoff/next-chat.md) に記録します。

## 作業開始時

1. このファイルを読み、次に `docs/handoff/next-chat.md` を確認する。
2. `git status --short --branch`、`git branch -vv`、`git remote -v` で実際の作業先と変更を確認する。
3. 対象に関係する README・仕様・既存テスト・CI定義を読み、必要なら GitHub の最新 main・対象PRの状態と照合する。
4. 未コミット変更を破棄しない。競合する場合は内容を保全し、必要に応じて別ブランチ・作業ツリーを使う。依頼外の修正を混ぜない。
5. 引き継ぎの記載よりも、実ファイル・Git・GitHub の確認結果を優先する。古い「次の作業」を自動実行しない。

## 正本・仕様・構成

- 正本は GitHub の `wasawo/eo-log-maintenance-public`。旧 Private リポジトリは過去の証跡であり、変更・履歴を無断で取り込まない。
- `README.md` は目的と運用概要、`docs/decision-register-c18-c32.md` と個別承認記録は決定事項、`docs/requirements-traceability.md`・`docs/p0-gap-register.md` は要件と残課題の入口。
- `docs/implementation-workflow.md`、`docs/powershell-python-contract.md`、対象スキーマ・個別仕様を変更前に確認する。未決定事項を実装都合で確定しない。矛盾は明示して解決する。
- `Common/` は共通ヘルパー、`Config/*.example.json` は公開用設定例、`contracts/` はJSON Schema、`scripts/` は運用入口の配置先、`tests/` は合成テスト。
- `.github/scripts/Build-ReleasePackage.ps1` とワークフローは配布・検証用。ヘルパーやテンプレートの存在を正式ランタイムの完成と扱わない。
- このファイルは作業方法を定める。ドメイン仕様の変更や安全条件の緩和を、このファイルの編集だけで承認した扱いにしない。

## 維持する安全条件

- PC-B は同期・検証・マニフェスト作成のみ。アーカイブ・削除機能やアーカイブ入口を提供しない。
- PC-A のアーカイブは明示的な許可、両PCの対象期間・ログ種別に合うマニフェスト、鮮度・内容・ハッシュ・クラウド検証を満たした場合のみ。欠落・破損・不一致・不明な状態は保留する。
- アーカイブはコピー・検証・結果記録。初期実装にはローカル元ログ・Driveログの削除コード、操作、設定を含めない。
- Drive for desktop のローカル可視性をクラウド反映完了の証拠としない。同名競合を上書きせず、出所を推測しない。
- 期間判定は承認済みのファイル名日付と保持条件に従う。LastWriteTime を代用しない。
- 初期インベントリ・復元記録を通常マニフェストと分離する。未照合・競合・出所不明は保留し、自動復元しない。
- 実ログ・実端末・Driveを使う検証を通常テストとして実行しない。合成データ、一時領域、模擬API、固定日時を使う。
- 単体・スキーマ・配布・CIの成功を、ランタイム受け入れ・本番安全性・クラウド同期・電源断耐久性の証明としない。未実施・未確認を完了扱いしない。
- example 設定のPC別フィールド・安全な既定値・絶対Windowsパス形式・領域分離を維持する。
- 導入時は対象PCの実設定を未作成時だけ example から生成し、手動設定は実パス入力だけにする設計。更新時は既存実設定を保持する。実装済みかはソースで確認する。

## 公開情報・Git操作

- 実運用パス、実DriveフォルダURL/ID、個人メール、実設定、ログ、実行時マニフェスト、トークン、秘密鍵を追跡ファイル・PR・ログへ追加しない。例は明確なダミーとする。
- 実設定 `Config/PC-A.json` / `Config/PC-B.json` は Git 管理・配布対象外。配布の許可リスト、役割別入口、非配布マーカーの制御を維持する。
- コミット前に差分とステージ内容を確認し、作成者メールに個人アドレスを使わない。既存の GitHub noreply 設定を確認する。
- Public/Private変更、履歴書き換え、force push、ブランチ削除、本番適用は明示承認の範囲内でのみ行う。過去の承認を別リポジトリ・別操作へ拡張しない。
- 作業依頼の範囲に応じてブランチ・PRを使う。PR作成やCI確認の依頼をマージ許可と解釈しない。

## 変更と検証

- 関連する仕様・コード・テスト・引き継ぎ変更は同じPRにまとめる。小さい単位に絞り、要件ID/P0項目と影響を説明する。
- PowerShell はリポジトリで固定する 7.6.7 を使用。Python はCI定義の版を基準とし、ローカルとの差・スキップを記録する。版の変更は別途根拠と検証を伴わせる。
- 検証コマンドの正本は `.github/workflows/validate.yml` と `package-validation.yml`。環境が整っていれば次を使う。

```powershell
python -m unittest discover -s tests -p "test_*.py"
pwsh -NoProfile -File tests/Test-ReleasePackage.ps1
# 必要なPowerShellヘルパー検証は tests/Test-*.ps1 の対象スクリプトを実行
git diff --check
```

- Python依存は `requirements-test.txt` / `requirements-runtime.txt`、PowerShell構文解析・PSScriptAnalyzer はCI定義を参照する。
- 文書だけの変更ではリンク・記述整合・差分検査を行う。関連しない全テストの実行や新規テスト追加を義務化しない。
- CI利用可能時は最新PR HEADに対する Validate と Package Validation を確認する。コミット後は古いSHAの成功を流用しない。
- CI待ちは初回確認後、90秒間隔で最大5回再確認。未完なら状態・URLを報告し、マージしない。
- CI不可時は対象に必要なローカル検証を実施し、実施範囲・環境差・未実行CI・理由を明記する。代替をCI成功と記載せず、マージ条件を勝手に緩和しない。
- マージが別途承認された場合も最新HEADの必要検査を確認し、マージ後の実SHAとmainのCIを確認する。利用者が承認した特定PRのCI代替は他PRへ自動適用しない。

## 引き継ぎ文書の運用

- 各作業単位で `docs/handoff/next-chat.md` を更新する。最新の状態を上部にまとめ、古い指示を累積して現行指示にしない。
- 記録項目：更新日、確認した基準SHA、作業ブランチ/PR、変更内容、検証結果とURL、未完了・決定待ち、次の具体的な作業、未実証の範囲。
- 未コミット・未push・未マージ・未実行を正確に区別し、将来の結果を先に成功と書かない。
- 恒久ルールはここへ、変動する状態は引き継ぎへ置く。長い過去記録は `docs/handoff/archive/` に保存し、必要な証跡だけ参照する。アーカイブ内の旧指示を現行ルールとして実行しない。
