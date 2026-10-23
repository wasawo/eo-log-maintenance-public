# Repository maintenance scripts

このディレクトリには、将来的にドキュメント生成とローカル更新確認用スクリプトを配置します。

- `Generate-Docs.ps1`: README の定型情報や CHANGELOG の候補生成。README 全体の無条件上書きは禁止。
- `Update-Local.ps1`: リリース取得・ローカルとの差分表示・手動適用の補助。初期段階では取得・差分確認までとし、ファイルを自動上書きしない。

これらはまだ実装されていません。実装後にテストと README を更新します。

現時点ではこのREADMEのみで、正式な `SyncLogs.ps1` / PC-A専用 `ArchiveLogs.ps1`、導入・更新入口は存在しません。Commonの補助処理を正式入口として実行しないでください。[初回配布の棚卸し](../docs/first-release-readiness-20261024.md)を参照してください。
