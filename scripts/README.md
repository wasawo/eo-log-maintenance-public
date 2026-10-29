# Repository maintenance scripts

現在は[Show-MoveRun.ps1](Show-MoveRun.ps1)で、移動記録の実行別概要を読取専用で表示できます。[使い方と集計範囲](../docs/design/move-run-report.md)を参照してください。移動・削除・回復は行いません。

次のドキュメント生成とローカル更新確認用スクリプトは今後の候補です。

- `Generate-Docs.ps1`: README の定型情報や CHANGELOG の候補生成。README 全体の無条件上書きは禁止。
- `Update-Local.ps1`: リリース取得・ローカルとの差分表示・手動適用の補助。初期段階では取得・差分確認までとし、ファイルを自動上書きしない。

これらはまだ実装されていません。実装後にテストと README を更新します。

[SyncLogs.ps1](SyncLogs.ps1)はS1のPC-B専用・削除なし合成E2E入口です。既存のファイル名/期間判定を呼び、再帰列挙→平坦化→模擬Driveへの非上書きコピー→SHA-256照合→JSON結果表示まで実行します。成功はコピー検証の成功であり、`CompletedMoveCount`は常に0です。不正名/取得失敗は失敗、異内容は保留として理由と件数を表示します。

`-Synthetic -SyntheticRoot <合成fixture>`が必須です。fixtureはOS一時領域直下の`eolm-s1-sync-<32桁GUID>`で、`.synthetic-fixture`の内容は`eolm-s1-synthetic-v1`、ディレクトリは`source/BattleLog`・`source/ErrorReport`・`mock-drive/BattleLog`・`mock-drive/ErrorReport`です。元のサブフォルダは許可します。reparse point、模擬Drive内のサブフォルダ、二重起動は拒否します。実設定・任意の実ログroot・実Drive接続は受け付けません。

再現は`pwsh -NoProfile -File tests/Test-SyncLogsE2E.ps1`で、試験自身が合成fixtureを作成し、入口を別プロセスで起動して後片付けします。入口単体は`pwsh -NoProfile -File scripts/SyncLogs.ps1 -Synthetic -SyntheticRoot <合成fixture> -ReferenceDate 2026-10-29`です。`-DryRun`は計画表示のみ、`-MockFault hash_mismatch|copy_failed|enumeration_failed`は合成環境限定の失敗注入です。失敗・保留時は終了コード1、成功・正常な対象なしは0です。入口自身は失敗コピーも元も削除しません。

[ArchiveLogs.ps1](ArchiveLogs.ps1)はS2のPC-A限定・削除なし合成E2E入口です。`-Synthetic -SyntheticRoot <合成fixture>`を必須とし、OS-temp直下`eolm-s2-archive-<32桁GUID>`、marker内容`eolm-s2-synthetic-v1`、`mock-drive/BattleLog`・`mock-drive/ErrorReport`から`archive/BattleLog`・`archive/ErrorReport`へ同じコピー/照合処理を使います。BattleLogは前年末以前、ErrorReportは前々年末以前を選び、PC-Bの期間完了や実行は待ちません。遅着分は次回コピーし、既存の同内容archiveは再利用します。実行: `pwsh -NoProfile -File tests/Test-ArchiveLogsE2E.ps1`。PC-B、Sync操作、実設定の入力は受け付けません。

両入口は[SyntheticLogTransfer.ps1](../Common/SyntheticLogTransfer.ps1)を再利用し、S1の入力・結果・役割制限は維持します。実Driveの運用adapter/認証資格、実元削除、導入・更新入口は未完です。両入口の`EOLM-SYNTHETIC-ONLY`マーカーにより、役割別ビルダーは配布可能と扱いません。[初回配布の棚卸し](../docs/development/implementation-workflow.md#9-既存の実装資産と不足)を参照してください。

S3のAPI模擬結合は、両入口へ`-DriveApiMock -PythonExecutable <Python>`を指定します。公式SDKと既存reader、[DriveTransferAdapter.py](../Common/DriveTransferAdapter.py)を呼び、Syncは新規upload/現在内容確認、ArchiveはAPI列挙/downloadから既存のローカルcopy/hashへ接続します。fixtureの構成と役割制限はS1/S2と同じです。`-ApiFault auth_denied|api_error|upload_unknown|content_changed|version_changed|duplicate_name`は完全オフラインの試験注入です。Dry RunではPythonを起動しません。

このモードはtests専用HTTP workerに固定され、実Drive接続CLIや既定認証は提供しません。結果の`AdapterMode=sdk_http_mock`、`CloudObserved=false`は模擬結合を表し、実接続成功やS3完了の表示ではありません。libraryのSDK結合は追加しましたが、運用認証/service資格・実root・隔離実Drive受け入れは未完。実操作には利用者の別途の明示承認が必要です。
