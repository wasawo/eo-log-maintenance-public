# Drive一覧・メタデータの公式クライアント接続

更新日: 2026-10-29。[移動設計](log-move-design.md)のクラウド対象確認へ向け、[DriveMetadataReader.py](../../Common/DriveMetadataReader.py)を追加した。T0/T2/T3の読取部分であり、正式Sync/Archive入口や両経路の完成ではない。

その後、別moduleへ[内容取得・ハッシュ・版再確認](drive-content-reader.md)を接続した。metadataの`require_download=true`では、要求fieldsにcapabilities.canDownloadも追加し、trueを確認できなければ拒否する。既存の通常metadata読取はこの追加条件を必須にしない。

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

初回接続時は新規10試験、関連8群87試験、役割別package回帰が成功した。内容確認の追加結果は上記の別仕様を参照。実Driveのaccount/権限・保存先の継続的な保護・再帰列挙・download保存・upload・版固定削除・正式入口は未完。実Drive通信、リモートCI、独立レビュー、実環境受け入れは実施していない。配布拒否ガードとT0/T1/T4/AC全体の未完を維持する。

## S3 実Drive結合試験の限定計画（未承認・未実施）

[current-sliceの条件③④](../development/current-slice.md)を実証するための実行前チェックリスト。本節の作成・PR/mergeは、認証、consent、credential読取/更新、実APIアクセスの許可ではない。方式の根拠は[採用済み回答](../archive/decisions/selected-policy-decisions-20261024.md)と[OSD-05の未完事項](../requirements/p0-open-specification-decisions.md)。正式AC・P0・削除条件を変更しない。

### 現在利用できる機能と実行前の不足

- metadata/list/content readerと[転送adapter](../../Common/DriveTransferAdapter.py)は、呼出し側が明示的に渡す公式Drive v3 serviceを利用できる。新規uploadは1試行、既存同内容は再利用、異内容/複数候補/確認不能は保留する。転送adapterのbytes上限は4 MiB。
- 正式Sync/Archive入口は合成root専用で、`-DriveApiMock`はtests専用HTTP workerに固定される。追加承認された実装は別の `-IsolatedDrive -ConnectionConfig <非公開設定>` から明示runnerへ接続する。このmodeも固定の合成root/marker/期間/元保持を維持する。既存の模擬workerへ実ID/tokenを渡したり、隔離ガードを外したりしない。
- 認証store/service/runnerは後述の合成検証済み部分実装を利用できる。実consent・初回保管・両PCのWindows保護/refresh/資格・実API接続は未実施で、実行には別の明示承認が必要。SDKやコードの存在だけで認証可能・S3完了とはいえない。
- PowerShellは7.6.7、PythonはCIの3.12を基準とし、既存`requirements-runtime.txt`の依存を用いる。実施時は明示したinterpreterとSDK版を確認し、未設定の`python` shimや過去の一時依存を暗黙に利用しない。認証情報・環境変数・実設定を列挙して前提を調べない。

### 利用者が非公開で用意・確認する前提

1. 両PCで同じGoogle principal、Desktop user OAuth、`drive.file`、各PCの承認実行Windows userに結び付く暗号化保存という採用済み方針を維持する。PC間でtokenをコピーしない。OAuthアプリ登録の同一性、consent対象/許可scope、各PCでの初回認証・refresh/store更新の扱いを確定し、それらの操作は個別に承認する。service account、平文token、自動scope拡大へ切り替えない。
2. 本番から独立したMy Driveの試験領域と、BattleLog/ErrorReportの平坦な専用folderを指定する。folder作成・共有変更・アプリへの対象選択/認可を含む利用者の準備も、本計画から実施済み・許可済みとはしない。実ID/path/mail/client/tokenは追跡file・PR・通常ログに書かず、承認対象との対応を非公開で管理する。
3. Drive画面等でowner・共有/継承/limited-access・使用可能容量を利用者が確認する。PC-A/Bの独立したローカル合成元・download領域にも空き容量と書込権限が必要。容量不明、scopeの対象不明、未知の同名file、第三者の同時操作がある場合は開始しない。既存readerはowner/quotaやfolderのcreate能力を観測しておらず、列挙成功からこれらを推定しない。
4. 各PC・各ログ種別1件、計4件、各4 KiB以下の固定合成bytesと異なる承認済み形式の名前を用意する。新規upload上限4件/合計16 KiB、既存fileの更新・上書き・改名・移動・削除は0件。可視性比較用に、consent前からある合成fileと未認可の合成fileを各1件、各4 KiB以下で区別する（準備分を含むcloud合成bytes上限24 KiB）。未知の既存データをfixtureとして流用しない。

