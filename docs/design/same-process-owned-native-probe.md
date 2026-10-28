# 所有mutexと実体保持を同じプロセスで行う隔離試験

更新日: 2026-10-29。[Windows削除probe](windows-move-delete-probe.md)へ既存の所有ロックを接続し、所有確認・Q5再読・記録保護・同一ハンドル削除を一つのプロセスで試験する。正式providerの採用や、PowerShellのモデル入口を実削除へ切り替える変更ではない。

## 範囲と実行

実装はtests配下の`OwnedDisposableMoveDeleteProbe`。自分で生成したOS-temp直下のroot・所有marker・合成元/保存先・journalだけを使う。利用者がroot/pathを指定する入口は追加しない。Common・配布物・実設定・実ログ・Driveには接続しない。

```powershell
python -B -m unittest discover -s tests -p "test_owned_windows_move_probe.py" -v
```

## 保持する区間

1. fixture・所有記録・journalの3ディレクトリをBACKUP_SEMANTICS/OPEN_REPARSE_POINTで開き、FILE_SHARE_DELETEを許さず処理終了まで保持する。保持不能なら弱い共有指定へ落とさず拒否する。その後、既存`acquire_owned_lock`でfixture固有scopeのGlobal mutexとtoken記録を取得する。所有と削除を別プロセスへ分けず、同じ実行スレッドで保持する。
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

2026-10-29に[5つの境界試験](../../tests/test_native_provider_boundaries.py)を追加した。CreateFileMappingW/MapViewOfFileで書込viewを作り、元のfile handleとmapping object handleを両方閉じてから、viewだけを残す。元/保存先の保護openは実Win32の共有違反32で拒否された。viewから内容を変更した場合は、view終了後の再試行でも旧コピー基準との不一致により元を残す。読取専用handleからの書込mapping作成もaccess denied 5で拒否された。

同試験では、保持した3ディレクトリのMoveFileExWによる名前変更が共有違反32になることと、先にDELETE accessを持つdirectory handleがある場合にこちらの保持を拒否することを確認した。fixtureの全祖先を保持したわけではなく、rootより上の名前空間やACLの資格は別途必要である。

