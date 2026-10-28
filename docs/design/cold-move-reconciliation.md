# 別プロセスで現在の元・保存先を再観測する隔離試験

更新日: 2026-10-28。対象は[正式設計](log-move-design.md)§9〜16と、[移動記録v1](move-record-v1.md)を実観測へ接続するT0/T4の作業。

## 今回進めた範囲

前回の記録試験は、子プロセスが合成の観測値を使って照合記録を作っていた。[今回の試験](../../tests/test_cold_move_reconciliation.py)では、子プロセスが合成元/保存先の現在の実ファイルをWindows APIで観測する。親から「元不在」や「保存先一致」という結果を渡さず、保存済みの準備記録と現在状態を照合する。

```powershell
python -B -m unittest discover -s tests -p "test_cold_move_reconciliation.py" -v
```

元ファイルの実削除は、既存の[Windows probe](windows-move-delete-probe.md)が自動生成したOS-temp領域内だけで行う。保存先も同じ合成領域のファイルであり、cloud IDとローカル実体を対応付けた模擬cloud providerである。実Driveにアクセスせず、通常ログの対象選択や正式な同期入口は提供しない。fixtureの`source.bin`等はログ名規則の受け入れ試験には使わない。

## 準備記録から子プロセスへ渡すもの

probeの`journal=True`で、元/保存先を確認した後、元の削除より前に移動記録v1のpreparedを保存・読戻しする。元のvolume/File ID・コピー基準size/hashを結び付け、専用journal rootへ非上書き公開する。実体のroot/祖先、対応する合成保存先のFile ID、prepared IDとexact bytesのSHA-256は、所有markerのあるfixture記述にも保持する。

元削除後の記録を失敗させる場合はpreparedだけが残る。別readerが残る場合は、要求成功と元の除去未確認を区別したdeletion_resultを保存する。いずれも、記録の保存を成功へ書き換えて回復した扱いにしない。

子プロセスへ渡すのは自作fixtureのrootと所有marker照合用nonceだけである。元/保存先のハッシュ、存在の判定値、親のメモリ上の準備記録は渡さない。子はディスク上のjournalとfixture記述から必要な基準を読み直す。

fixture記述は試験専用の対応情報であり、実運用のroot資格・ACL・署名の代用品ではない。nonceの一致だけで任意の実運用rootを認可しない。

## 子プロセスの観測と判断

[専用worker](../../tests/cold_move_reconciliation_worker.py)は、OS-temp直下の固定prefix、通常ディレクトリの祖先、marker、元のroot identityを確認する。journal全体とpreparedの参照を検査し、record内の任意pathを操作せず、固定の合成元/保存先だけを開く。

保存先のハンドルで現在の実体ID、size、SHA-256を確認し、fixtureの対象との対応を検査する。保存先のguardを保持したまま元を調べ、元の通常読取ができれば実体IDを比較する。同じ元があれば未完了、別実体なら不明とする。欠落時は健全な自作rootの下で不在を追加確認する。共有違反やdelete pending等の読取不能を不在にしない。

元の確実な不在、現在の同じ保存先の内容一致、有効な対応記録がそろった場合だけ、別のreconciliationを新しいrun/attemptとして保存する。必要条件がそろわない場合も、その観測に応じた未完了/不明を別記録へ保存する。観測・記録時刻は今回取得し、前回記録の時刻を流用しない。時刻の取得自体を時計の信頼性の証明にはしない。

workerは元を削除し直さない。読取専用observerだけを組み立て、誤ったWRITE/DELETEアクセスのopenとdisposition呼出しを拒否するwrapperも入れる。これはこの試験コードの誤呼出しを防ぐ仕組みであり、任意native codeに対するセキュリティsandboxではない。書き込むのは新しいjournal記録だけで、旧prepared/結果/照合記録を上書きしない。

## 検証結果と残件

Python 3.11.9/Windowsで新規6試験と既存probe回帰9試験が成功した。削除後の結果記録欠落、別readerによるpending、その解消後の照合、元が残る場合、読取不能、元の再作成、保存先の破損/欠落/同内容別実体への差替え、prepared/fixtureの改変、部分記録、nonce不一致を検査した。元が残るケースでは、その内容が回復処理後も不変であることを確認した。

試験は置換・hardlink等を利用するため、過去と同じくsandbox外で自作一時領域だけを対象に実行した。CIにはPython 3.12/Windowsの専用ステップを追加したが、新ブランチのリモートCIは未実行。

今回確認したのは、隔離fixtureでの実ファイル状態と移動記録v1を別プロセスで結び付ける流れである。プロセスをまたぐ実観測はできたが、クラッシュ/電源断の耐久性、実運用root/ACL/所有排他、書込可能mapping、攻撃的な名前空間変更、実Driveの版固定操作や権限による不可視と不在の区別は未確認。PowerShell制御、正式なSync/Archive入口、経路間照合、実運用の件数集計にも未接続で、T0/T1/AC全体を完了とはしない。
