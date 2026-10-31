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

### PC-A/Bのセットアップ順序とコマンド（準備資料・未実行）

以下は将来の承認後に操作者が使用する手順で、今回の文書変更から実行許可を得ない。初回登録/保護設定/Desktop Picker支援は下記のS3③-A手順を使う。実環境の資格・操作承認は別に必要であり、コマンドの成功だけでS3③④は完了しない。すべての値はダミーまたは私的な変数とし、実値をこの文書・チャット・PR・シェル引数の直書きへ移さない。

#### 1. 両PCのローカル前提

PowerShellの許容集合は7.6.7と7.6.9の2版のみ。7.6系列すべてや将来patchを無条件に許容せず、7.6.8/7.6.10以降・previewは未検証として停止する。`#requires -Version 7.6.7`は最低版宣言であり、実際の許容集合は共通guardで検証する。CIは両版の公式ZIPをSHA-256照合し、版を厳密に確認して同じ検査を行う。下記のローカル依存環境構築は再開できるが、OAuth/credential/Driveの操作許可は増えない。

各PC内で承認済みのWindows userとしてログオンし、同じuserで準備・手動起動する。PC間のWindows user一致やtokenコピーは要求しない。リポジトリの確認済みmainを使い、公開用packageの配布拒否を解除しない。PowerShellは検証済みの7.6.7または7.6.9、Pythonは3.12系、venv/store/非公開設定はrepo・共有Drive・同期領域の外の明示領域とする。reparse/UNC・不明ACLの領域は使わない。

将来、各PCの非記録端末で実行するローカル依存準備の例（この作業では実行しない）。`py -3.12`がなければ停止し、Python/launcherの導入を利用者側で準備する。`$Repo`は確認済みcheckout、`$Venv`は新規のrepo外venvを非公開で指定する。既存の不明な環境を自動探索/上書きしない。

```powershell
$Repo = Read-Host -MaskInput '確認済みcheckoutの絶対パス'
$Venv = Read-Host -MaskInput '新規のrepo外venvの絶対パス'
Set-Location -LiteralPath $Repo
. (Join-Path $Repo 'Common/LogFunctions.ps1')
Assert-SupportedPowerShellVersion
py -3.12 --version
if ($LASTEXITCODE -ne 0) { throw 'python_unavailable' }
if (Test-Path -LiteralPath $Venv) { throw 'new_environment_required' }
py -3.12 -m venv $Venv
if ($LASTEXITCODE -ne 0) { throw 'venv_setup_failed' }
$Python = Join-Path $Venv 'Scripts/python.exe'
& $Python -B -m pip install --quiet -r requirements-runtime.txt
if ($LASTEXITCODE -ne 0) { throw 'dependencies_unconfirmed' }
& $Python -B -c "import sys,importlib.metadata as m; print(sys.version.split()[0]); print(m.version('google-api-python-client')); print(m.version('google-auth'))"
if ($LASTEXITCODE -ne 0) { throw 'dependencies_unconfirmed' }
```

この準備は認証情報を必要としない。`PYTHONPATH`に過去の一時依存を追加する方法を実環境手順にしない。版だけを公開できる記録とし、pipのerrorや絶対pathをそのまま共有ログへ保存しない。

#### 2. Google側の準備と初回登録の停止点

