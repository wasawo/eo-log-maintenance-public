# Repository maintenance scripts

現在は[Show-MoveRun.ps1](Show-MoveRun.ps1)で、移動記録の実行別概要を読取専用で表示できます。[使い方と集計範囲](../docs/design/move-run-report.md)を参照してください。移動・削除・回復は行いません。

次のドキュメント生成とローカル更新確認用スクリプトは今後の候補です。

- `Generate-Docs.ps1`: README の定型情報や CHANGELOG の候補生成。README 全体の無条件上書きは禁止。
- `Update-Local.ps1`: リリース取得・ローカルとの差分表示・手動適用の補助。初期段階では取得・差分確認までとし、ファイルを自動上書きしない。

これらはまだ実装されていません。実装後にテストと README を更新します。

正式な `SyncLogs.ps1` / PC-A専用 `ArchiveLogs.ps1`、導入・更新入口は存在しません。概要表示コマンドやCommonの補助処理を、正式な移動入口として扱わないでください。[初回配布の棚卸し](../docs/development/implementation-workflow.md#9-既存の実装資産と不足)を参照してください。
