# C-01/C-02: IPCパス・操作別resultの判断資料

- 状態：C-01のP1・検査V1・L1全体・現1.0改訂方針、C-02のR1・N1・D1を利用者承認済み（2026-10-24）。具体的な操作別field集合・型・最大値/serialization・SDK操作履歴と、変更実施/実装は未確定・未実施。未採用案も比較履歴として保持する。
- 対象：[契約レビューC-01/C-02](../validation/p0-contract-review-findings.md)。adapter実装前に判断する項目を具体化する。
- 選択の正確な範囲は[回答記録](selected-policy-decisions-20261024.md)に従う。第1回の「①P1」だけを質問の提案一式へ拡張せず、検査V1・L1・現1.0改訂は④⑤⑥、R1/N1/D1は⑦⑧⑨が根拠。L1の正確な内容は[詳細字句資料](c01-drive-rooted-lexical-candidate.md)に従う。C-02の操作別field集合・型等の候補表は一括採用ではなく、schema/コード/テスト/CI/allow-rootの変更実施を仕様選択から推定しない。

## 1. 現在の根拠と未決の範囲

| 根拠 | 現在の規則・証拠 | 本書で判断する不足 |
| --- | --- | --- |
| [PS/Python契約](../design/powershell-python-contract.md) §2–5 | PSはrole/path/allow-root/後続安全判断、Pythonは入力構文検査と限定API操作。schemaが規範で、例は説明用 | パス構文の対応範囲とschemaへの表現、操作別resultの最小形 |
| [request schema](../../contracts/drive-request.schema.json) | 4操作のみ。uploadの `local_path` とdownloadの `staging_path` は最小長3の文字列。listには `page_token` / `page_size` がある | relative/device等の構文をschemaで拒否するか |
| [response schema](../../contracts/drive-response.schema.json) | `schema_version: "1.0"`。成功はresult object/error null、失敗はresult null/error object。result内部はopen | 操作別の必須・任意・null・欠落、未知field |
| [既存schema tests](../../tests/test_contract_schemas.py) | drive-rooted例を受理。metadata成功の `result: {"file_id":"file-123"}` も受理 | negative path、操作別result、意味論の拒否fixtureが不足 |
| [設定/root設計](../design/configuration-local-root.md)、[設定parser](../../Common/MachineConfiguration.ps1) | 現在の設定はdrive-rooted Windows pathのみ。構造検証は実root認可・物理的分離の証明ではない | UNCをIPCで許す場合の設定側との整合と独立したroot資格 |
| [Dry Run A設計](../design/dry-run-execution-design.md) §2–4 | root/排他資格未完なら停止。bytes取得・書込み・live接続・認証refresh/storeは解禁しない | result契約を選んでもこれらのゲートは残る |

Google公式一次資料で確認したREST APIの返却条件は§7にまとめる（2026-10-24 JST確認）。SDKは未選定で、型変換・自動pagination・内部retry・upload/downloadの呼出し履歴は未確認。REST仕様で確認できる事実を、adapterでの返却保証や試行回数の検証済み証拠に置き換えない。C-02のR1/N1/D1方針は確定したが、操作別field集合・型・値域・正規化/serializationと実装は未確定・未実施である。

## 2. C-01: 対応するパス構文と検査責務を別々に選ぶ

### 2.1 構文の対応範囲

以下は比較履歴（P1採用、P2未採用）。`local_path` / `staging_path` はdrive-rooted Windows pathのみを対象とし、UNC対応は採用しない。すべてダミー例であり、使用・配布する実rootではない。