| 順序 | 利用者が非公開で準備・確認する内容 | 既存実装と停止点 |
| --- | --- | --- |
| Cloud設定 | 試験用projectでGoogle Drive APIとGoogle Picker APIを有効化（別途承認後）。Google Auth platformのアプリ情報/Audience/Data Accessを設定し、OAuth client種類はDesktop app。同じproject/アプリ/client IDを両PCで使用 | API有効化・アプリ登録・client情報取得を行うCLIはない。現taskではConsoleにもアクセスしない |
| principal/scope | 両PCで同じGoogle accountを使い、要求scopeは `https://www.googleapis.com/auth/drive.file` のみ。外部アプリのTestingの場合は該当accountをtest userへ追加。追加scopeは選ばない | account chooser/consent画面で利用者がaccountとscopeを確認し、非公開に証拠を残す。`login_hint`や設定のprincipal文字列だけでは本人性の証明にならない |
| client/store | Desktop clientの情報をrepo/package/共有領域へ置かず、各PC専用の保護領域で扱う。Windows user-bound暗号化、current-userのprotected ACL、別PCへのtoken非コピーを維持 | `WindowsProtection.create_directory`、`CredentialStore.validate`、`transaction`/`save(..., initial=True)`はlibraryとしてある。初期設定/登録は後述の`Common.DriveSetup`の明示CLIを使う |
| consent/callback | 各PCで別々に初回consentを行い、`http://127.0.0.1:<明示port>/<path>`で受領。通常のnon-interactive実行中にloginを開始しない | `DesktopAuthorization`はPKCE/state付きURL生成とcode交換を行う。`Common.DriveSetup enroll`がbrowser・単回loopback・選択ID照合・初期保管を結ぶ。実操作は別途承認まで停止する |
| token保存 | 承認後の登録支援でcode交換結果をメモリからDPAPI storeへ渡す。token JSONを手作業で端末/ファイル/チャットへ貼らない | `exchange`後にrecord検証→storeの排他transaction→`save(record, initial=True)`。store名は`credential.bin`。このAPI順序を`Common.DriveSetup enroll`が再利用し、既存credentialがあれば読取/交換前に拒否する |
| refresh | 初回試験は`allow_refresh=false`。refresh試験を承認した段階だけtrueとし、期限が近いtokenの更新と保存を確認する | `create_service`は残り300秒以下で明示refreshを1回試行し、scope確認・保護保存後にserviceを返す。false/失敗/保存失敗は停止。Drive要求中の401/期限切れは再認証・自動再送しない |

