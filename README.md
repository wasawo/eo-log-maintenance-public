# ElectronicObserver Log Maintenance

管理原本: [wasawo/eo-log-maintenance-public](https://github.com/wasawo/eo-log-maintenance-public)。旧リポジトリの PR・CI リンクは過去の証跡として残しており、閲覧権限が必要な場合があります。

ElectronicObserver の BattleLog / ErrorReport を、Windows PC-A と PC-B 間で安全に同期・検証・アーカイブするための PowerShell 管理プロジェクトです。

> **現在の段階:** リポジトリ初期化。既存スクリプトの移行と本番実行は未完了です。P0受け入れは未完了で、正式な同期／アーカイブ入口とランタイム検証も未実装です。初期実装にはローカル元ファイル削除・Drive削除の機能自体を含めません。P0の判定基準は [`docs/implementation-workflow.md`](docs/implementation-workflow.md) §4 と [`docs/p0-gap-register.md`](docs/p0-gap-register.md) を参照してください。

## 目的

- PC-A / PC-B のログを Google Drive for desktop 配下へ同期する
- コピー先ファイルを SHA-256 等で検証する
- 実行結果をマニフェストに記録し、PCごとの処理完了を判別する
- PC-A のみが、両PCの完了記録と検証結果を確認した後にアーカイブ（コピー・検証・結果記録）する。初期実装では削除しない
- README、変更履歴、バージョンと検証を GitHub で管理する

## PCごとの役割と実行パス

maintenanceLocal は各PC自身のマニフェスト・検証証拠・レポートのローカル原本領域です。両PCの example に必須項目として追加し、実行先・元ログ・Drive・アーカイブとの重複を拒否します。[設定仕様](docs/configuration-local-root.md)を参照してください。読み取り専用の構造検証ローダーは追加済みです。初回だけ生成して既存設定を保持する補助処理も追加済みです。既存ディレクトリのメタデータを読む分離検査も補助処理として追加済みです。物理領域の承認・利用直前までの保護・正式導入入口への接続は未完了です。

以下と `Config/*.example.json` のパスは公開用のダミー値です。実運用値は Git 管理外の `Config/PC-A.json` / `Config/PC-B.json` に保存します。

導入処理の要件は、対象PCの example 設定から実設定を未作成時のみ生成し、利用者の手動設定を実パスの入力だけにすることです。コピー・リネームは導入処理側で行い、更新時は既存の実設定を保持します。PC別の役割と安全な既定値はテンプレートで定義します。初回生成用の補助処理は実装済みですが、正式な導入処理・入口への設定ローダー接続は未実装です。

| 項目 | PC-A | PC-B |
| --- | --- | --- |
| ローカル実行ディレクトリ | `C:\Example\PCA\Runtime\` | `C:\Example\PCB\Runtime\` |
| BattleLog 元フォルダ | `C:\Example\PCA\Source\BattleLog` | `C:\Example\PCB\Source\BattleLog` |
| ErrorReport 元フォルダ | `C:\Example\PCA\Source\ErrorReport` | `C:\Example\PCB\Source\ErrorReport` |
| 同期先 | Google Drive の共有同期フォルダ | 同左 |
| アーカイブ | 明示設定と安全条件を満たした場合のみ | **禁止** |
| ローカル元ファイル削除・Drive削除 | **初期実装では機能自体を実装しない** | **機能自体を実装しない** |

Google Drive 同期先:

- BattleLog: `G:\ExampleDrive\SharedLogs\BattleLog`
- ErrorReport: `G:\ExampleDrive\SharedLogs\ErrorReport`
- マニフェスト等: `G:\ExampleDrive\SharedLogs\_maintenance\`

PC-A のアーカイブ先:

- BattleLog: `C:\Example\PCA\Archive\BattleLog`
- ErrorReport: `C:\Example\PCA\Archive\ErrorReport`

## 安全上の必須ルール

1. PC-B は同期・検証・マニフェスト作成のみを担当し、アーカイブや削除を行わない。
2. PC-A は対象期間の PC-A / PC-B 両方のマニフェストとファイル検証を確認した場合に限りアーカイブする。初期実装ではDrive上の元ファイルを削除しない。
3. マニフェストがない、古い、破損している、対象期間・ログ種別が一致しない、ハッシュ不一致、またはクラウド反映を確認できない場合はアーカイブを保留する。
4. Drive for desktop のローカルファイルが存在することだけで、クラウドへのアップロード完了とは判定しない。
5. 初期実装にはローカル元ファイル削除・Drive削除のコード、操作、設定を含めない。Dry Run は削除機能の代替実装ではない。
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