### 承認後にCodexが実施する順序（現在は実行不可）

認証/store/service/runnerの未完を解消し、対象・操作・制限・非公開証拠の保存先を明示した利用者承認が揃ってから実行する。実APIは指定folder直下の`files.list`、指定folder/fileのmetadata `files.get`、新規bytesの`files.create`、指定fileの`files.get`によるmedia取得だけに限定する。`about.get`、permissions API、全Drive探索、folder作成、共有/owner/ACL変更、delete/update/trash/copy APIは含めない。容量・所有の事前情報は利用者の非公開確認とし、追加APIが必要なら別途提案して停止する。

| 順序 | 操作・期待する結果 | 続行できない場合 |
| --- | --- | --- |
| 1 | PC-A/Bのprincipal・OAuthアプリ・scope・保護store資格と、承認されたroot/fixture一覧を非公開で照合。必要なfolder metadataと全pageの一覧だけを読み取る | 認証/権限/対象が未確認ならuploadせず停止。見えないfileを不在と扱わない |
| 2 | 既知のconsent前/未認可合成fileの可視性を期待一覧と照合。両PCの可視範囲を分けて記録 | `drive.file`の適合が不明・不足なら停止。scopeや共有を自動修復しない |
| 3 | 各PCから各種別1件を新規uploadし、返されたIDのparent/name/size/versionを確認。内容をdownloadして元bytesのSHA-256と照合し、再列挙で同名候補一意を確認 | hash/版/親/名前の不一致・複数候補・部分列挙なら保留。新規uploadを追加しない |
| 4 | PC-AがPC-B作成分を、PC-BがPC-A作成分を列挙・取得・照合。同じprincipalでもPC間可視性は実証する | 片方だけ成功なら③④の合格としない。PC-Bでarchiveを呼ばない |
| 5 | 同じ名前/bytesを再度照合し同じIDを再利用。次に同名の異なるローカル合成bytesで照合し、競合保留・既存ID/内容の不変・元保持を確認 | 同名異内容でPOST/上書き/改名が生じたら即停止。競合fixtureのための追加cloud作成はしない |
| 6 | 承認download領域への保存・hashとPC-A側経路を、資格確認済みrunnerが提供する範囲で検証 | `download_bytes`から既存Archive書込/hashへ接続する。模擬通信での共有経路成功を実接続/正式AC成功にしない |

列挙は既存上限100 pages/4096 files以内、今回の転送は各4 KiB以下。大量データで上限を試さない。実試験のtimeout案はHTTP要求30秒、操作を扱う子process120秒、試験全体10分とし、超過時は停止・結果不明を維持する。実施runnerにはこの有限timeoutと、認証transportを含む暗黙再送の抑止の確認が必要（現行bridgeの30秒だけでlive transportが認定されたとはしない）。未実装/未合意なら開始しない。Dry Runはlive接続資格の代用にせず、認証・API・downloadを呼ばない。

### 停止・元保持・後処理

- 認証失敗、401/403、quota不足、429/5xx、timeout、通信断、不正/不完全応答、同名複数、hash/版変更、対象外IDや想定外の操作要求で、その実試験を停止する。既存の模擬fault試験を基本証拠とし、実権限剥奪・token失効・容量枯渇・通信切断・強制終了を誘発する試験は本計画に含めない。実環境で自然発生した失敗と模擬検証を区別する。
- POST開始後の応答不明や途中中断は「未作成」や「成功」としない。自動再送・自動再開しない。ローカル元、download途中物、cloudの作成候補は保持し、非公開の要求/対象対応と状態を残す。次回は別途承認された読取照合で完全列挙・候補一意性・内容一致を確認してから続行判断する。不在/一意性が確認不能なら再uploadしない。
- 正常・競合・失敗のすべてでローカル元とcloud元を保持する。APIエラーの生body、header、token、実ID/path/mailは公開しない。公開報告は匿名化したfixture番号、件数、結果と未検証条件に限定し、詳細証拠は事前承認した非公開保存先のみで扱う。
- 後処理は自動化しない。cloud fixture、ローカル合成元、download/途中物、非公開証拠を残し、利用者へ対応表を非公開で引き渡す。利用者が別途明示する保持期間・確認済み対象・手動後処理の指示を待つ。成功したことや試験終了だけを削除許可にしない。token失効/store消去も自動で行わない。

③は両PCの認証/store・principal・可視性/所有/容量・root資格の証拠、④は承認範囲内の実API結合結果で判断する。未完のproviderやlive正式入口を計画文書だけで完成扱いにしない。合成/API模擬の既存成功、実接続試験、正式ACを分け、S3は証拠が揃うまで未完、S4は未着手とする。

