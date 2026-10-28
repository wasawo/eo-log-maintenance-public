# Drive一覧・メタデータの公式クライアント接続

更新日: 2026-10-29。[移動設計](log-move-design.md)のクラウド対象確認へ向け、[DriveMetadataReader.py](../../Common/DriveMetadataReader.py)を追加した。T0/T2/T3の読取部分であり、正式Sync/Archive入口や両経路の完成ではない。

## 呼出しと対象

呼出し側が用意したGoogle公式PythonクライアントのDrive v3 serviceを受け取る。認証情報の探索・保存、OAuth画面、既定accountの取得、service生成は行わない。実運用のaccount・drive.fileによる対象folderの資格確認は別途必要となる。引数のfolder IDは観測の比較対象であり、実行許可ではない。

- `read_drive_listing`: 指定folderのmetadataを確認し、その直下の全pageを取得して既存の`DriveListingObservation`へ渡す。再帰的なログ選択は行わない。
- `read_drive_file_metadata`: 指定IDのmetadataを取得する。期待ID・親folderが異なれば拒否し、名前が同じ別IDへ切り替えない。

両関数はGETだけを使う。upload/download、ローカル保存、クラウド削除、共有/ACL変更、CLI、C-02結果の生成は提供しない。認証・timeout・接続のcloseは呼出し側が所有する。第三者クライアントや認証層全体のログ/refresh動作は、正式なservice生成時に確認する。

## 確認する情報

folderは期待ID・folder MIME・非ごみ箱を確認する。ファイルはID/name/parent/trashed/MIME/size/versionを確認し、実際に返されたSHA-256だけを利用する。sizeとversionはDriveのint64文字列として扱い、未知の値をゼロなどへ補完しない。hashがない場合はNoneのまま、既存比較のdownload確認へ残す。Google Workspace文書、shortcut、子folderは未対応として拒否し、黙って除外して列挙完了としない。古い階層内のログへの対応は正式列挙の残件である。

APIの`nextPageToken`がある限り、空のpageでも続ける。途中失敗、`incompleteSearch=true`、token循環、重複ID、任意の上限超過では部分結果を返さない。終了pageまで取得できた場合だけ既存のpage検証へ渡す。APIの省略可能な空filesとfalseのincompleteSearchは、それぞれ空リスト・falseとして扱う。

`DriveFileObservation`へ任意のversionを追加した。従来の純粋helper入力はNoneのまま使えるが、このreaderはversionを必須とする。前後の一覧でversionが変われば、ID/内容hashが同じでも既存比較は保留する。versionは観測された変更の検出用であり、削除の前提条件としてDriveへ渡せると確認したものではない。既存の比較結果の操作許可flagもfalseのまま維持する。

SDKの追加再試行は`num_retries=0`とする。非2xxはSDKのretry診断へ生のerror bodyを渡す前に拒否する。失敗は固定の`drive_metadata_unconfirmed`だけを返し、生の例外を表示する入口は作らない。認証層の再送・refreshや実環境のnetwork動作を、この設定だけで検証済みとはしない。

## 比較した実装とAPI資料

[Google公式sample](https://github.com/googleworkspace/python-samples/blob/main/drive/snippets/drive-v3/file_snippet/search_file.py)の明示的なfieldsとpage tokenループを、[rclone](https://github.com/rclone/rclone/blob/master/backend/drive/drive.go)の一覧取得と比較した。公式SDKを使う既存方針を維持し、空pageで打ち切らず、完全取得後に既存比較へ渡す方式とした。sampleの既定認証探索やprint、rcloneの広い機能集合は取り込んでいない。コード転載はない。

根拠は[files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list)、[File resource](https://developers.google.com/workspace/drive/api/reference/rest/v3/files)、[公式Pythonクライアント](https://github.com/googleapis/google-api-python-client)。[files.delete](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/delete)の公開引数にはversion条件を指定する項目がなく、任意のHTTP条件が利用可能とも確認していないため、cloud元削除の契約は未確定のまま残す。版情報を取得できることから条件付き削除へ進まない。

## 試験と残件

[10試験](../../tests/test_drive_metadata_reader.py)は公式SDKの同梱Discoveryを使い、HTTP応答だけを合成する。認証情報と実ネットワークを使わず、生成されたURL/query/fields、空の中間page、完全列挙、metadata拒否、error、ログへのerror body漏れ防止、既存比較への接続、version変更を確認した。SDKを丸ごとmockする試験ではない。

依存関係は`requirements-runtime.txt`の`google-api-python-client>=2,<3`へ追加し、試験側も同じruntime依存を参照する。ローカル確認版は2.201.0で、作業専用の一時領域へ導入した。ローカルPython3.11.9（CI定義3.12）、PowerShell7.6.7。SDK依存からPython3.11の将来のサポート終了予告が出たが、現時点の試験は成功した。

新規10試験、関連8群87試験、役割別package回帰が成功した。実Driveのaccount/権限・保存先の継続的な保護・再帰列挙・真正な内容download・upload・版固定削除・正式入口は未完。実Drive通信、リモートCI、独立レビュー、実環境受け入れは実施していない。配布拒否ガードとT0/T1/T4/AC全体の未完を維持する。
