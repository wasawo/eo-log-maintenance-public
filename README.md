# ElectronicObserver Log Maintenance

管理原本: [wasawo/eo-log-maintenance-public](https://github.com/wasawo/eo-log-maintenance-public)。旧リポジトリの PR・CI リンクは過去の証跡として残しており、閲覧権限が必要な場合があります。

ElectronicObserver の BattleLog / ErrorReport を、Windows PC-A と PC-B 間で安全に同期・検証・アーカイブするための PowerShell 管理プロジェクトです。

ファイルの配置と分野別文書は [リポジトリ構成・文書索引](docs/README.md) を参照してください。

> **2026-10-27 要件再確認中:** 初回完成は、手動で両移動経路を元削除まで通すことです。削除条件は「保存先の内容一致」と「削除直前の元ログがコピー時から変わっていないこと」の両方。確認不能なら元を残します。合意は[再確認台帳](docs/development/requirements-design-task-review-20261027.md)、完成判定と作業順案は[初回移動計画](docs/development/initial-move-delivery-plan-20261027.md)を参照してください。詳細契約の確定とコード実装の再開は未完です。

> **現在の段階:** 既存実装は安全基盤・検証補助処理が中心で、現在は文書を見直しています。正式な同期／アーカイブ入口と削除経路は未完成、P0受け入れも未完了です。元削除を含む要件への更新は実装済み・本番適用可能を意味しません。判定基準は[実装計画](docs/development/implementation-workflow.md) §4と[P0台帳](docs/requirements/p0-gap-register.md)を参照してください。

2026-10-24時点の[実装棚卸しと初回配布までの作業順序](docs/status/first-release-readiness-20261024.md)、[選択済みの仕様と残る詳細](docs/decisions/selected-policy-decisions-20261024.md)を参照してください。レビュー用ZIPを生成できることと、本番導入できることは別です。

Codexでの開発は [AGENTS.md](AGENTS.md) から開始します。[root単独運用](docs/development/agent-workflow.md) と [詳細仕様への参照表](docs/development/development-guide.md) を必要時に確認してください。進捗は [引き継ぎ](docs/handoff/next-chat.md) に記録します。

## 目的

- PC-A / PC-B の対象ログを共通クラウドへ集約し、保存先確認と元不変確認ができたファイルの元を削除する
- コピー先ファイルを SHA-256 等で検証する
- 実行結果をマニフェストに記録し、PCごとの処理完了を判別する
- PC-A のみが、クラウドにある古い対象をarchiveへ移し、同じ2条件を確認してクラウド元を削除する。両PCの期間完了を待たず、遅着分は次回扱う
- 両保存先はログ種別ごとの共通フォルダ直下へ集約し、元サブフォルダを再現しない。同名同内容は再利用、異内容は元を残して競合表示する
- README、変更履歴、バージョンと検証を GitHub で管理する

## PCごとの役割と実行パス

maintenanceLocal は各PC自身のマニフェスト・検証証拠・レポートのローカル原本領域です。両PCの example に必須項目として追加し、実行先・元ログ・Drive・アーカイブとの重複を拒否します。[設定仕様](docs/design/configuration-local-root.md)を参照してください。読み取り専用の構造検証ローダーは追加済みです。初回だけ生成して既存設定を保持する補助処理も追加済みです。既存ディレクトリのメタデータを読む分離検査も補助処理として追加済みです。物理領域の承認・利用直前までの保護・正式導入入口への接続は未完了です。

以下と `Config/*.example.json` のパスは公開用のダミー値です。実運用値は Git 管理外の `Config/PC-A.json` / `Config/PC-B.json` に保存します。

導入処理の要件は、対象PCの example 設定から実設定を未作成時のみ生成し、利用者の手動設定を実パスの入力だけにすることです。コピー・リネームは導入処理側で行い、更新時は既存の実設定を保持します。PC別の役割と安全な既定値はテンプレートで定義します。初回生成用の補助処理は実装済みですが、正式な導入処理・入口への設定ローダー接続は未実装です。

| 項目 | PC-A | PC-B |
| --- | --- | --- |
| ローカル実行ディレクトリ | `C:\Example\PCA\Runtime\` | `C:\Example\PCB\Runtime\` |
| BattleLog 元フォルダ | `C:\Example\PCA\Source\BattleLog` | `C:\Example\PCB\Source\BattleLog` |
| ErrorReport 元フォルダ | `C:\Example\PCA\Source\ErrorReport` | `C:\Example\PCB\Source\ErrorReport` |
| 同期先 | Google Drive の共有同期フォルダ | 同左 |
| アーカイブ | 明示設定と安全条件を満たした場合のみ | **禁止** |
| 初回完成で必要な元削除（未実装） | 自端末→クラウドの元、クラウド→archiveの元。各2条件を確認した対象のみ | 自端末→クラウドの元のみ。archive・クラウド元削除は禁止 |

Google Drive 同期先:

- BattleLog: `G:\ExampleDrive\SharedLogs\BattleLog`
- ErrorReport: `G:\ExampleDrive\SharedLogs\ErrorReport`
- マニフェスト等: `G:\ExampleDrive\SharedLogs\_maintenance\`

PC-A のアーカイブ先:

- BattleLog: `C:\Example\PCA\Archive\BattleLog`
- ErrorReport: `C:\Example\PCA\Archive\ErrorReport`

## 安全上の必須ルール

1. PC-B は自端末→クラウドの移動と個別結果を担当し、archive・クラウド元削除は行わない。
2. PC-A はクラウドの現在対象をファイル単位で確認してarchiveする。PC-B未実行や期間全体の失敗だけで、確認済みの別ファイルを一律に待機させない。
3. 保存先内容と元不変を確認できない対象は元を残す。必要な対象記録の破損/不一致、内容不一致、クラウド状態不明は依存する処理を保留する。古い成功記録を現在確認の代用にしない。
4. Drive for desktop のローカルファイルが存在することだけで、クラウドへのアップロード完了とは判定しない。
5. 削除は合意した2経路・2条件の対象のみ。Dry Runでは元/保存先を変更しない。文書見直し中は削除コード/schemaを追加せず、実装再開・実データ操作はAGENTSの条件に従う。
6. スクリプトは Google Drive 上の管理原本から直接実行せず、各PCのローカル実行ディレクトリへ取得した版を使用する。
7. 実ログ、実行時マニフェスト、PC固有の実設定や秘密情報を Git に登録しない。

## リポジトリ構成

```text
.
├── README.md
├── CHANGELOG.md
├── VERSION
├── Config/
│   ├── PC-A.example.json
│   └── PC-B.example.json
├── Common/
├── scripts/
├── tests/
└── .github/
    ├── workflows/
    └── PULL_REQUEST_TEMPLATE.md
```

## 開発・変更手順

1. Issue または変更理由を明確にする。
2. ブランチ上で変更する。
3. Pull Request に目的、影響範囲、テスト結果、削除処理への影響を記録する。
4. GitHub Actions の検査を通し、差分を確認する。
5. レビュー後に main へ反映する。
6. リリース時に `VERSION` と `CHANGELOG.md` を更新する。
7. PCへはリリース内容を確認してから手動で適用する。

## 初期インベントリと復元

初期インベントリ・復元記録は通常運用マニフェストから分離します。PC-AバックアップとDrive上のファイルを名前・サイズ・SHA-256で照合し、Dry Runレビュー後に一致が確認できたものだけ復元します。不一致・競合・出所不明のファイルは保留し、自動復元・アーカイブ・削除しません。インベントリ完了は通常同期成功やアーカイブ許可の証明ではありません。

## 配布パッケージ

- 配布パッケージは `.github/scripts/Build-ReleasePackage.ps1` で生成する。
- `tests/Test-ReleasePackage.ps1` で許可リスト、除外対象、SHA-256、実設定ファイルの混入防止を検証する。
- `workflow_dispatch` で生成できるレビュー用パッケージは、実行スクリプト未実装の場合に非配布用マーカーを含む。PC-A / PC-B には適用しない。
- 実行用スクリプトが `scripts/` に移行され、テストが整うまでは本番リリースを作成しない。
- Google DriveへのアップロードとPCへの自動適用は未実装。

## バージョンと変更履歴

- `VERSION`: 現在の管理対象バージョン
- `CHANGELOG.md`: 利用者に影響する変更の記録
- Git commit / Pull Request: 詳細な変更理由と差分の記録

README 全体を自動上書きするのではなく、安定した説明は手書きで管理し、将来的にバージョン等の定型情報だけを自動生成します。

## 保持期間の要約（2026年10月時点）

- BattleLog：同期対象は2026年9月以前、アーカイブ対象は2025年12月以前。
- ErrorReport：同期対象は2025年以前、アーカイブ対象は2024年以前。
- 対象期間はファイル名の日付で判定し、LastWriteTime を代替にしません。

## 現在の制約

- 同期、クラウド検証、マニフェスト、アーカイブのランタイム実装と安全性テストは未完了です。
- GitHub Actions の成功は、本番PCでの動作保証や Google Drive のクラウド同期完了を意味しません。
- PCへの自動適用は行いません。更新の取得・差分確認後に手動適用する方針です。