公開資料の根拠: [drive.fileの対象範囲](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)、[File metadataとcapabilities](https://developers.google.com/workspace/drive/api/reference/rest/v3/files)。folder IDや同一principalのみでは可視性・実能力の証明にならないため、上記の事前確認とPC間照合を置く。

### 認証store・service・接続runnerの実装境界

[DriveCredentialStore](../../Common/DriveCredentialStore.py)はWindows current-user DPAPI（UI禁止、machine-wide flagなし）と、現userだけの明示protected DACLで暗号化fileを扱う。既存のACL profile判定を再利用し、repo外の明示directoryだけを許可する。directoryは自動探索/自動修復せず、reparse/UNC/不明ACLを拒否。明示的な初期保管は`transaction()`内の`save(record, initial=True)`、更新は既存fileの検証と排他的lease、暗号化一時fileのflush/fsync・復号read-back後の置換とする。初期公開はno-replace。失敗時は旧storeを維持し、暗号化pending/lockを自動削除しない。暗号化中のPythonメモリ全体の消去、敵対的なprivileged process、電源断耐久性、他user/両PCの実資格は保証しない。

[DriveAuthentication](../../Common/DriveAuthentication.py)の`DesktopAuthorization`はPKCE S256/state・loopback redirect・単回code交換を結ぶlibraryで、browserやlistenerを自動起動しない。操作者によるprincipal確認は必須だが、設定の`principal_verified`だけでtokenのGoogle identityが証明されたとはしない。実認証時の確認記録は条件③の残件。`create_service`は明示storeのprincipal/client/scopeを照合し、期限が近い場合は`allow_refresh`がtrueのときだけtoken endpointへ1試行し、scope確認・保護store保存が成功してからserviceを返す。失敗時はDrive要求へ進まない。Drive transportは期限/401でrefresh・再送せず、HTTP30秒、redirect/環境proxy/既定認証なし、応答上限64 KiBで停止する。認証code/token/header/error bodyを公開しない。

[IsolatedDriveRunner](../../Common/IsolatedDriveRunner.py)は保護ACL付きのrepo外JSON設定をstdin経由の明示pathだけから読み、未知/重複field、未承認flag、scope/root/role不一致をcredential読取前に拒否する。必須keyは`version=1`、`mode=isolated_drive`、`machine_id`、`principal`、`client_id`、`scope`、`folders`（BattleLog/ErrorReportの別ID）、`store_directory`、`fixture_root`、`upload_names`（種別ごと最大1件）、`required_visible`（種別ごと最大6件）、`principal_verified`、`environment_verified`、`allow_refresh`、`execution_approved`。実値をrepoや引数例に埋め込まない。flagは実行前の操作者確認を表す条件であり、利用者の作業許可を自動生成しない。

呼出しは既存正式入口の `-Synthetic -SyntheticRoot <隔離fixture> -IsolatedDrive -ConnectionConfig <非公開設定> -PythonExecutable <明示Python>`。既存S1/S2 fixture/markerを残し、Syncは承認済みの各PC→cloudに合わせ両PC、ArchiveはPC-Aだけ。PC-B拒否は認証より前。mock flagとの併用は拒否し、既存のfilesystem/API模擬modeを変えない。Dry Runは設定/store/Python/APIに触れない。workerの上限は120秒、経路全体の残り10分内で打ち切る。通常IPC1.0/schemaや配布拒否は変更しない。

runnerは明示folder/許可名/required-visibleを確認して既存adapterを呼ぶ。未知/欠落候補・同名複数・API失敗で停止し、uploadは種別ごと許可名1件・各4 KiBのみ。同内容再利用/異内容保留は既存処理を維持する。POST前の意図をprivate storeにflushし、成功/既知の競合結果だけ確認済み記録を追記する。応答不明・強制終了後に未確定意図が残れば、次回はAPI前に停止し、自動再uploadしない。解除/読取照合の専用手順は未実装で、別途承認された診断・判断が必要。両PC合計4件/16 KiBの実試験予算は操作者の限定計画でも管理し、PC間のglobal quota機構を追加したとはしない。保留時も元/途中物/cloudを消さない。

根拠: [Microsoft DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)、[Google Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app)、[公式Credentials](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html)。初回consentと安全なcallback受領、実principal/scope・所有/容量/可視性、両PC store/ACL/失効/復旧の実資格と本計画の実行承認は未完。新機能を実credentialに対して実行しない。
