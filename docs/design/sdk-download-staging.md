# SDK取得から所有された隔離ステージングへの接続

更新日: 2026-10-29。[SDKの内容読取](drive-content-reader.md)を、既存の[隔離staging fixture](../../tests/download_staging_fixture.py)へ接続した。実装は[SdkDownloadStagingFixture](../../tests/sdk_download_staging_fixture.py)で、tests専用である。実運用rootや任意の保存pathを受け付けるfactoryは追加しない。

## 処理と保存の範囲

既存fixtureが自作するOS-temp直下のroot・nonce markerだけを使う。同じプロセスで既存の所有mutex/token記録を保持し、試行ごとに新しいdirectoryと`download.bin`を作る。作成はxbで行い、占有済みの名前を上書きしない。root/祖先chain/所有tokenは書込みと検証の境界で確認する。

SDK転送はCommonの内部`_read_drive_content`へまとめ、公開`read_drive_content_hash`も同じ処理を使う。SDKの取得・Range確認・hash・版再確認をfixture側で再実装しない。公開hash入口は従来どおりメモリ内のhashだけを返し、ファイルは作らない。内部sink/verifierを渡せることは、実rootの資格や保存の認可ではない。

保存接続の順序は次のとおり。

1. コピー対象のfile IDと期待sizeを既存のdownload requirementから受け取る。確認・保存対象はfixtureが作る試行だけとする。
2. SDKが確認したchunkを実ファイルへ書く。期待size超過、短い書込み、書込失敗は元のHTTP処理へ伝わり、結果を返さない。
3. SDK転送の完了・hash確認後、flush/fsyncを行い、開いたfileのsignatureを記録して閉じる。API hash不一致が既知の場合はこの先へ進まない。
4. root/所有を確認し、単一リンクの通常file・実体signatureを確認して実bytesを読戻す。size/hashをSDK取得結果と照合する。
5. Commonがcloud元のmetadataを再取得する。版・対象・内容等が変わっていたら、保存済みfileを残して結果を返さない。
6. このHTTP待機後にもstagingの実体と内容を読み直し、所有/現在fileの対応が成立した場合だけ版付きhash観測を返す。

失敗した部分fileや、内容が保存済みでも元が変更された試行は保持する。通常の再試行は別の新規directoryを作り、古い試行を再利用・上書き・自動削除しない。占有名、改変された所有記録も保持する。試験終了時のcleanupは、nonce/root実体を確認した自作fixture全体だけを明示的に破棄する操作で、runtime回復やlock解除ではない。

## 検証と残る限界

[8試験](../../tests/test_sdk_download_staging.py)で、公式SDK＋合成HTTPからの実保存、API hashなしの一覧/plan/比較接続、中断・版変更と新規再試行、占有名、短い書込み・disk-full・flush失敗、保存後/metadata待機中の改変、所有喪失、空file/期待size不一致を確認した。I/O故障は実fileを開いた小さなstream proxyで注入し、SDKと本体の転送処理は実物を使う。実際のvolume枯渇を再現したものではない。

既存SDK/hash/比較/plan/旧stagingの関連10群105試験と役割別package回帰も成功した。ローカルSDK2.201.0、Python3.11.9（CI定義3.12）、PowerShell7.6.7。既存のSDK用一時依存と、承認されたsandbox外の自作合成一時領域を使い、実Drive・実ログ・実設定は使用していない。

streamとfileの扱いは既存fixtureのxb/flush/fsync/close/読戻しを再利用し、SDKは前回のGoogle公式sampleとrcloneの比較に基づく共通転送を使う。全bytesをメモリへ集めるpublish_bytes_no_overwriteはこのchunk保存には使わず、ready状態や最終archive先の公開を実装したものとも扱わない。新たな依存・コード転載はない。

実root/ACL/FSの資格、metadata-firstの永続記録、容量の使用点判定、任意の並行変更からの保護、電源断、認証service、正式download/移動入口、元削除は未完。結果は比較用の観測であり、削除許可やready状態ではない。実環境検証、リモートCI、独立レビューも未実施。T0/T1/T4/AC全体の未完と配布拒否ガードを維持する。