[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)の共有条件、[CreateFileMappingW](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-createfilemappingw)の必要access、[MapViewOfFile](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-mapviewoffile)のview種別を根拠に、[CPythonのmapping実装](https://github.com/python/cpython/blob/19270d3bbb58c08a97bd9b481655adf42bdfbe3c/Modules/mmapmodule.c)と[libuvのdirectory open](https://github.com/libuv/libuv/blob/9d8bbff7be6298900c494f39619deab799826f30/src/win/fs.c)を比較した。高水準mmapの保持handleに依存せず、Win32で両handleのCloseを確認してからviewを試験する。コード転載や依存追加はない。

[9試験](../../tests/test_owned_windows_move_probe.py)で空/複数chunkの内容、同一ハンドル再読、別スレッドのmutex競合、元のwrite/delete open拒否、所有/準備記録の書込拒否、記録改変、所有確認不能、再読位置移動失敗、pending、所有プロセス終了前後の別プロセス照合を確認する。共有拒否のerror 32はPython CRT例外の変換値へ依存せず、Win32 APIを直接使って検査する。

これは特定の合成rootでの実OS試験であり、PowerShellモデルの別プロセス所有方式を置き換えていない。既存memory mappingによる書込み、祖先の名前空間保護、実効ACL、FS差、電源断、close失敗、実Drive保存先を解決済みとはしない。既に始まった削除要求の取消しも保証しない。正式providerへの昇格、T0/T1/T4/AC全体の受け入れ完了にはしない。

## 正式providerへ渡す前の拒否契約

以下は合意済みQ5・元保全をローカル元削除の前提へ具体化したもので、実運用の許可やqualificationの完了記録ではない。単一試行の失敗を無視して削除を繰り返す契約にもせず、通常再実行では現在の元・内容を新たに評価する。

| 境界 | 元削除へ進めない条件 | 今回の部分証拠と残件 |
| --- | --- | --- |
| rootと役割 | 実設定との対応、端末/経路、実体・祖先・ACLの資格が確認不能 | marker付き自作rootのfixtureだけを許可。任意pathのfactoryは未実装。設定値やACL profileのmatchesだけを認可にしない |
| directory保持 | root/管理領域を保持できない、reparse/実体変更を検出、必要な親の保証がない | 3ディレクトリの保持と競合拒否は確認済み。全祖先・別volume・実環境資格は未完 |
| 所有と必要記録 | mutex/token対応・記録bytes・同一プロセスの保持が確認不能 | 所有/準備記録のguardとv1記録はfixtureで確認。失効lockの勝手な回復は禁止 |
| 元/保存先の保持 | READ/DELETE等の必要accessを得られない、書込mapping/既存handle等で共有拒否 | FILE_SHARE_WRITE/DELETEを追加して回避しない。元は残して再実行へ。write viewの拒否は当該fixtureの部分証拠で、mapping種別/他FS全般の受け入れではない |
| Q5と実体結合 | 同一File ID・現在内容・コピー基準・一意な保存先を確認不能/不一致 | 保持handleから再読し同じ元handleだけを対象とする。path文字列だけのunlinkへ置換しない。実Drive保存先の観測/保持はこのローカル代用では証明しない |
| 結果観測 | 要求成功だけ、pending/権限不足/記録不明、不在の確証がない | 完了にせず結果不明/未完了として保全し、Q11の現在状態照合へ。元が消えただけで過去成功を作らない |

Q12の直接削除方式、対象期間、同名競合、PC-Bの権限を変えるものではない。これらの根拠を実root/実providerでそろえる前に、tests内候補を公開された実削除入口へ昇格させない。

## 保持handleのsecurity観測と残る資格

2026-10-29に`tests/windows_security_observation.py`を追加した。保持中のdirectory handleからGetSecurityInfoでowner/DACLの記述子を読み、File ID・object種別を取得前後に確認する。pathからGet-Aclを取り直す方式と異なり、観測を開いている実体へ結び付ける。READ_CONTROL不足、無効/未対応の記述子、64 KiBを超える応答、API失敗は固定理由で拒否し、不足する情報を補完しない。

観測値はobject kind、volume/128-bit File ID、owner/DACLの自己相対bytes、owner SID、process primary tokenのuser SID、DACL present/null/protectedを持つ。GetTokenInformationのbufferも64 KiB以内とし、Native APIの割当てを解放する。SID・記述子はprivateなメモリ内に限り、repr・journal・コンソール・PRへ出さない。プロセスprimary userの観測は、thread impersonation下のeffective userやgroup/privilege/elevationの証明ではない。

候補は3ディレクトリのhandleを保持した後に基準観測を取得する。取得不能なら通常所有記録の生成より前に拒否する。取得後も各所有checkpointで同じhandleを読み直し、実体/記述子/観測したprocess userが変われば元削除や成功記録を止める。除去後に検出した場合は結果不明とする。

[6試験](../../tests/test_native_security_binding.py)では、実handleとprocess userの観測、READ_CONTROLのないhandleの拒否、初回観測失敗、保持中のDACL変更の検出、除去後の変更で成功記録を作らないことを確認する。fault fixtureは自分で作った3ディレクトリだけを対象に、実行user/SYSTEM/local Administratorsの明示DACLへ設定する。observer自身はACLを書き換えず、任意pathやSDDLを受け取らない。実accountの権限・task・設定・利用者の既存rootは変更しない。

共有modeでdirectoryの名前変更を拒否できても、WRITE_DACによるDACL変更を凍結できるわけではない。今回もholding中の変更が成功し、再観測で検出した。checkpoint間の変更/復元、観測直後の変更、全祖先、SACL・mandatory label、group/privilege/impersonation、実効AccessCheck、実運用rootのqualificationは残る。観測一致の`may_change_state`は常にfalseであり、自作fixtureの試験が通ることを任意rootの削除許可へ流用しない。

既存の[private file ACL profile](reference/private-evidence-acl-profile.md)はfile専用のまま維持し、directoryをfileと偽って分類しない。初期directory policyや正式factoryの資格条件を推測で採用していない。

根拠は[GetSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo)、[GetSecurityDescriptorLength](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getsecuritydescriptorlength)、[GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation)。[pywin32のhandle取得](https://github.com/mhammond/pywin32/blob/7743a95fcdb03cd1c7939259caaea70ebace1e53/win32/src/win32security.i)と[libuvの利用例](https://github.com/libuv/libuv/blob/9d8bbff7be6298900c494f39619deab799826f30/test/appcontainer.c)を比較し、SACL privilegeを要求せずowner/DACLだけをhandleから取得する。fixtureのDACL変更は[SetSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setsecurityinfo)を使い、Native割当てをLocalFreeで解放する。依存追加やコード転載はない。

## スレッド偽装時の拒否

process primary userが同じでも、スレッドの偽装tokenではgroupやprivilege等が異なる可能性がある。候補の観測はそれらを評価していないため、2026-10-29にsecurity観測の開始・終了でOpenThreadTokenを呼ぶ拒否処理を追加した。TOKEN_QUERYとOpenAsSelf=trueで呼び、ERROR_NO_TOKEN（1008）の場合だけ観測を続ける。tokenを取得できた場合はhandleを閉じて拒否し、アクセス拒否などの取得失敗も「tokenなし」と推測しない。同じSIDの自己偽装も例外にしない。

拒否理由は固定の`probe_security_context_unconfirmed`とし、tokenやSIDは出力しない。初回観測で拒否したら所有記録・準備記録を作らない。処理中は既存の所有checkpointへ接続され、元削除前は元を保持、元削除後は結果不明となり成功記録を作らない。候補が利用者の偽装を解除して続行することはない。通常のprimary contextへ戻った後の再実行では、新たに観測する。

既存6試験に4試験を追加し、同じprocess userの自己偽装の拒否、開始時の拒否と通常再実行、削除前後の偽装による停止、token照会のアクセス拒否を確認する。実偽装は試験自身のスレッドにImpersonateSelfで設定し、finallyでRevertToSelfを呼ぶ。解除できなければ試験プロセスを終了し、不明な権限のまま後続試験を実行しない。照会失敗の注入だけは模擬APIを使い、主要な拒否・停止は実Win32で試験する。

調査では[pywin32](https://github.com/mhammond/pywin32/blob/main/win32/src/win32apimodule.cpp)のTOKEN_QUERYによる照会と、[PHP](https://github.com/php/php-src/blob/master/TSRM/tsrm_win32.c)のthread context利用を比較した。両者の「thread tokenがない場合だけprocess tokenを使う」という区別を参考にし、この候補では偽装を扱う機能を増やさず拒否する方式にした。APIの意味は[OpenThreadToken](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthreadtoken)、試験の設定・解除は[ImpersonateSelf](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-impersonateself)と[RevertToSelf](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-reverttoself)に従う。依存追加・コード転載はない。

これはtests内候補の未対応状態を拒否する変更であり、正式providerの実効token資格やAccessCheckを実装したものではない。観測間・観測直後の変更/復元、process tokenのgroup/privilege/elevation、全祖先とdirectory policy、実root資格、実Driveとの結合は未完。`may_change_state=false`と既存の本番操作境界を維持する。
