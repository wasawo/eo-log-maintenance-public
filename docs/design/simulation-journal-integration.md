# 模擬移動・記録・通常再実行・概要表示の接続

更新日: 2026-10-28。[模擬移動](log-move-simulation.md)、[移動記録v1](move-record-v1.md)、[実行別概要](move-run-report.md)を、両経路の一連処理として接続する。

## 実行と範囲

```powershell
pwsh -NoProfile -File tests/Test-LogMoveJournalIntegration.ps1
```

PowerShell 7.6.7または7.6.9とruntime依存を導入したPythonを使う。必要なら`-PythonExecutable`で実行ファイルを指定する。試験が自分で作った一時journalとメモリ上の合成ログだけを使用する。

`Invoke-EoLogMoveSimulation`に、任意の`JournalRoot`、`PythonExecutable`、`RunId`を追加した。JournalRootを省略した従来のメモリ上の試験は維持する。指定した場合もrootを自動生成・認可せず、呼出し側が用意した専用領域へ記録だけを保存する。設定内の実ログrootへはアクセスしない。

元/保存先の移動はメモリ上だけである。ローカルの実体IDは合成IDから作る模擬値、cloud IDやversionも模擬値で、実Windows/Drive観測として採用しない。実ログ削除、Drive操作、正式Sync/Archive入口、実run所有排他は追加していない。

## 1回の移動と再実行

1. 既存の設定・役割・期間・平坦化・同名比較を行い、モデルの保存先内容とコピー基準の一致を確認する。
2. `LogMoveSimulationJournal.ps1`から内部の`MoveJournalCommand.py`を1回呼び、preparedを非上書き保存・読戻しする。記録が確認できなければ、その元を削除しない。journalの共通不備が分かれば、残りの元も保全する。
3. journal内の同じ経路/PC/ログ種別・元参照・コピー内容を照合し、過去の準備があればmove IDを再利用する。run IDとattempt IDは新しい値とし、以前の試行を上書きしない。実体またはコピー内容が変わった場合は別moveとする。
4. モデルのQ5確認と対象限定削除を行い、その結果をdeletion_resultへ保存する。削除後の記録失敗は不明とし、メモリ上のイベントも完了扱いにしない。
5. 普通の削除失敗なら、同じ関数の再実行で保存先を再利用して残りを進める。削除結果不明で元がなくなっている場合は、現在のモデル状態を照合してreconciliationを追加する。有効な削除結果があれば、その記録にも明示参照を付ける。
6. `Show-MoveRun.ps1`で保存した記録の概要を読戻し、戻り値のJournalSummaryへ含める。返されたRunIdで同じ概要を別途表示することもできる。

同じ元・コピー内容に複数のmove IDが既に存在する場合は、勝手に統合・選択しない。新しい記録や元削除へ進めず、診断を要する不整合として扱う。並行writerに対するID割当の原子性は実装しておらず、実run接続には資格を確認した所有排他が必要となる。

## 記録と表示の注意点

モデル内のpreparedにv1 recordとexact bytesのSHA-256を結び付け、結果/照合の参照を取り違えない。複数のpreparedがあっても、記録との明示対応を使う。PowerShellのJSON読取ではUTC文字列をDateTimeへ自動変換せず、端数と表記を保持してechoを照合する。

内部応答はversion、request/record/run ID、scope、型・key、recordのechoとdigest形式を検査する。preparedのmove ID再利用と、照合への既存結果参照の追加だけを認める。stdin書込・子プロセス待機はそれぞれ30秒を上限とし、未確認時に成功へ置き換えない。これは模擬journal用の内部契約で、Drive IPCの操作を増やすものではない。

コピー失敗・競合・不正名など、preparedより前の失敗を「保存先確認済み」と偽ってv1へ保存しない。それらはファイル別Resultsと、任意の[模擬実行結果レポート](simulation-run-report.md)へ残す。journal概要だけでは現在runの全対象・失敗を網羅しない。正式な実行全体の判定は後続である。

メモリ上の対象が0件でも、journalの過去未解決があればfailureにする。journalを読めない場合もno_workにしない。JournalReadStatusとJournalUnresolvedSourceCountを、モデル内のファイル別未解決件数とは別に返す。同じ対象が両方へ現れ得るため、これらの件数を単純に足さない。過去の記録を読み、未解決を示すことは、現在のファイルモデルを復元したことにはならない。

同じ元/コピー内容の別試行で完了を確認できれば、古い失敗試行だけを未解決として持ち越さない。一方、同一preparedからの先後関係不明な結果や、元/コピー内容の対応矛盾は保留する。概要表示の「今回初めて完了」と、模擬関数が返す今回の照合完了件数は区別する。

Dry Runではjournalを読書きせず、モデルも変更しない。古いモデルイベントしかなく、v1記録との対応を確認できないものは、journal有効時の照合完了へ変換しない。壊れた記録や残存tmpの自動削除も行わない。

## 検証と未完

[PowerShell接続試験](../../tests/Test-LogMoveJournalIntegration.ps1)で、両経路の削除失敗→通常再実行→概要、結果不明と結果記録欠落→照合、Dry Run、壊れたjournal、準備前の失敗、PC-B SyncとArchive拒否を確認する。[内部コマンド試験](../../tests/test_move_journal_command.py)ではID再利用・別実体/内容の分離・同内容再保存・矛盾拒否を検証する。

模擬状態は呼出し側が保持しており、journalだけで現在の元/保存先を復元するものではない。正式coordinator、実列挙と実run全体の記録、private root/ACL/排他資格、実providerとDrive版固定削除、実運用の詳細表示・性能・実環境受け入れは未完。T0/T1/T4全体を完了にはしない。