token発行/失効の条件はGoogle側にも依存し、Testing等の設定を恒久的なrefresh資格とみなさない。refreshが必要なら、OAuth token endpointへの接続とstore更新をDrive読取許可と分けて承認する。Windows保護storeを作成してもGoogleへの認証は行われない。API/client/scopeの準備根拠: [Google初期設定](https://developers.google.com/workspace/guides/configure-oauth-consent)、[Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app)、[tokenの失効条件](https://developers.google.com/identity/protocols/oauth2#expiration)。

#### 3. 非公開設定の全項目とPC別の差

以下は構造確認用のPC-B Syncのダミーであり、そのまま実行する設定ではない。16 KiB以内のUTF-8 JSON、未知/重複keyなし、ファイルのprotected ACLが必要。`client_secret`/access token/refresh tokenは接続JSONに追加できない（DPAPI record側だけ）。principal/client IDと2つのfolder IDは両PCで同じ実値へ私的に置換する。owner/容量/可視性はJSONから自動取得されない。

```json
{
  "version": 1,
  "mode": "isolated_drive",
  "machine_id": "PC-B",
  "principal": "DUMMY_GOOGLE_PRINCIPAL",
  "client_id": "DUMMY_DESKTOP_CLIENT_ID",
  "scope": "https://www.googleapis.com/auth/drive.file",
  "folders": {"BattleLog": "DUMMY_BATTLE_FOLDER", "ErrorReport": "DUMMY_ERROR_FOLDER"},
  "store_directory": "C:\\DUMMY\\pc-b\\store",
  "fixture_root": "C:\\DUMMY\\TEMP\\eolm-s1-sync-00000000000000000000000000000000",
  "upload_names": {
    "BattleLog": ["20240101_12345678@s3-pc-b.txt"],
    "ErrorReport": ["20231231_12345678.txt"]
  },
  "required_visible": {"BattleLog": [], "ErrorReport": []},
  "principal_verified": false,
  "environment_verified": false,
  "allow_refresh": false,
  "execution_approved": false
}
```

確認flagをtrueにする行為は、新しい操作許可や実証結果を生成しない。principal確認、owner/容量/対象root等の利用者確認、当該限定実行の許可が揃ったときだけ、承認済みの非公開設定にその事実を反映する。`required_visible`が空の例を、既存fileの見落としや資格不足の回避に使わない。

| 設定 | PC-B Sync | PC-A Sync | PC-A Archive |
| --- | --- | --- | --- |
| machine/fixture | PC-B / B専用s1 root | PC-A / A専用s1 root | PC-A / 別のs2 root |
| store_directory | Bの承認Windows user専用 | Aの承認Windows user専用 | Aと同じ保護storeを使えるが実行は直列 |
| upload_names各種別 | 上記Bの2名 | Battle `20240101_12345679@s3-pc-a.txt` / Error `20231231_12345679.txt` | 両種別とも空配列。Archiveでuploadしない |
| required_visible | 初回は既存の可視性確認fixture。A upload後の再照合ではA名も追加 | 既存可視fixtureと先にuploadしたB名 | 既存可視fixtureとA/B名をすべて含める |
| fixture_root | OS-temp直下の生成済B rootと一致 | OS-temp直下の生成済A rootと一致 | OS-temp直下の生成済s2 rootと一致 |

許可名は種別ごとupload最大1件、required-visible最大6件。既存fileをrequired-visibleから省略して隠さない。列挙結果に未知名/同名複数がある場合やrequired-visibleが欠ける場合は停止する。configは後述の`Common.DriveSetup prepare`でprotected ACL付きの新規fileとして作成し、`validate`で確認する。既存fileの上書きや不明ACLの修復は行わず、平文credential入り設定やeditor保存で代用しない。

#### 4. fixture作成と正式入口のコマンド

以下も将来の承認後の利用者操作で、今回は実行しない。PowerShell 7.6.7でrepo rootから実行する。Sync部分はPC-A/Bそれぞれで、各PCの`$MachineId`を明示して使う。新しいGUID rootだけを作り、元の実ログからコピーしない。最初は空のsourceで準備し、後述の読取確認が終わるまでデータを追加しない。

```powershell
$MachineId = 'PC-B'  # PC-A側は 'PC-A'
$ReferenceDate = [datetime]'2026-10-29'  # 合成試験の固定基準日
$SyncRoot = Join-Path ([IO.Path]::GetTempPath()) ('eolm-s1-sync-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($SyncRoot)
[IO.File]::WriteAllText((Join-Path $SyncRoot '.synthetic-fixture'), 'eolm-s1-synthetic-v1')
foreach ($side in @('source','mock-drive')) {
    foreach ($kind in @('BattleLog','ErrorReport')) {
        [void][IO.Directory]::CreateDirectory((Join-Path $SyncRoot "$side/$kind"))
    }
}
$SyncConfig = Read-Host -MaskInput '準備済みの非公開Sync設定の絶対パス'
# 設定のfixture_rootはこのSyncRootを私的に反映する。実値を表示/保存ログへ出さない。
& (Join-Path $Repo 'scripts/SyncLogs.ps1') -Synthetic -SyntheticRoot $SyncRoot `
    -MachineId $MachineId -ReferenceDate $ReferenceDate -IsolatedDrive `
    -ConnectionConfig $SyncConfig -PythonExecutable $Python -DryRun
```

Dry Runはconfig/store/Python/APIを読まず、空のsourceではno_workとなる。認証・設定・可視性検証の成功を示さない。初期登録/アプリ対象認可/保護設定の不足を解消し、実credential読取・storeのlease処理・ローカルfixture操作・指定folderのDrive読取を承認した後、空のsourceかつ`allow_refresh=false`のまま同じコマンドから`-DryRun`だけを外すと、現行Syncは両folderを列挙するがupload対象は0件となる。tokenの有効期間が不足すれば停止する。列挙JSON/workerを直接実行・ログ保存せず、正式入口の匿名化結果と非公開の確認記録を使う。

両PCの読取資格を確認し、限定uploadも承認された段階でだけ、各SyncRootに次の合成元を新規作成する。1件の再作成・改変を黙って行わず、同名があれば停止する。

```powershell
$BattleName = if ($MachineId -eq 'PC-B') { '20240101_12345678@s3-pc-b.txt' } else { '20240101_12345679@s3-pc-a.txt' }
$ErrorName = if ($MachineId -eq 'PC-B') { '20231231_12345678.txt' } else { '20231231_12345679.txt' }
$BattleBytes = [Text.Encoding]::UTF8.GetBytes("s3 synthetic $MachineId BattleLog")
$ErrorBytes = [Text.Encoding]::UTF8.GetBytes("s3 synthetic $MachineId ErrorReport")
foreach ($item in @(@('BattleLog', $BattleName, $BattleBytes), @('ErrorReport', $ErrorName, $ErrorBytes))) {
    $path = Join-Path $SyncRoot ("source/" + $item[0] + '/' + $item[1])
    $stream = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $stream.Write($item[2], 0, $item[2].Length) } finally { $stream.Dispose() }
}
# 上記upload_namesと作成した名前/bytesの私的な対応確認後に限る。
& (Join-Path $Repo 'scripts/SyncLogs.ps1') -Synthetic -SyntheticRoot $SyncRoot `
    -MachineId $MachineId -ReferenceDate $ReferenceDate -IsolatedDrive `
    -ConnectionConfig $SyncConfig -PythonExecutable $Python
```

実行順序は、両PCの空source読取確認→Bの2件upload→A設定にB可視名を含めAの2件upload→B設定にA可視名を追加しBの同内容再照合→A Archiveとする。既存の可視性fixtureは全段階で保持し、設定に期待一覧を反映する。A/Bの共有folderとtoken/storeを同時操作しない。同名異内容の試験は、元を変更せず保持する別の新規ローカルfixtureを非公開設定とともに承認する必要がある。通常の同内容再実行を競合試験の代わりにしない。cloudへの追加競合file作成は行わない。

PC-Aだけで、別の空s2 rootとprotected Archive設定を準備した後のコマンド:

```powershell
$ArchiveRoot = Join-Path ([IO.Path]::GetTempPath()) ('eolm-s2-archive-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($ArchiveRoot)
[IO.File]::WriteAllText((Join-Path $ArchiveRoot '.synthetic-fixture'), 'eolm-s2-synthetic-v1')
foreach ($side in @('mock-drive','archive')) {
    foreach ($kind in @('BattleLog','ErrorReport')) {
        [void][IO.Directory]::CreateDirectory((Join-Path $ArchiveRoot "$side/$kind"))
    }
}
$ArchiveConfig = Read-Host -MaskInput '準備済みの非公開Archive設定の絶対パス'
& (Join-Path $Repo 'scripts/ArchiveLogs.ps1') -Synthetic -SyntheticRoot $ArchiveRoot `
    -MachineId PC-A -ReferenceDate $ReferenceDate -IsolatedDrive `
    -ConnectionConfig $ArchiveConfig -PythonExecutable $Python
```

`mock-drive`は既存fixture構造のための空directoryで、実Driveをmount/同期する場所ではない。内容は実API readerから取得して`archive`へ検証コピーする。PC-Bではこの操作を起動しない。上記例の2024 Battle/2023 Errorは固定基準日のSync/Archive期間条件を満たす。Archiveはcloud元を消さず、`CompletedMoveCount`は0のまま。mode/result flagだけで③④や正式ACを合格にしない。

#### 5. owner・可視性・容量・秘密保全と不足機能

- 操作者がGoogle Driveの非公開画面で同一account、My Driveの2専用folder、owner・共有/継承・limited-access例外、既存fileの全期待一覧、使用可能容量を確認する。両PCのOS-temp/archiveにも空き容量と書込権限を確認する。runnerはowner/quotaを自動照会せず、`about.get`/permissions APIも計画外。容量を枯渇させて検証しない。
- `drive.file`はアプリごとの対象資格であり、所有/ACL/folder ID/同じprincipalだけでは既存folderと全配下の可視性を保証しない。Desktop Pickerで指定した2folderを選択する導線を実装したが、readerは実際にfolder metadataと必要fileが見えるまでuploadできない。単なるDrive画面でのfolder作成/共有で解消したとは扱わず、見えなければ停止する。folder作成API・scope拡大・別アプリの認可を自動代用しない。[Googleのscope説明](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- consent前/未認可の2対照fixtureもPR #56の計画どおり非公開に追跡する。見えない対象を不在に置き換えず、required-visibleとの不一致は想定された停止として扱う。必要な全対象の資格を確認できるまでupload段階へ進めない。
- 保護store/設定/証拠はrepo/package/Drive同期外。storeは`credential.bin`と暗号化pending・lease/意図記録を保持する。copy/backup/別user/別PCの復号、失効や回復の資格は未検証で、自動cleanupしない。共有terminal/CI/Transcript/PSDebug/画面記録で実設定やcode/URL/tokenを扱わず、入力は非記録の私的な端末で行う。実値をコマンドへ埋め込まず、例外/HTTP body/credentialのprintをしない。環境変数・shell履歴・チャットでtokenを受け渡さない。
- **S3③-Aの実装と残件**: 初回登録・loopback受領・DPAPI初期保存・保護設定・指定folderのDesktop Picker選択を実装し、合成検証する。実folder/配下fileへのアプリ資格と両PCの実証は残件。principalの自動的なGoogle identity証明もなく、手動確認で残す証拠/受け入れ判断が必要。新たなscopeやidentity APIを勝手に選ばない。

次の実操作承認では、両PC・principal/client・2folder・非公開保存先を指定し、初回consent/code交換/DPAPI保存、credential読取、refresh、Drive読取、最大4件/16 KiBのupload/download/hash/競合検証を段階ごとに承認する。folder認可や共有の変更も別に範囲を明示する。合成準備分を含む24 KiB上限、非上書き/元保持、停止/結果不明/別途後処理というPR #56の制限を維持し、未承認の操作に進まない。


### S3③-A セットアップ支援の操作（準備資料・実操作未承認）

この節は両PCで将来実施する手順。今回実行するのは合成試験のみであり、実認証・保護設定の実値入力・Cloud変更・実Drive操作は開始しない。新規helperの追加理由は、既存libraryでは不足していた初回登録と保護設定の運用入口を接続するため。

1. 利用者は別途承認後に同一projectのDesktop OAuth client、Google Drive APIとGoogle Picker API、同一Google principal/test userとdrive.fileのみのconsentを準備する。Web client/API key/JavaScript Pickerや追加scopeは不要。既存folderの所有/容量と試験用対応表を私的に確認する。Pickerの実選択も別途承認対象。
2. PC-A/Bそれぞれ承認Windows user・上記venvで、隔離Sync/Archive fixtureと新規storeの既存parentを非公開に指定する。上記15項目JSONを1行で準備し、確認flagは未確認ならfalse、初回allow_refresh=false。PC-BはSync、PC-AのArchiveは既存の役割/root条件を満たす。principal/client/folderは共通、storeとfixtureはPC/経路別。
3. 次のprepareで私的な設定pathとJSONを非表示入力する。出力先はrepo外のstore直下の新規ASCII名.json。storeのleafだけをcurrent-user protected ACLで作成し、既存directoryはACLを検証する。既存file・不明ACL・設定不整合は停止し、既存credentialは一切読まない。

```powershell
& $Python -B -m Common.DriveSetup prepare
if ($LASTEXITCODE -ne 0) { throw 'setup_unconfirmed' }
& $Python -B -m Common.DriveSetup validate
if ($LASTEXITCODE -ne 0) { throw 'setup_unconfirmed' }
```

4. 実OAuth/code交換/DPAPI初期保存への明示承認が揃った段階でのみ、各PCで次を実行する。設定path/client secretは非表示入力。browserで実account・scopeと指定2folderを確認する。callback後、端末の非表示入力で実accountの確認にCONFIRMと答える。login_hintやこの確認はGoogle identityの暗号学的な証明ではなく、受け入れ記録は別に残す。既存credentialがあればbrowser/token交換前に拒否し、更新・削除・自動再登録しない。

```powershell
& $Python -B -m Common.DriveSetup enroll --execute --principal-verified
if ($LASTEXITCODE -ne 0) { throw 'enrollment_unconfirmed' }
```

Desktop URLは既存PKCE/state/drive.fileにprompt=consent、trigger_onepick=true、allow_multiple=true、allow_folder_selection=true、mimetypes=application/vnd.google-apps.folder、file_ids=指定2IDを追加する。[公式Desktop Picker](https://developers.google.com/workspace/drive/picker/guides/desktop-mobile-picker)に従い、callbackのpicked_file_idsを重複なし・指定2ID完全一致で検証する。キャンセル/不足/追加ID/不正state/未知queryはtoken交換前に停止する。127.0.0.1の動的port・ランダムpath、Host/Origin検証、最大120秒・接続2秒・単回受領を用い、callback/code/token/secretを出力しない。入力の非表示が利用できなければ停止する。共有terminal/Transcript/画面記録・browser履歴の公開は避ける。

5. 初期tokenは既存DPAPI storeへno-replace保存し、失敗時に旧credentialを変更しない。応答はstatusとgoogle_identity_verified=false/drive_visibility_verified=falseのみ。prepare/enrollは未確認flagをtrueに変更しない。両PCのprincipal/所有/容量/必要file可視性と当該実行許可を別途確認した場合だけ、事実を反映した新しい名前の保護設定をprepareで作成し、次でready条件を検証する。

```powershell
& $Python -B -m Common.DriveSetup validate --ready
if ($LASTEXITCODE -ne 0) { throw 'qualification_unconfirmed' }
```

ready検証もcredential/Driveへ接続せず、設定flagは実証の代用品ではない。実Driveの列挙/upload/download/hashは上記限定計画の正式入口から別承認後に行う。folderの選択ID取得だけで配下fileを含む可視性やS3③④を合格にしない。refresh/失効/回復・実環境資格・実API結合は未検証のまま残す。新規設定/暗号化pending/試験物の後処理は自動化しない。
