# 所有ロックと開始・終了記録を接続した模擬実行

更新日: 2026-10-28。[模擬移動](log-move-simulation.md)・[移動記録](move-record-v1.md)・[結果レポート](simulation-run-report.md)を、既存の所有権付きOSロックで囲む。実ログやDriveを扱う正式入口ではない。

## 呼出しと配置

`Common/OwnedLogMoveSimulation.ps1`の`Invoke-EoOwnedLogMoveSimulation`を使う。既存モデルと同じ設定JSON・PC・経路・State・基準日・故障指定に加え、`LifecycleRoot`・`JournalRoot`・`ReportRoot`を必要とする。Python実行ファイルとrun UUIDは任意指定できる。検証は次の合成試験で行う。

```powershell
pwsh -NoProfile -File tests/Test-OwnedLogMoveSimulation.ps1
```

3領域は呼出し側が事前に用意する。LifecycleRootはJournalRootの兄弟で、名前を`<JournalRootの末尾名>.lifecycle`に固定する。例えばjournalの末尾名が`journal`なら`journal.lifecycle`となる。3領域の同一/親子関係とreparse経由を拒否する。固定配置は、所有プロセスの終了後に別の保存先を指定して残存lockを迂回することを防ぐ。

ディレクトリを指定しただけで実運用のprivate root資格・ACL・所有者・名前空間保護が成立したとは扱わない。rootの実体chainは起動時と終了要求時に照合するが、敵対的な並行置換を原子的に防ぐものではない。

## 実行順序

1. PowerShell側で設定と役割を確認する。PC-BのArchiveを拒否する。Dry Runなら通常ロック・開始記録・通常cleanupへ入らず、既存の読取モデルへ分岐する。
2. 固定の`Common/SimulationRunOwner.py`を起動する。既存`OwnedRunLock.acquire_owned_lock`でWindows Global mutexと所有token記録を取得する。待機は0秒とし、競合・abandoned・既存lockは拒否する。既存方式と調査結果を再利用し、外部依存を追加しない。
3. `<run_id>.started.json`を非上書き公開・読戻しした後、readyを返す。run UUIDは単回使用とし、以前の開始/終了記録があれば処理を始めない。
4. PowerShellが既存モデルの移動・journal・結果レポートを実行する。所有プロセスはこの区間でmutexを保持する。
5. 終了要求を受けた所有プロセスが、保存確認済みレポートを現在bytesから再読し、run/PC/経路・集計状態を照合する。`<run_id>.ended.json`へ開始記録と最終レポートのexact bytes SHA-256を結び付ける。レポート未確認ならdigestを捏造せず、その状態を残す。
6. 自分の所有記録だけを既存cleanupで処理し、mutexを解放する。lock記録の不在も確認してからfinishedを返す。改変・確認不能なlockは保全し、終了応答を成功にしない。

scopeは正規化したjournalパスのSHA-256から導く。同じjournalを使う協調的な呼出しはPC/経路を問わず直列化される。これは同じ管理rootを使う模擬処理の排他であり、別journalを使う実クラウド保存先の同時更新まで防ぐものではない。

## 記録と応答の意味

開始/終了記録はversion、simulation_only、run/PC/経路、不透明なscope参照、記録時刻を持つ。終了記録のdispositionは`finished`または`interrupted`。`finished`は処理が終端へ達したことを示し、operation_statusのsuccess/no_work/partial_failure/failureとは別である。所有解放前に終了記録を保存するため、終了ファイルだけでcleanupの成功を証明しない。

wrapperの`LifecycleStatus`は`confirmed`、`unconfirmed`、Dry Runの`not_started`。移動結果が返った後に終了応答を確認できなくても、その移動件数やStatusを過去の未実施へ書き換えない。モデル処理自体が例外になった場合は、固定理由`owned_simulation_interrupted`で停止する。

IPCのready/finished応答はversion・phase・run UUID、所有確認のowned応答はこれらにsequenceを加えた閉じた構造とする。ready待ち、各要求書込・応答待ち、終了待ちをそれぞれ30秒以内にする。所有token・PID・host・raw例外/stderrをコンソールへ転送しない。所有lock内のtoken/PID/hostは既存契約の非公開情報であり、実行時の記録をGit・配布物・PRへ追加しない。

