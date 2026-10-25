# Checkpoint比較更新provider：候補APIと隔離probe

2026-10-25。根拠は[採用済みC1/C2](../decisions/osd-02-crash-concurrency-options.md)、[確認予算契約](completion-wait-budget.md)、[対象FS受け入れ](../validation/target-filesystem-acceptance.md)。実writer/providerは未採用・未資格で、実設定/root/Driveには接続しない。

## 一次資料から確認した条件

| API・一次資料 | 確認できる条件 | 資格への含意 |
| --- | --- | --- |
| [ReplaceFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew) | 引数は置換先/置換元/任意backup等で、expected bytesの比較引数はない。WRITE_THROUGH指定は未サポート。ACL等の情報を引き継ぐ | API単独を条件付き比較更新や電源断耐久性の証明にはできない、というのが本資料の推論。IGNORE_ACL_ERRORS等を安全性の代用にしない |
| [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew) | handleのsharing制約はcloseまで有効。delete accessはrenameにも関係する。既存handleと衝突するaccess/shareは共有違反になる | deny-write/delete handleを保持したまま置換できるとは仮定しない。close後の検査/置換間の変更も独立に扱う |
| [Byte-range locking](https://learn.microsoft.com/en-us/windows/win32/fileio/locking-and-unlocking-byte-ranges-in-files) | byte-range lockはmemory-mapped accessでは無視される | LockFileExだけを全writer排除・namespace保護とみなす案も未採用 |
| [FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers) | 指定fileのbufferをflushする | file flushから名前のpublicationや実電源断時の復旧を証明せず、別の資格証拠を要する |

ReplaceFileWの1175/1176/1177等には、元/置換fileの名前や存在が異なる失敗結果が記載される。戻り値falseを「元bytes不変」と一律に分類しない。保存結果不明時は確認へ進めず、予算を払い戻したり無条件再試行したりしない。backup位置・保全/回復手順、ACL/stream/metadataの許容条件は正式provider設計で確定する。[ReplaceFileWの失敗条件](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew)

## 実Win32隔離probe

[probe](../../tests/checkpoint_replace_probe.py)と[試験](../../tests/test_checkpoint_replace_probe.py)はtests専用。caller指定の保存先を受けず、自分で作ったOS-tempの新規rootと固定fixture名だけを使う。root/所有marker・regular file・reparse/hardlinkを確認してから変更し、cleanup直前にもrootを検査する。内容は既存schemaに従う合成checkpointで、実運用データや秘密を使わない。

1. read handleをFILE_SHARE_READのみで保持し、実ReplaceFileWを試す。失敗と元/候補bytes保持を確認してからhandleを閉じ、置換成功を確認する。実験の失敗コードを特定の一種類に決め打ちせず、両fileの観測も行う。
2. 実mutex/ownerの内側で現行使用点検査を行った後、mutexプロトコルを使わない操作を意図的に挿入し、実ReplaceFileWで競合candidateを公開する。続く古いcandidateの無条件置換が競合内容を上書きできる反例を確認する。使用点検査結果は元々non-authorizingであり、これは意図的に危険な順序を実行する負例fixtureである。
3. root markerの変更、許可名外、hardlink aliasで、native変更へ進めないことも検査する。

このprobeは共有制約と無条件置換の限界を調べるもので、実providerを実装/採用するものではない。mockを実checkpoint更新へ昇格させず、metadata-onlyなroot検査やmutex保持だけを全writerの排除と読み替えない。testsは配布対象外。このprobe追加時点の非配布レビュー集合は46件で、現在の集合は[配布棚卸し](../status/first-release-readiness-20261024.md)を参照する。

## File使用点との実置換接続（2026-10-26）

[追加fixture](../../tests/test_checkpoint_file_replace_integration.py)は既存probeの自作/所有検査済みtempと固定3名だけを使い、[上限付きfile読取→plan/使用点](completion-wait-budget.md#既存fileの上限付き読取観測2026-10-26)を実Win32置換へ接続する。通常providerやcaller指定先を追加しない。

- 既存fileから生成したplanを共有guard内で置換しようとすると、この隔離試験では失敗し元/候補bytesが残る。after_commit検査も拒否する。guard解放後の置換・file再読取りは成立するが、全確認/状態変更/Archive許可falseのまま。
- 一度before_commit検査した後にnative competitorへ置換し、再度before_commitを実行すると変更を拒否し、競合checkpointと未使用candidateを保全する。ownerは解放される。
- 負例として、検査後にcompetitorへ置換し、意図的に古いcandidateで無条件上書きすると、その後のafter_commit bytes検査は成立し得る。この試験は「読戻し一致だけで途中writer不在を証明できる」という解釈を否定するもので、危険な順序を製品実装へ採用しない。
- 同一元bytesを持つ別fileへnative置換し、前後の実metadataでidentity変更を確認したケースでも、別々のbefore_commit呼出しは同じ非認可結果を返す。呼出し内のmetadata安定検査は、呼出し間のidentity lease/rollback/ABA防止ではない。

以上はこの隔離fixtureで観測した反例であり、全FS/API失敗形や対象volumeの資格を証明しない。正式CAS、trusted writer排除、exact predecessor/更新/readbackのbinding、一回限りreceipt、再起動/電源断は未完。新しいmetadata field、API選択、実更新許可を採用せず、レビューpackage file集合50件も不変。

## 次に必要な設計・資格

- writer排除の信頼境界：全writerが同じprovider/実scopeに従う前提を置けるか、従わないwriterやmapped writeも含め何を排除するか。ACL/SIDだけで同一user内の全processの協調を証明しない。この前提を自動採用しない。
- 対象root/祖先/実効ACL/volume/FSと、owner・handle・名前・bytes・更新のbinding。共有制約を解放するなら解放後の変更も閉じる仕組みが必要。
- API失敗・receipt喪失・競合・metadata継承の扱い。戻り値だけでcommitを確定せず、真正なreadbackと一回限りの確認receiptを結び付ける。古い同一bytesやstagingの冪等性を新しいreceiptにしない。
- 対象FSでのflush/publication/再起動/電源断の証拠。今回のprobeはTier Aの隔離実験に限り、両PCのTier B/Cや実保存を認可しない。

実行例：`python -B -m unittest discover -s tests -p "test_checkpoint_replace_probe.py"`。実rootを渡す引数や自動fallback/cleanup運用を追加しない。
