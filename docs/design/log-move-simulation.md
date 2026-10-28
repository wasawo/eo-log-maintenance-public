# 両経路の移動フローを確認する模擬実装

更新日: 2026-10-28。根拠は[要件定義書](../requirements/log-move-requirements.md)、[設計書](log-move-design.md)、[実装計画](../development/implementation-workflow.md)のT0/T1。

## 目的と実行方法

利用者の実装再開指示に基づき、両経路の対象選択から移動完了までをメモリ上で一連に動かす。資源制限の補助処理を単独追加するのではなく、設定・期間・平坦化・同名比較・Q5・個別削除結果・再実行を接続して、実adapterへ必要な境界を具体化する。

```powershell
pwsh -NoProfile -File tests/Test-LogMoveSimulation.ps1
```

実装は[LogMoveSimulation.ps1](../../Common/LogMoveSimulation.ps1)、従来のメモリ上の検証は[Test-LogMoveSimulation.ps1](../../tests/Test-LogMoveSimulation.ps1)。PowerShell 7.6.7で動かす。設定内のパスへアクセスせず、Drive接続、ログ本文のディスク読取、実ファイルのコピー・削除、ロック取得は行わない。JournalRootを省略した場合はメモリ上だけを変更する。指定時は[記録接続](simulation-journal-integration.md)に従って、用意済みの専用rootへ移動記録v1を保存する。

正式な`SyncLogs.ps1`と`ArchiveLogs.ps1`は追加しない。実装基盤と運用入口を取り違えず、既存ビルダーの正式入口不在による配布拒否も維持する。

[所有ロック付きwrapper](owned-simulation-run.md)では、このモデル呼出しを実OS mutexと開始/終了記録で囲む。直接のモデル呼出し自体は従来どおりロックを取得しない。実providerの所有資格を与えるものではない。

## 今回の模擬契約

`Invoke-EoLogMoveSimulation`は設定JSON、実行PC、Sync/Archive、固定基準日、モデル状態、任意の故障指定、Dry Run指定を受け取る。既存の厳密な設定読取とファイル名・期間判定を再利用する。PC-BのArchiveと、PC-AのallowArchive無効は状態を読む前に拒否する。設定値だけで本番操作を認可するものではない。

モデル状態は`Files`と`Events`のリストで構成する。各ファイルの`Id`はモデル内の一意な実体、`Location`はPC-A/PC-B/Cloud/Archive、`LogType`はログ種別、`RelativePath`は論理相対パス、`Bytes`は合成内容である。これは列挙済みの完全なモデルであり、実環境の列挙成功を推測する仕組みではない。元のサブフォルダは相対パスで識別し、保存先にはbasenameだけを使う。

元のbytesを複製したステージングを比較基準とし、同名の保存先が一意か確認する。同内容なら再利用し、異内容または複数候補なら元を残す。保存先内容、削除前の記録作成、元の実体と内容を順に確認する。不一致・確認不能・記録失敗なら削除せず、独立した別ファイルは進める。モデル内の単一元を除去した場合だけ完了件数に加える。

イベントは`prepared`（対象とsize/SHA-256の対応）、`delete_result`（完了/不明）、`reconciled`（今回の照合完了）を区別する。元を取り除いた直後に応答が失われるケース、元が残るケース、除去後の結果記録だけが失敗するケースを注入できる。前回不明の対象や結果未記録の対象が列挙から消えても「対象なし」に落とさず、次回に同じ経路・元/保存先の記録と現在の内容を確認する。対応記録の欠落、保存先欠落・不一致、同じパスの再作成、存在確認不能は完了にしない。旧不明イベントは書き換えず、完了した元を次回再計上しない。

上記フィールド名と状態名は模擬モデル内の契約であり、v1 recordそのものではない。JournalRoot指定時はpreparedとv1記録の明示対応を追加する。manifest v1とDrive IPCは変更しない。メモリ上の完全な存在確認と単一処理による除去を、Windowsのハンドル操作やDriveの条件付き削除で実現できると主張しない。

Dry Runでは、対象判定と不正名の報告だけを行い、モデルのbytes・ファイル集合・イベントを変更しない。返却結果には常に`SimulationOnly = true`を付ける。個別結果と、元単位の完了/未解決件数を返し、同じ保存先を使う複数の元も個別に数える。表示用のJSONを永続証拠として読み戻す機能はない。

## 対象シナリオと未完

AC-01〜09/11に関係する期間境界、古いAログのクラウド経由、B未実行と遅着、平坦化、同内容再利用、異内容競合、コピー/確認/記録/削除失敗、元変更・差替え、通常再実行、応答不明と照合を合成入力で確認する。これは各ACの実環境条件や正式入口・配布までを通した受け入れではない。AC全体を完了へ更新しない。

T0の実API/FS保証、条件付き削除と確認対象の結合、新しい永続記録と破損・中断後の回復、次経路移動後の照合、実列挙・staging・所有排他、概要/レポートの実保存が残る。T1の正式入口、T2/T3の実adapter・元削除、T4/T5の統合と受け入れも未完。模擬モデルの成功を理由に、これらの前提を省略しない。

## 実装前の比較

2026-10-28にGitHub上の[rcloneの移動説明](https://github.com/rclone/rclone/blob/master/docs/content/commands/rclone_move.md)と[operations実装](https://github.com/rclone/rclone/blob/master/fs/operations/operations.go)を確認した。サーバー側moveを使う方式と、コピー後に元を削除する方式を比較した。今回の2経路はコピー・保存先確認・元不変確認・限定削除の順序を明示するため、後者の分解を参考にする。ただしQ5やQ11に必要な対象結合・観測記録は別途設計が必要で、外部コマンドの成功を削除条件の証拠にしない。コードの転載や依存関係の追加、rclone採用は行っていない。
