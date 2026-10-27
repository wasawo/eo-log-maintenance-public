# owner-v2: field・identity・snapshot束縛の判断資料

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

状態：F1（canonicalな10進文字列）とB1（外部exact-byte binding）は [利用者の第5回回答](selected-policy-decisions-20261024.md) で方向を採用済み。その他は未確定の技術比較である。[v2論理契約](../../design/recovery-owner-evidence-v2-contract.md)の未確定field/type/serialization/digestを具体化する資料で、schema/provider/writer/認可を追加しない。

[互換方針の承認](recovery-owner-evidence-v2-proposal.md)はv1診断・保全、新規取得時から証拠を持つv2だけを将来回復対象とする方向までで、正確なfieldsの同時承認ではない。この方針は再質問しない。現[v1実装](../../../Common/OwnedRunLock.py)のrecordは `schema_version` / `scope_id` / `owner_token` / `pid` / `host` の正確な5field。通常v1 writer/reader/releaseを維持し、v1からの自動変換・補完・修復を行わない。

## 1. fieldと出所の候補

以下の具体field名・全体集合・必須条件は**提案候補**。F1の表現とB1のdigest方向は選択済みだが、field集合や実OS providerを同時採用しない。実token/host/PID/boot ID/pathは使わず、例も合成値に限る。providerの未選定をfieldの仮値で埋めない。

| 論理情報 | field/type候補 | 出所・比較と未確定事項 |
| --- | --- | --- |
| version | `schema_version`: integer、supported値は別途承認 | v1と区別。v2の名前から数値を実装で先決めせず、未知版/重複key/未知field拒否を維持 |
| scope | `scope_id`: string | recordだけでなく独立したtrusted sourceから期待scopeを得て一致を検証。任意path/PIDから導出しない。形式・上限・source providerは未確定 |
| ownership token | `owner_token`: string | 取得時の新しい秘密値。現行v1のASCII・長さ制限/生成方式をv2へ取り込むかも候補。公開出力・通常例外へ出さず、token一致だけで旧owner終了としない |
| process | `pid`: positive integer と生成identity（§2） | 同一handleから得たOS生成identityと対にする。PID再利用、不在、query不能は終了証明にならない |
| machine/boot | `machine_identity` / `boot_identity`: opaque string、またはprovider/version付き構造 | 型・正規化・providerとも未選定。host名・入力値・時刻で代用しない。合成fixture値と実OS証拠を区別し、providerの資格なしに実値をqualifiedな証拠として生成しない |
| snapshot | 外部 `record_sha256` 等、またはrecord内部digest（§4） | exact bytes、scope/root/file identityの観測と束縛。hashは出所・権限・現在性を証明しない |

JSON全体の候補はUTF-8 strict JSON、重複key/未知field拒否。外部exact-byte digest案なら空白・key順・末尾改行の違いも別bytesとして扱う。writerのkey順/改行を固定するか、token/identityの文字集合と上限、nullと欠落の拒否条件はschema承認時に決める。構文成功から実OS証拠の資格を推定しない。

## 2. process生成FILETIMEの表現を選ぶ

[GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)は生成時刻をFILETIMEとして返す。[FILETIME](https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-filetime)は1601年起点のUTC・100ns単位の64bit値を二つのDWORDで表す。以下はその値をJSONへ写す設計候補で、APIの別identity保証ではない。

| 選択 | field/typeとserialization候補 | 正規化・範囲・比較 | tradeoff |
| --- | --- | --- | --- |
| F1: canonical decimal string | `process_created_filetime`: string、合成例 `"123456789"` | 符号/空白/先頭0なし。unsigned64上限 `18446744073709551615` はAPI表現由来。0や取得不能を有効証拠にしない。検証後の整数値をexact比較 | JSON consumerの浮動小数点化を避けやすいが、文字列の数値範囲検査が必要 |
| F2: hi/lo pair | `process_created_filetime`: object、`high` / `low`: uint32 | 各0〜4294967295、bool不可。結合した64bit値をexact比較し、両方0等unknownを証拠にしない | API構造に近いが、片側欠落・型違い・結合順を検査する必要 |
| F3: UTC日時string | `process_created_utc`: string | UTC正規形・100nsを失わない桁数・暦日/範囲・元FILETIMEとの可逆変換を別途確定 | 人が読める反面、日時libraryの範囲・丸め・比較差に注意。通常のmicrosecond精度datetime経由で100ns精度が失われ得る点は表現/実装上の推論 |

64bit値をJSON numberへ直に置く別案はconsumerが全値をexact保持できるか未確認で、採用時にはPS/Python双方の精度試験が必要。表現が一致しても、machine/bootの資格やrecordとの対応を証明したことにはならない。

## 3. identity providerの選択前に止める範囲