| 選択 | 対応候補 | 利点 | 制約・必要な整合変更 |
| --- | --- | --- | --- |
| P1: drive-rootedのみ | `C:\dummy-source\sample.log` | 現在の設定parserと範囲を揃えやすい。UNC資格を新たに扱わない | drive文字だけではローカル実体や許可FSを証明しない。mapped drive、alias、reparse、root authorityを別途検査 |
| P2: drive-rootedとUNC | P1に加え `\\dummy-host\dummy-share\staging\sample.log` | UNCを必要とする構成を表現できる | 現設定parserはUNC拒否。設定/schema/package例と検証、共有先identity/access/FS/排他の資格を別途設計・承認する必要がある。IPC構文だけ許しても現在の構成では使用資格なし |

「adapterで構文検証する」は対応範囲P1の代替ではなく、次表の検査配置である。追加回答によりV1とL1全体、現1.0改訂の方針は確定したが、実施と実装完了は別。P1/V1/L1やschema成功だけでroot authority・FS資格・physical containmentを証明しない。

### 2.2 schema・PS・Pythonの責務

| 選択 | schema | PowerShell | Python | tradeoff |
| --- | --- | --- | --- | --- |
| V1: 採用・schemaにも構文制約 | P1/L1の字句形と不正形を拒否する方向 | 信頼済み設定、role、操作別allow-root、物理identity/分離、使用点再検証 | schema再検証と独立した構文/指定先検証。使用直前のpath資格を確認 | 正規表現と両言語の判定差をfixtureで管理する必要。追従は未実装 |
| V2: 未採用・構文はruntime検査に委ねる | 現行の型/最小長に留め、構文保証なしを明記する比較案 | 選んだ構文範囲とruntime資格の検査が必要 | 独立した構文/指定先検証を必須にする比較案 | schema単独でrelative等を受理する限界が残る |

どちらもschema成功は認可ではない。Pythonが許可rootをどの信頼済み経路から得るか、PS検証とのidentity引継ぎをどう保証するかはadapter前の設計課題であり、現在のrequestに未承認のroot/token fieldを足して解決しない。

### 2.3 二つのpathの用途と拒否境界

| request field | 用途とallow-rootの役割 | そこから得られない権限 |
| --- | --- | --- |
| upload `local_path` | アップロードする既存入力を読む。対象PC/操作で許されたコピー元root内かをPSが検証し、Pythonも使用対象を検証する。直前に `expected_sha256` と照合 | 任意rootの読取り、別ファイルの代用、変更・削除・上書き |
| download `staging_path` | 指定されたステージング先への限定書込み。コピー元と最終archive先から分離された許可root・対象identity・新規/空の再試行先を検証 | 最終配置、既存運用物の上書き、archive、削除。Dry Run Aでのbytes取得・保存 |

具体的なallow-rootの設定キー、追加許可値、root一覧は本書では決めない。両fieldに同一rootを無条件で許すこともしない。

| 合成ケース | 採用P1/L1とruntimeの期待値 | 検査配置V1での扱い |
| --- | --- | --- |
| `relative\sample.log`、`C:sample.log`、`\sample.log` | L1で相対・drive-relative・root-relativeは拒否 | schemaに加えてPS/Pythonでも独立検査 |
| `\\?\C:\dummy\sample.log`、`\\.\dummy-device` | L1でrequestのdevice/extended namespaceを拒否。内部handle検査のvolume-GUID表現とは区別 | schema/両言語の負例へ。内部表現の例外をrequestに持ち込まない |
| `C:\dummy\..\outside\sample.log` | L1はdotdot component自体を拒否。正規化して通す方式ではない | 字句拒否とは別に物理的包含をruntimeで確認し、schemaへ期待しない |
| UNCダミー | P1/L1で拒否。P2は未採用 | 両path fieldのschema/両言語負例へ |
| root内に見えるreparse/alias、root検査後の差替え、未資格root | 使用対象のidentity/包含/分離を確立できなければ拒否。短縮名やmapped driveも字句だけで認可しない | schema成功でもsemantic試験で拒否 |

詳細字句は[L1全体](c01-drive-rooted-lexical-candidate.md)の採用内容へ従う。上表は比較用の概略で、正確な文字・component・名前・Unicode・長さの条件を省略/追加しない。root資格を証明できない入力は停止する。

