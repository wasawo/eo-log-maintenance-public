# 所有mutexと実体保持を同じプロセスで行う隔離試験

更新日: 2026-10-28。[Windows削除probe](windows-move-delete-probe.md)へ既存の所有ロックを接続し、所有確認・Q5再読・記録保護・同一ハンドル削除を一つのプロセスで試験する。正式providerの採用や、PowerShellのモデル入口を実削除へ切り替える変更ではない。

## 範囲と実行

実装はtests配下の`OwnedDisposableMoveDeleteProbe`。自分で生成したOS-temp直下のroot・所有marker・合成元/保存先・journalだけを使う。利用者がroot/pathを指定する入口は追加しない。Common・配布物・実設定・実ログ・Driveには接続しない。

```powershell
python -B -m unittest discover -s tests -p "test_owned_windows_move_probe.py" -v
```

## 保持する区間

1. 既存`acquire_owned_lock`で、fixture固有scopeのGlobal mutexとtoken記録を取得する。所有と削除を別プロセスへ分けず、同じ実行スレッドで保持する。
2. token記録を読取＋FILE_SHARE_READで開き、同じscope/token/PID/hostを含む生成bytesのsize/hashを確認する。このハンドルを処理終了まで保持し、通常の競合する書込/削除openを拒否する。
3. 元を読取＋DELETE、保存先を読取で開く。FILE_SHARE_READで保持し、volume/128-bit File ID・size/SHA-256を確認する。
4. 準備記録と移動記録v1を非上書き保存・読戻しする。さらに両記録を読取ハンドルで保持し、保存時のbytesと照合する。改変・確認不能なら元を削除しない。
5. 同じプロセスの所有token対応とroot chainを確認した後、保持している元/保存先のハンドルを先頭へ戻し、全内容を再読する。記録作成前のハッシュやmetadataだけでQ5を代用しない。
6. 同じ元ハンドルへFileDispositionInfoを指定し、元ハンドルを閉じる。保存先・確認記録・所有記録・mutexは除去観測と結果保存まで保持する。
7. 所有確認に失敗した場合、削除前なら元を保持し、削除後なら結果不明を返す。確認不能な状態で成功journalを作らず、最後に自分の所有記録だけを既存規則で処理する。

所有記録の不変ハンドルとtoken照合は、実環境のACLやowner qualificationを完了した証拠ではない。呼出しにscriptを渡しただけで実削除を許可するものでもない。

## 同じハンドルを読み直す方式

Microsoftの[SetFilePointerEx仕様](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfilepointerex)を確認し、[CPython](https://github.com/python/cpython/blob/3a304c25f106c4f39de4c2d3380def82f39abcc7/Modules/mmapmodule.c)の同じhandleで位置を指定する例と、[libuv](https://github.com/libuv/libuv/blob/338ac6ac0714e6d8043a2826c9b3bc78e85bb961/src/win/fs.c)のoffset指定/位置復元を比較した。

probeのハンドルは専用・同期読取であり、他スレッドへ共有しない。このためFILE_BEGINへ戻して再読する方式を選んだ。並行読取を扱う場合のoverlapped offset管理を採用したわけではない。SetEndOfFileや内容書換えは行わず、位置移動の失敗でも元を削除しない。コード転載や依存追加はない。

## 所有プロセスの終了と照合

専用workerは自分でfixtureを生成し、削除直前または削除直後にプロセスを終了する。親試験へroot/nonceをprivate pipeで渡すが、workerは利用者指定pathを受け付けない。

削除前の終了では元が残り、準備記録だけが残る。削除後の終了でも成功した削除結果記録は作らない。どちらも所有lockが残り、別プロセスの既存読取workerが現在の元/保存先を再観測する。前者は未完了、後者はQ11条件がそろった場合だけ照合完了となる。旧prepared bytesと残存lockを変更せず、lock解除・再削除・旧要求の成功化は行わない。

親の再帰cleanupも、OS-temp直下のprefix、nonce marker、root/祖先の実体検査を通した、その試験が生成したfixtureだけを対象にする。

## 検証と残る限界

[9試験](../../tests/test_owned_windows_move_probe.py)で空/複数chunkの内容、同一ハンドル再読、別スレッドのmutex競合、元のwrite/delete open拒否、所有/準備記録の書込拒否、記録改変、所有確認不能、再読位置移動失敗、pending、所有プロセス終了前後の別プロセス照合を確認する。共有拒否のerror 32はPython CRT例外の変換値へ依存せず、Win32 APIを直接使って検査する。

これは特定の合成rootでの実OS試験であり、PowerShellモデルの別プロセス所有方式を置き換えていない。既存memory mappingによる書込み、祖先の名前空間保護、実効ACL、FS差、電源断、close失敗、実Drive保存先を解決済みとはしない。既に始まった削除要求の取消しも保証しない。正式providerへの昇格、T0/T1/T4/AC全体の受け入れ完了にはしない。