## 処理境界での所有確認

所有プロセスはcheck要求を受けるたびに、管理rootの実体chainと、既存`_record_matches`によるscope/所有tokenの対応を読み直す。要求はversion・run UUID・kind・連番だけを持ち、同じrun内の1からの連続整数を要求する。異なるrun、再送された番号、型不正、未知keyを拒否し、tokenは相手へ渡さない。最終要求も同じ所有確認を通す。

wrapperはこの往復をモデルの`OwnershipCheck`へ渡す。各元の開始、保存先モデル追加、prepared保存、元除去の直前/直後、結果保存、過去照合、概要読取、最終レポート保存の境界で確認する。確認が失敗したら同じ実行内では成功へ戻さず、後続のコピー・元除去・永続保存を止める。空の対象一覧でも概要前の確認を行う。Dry Runは通常の所有確認を呼ばない。

`OwnershipStatus`は`confirmed`、`unconfirmed`、直接モデル呼出しやDry Runの`not_checked`。直接渡すscriptblockがtrue以外や例外を返した場合も確認不能にする。callbackを指定したこと自体を実運用の所有資格とはみなさない。

元除去前の失敗は元を保持した結果、除去後に確認を失った場合は結果不明としてメモリ上へ返す。後者で元を復元したり、削除成功のjournalを捏造したりしない。過去照合の結果保存失敗は、今回の削除とは別の理由で返す。既に記録まで確認できた別ファイルの完了数は維持し、runは失敗/部分失敗とする。coreが喪失を検知した場合のjournal概要・レポート保存状態はunconfirmedとし、成功レポートを追加しない。

所有応答は待機し得るため、応答後に元/保存先のモデル内容を再確認してから元を除去する。Q5を確認できず削除を送らなかった結果では、現在内容を準備時の値で代用せず、確認不能な観測をnull/unavailableとして記録する。これはモデルの再検証であり、実FS/Driveの原子的なQ5保証ではない。

## 中断と残る限界

PowerShellの例外や入力EOFでは、所有プロセスがinterruptedを保存して自身のlockを解放する。通信がないだけで移動成功を推測しない。所有プロセス自体を強制終了した場合は開始記録とlockが残り、通常再実行は拒否する。古さだけで解除・採用・書換えをせず、別途の明示回復設計へ残す。開始だけの記録を対象なしや完了にしない。

この接続は、元/保存先の操作がメモリ上のモデルである。既知の所有喪失では次の処理へ進めないが、所有確認と次の操作を原子的に結び付けてはいない。確認直後の喪失や、既に呼び出したjournal/レポート書込みを取り消す保証はない。最終応答で失敗した場合も、既に確認済みの成果物を削除しない。実providerへそのまま接続せず、所有喪失と実操作の停止・実体保護を正式run側で結び付ける必要がある。

任意の`SnapshotRoots`を指定した場合は、所有取得後に[合成ファイルを読取列挙](file-snapshot-simulation.md)してモデルへ渡す。全領域を確認できなければモデル処理前に中断する。未指定時の直接モデル呼出しを維持し、物理ファイルの移動・削除は追加しない。

所有資格・ACL、実列挙、複数端末/別root間のクラウド競合、実Driveの版固定削除、開始だけ残った記録の正式診断、実環境受け入れは未完。T0/T1/T4やAC全体は完了にしない。既存の直接モデル呼出しは排他を持たないため、このwrapperを迂回する並行writerの保証も含めない。

[所有プロセス試験](../../tests/test_simulation_run_owner.py)では実Win32 mutexによる競合、EOF、強制終了と残存物保全、異常要求、レポート/開始digest、改変lock、run再使用を検証する。[PS接続試験](../../tests/Test-OwnedLogMoveSimulation.ps1)ではPC-Aの両経路とPC-B Syncをjournal/レポートまで通す。通常試験は自作合成一時領域のみを使う。

[所有喪失試験](../../tests/Test-OwnershipLossMoveSimulation.ps1)では、両経路の各境界・除去後・照合中の喪失、応答待機中の内容変更、実所有記録の改変からモデル停止までを接続し、元保全・結果不明・残存記録保全・Dry Runを確認する。
