# 元の確認から同じハンドルで削除するWindows隔離試験

更新日: 2026-10-28。対象は[正式設計](log-move-design.md)§3/4/6/9〜11と、[実装計画](../development/implementation-workflow.md)のT0に残るローカル元削除・記録の方式確認。

## 今回確認する範囲

[両経路の模擬接続](log-move-simulation.md)では、元をメモリ上で一意に識別して取り除いていた。次の段階として、合成ファイルのコピー先の内容と元の不変を確認し、その元の同じハンドルへ削除を指定する方式を実Windowsで試験する。実装は[専用probe](../../tests/windows_move_delete_probe.py)、検証は[統合試験](../../tests/test_windows_move_delete_probe.py)に置く。

```powershell
python -B -m unittest discover -s tests -p "test_windows_move_delete_probe.py" -v
```

probeはOSの一時領域に新しい専用ディレクトリと所有marker、合成元/保存先を自分で作る。利用者指定のrootやpathを受け付けない。操作名も固定し、実ログや本番Driveへ接続する機能はない。rootと祖先の実体、marker、通常ファイル・単一linkを確認する。試験後の再帰cleanupは、この確認を通った自作領域だけに限る。元削除操作自体は単一ファイルのハンドルへ行い、cleanupとは分ける。

これは通常の合成データ試験であり、実運用予定volumeのTier B/C検証や本番削除ではない。tests配下のprobeは配布対象に追加しない。

## ハンドルと記録の順序

1. 合成内容を元と保存先へ用意し、コピー基準のsize/SHA-256、元/保存先のvolume番号と128-bit File IDを保持する。
2. 保存先を読取アクセス、元を読取＋DELETEアクセスで開く。両方の共有指定はFILE_SHARE_READだけとし、通常の書込・削除openを許さない。既存writerのため開けなければ処理を止める。
3. 各ハンドルからFile ID、size、通常ファイル/単一linkを確認し、全bytesを読んでハッシュを比較する。読取前後もmetadataを確認する。同内容でも元/保存先の実体が基準から変わっていれば元を残す。
4. 確認した元/保存先identityと内容を`prepared.json`へcreate-onlyで保存し、flush/fsync後のbytesを読戻して照合する。失敗時は元削除を呼ばない。これは本番用の永続記録schemaの採用ではない。
5. ハンドルを保持したまま、元への競合する書込/DELETE openが共有違反で拒否されることを確認する。rootと両ハンドルのidentity/sizeも再確認する。
6. 同じ元ハンドルへSetFileInformationByHandle / FileDispositionInfoを指定し、そのハンドルを閉じる。保存先ハンドルは、除去結果の観測と結果記録まで保持する。
7. 自作root内の元名について、正常な不在を観測できた場合と、delete pendingなどで未確認の場合を区別し、別ファイル`result.json`へ記録する。削除後の記録失敗は結果不明とし、元削除を繰り返さない。

Microsoftの[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)と[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle)を根拠にした候補である。GitHubの[Microsoft STL実装](https://github.com/microsoft/STL/blob/main/stl/src/filesystem.cpp)も比較し、拡張削除フラグを使う方式と従来のFileDispositionInfoを調べた。今回はread-only属性の無視やPOSIX削除を導入せず、単一ハンドルでの基本操作とpendingの区別を先に確認する。コードの転載や外部依存の追加はない。

## 結果不明と照合記録

別の読取ハンドルがDELETE共有を許可して開いている場合、削除指定が成功しても、その読取ハンドルを閉じるまで除去が完了しないことを確認する。API成功だけで移動完了にせず、`delete_pending`として記録する。

同じprobeインスタンス内で、元の不在、現在の同じ保存先の内容、保存済みの準備記録bytesがすべて一致すれば照合完了を返す。照合結果は別の`reconciled.json`へ準備記録のSHA-256とともに保存する。旧`result.json`を成功へ書き換えず、再照合でも同じファイルを上書きしない。元の再作成、保存先変更・差替え、記録欠落・改変は完了にしない。

probeは元の基準情報と準備記録bytesをメモリにも保持する。別プロセスからの再開や、信用できない記録をロードするvalidatorを提供していない。従って、ディスク上の記録を使う流れの確認ではあるが、実装計画の新しい永続記録契約やクラッシュ回復を完了したものではない。

## 検証結果と残る限界

ローカルのPython 3.11.9/Windowsで9試験が成功した（skipなし）。CIはPython 3.12のWindows jobへ接続したが、新ブランチのリモート実行は未実施。通常・空内容・複数chunk、元/保存先変更・同内容差替え、既存writer、競合open、記録失敗、別readerによるpending、結果記録欠落後の照合、record改変、hardlink、marker変更、指定外path拒否を確認した。

最初のsandbox内実行は、置換とhardlink作成がWinError 5となった。試験を省略せず、同じ自作一時領域限定の試験をsandbox外で実行する。検証の成功は実運用予定root/volumeでの成立を意味しない。

本方式はまだ正式providerとして採用していない。既存の書込可能memory mapping、祖先/名前空間の攻撃的変更、実効ACL、対象FS差、電源断、close/記録結果不明、別プロセス回復を解決済みとはしない。実Drive上の保存先をローカル合成保存先で代用できるとも扱わない。通常移動へ接続する前に、これらの保証・拒否条件と永続記録契約を閉じる。

Driveの[files.delete](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/delete)の公開パラメーターからは期待version指定を確認できず、[404仕様](https://developers.google.com/workspace/drive/api/guides/handle-errors)は不在と権限不足の両方を含む。今回の再確認でも条件付き削除の保証は得ていない。「非対応」と断定せず、未確認時は削除・照合完了へ進めない方針を維持する。実API試行、OAuth/scopeの変更、cloud元削除は行わない。