| 一次資料の事実 | provider候補への含意・未確認 |
| --- | --- |
| [OpenProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess)は権限指定でhandleを開く。[process handles](https://learn.microsoft.com/en-us/windows/win32/procthread/process-handles-and-identifiers)はhandleとPIDの寿命を区別する | 同じhandleで生成identityをqueryし、同じobjectのwait結果を観測する候補。native handle数値を永続identityとしてrecordへ保存しない |
| queryとwaitには対応する権限が必要。[process rights](https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights) | 必要最小限の権限・handle寿命を資格確認する。permission/query失敗、PID再利用、handleなしはunknown。対象process終了/制御や昇格を追加しない。close失敗も固定理由で拒否 |
| [CIM_OperatingSystem](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/cim-operatingsystem)のLastBootUpTimeは起動日時 | uniqueな永続boot IDとする保証は確認できない。WMI時刻をそのままboot証明にしない |
| [About time](https://learn.microsoft.com/en-us/windows/win32/sysinfo/about-time)は時刻・経過時間を扱う | uptime/時計だけで永続boot identityを得たとしない。host名も同様に代用不可 |

公式資料の確認日：2026-10-24 JST（analystの一次調査）。same-handleの組合せは設計候補であり、実provider未実装。**machine/bootを結ぶ適格persistent providerは未特定**である。formalなfield/type/source/serialization契約が未確定の間は、未決を実装で埋める規範schema/validatorを保留する。契約確定後の純粋な構造検証と、実OS providerの資格確認は分離する（§5）。実OS接続、qualifiedなmachine/boot・provenance・live観測に基づくv2生成/回復は、独立した資格確認と対象限定検証のゲートを満たすまで停止する。provider未選定のままfieldを仮値で埋めたり、F1等の表現選択だけで実OS証拠をqualifiedにしたりしない。

## 4. snapshot digestの対象と格納位置

| 選択 | digest対象・格納位置候補 | 利点 | 残る規則・限界 |
| --- | --- | --- | --- |
| B1: 外部exact-byte binding | 元recordのexact original bytes全体をSHA-256。snapshot/evidence側の `record_sha256` 等へ格納 | 自己参照を避け、[private evidence契約](../../design/recovery-private-evidence-contract.md)のraw bytes＋digestと対応させやすい | snapshotの取得元、scope/root/file identity、観測中/後の変更検出を別途要求。既存private metadataへfieldを暗黙追加しない |
| B2: record内self-digest | record内 `record_digest` 等。digest fieldを除いたcanonical serializationをhashする等の規則候補 | record内で検査情報をまとめられる | 除外field、key順、空白、encoding/改行、数値表現、自己参照回避を厳密定義する必要。exact original bytesのdigestとは別物 |

両案ともdigest一致はauthority・出所・現在性・改変耐性の保証ではない。token/scope/原本差替えを検出しても、最新manifest/Drive/disposition等のゲートを省略しない。外部snapshot/evidenceを新設する場合も実保存は未承認であり、既存の非公開保全・ACL・保持・公開順序契約を別途満たす必要がある。

## 5. 独立した回答欄と承認後の作業

| 判断 | 回答済み/残る選択 | 確定が必要な内容 |
| --- | --- | --- |
| process生成表現 | F1を選択済み。F2/F3は未採用 | field名、型、正規化、精度、範囲、0/null/欠落の拒否条件 |
| scope/token | 個別条件を記入 / 保留 | trusted source、比較、秘密値形式と上限。現行v1値域の継承可否 |
| machine/boot | provider候補の追加調査 / 保留 | 永続identityの出所・OS/再起動/複製時の意味・資格計画。適格provider未選定は維持 |
| digest | B1を選択済み。B2は未採用 | digest対象、field名、serialization、格納位置、snapshotとの対応 |
| 全体field集合 | 表の候補を修正して記入 / 保留 | supported version、required/null/unknown、JSON正規化・上限 |

v1保全/v2のみの既承認方針を再選択する欄ではない。F1/B1以外の残る契約は未承認であり、F1/B1の選択だけでは実装開始・実OS接続・回復を認可しない。

formalなfield/type/source/serialization契約が承認・確定した後は、合成fixtureだけを使うclosed schema/純粋strict validatorを、実OS providerの資格確認と分離して進め得る。本資料では契約未承認のため、今回はその実装も開始しない。provider資格未確認を合成値で補完せず、構造検証の成功を実証拠の資格や回復認可にしない。

実OS provider接続、取得時writerによるqualifiedなv2生成、独立trusted source照合と同一handleのlive観測、回復は、それぞれの独立資格・対象限定検証ゲートを満たすまで停止する。選定後にprovider寿命・権限・秘密除去を具体化し、実保存/回復の既存契約も別途満たす。既存normal v1経路を変更する場合は別途互換性レビューを行う。

| 論理契約の試験ID | 契約承認後の合成試験候補。実OS確認は独立ゲート通過後のみ（すべて未実装・未実行） |
| --- | --- |
| OWNER-01 | v1/未知版/欠落/重複key/未知fieldとF1非正規形・範囲外、F2片側欠落、F3精度欠落を拒否。原本bytes不変 |
| OWNER-02 | 合成providerでlive/終了/別生成identity/PIDなしを分離。実OS確認は自分で作成した合成子processだけ |
| OWNER-03 | machine/boot不一致、provider不足、permission/query失敗、再起動/複製を模した値をunknownに維持 |
| OWNER-04 | 同一handleのquery→wait→close履歴、途中closeなし、例外/close失敗の固定拒否。実processの制御・昇格なし |
| OWNER-05 | scope/token/record差替え、同サイズ別bytes、serialization差、snapshot後変更を検出。旧計画の再利用不可 |
| OWNER-06 | 公開出力・通常例外へ秘密値なし、元record/manifest不変。保存helper成功を出所/authorityの証拠へ昇格しない |

今回行うのは文書のリンク・記述・差分検証のみ。契約未承認のためschema/純粋validator/合成試験は開始せず、実OS provider接続・qualifiedなv2生成・実保存・本番回復も行わない。将来の純粋な構造検証と実OS資格確認の開始条件を、一つの順序ゲートとして確定する資料ではない。
