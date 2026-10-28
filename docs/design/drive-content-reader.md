# Drive内容の取得・ハッシュ・版再確認

更新日: 2026-10-29。[metadata読取](drive-metadata-reader.md)へ、[DriveContentReader.py](../../Common/DriveContentReader.py)の内容確認を接続した。T0/T2/T3の読取側の部分実装で、正式な移動・保存・元削除は提供しない。

その後、[所有された隔離stagingへの保存](sdk-download-staging.md)をtests内へ接続した。SDK転送の内部処理を共用し、保存側が渡すverifierを転送/hash確認後・cloud metadata再取得前に呼ぶ。API hash不一致が既知なら追加のmetadata要求より前に停止する。公開hash入口は引き続きファイルを作らず、内部sinkを渡すことも実root資格にはしない。

## 処理の順序

`read_drive_content_hash`は呼出し側の公式Drive v3 service、期待folder/file ID、明示的なchunk_size、任意の最大download bytesを受け取る。認証情報を探索・保存せず、ファイルパスも受け取らない。

1. 既存readerでID/親/名前/size/version/任意hashと`capabilities.canDownload=true`を確認する。最大bytesを超える場合はmedia要求前に拒否する。
2. 同じIDにget_media要求を作り、公式SDKのMediaIoBaseDownloadでchunkを取得する。bytesは専用sinkからSHA-256へ渡し、内容を保持したり、ディスクへ保存したりしない。
3. HTTP Rangeの開始/終了/総size、実byte数、任意Content-Length、取得先の継続を確認してからSDKへ渡す。空の非終端chunk・途中の全体応答・異なるContent-Location・errorは拒否し、部分的なhash結果を返さない。
4. SDKの完了と総byte数一致を確認した後、metadataをもう一度取得する。ID/名前/親/版/size/任意hashの変化、取得権限の確認不能、実内容とAPI hashの不一致なら拒否する。
5. 確認したfile ID/version/size/SHA-256だけを返す。元/保存先の削除許可や、クラウド元がその後も不変である保証にはしない。

空ファイルは200の空応答、またはmetadata size=0と一致する416/`bytes */0`を受け、後続metadataも一致した場合だけ空内容として扱う。416のerror bodyは内容としてhashせず、SDKの診断へも渡さない。非空ファイルの416やsize不明を空と推測しない。

HTTP非2xxの生のerror bodyはSDKのretry診断より前に拒否する。SDK追加再試行は0、失敗は固定の`drive_content_unconfirmed`だけを返す。サービス/timeout/接続close・認証層のrefresh・ログ設定は呼出し側の責任として残す。SDK/HTTPが応答bodyを先にメモリへ展開する可能性があり、chunk_sizeや最大bytesの検査をtransport全体のメモリ上限とはしない。

## 既存比較との接続

`DownloadHashObservation`へ任意のversionを追加した。このreaderの結果は必ず版を持ち、既存の直接比較・plan付き比較は、一覧の版と異なるdownload hashを拒否する。API hashがない場合でも、実download/hashを不足hash計画へ渡せる。

旧純粋helperのversion=None入力は互換性のため維持する。Noneは版の確認済みという意味ではなく、旧helperを正式providerの観測として採用する許可も追加しない。比較結果の操作許可flagはfalseのまま。metadataの前後一致は、観測間の変更/復元や条件付き削除の原子性を証明しない。

## 比較した方式と検証

[Google公式download sample](https://github.com/googleworkspace/python-samples/blob/main/drive/snippets/drive-v3/file_snippet/download_file.py)のMediaIoBaseDownloadと、[rcloneの読取](https://github.com/rclone/rclone/blob/master/backend/drive/drive.go)を比較した。公式SDKを再利用し、sampleのBytesIOへの全内容保持・print・既定認証探索は取り込まず、hash sinkと前後metadata確認へ置き換えた。API上の根拠は[download説明](https://developers.google.com/workspace/drive/api/guides/manage-downloads)と[公式SDK実装](https://github.com/googleapis/google-api-python-client/blob/main/googleapiclient/http.py)。SDKがRangeの開始位置全体を検証するとは仮定せず、応答を受け入れる境界で確認する。コード転載・追加依存はない。

[8試験](../../tests/test_drive_content_reader.py)で公式SDKのHTTP応答だけを合成し、分割取得、空ファイル、metadata変更、取得可否、上限、不正Range/長さ/継続先、途中失敗、内容hash不一致を確認した。API hashなしの取得を既存plan/比較まで接続し、別版のhashを再利用できないことも確認した。

新規8・関連9群97試験と役割別package回帰が成功。ローカルSDK2.201.0、Python3.11.9（CI定義3.12）、PowerShell7.6.7。SDKは前回用意した専用一時領域の依存を再利用した。実Drive通信、リモートCI、独立レビュー、実環境受け入れは未実施。実ファイルへのdownload保存、upload、元削除、service資格、正式入口、T0/T1/T4/AC全体は未完のまま。
