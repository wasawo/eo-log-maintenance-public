# ファイル列挙から所有ロック付き模擬移動への接続

更新日: 2026-10-28。[所有ロック付き模擬実行](owned-simulation-run.md)へ、読取専用のファイルスナップショットを渡す。合成ディスク入力を期間判定・同名比較・移動記録・結果レポートまで接続する試験基盤であり、実ログやDriveを移動する入口ではない。

## 呼出しと実行順序

`Invoke-EoOwnedLogMoveSimulation`へ任意の`SnapshotRoots`を追加した。未指定なら既存のメモリ上のStateをそのまま使う。指定時は次の4要素を渡し、State.Files/Eventsは空のListとする。既存モデルの結果や履歴を黙って上書きしない。

| side | log_type | pathの役割 |
| --- | --- | --- |
| source | BattleLog | 元のBattleLog合成フォルダ |
| source | ErrorReport | 元のErrorReport合成フォルダ |
| destination | BattleLog | 保存先のBattleLog合成フォルダ |
| destination | ErrorReport | 保存先のErrorReport合成フォルダ |

pathは事前に作成した絶対パスとし、4領域同士の同一/親子関係、及びjournal/lifecycle/report領域との重複を拒否する。設定JSON内の実ログパスやDrive IDから入力を自動発見しない。Syncではsourceを実行PC、destinationをCloudとしてモデル化し、ArchiveではsourceをCloud、destinationをArchiveとしてモデル化する。Cloudの合成フォルダを読むことは、Drive APIによる内容確認ではない。

通常実行は所有ロック取得・開始記録の確認後に列挙する。`SimulationFileSnapshot.py`は既存の`SourceInventoryEvidenceBuilder`の列挙/reparse検査と、`ArtifactSetDirectoryVerification`の安定読取を再利用する。全rootを再帰列挙し、ファイルの実体・サイズ・時刻・親chainを照合して内容を読み、全rootの最終再走査で観測した構成の変化も確認する。

4領域全体の収集と応答検証が完了した場合だけStateへ反映し、既存モデルを実行する。相対パス・合成内容・不透明なIDを保持し、期限内や不正名も取り込む。期間・ログ名の判定はPowerShellの既存処理へ任せ、古いB2 collectorの同期向けcutoffをArchiveへ流用しない。元サブフォルダの識別と、保存先basenameへの平坦化は既存モデルの規則に従う。

Dry Runは通常所有ロック・開始記録に入らず、読取スナップショットを一時的なモデルとして判定する。呼出し側の空State、物理ファイル、journal/レポート/lifecycleは変更しない。

## 失敗と入力の範囲

列挙・読取・照合の失敗、root不在、途中変更、junction/reparse、非通常ファイル、上限超過では部分一覧を返さない。通常実行はモデル移動前に中断し、呼出し側Stateを空のまま保つ。開始記録があれば所有プロセスがinterruptedを残す。完全な空一覧と列挙失敗を区別し、失敗を対象なしへ置き換えない。

輸送上限は各走査で4領域合計4096 entry、1ファイル1 MiB、内容合計4 MiB、要求JSON 64 KiB。これらは小さい合成モデル用の制限であり、実運用ログのサイズ制限として採用したものではない。上限に達したからといって残りを省略して成功にしない。

応答はversion・request UUID・PC・経路・全列挙完了・件数・総bytesとファイル一覧を持つ。内容はprivate pipe内でBase64輸送し、PowerShellで型/key、範囲、参照の重複、相対パス、復号size/SHA-256、総数を検査する。raw応答・内容・入力絶対パスをコンソールへ転送しない。取得失敗は固定理由で返す。

IDは位置・ログ種別・rootの実体・ファイルの実体・相対パスから作るモデル用SHA-256であり、同じ物理ファイルの内容変更だけでは変えない。同内容でも別実体へ置換した場合は変わる。Windows providerの128-bit IDやクラウドの版情報としては扱わず、削除認可にも使わない。

## 検証と残件

```powershell
pwsh -NoProfile -File tests/Test-FileSnapshotMoveSimulation.ps1
```

[Python試験](../../tests/test_simulation_file_snapshot.py)で両経路、変更/置換、空と失敗、読取失敗、別root読取中の先行root変更、上限、不正scope/領域、実junction、失敗時の秘匿を検証する。[接続試験](../../tests/Test-FileSnapshotMoveSimulation.ps1)ではPC-A Sync/Archive・PC-B Sync、両ログ種別、保持期間内・同内容再利用・異内容競合・不正名、Dry Run、中断と最終レポートを通し、元/保存先の全物理ファイルが不変であることを確認する。

スナップショット読取後の移動・コピー・削除はメモリ上だけである。物理的に元が残るため、再収集で再びモデルへ現れることを実移動の再到着とはみなさない。journalだけから前回のモデルEventsを復元したり、実ファイルの現在状態を使ってQ11照合完了へ昇格したりしない。

この観測は原子的なディレクトリスナップショットではなく、metadataを復元する変更やABAを排除しない。取得後のQ5確認・実体保持、所有喪失時の停止、実運用root/ACL資格、実Drive列挙/版固定削除、正式Sync/Archive入口は未完である。T0/T1/T4/AC全体を完了にはしない。実ログや本番Driveを試験に持ち込まない。