## 3. C-02: 操作別resultの閉じ方と不足の表現

### 3.1 契約範囲

| 選択 | resultの扱い | 利点 | 負担・残る限界 |
| --- | --- | --- | --- |
| R1: 採用・操作別closed | 4操作ごとにfield集合・型・required・null条件を定義し、未知fieldを拒否する方針 | 欠落/型違い/他操作のfieldをschemaで拒否可能 | 具体的なfield集合・型・最大値等は未確定。候補表を丸ごと採用した意味ではない |
| R2: 未採用・段階的open | 最小fieldと型を定義し、追加fieldを暫定許容する比較案 | 最小形から段階的に具体化できる | 契約§1の未知field拒否原則への例外承認と移行条件を要する案。今回採用しない |

R1を選択しても、具体形が未確定な操作はadapter接続を保留する。現response schemaの任意objectをclosed実装済みと扱わない。失敗envelopeの `result: null` は現行規則を維持し、部分成功データを失敗resultに混ぜる変更は含めない。

### 3.2 必須・任意・nullable・missingの比較候補

N1は、対象metadata/tokenを必須nullableにし、未取得値はnull、field欠落は拒否する方針として採用した。必須非nullのID等をnullで代用してはならない。対象とする具体的field集合・型・最大値/serializationは未確定で、以下の候補名・個別required条件は一括採用ではない。`必須` は成功resultで欠落不可、`任意` は欠落可、`nullable` は明示null可を意味する。数値sizeはadapterによる非負整数への正規化候補であり、API生値ではない。RESTの `size` はstring形式のint64で、folder/shortcut等には未設定となる。checksumは実際に取得した値だけとし、ローカル値をクラウド値として補完しない。[File resource](https://developers.google.com/workspace/drive/api/reference/rest/v3/files)

型の候補は `file_id` / `name` / `mime_type` が非空文字列、`modified_time` がタイムゾーンを伴う日時文字列、`parent_ids` が非空文字列の配列、`sha256` / `staging_sha256` が64桁hex、tokenが非空文字列。nullableを選ぶfieldだけnullを追加許容する。日時の正規化とAPI値の変換、checksumの出所を示す表現も承認前に確定し、APIがこの型で返すとは仮定しない。list/getの既定fieldは一部だけであり、ID/name等を必須にするには明示的な `fields` 要求と欠落時停止を検証する必要がある。fieldを要求しても、そのresourceで値が利用可能になるとは限らない。[fields parameter](https://developers.google.com/workspace/drive/api/guides/fields-parameter)

| operation | 必須・非nullの最小候補 | 必須nullableのfield候補（N1方針採用） | 未採用N2の比較履歴 | missing/nullを安全判断でどう扱うか |
| --- | --- | --- | --- | --- |
| `list_files` | `files` 配列（0件可）、各要素 `file_id`、`name`。ページの不完全性を示す `incomplete_listing` 真偽値候補 | `next_page_token`（文字列/null）。各要素の `mime_type`、`size`、`modified_time`、`parent_ids`、`sha256` は取得不能時null候補 | 同じmetadata群は取得時のみ出す。末尾ページのtoken欠落を許す場合はその意味を明文化 | token null/欠落だけで全体完了にしない。incompleteが不明・true、ページ失敗、identity不足なら不在証明不可 |
| `get_file_metadata` | `file_id`、`name`、`cloud_content_verified`（metadataだけならfalse） | `mime_type`、`size`、`modified_time`、`parent_ids`、`sha256` | 同じmetadata群を取得時のみ出す | hash欠落/nullは未検証。必要なidentity/sizeがなければ後続安全判断を停止。resource不在とhash欠落は別 |
| `upload_file` | 返却対象の `file_id`、`name`、`cloud_content_verified`（API成功だけならfalse） | `parent_ids`、`size`、`sha256` 等、APIから実際に取得したmetadata | 同じmetadata群を取得時のみ出す | 応答identityが不足/矛盾なら完了扱い不可。expected hashのechoはクラウド検証ではない。応答喪失は既存の不明upload照合へ |
| `download_file` | `file_id`、`bytes_received` 非負整数候補、`cloud_content_verified`（独立検証前はfalse） | 実際に得たremote `size` / `sha256` 等 | 同じremote metadataを取得時のみ出す。ローカル `staging_sha256` を含めるかは別候補 | bytes数だけでは内容/identity検証にならない。PSは指定済みstagingのpath資格と実bytes/hashを独立検証し、最終配置を別判断 |

採用N1では「fieldは既知だが値なし」をnullで明示する。取得不能/未要求/未検証の区別が必要な場合の表現は具体形で確定する。N2の省略やN1/N2混用は採用していない。null・欠落を0/空配列/falseへ黙って変換せず、`parent_ids: []` を親情報不明の代用にしない。必須非nullの不足による停止と、nullable値が未検証であることの扱いも分ける。

`incomplete_listing` はRESTの `incompleteSearch` をどう変換するかという提案で、同名のAPI fieldではない。`incompleteSearch: true` は検索結果が欠け得ることを示す。[files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) `bytes_received` もAPI metadata fieldではなくclientが受信bytesを観測する提案である。`alt=media` の応答bodyはmetadataではなく内容bytesとなる。[files.get](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get) SDKからの正しい導出は未確認で、不能なら「false」や「0」を仮置きせず、nullable/別の状態表現を選ぶか停止する。必要な追加APIが1回試行原則に抵触する場合、暗黙に呼ばず契約設計へ戻す。download結果にローカル絶対pathをechoする必然性は未確定であり、上表では必須にしていない。

### 3.3 ページ成功、全一覧完了、検証成功を区別する

requestには `page_token` があるため、候補は**1 request＝1ページの1 API試行**。全ページをPython内部で取得して1回試行と数える案ではない。PSが次ページを要求し、それぞれの相関・exit・errorを検証する。再試行の所有者もPSのまま。ページ列のidentity/検索条件/継続tokenの整合、循環token、途中失敗、不完全listingを検査し、終端まで成功し必要な完全性を確認できた場合だけ全一覧の完了候補とする。pagination中の外部変更に対する整合保証は別途設計が必要で、終端tokenだけでsnapshotを証明しない。

RESTの `pageSize` は返却件数の上限であり、指定件数より少なく返ることがある。`nextPageToken` は追加ページを示し、終端では欠落する。token失効や列挙中の外部変更を無視して一覧完全性を保持したと解釈しない。[files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) `files: []` とtokenありは保守的な合成fixture候補であり、この組合せの具体的発生を保証する主張ではない。その入力を受けても不在証明にしない。1ページのREST応答とSDK内部の複数呼出しは区別して計測する。

終端でも不完全listingなら再uploadの許可にはならない。metadata取得成功、upload API成功、download bytes取得成功も、それぞれクラウド内容検証、両PC完了、archive認可を意味しない。内容検証の方法・根拠がない `cloud_content_verified: true` は拒否する。

### 3.4 採用D1と残る計画形の具体化

D1を採用し、同一operation内の `result_kind: "plan" / "executed"` で計画と実行を区別し、planを別のclosed形として定義する。plan/executedそれぞれの具体的field集合・型等は未確定で、上表のupload/download実行結果の必須fieldをDry Runの仮値で埋めない。D2（分離契約を別途決めるまで保留する方式）は未採用の比較履歴として保持するが、具体形・資格不足時に接続を止める原則は変わらない。新operation/transportを追加しない。

D1でも計画にfile ID・bytes数・検証成功を捏造せず、取得していないbytesを「0 bytes取得成功」としない。Aではdownload bytes取得（メモリ経由を含む）・upload・ファイル出力なし。mock/supplied snapshotの由来をlive観測に昇格させない。OSD-05のlive認証/接続、root/排他資格、単一JSON引数のencoding/引用/長さ/秘密除去とstdout/stderr捕捉のファイル不要IPCゲートを維持し、不成立なら停止する。

## 4. 互換性と移行の判断

現行request/responseは `schema_version: "1.0"` 固定。C-01は現1.0を実装前に改訂する方針を採用し、新version/期間限定併存は採用しない。P1/L1の厳格化で従来schema-validなpathが不適合になり得るため、外部consumerの有無と文書・fixture・配布物の互換性を確認する。C-02のIDのみresult等の扱いは別の未決事項で、C-01の選択からresult契約の改訂を推定しない。

| 移行候補 | 判断が必要なこと |
| --- | --- |
| C-01採用：現行1.0を実装前に改訂 | 従来例の受理範囲変更を明記し、参照物・fixtureを追従。repo外consumerの確認と実施は残る |
| C-01未採用：新versionへ分離 | 比較履歴。新version値、対応するrequest/responseの組合せ、旧version拒否時期が必要となる案 |
| C-01未採用：期間限定で両形を扱う | 比較履歴。正確なversion識別、対応表、廃止条件が必要で、同じversionの曖昧fallbackを許す案ではない |

R2は未採用であり、現open schemaから採用R1へ追従する具体的result契約は別途確定する。現行1.0の改訂方針だけで候補fieldの採用、schema変更の実施、IPC全体・runtime・実運用を承認したとは扱わない。

## 5. 独立した回答欄

未回答の項目を選択済みと扱わない。必要なら一方だけ回答し、もう一方は保留できる。

| 判断 | 選択・未回答欄 | 合わせて確定する事項 |
| --- | --- | --- |
| C-01対応範囲 | P1採用（第1回） | drive-rootedのみ。P2/UNC未採用 |
| C-01検査配置 | V1採用（追加回答④） | schemaとPS/Python。実体/使用点検査やallow-root権限を省略・追加しない |
| C-01詳細字句 | L1全体採用（追加回答⑤） | [L1資料](c01-drive-rooted-lexical-candidate.md)の全内容。実装・実root資格は未完了 |
| C-02閉鎖範囲 | R1採用（追加回答⑦） | 操作別closed。具体的field集合・型・最大値等は未確定、R2未採用 |
| C-02不足表現 | N1採用（追加回答⑧） | 対象metadata/token必須nullable、必須非null ID等の代用不可。具体的対象field集合等は未確定、N2未採用 |
| C-02 Dry Run形 | D1採用（追加回答⑨） | 同一operationでresult_kind=plan/executed、plan別closed。具体形未確定、D2未採用。未取得ID/bytes/検証成功を捏造しない |
| C-01版互換 | 現行1.0を実装前に改訂（追加回答⑥） | 外部consumer確認と受理範囲変更への追従は未実施。C-02のresult改訂は別判断 |
| 変更の実施 | 未承認・未実施 | コード/schema/tests変更、PR公開・runtime・実環境操作へ仕様選択を拡張しない |

方針の採用と残る具体形・未実施を区別する。⑦⑧⑨は[回答記録](selected-policy-decisions-20261024.md)が根拠であり、表の操作別field候補一式を自動採用するものではない。

## 6. 承認後に行う作業と具体的fixture

1. 判断記録を残し、規範契約のpath/result/unknown-field/version条項を整合させる。未確定のAPI返却保証・path authority引継ぎは実装前に解決する。
2. request/response schemaを承認された範囲だけ変更する。操作別resultと必要な計画形、null/欠落、versionの正負fixtureを追加する。
3. C-01 fixture：採用P1/L1の正負例（UNC/relative/drive-relative/device等の拒否を含む）、境界prefix、reparse/alias・差替え・未資格rootを合成で検査する。schema検査とPS/Python semantic検査の期待値を分け、L1全体の詳細を省略しない。
4. C-02 fixture：metadata hashなし/nullと未知field、ID欠落/型不正、他operationのresult、upload identity矛盾/応答喪失、download bytesと実file不一致を検査する。例：API成功でも `cloud_content_verified: false` を維持し、hash欠落をdownload fallbackへつなぐ場合も通常実行の独立資格を要求する。Aではfallback自体を呼ばない。
5. pagination fixture：空ページ＋継続token、終端成功、不完全listing、2ページ目失敗、token循環、検索条件不一致、外部変更で未検証を検査する。1ページ1 API試行とPS側の全ページ制御・再試行所有を別々に証明する。
6. caller/adapter semantic testでrequest ID/operation、exit/error/retryable、未知version、1 API試行・暗黙retryなし、streamの秘密除去、Aの副作用拒否を確認する。schema成功だけで完了扱いしない。C-03〜06とIPC全体のレビュー、OSD-05、runtime受け入れは別ゲートのまま。

本書の追加時点ではこれらのfixtureやadapterを実装・実行していない。機能テストの成功、P0-005/Phase 1/7の完了、cloud検証・実環境受け入れを示す資料ではない。

## 7. 公式一次資料で確認した範囲と未確認の境界

確認日：2026-10-24 JST。以下はREST仕様・公式ガイドの要約であり、提案fieldや本プロジェクトの契約変更を承認するものではない。

| 公式資料の事実 | 判断資料への影響・残る確認 |
| --- | --- |
| Fileの `size` はstring(int64)。`sha256Checksum` は利用可能な場合に提供され、通常のcontentを持つ対象と、Docs/shortcut等で可用性が異なる。[File resource](https://developers.google.com/workspace/drive/api/reference/rest/v3/files) | size整数化はadapter候補。hashがないことを取得失敗・内容一致・0値へ変換しない。対象種別と利用可能fieldのfixtureが必要 |
| `fields` は応答のfield集合を選ぶ。既定応答は全fieldではない。[fields parameter](https://developers.google.com/workspace/drive/api/guides/fields-parameter) | list/getの必要fieldを明示要求しても、resource固有の可用性条件を超えない。SDK変換後の欠落/nullと必須field検査は未確認 |
| listはpageSizeより少ない件数を返し得る。継続token、token失効、`incompleteSearch` を扱う必要がある。[files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) | ページ成功だけで全一覧完了としない。SDKの自動ページ取得・1 API試行との対応は未確認 |
| create成功時のFile応答はfield maskで部分応答となる。[files.create](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/create) multipartは1 HTTP request、resumableは開始時の空応答と完了後のFile応答を含む複数request方式。[manage uploads](https://developers.google.com/workspace/drive/api/guides/manage-uploads) | 成功/IDだけで独立content hash検証にはならない。既存の「1 API試行」が各方式で何を数えるかは未決で、本書だけで方式や試行単位を選ばない |
| `alt=media` は内容bytesを返す。[files.get](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get) Docs等のexportは別方式で説明される。[manage downloads](https://developers.google.com/workspace/drive/api/guides/manage-downloads) | metadata形とbytes取得結果を混同しない。export用operationを本書で追加しない。受信bytes計測、staging検証、client内部通信の確認は別途必要。Dry Run Aではbytes取得なし |
| 一般的なエラー対処としてbackoffが説明される。[handle errors](https://developers.google.com/workspace/drive/api/guides/handle-errors) | 本プロジェクトのPS-only retry契約を変更する根拠ではない。SDK未選定で暗黙retryやpage動作は未確認。選定後に設定と呼出し履歴を検証する |

C-01のP1/検査V1/L1全体/現1.0改訂と、C-02のR1/N1/D1方針は確定済み。具体field集合・型・値域・plan形と実装/実施の未了を維持する。上表をもって規範契約、schema、adapter、IPC全体レビューが完成したとは扱わない。
