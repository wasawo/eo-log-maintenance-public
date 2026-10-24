# C-01/C-02: IPCパス・操作別resultの判断資料

- 状態：未承認の比較資料。推奨案・選択済みの案はない。
- 対象：[契約レビューC-01/C-02](../validation/p0-contract-review-findings.md)。adapter実装前に判断する項目を具体化する。
- 本書は規範契約、schema、コード、テスト、CI、allow-root、承認状態を変更しない。以下の新しいフィールド名・型・必須条件はすべて**提案候補**であり、承認なしにschemaへ実装しない。C-01とC-02は独立に回答できる。

## 1. 現在の根拠と未決の範囲

| 根拠 | 現在の規則・証拠 | 本書で判断する不足 |
| --- | --- | --- |
| [PS/Python契約](../design/powershell-python-contract.md) §2–5 | PSはrole/path/allow-root/後続安全判断、Pythonは入力構文検査と限定API操作。schemaが規範で、例は説明用 | パス構文の対応範囲とschemaへの表現、操作別resultの最小形 |
| [request schema](../../contracts/drive-request.schema.json) | 4操作のみ。uploadの `local_path` とdownloadの `staging_path` は最小長3の文字列。listには `page_token` / `page_size` がある | relative/device等の構文をschemaで拒否するか |
| [response schema](../../contracts/drive-response.schema.json) | `schema_version: "1.0"`。成功はresult object/error null、失敗はresult null/error object。result内部はopen | 操作別の必須・任意・null・欠落、未知field |
| [既存schema tests](../../tests/test_contract_schemas.py) | drive-rooted例を受理。metadata成功の `result: {"file_id":"file-123"}` も受理 | negative path、操作別result、意味論の拒否fixtureが不足 |
| [設定/root設計](../design/configuration-local-root.md)、[設定parser](../../Common/MachineConfiguration.ps1) | 現在の設定はdrive-rooted Windows pathのみ。構造検証は実root認可・物理的分離の証明ではない | UNCをIPCで許す場合の設定側との整合と独立したroot資格 |
| [Dry Run A設計](../design/dry-run-execution-design.md) §2–4 | root/排他資格未完なら停止。bytes取得・書込み・live接続・認証refresh/storeは解禁しない | result契約を選んでもこれらのゲートは残る |

Google公式一次資料で確認したREST APIの返却条件は§7にまとめる（2026-10-24 JST確認）。SDKは未選定で、型変換・自動pagination・内部retry・upload/downloadの呼出し履歴は未確認。REST仕様で確認できる事実を、adapterでの返却保証や試行回数の検証済み証拠に置き換えない。C-01/C-02の選択・field必須化・正規化方式は引き続き未承認である。

## 2. C-01: 対応するパス構文と検査責務を別々に選ぶ

### 2.1 構文の対応範囲

すべてダミー例であり、使用・配布する実rootではない。

| 選択 | 対応候補 | 利点 | 制約・必要な整合変更 |
| --- | --- | --- | --- |
| P1: drive-rootedのみ | `C:\dummy-source\sample.log` | 現在の設定parserと範囲を揃えやすい。UNC資格を新たに扱わない | drive文字だけではローカル実体や許可FSを証明しない。mapped drive、alias、reparse、root authorityを別途検査 |
| P2: drive-rootedとUNC | P1に加え `\\dummy-host\dummy-share\staging\sample.log` | UNCを必要とする構成を表現できる | 現設定parserはUNC拒否。設定/schema/package例と検証、共有先identity/access/FS/排他の資格を別途設計・承認する必要がある。IPC構文だけ許しても現在の構成では使用資格なし |

「adapterで構文検証する」はP1/P2の代替となる対応範囲ではなく、次表の検査配置の選択である。後回しにする場合も、adapter実装前にP1/P2を確定する。未決のまま任意のWindows文字列を受理しない。

### 2.2 schema・PS・Pythonの責務

| 選択 | schema | PowerShell | Python | tradeoff |
| --- | --- | --- | --- | --- |
| V1: schemaにも構文制約 | 選んだP1/P2の字句形と明白な不正形を拒否 | 信頼済み設定、role、操作別allow-root、物理identity/分離、使用点再検証 | schema再検証と独立した構文/指定先検証。使用直前のpath資格を確認 | 入口で早く拒否できるが、正規表現と両言語の判定差をfixtureで管理する必要 |
| V2: 構文はruntime検査に委ねる | 現行の型/最小長に留め、構文保証なしを明記 | V1と同じ。選んだP1/P2の構文検査も実施 | 選んだP1/P2の厳密構文検査と指定先検証を必須にする | schema単独でrelative等を受理する限界が残る。両言語のsemantic試験が必須 |

どちらもschema成功は認可ではない。Pythonが許可rootをどの信頼済み経路から得るか、PS検証とのidentity引継ぎをどう保証するかはadapter前の設計課題であり、現在のrequestに未承認のroot/token fieldを足して解決しない。

### 2.3 二つのpathの用途と拒否境界

| request field | 用途とallow-rootの役割 | そこから得られない権限 |
| --- | --- | --- |
| upload `local_path` | アップロードする既存入力を読む。対象PC/操作で許されたコピー元root内かをPSが検証し、Pythonも使用対象を検証する。直前に `expected_sha256` と照合 | 任意rootの読取り、別ファイルの代用、変更・削除・上書き |
| download `staging_path` | 指定されたステージング先への限定書込み。コピー元と最終archive先から分離された許可root・対象identity・新規/空の再試行先を検証 | 最終配置、既存運用物の上書き、archive、削除。Dry Run Aでのbytes取得・保存 |

具体的なallow-rootの設定キー、追加許可値、root一覧は本書では決めない。両fieldに同一rootを無条件で許すこともしない。

| 合成ケース | P1/P2共通のruntime期待値 | schema期待値の決め方 |
| --- | --- | --- |
| `relative\sample.log`、`C:sample.log`、`\sample.log` | 相対・drive-relative・root-relativeは拒否 | V1ならschema拒否、V2ならschema通過してもPS/Python拒否 |
| `\\?\C:\dummy\sample.log`、`\\.\dummy-device` | 両案ともrequestのdevice/extended namespaceを拒否する比較条件とする。内部handle検査のvolume-GUID表現とは区別 | P1/P2の通常path範囲外としてV1 fixtureへ。例外が必要なら独立判断 |
| `C:\dummy\..\outside\sample.log` | 正規化後にallow-root外なら拒否。文字prefix一致だけで通さない | schemaに物理的包含を期待しない |
| UNCダミー | P1は拒否。P2も未資格共有先なら拒否 | V1は選んだ範囲へ一致、V2はruntimeで区別 |
| root内に見えるreparse/alias、root検査後の差替え、未資格root | 使用対象のidentity/包含/分離を確立できなければ拒否。短縮名やmapped driveも字句だけで認可しない | schema成功でもsemantic試験で拒否 |

device namespaceの例外を設けないことを含め、詳細字句規則も承認時に確定する。root資格を証明できない入力は、構文選択にかかわらず停止する。

## 3. C-02: 操作別resultの閉じ方と不足の表現

### 3.1 契約範囲

| 選択 | resultの扱い | 利点 | 負担・残る限界 |
| --- | --- | --- | --- |
| R1: 操作別closed | 4操作ごとにfield集合・型・required・null条件を定義、未知fieldを拒否 | 欠落/型違い/他操作のfieldをschemaで拒否可能 | API返却保証とDry Run計画形を先に詰める必要。追加fieldに互換性判断が必要 |
| R2: 段階的open | 承認した最小fieldと型は定義するが、追加fieldを暫定許容。PSは利用fieldを明示検査し未知fieldを判断へ使わない | 最小形から段階的に具体化できる | 契約§1の未知field拒否原則との例外範囲・期限・closed移行条件を明示承認する必要。openは省略項目の正当化にならない |

R2を選ぶ場合も、現状の任意objectだけで安全判断しない。最小形を決められない操作はadapter接続を保留する。失敗envelopeの `result: null` は現行規則を維持する候補で、部分成功データを失敗resultに混ぜる変更は含めない。

### 3.2 必須・任意・nullable・missingの比較候補

以下の名前は、契約例に既出のものも含め**操作別schemaとしては未承認の提案候補**。`必須` は成功resultで欠落不可、`任意` は欠落可、`nullable` は明示null可を意味する。数値sizeはadapterによる非負整数への正規化候補であり、API生値ではない。RESTの `size` はstring形式のint64で、folder/shortcut等には未設定となる。checksumは実際に取得した値だけとし、ローカル値をクラウド値として補完しない。[File resource](https://developers.google.com/workspace/drive/api/reference/rest/v3/files)

型の候補は `file_id` / `name` / `mime_type` が非空文字列、`modified_time` がタイムゾーンを伴う日時文字列、`parent_ids` が非空文字列の配列、`sha256` / `staging_sha256` が64桁hex、tokenが非空文字列。nullableを選ぶfieldだけnullを追加許容する。日時の正規化とAPI値の変換、checksumの出所を示す表現も承認前に確定し、APIがこの型で返すとは仮定しない。list/getの既定fieldは一部だけであり、ID/name等を必須にするには明示的な `fields` 要求と欠落時停止を検証する必要がある。fieldを要求しても、そのresourceで値が利用可能になるとは限らない。[fields parameter](https://developers.google.com/workspace/drive/api/guides/fields-parameter)

| operation | 必須・非nullの最小候補 | 必須nullable候補（N1） | 任意・欠落候補（N2） | missing/nullを安全判断でどう扱うか |
| --- | --- | --- | --- | --- |
| `list_files` | `files` 配列（0件可）、各要素 `file_id`、`name`。ページの不完全性を示す `incomplete_listing` 真偽値候補 | `next_page_token`（文字列/null）。各要素の `mime_type`、`size`、`modified_time`、`parent_ids`、`sha256` は取得不能時null候補 | 同じmetadata群は取得時のみ出す。末尾ページのtoken欠落を許す場合はその意味を明文化 | token null/欠落だけで全体完了にしない。incompleteが不明・true、ページ失敗、identity不足なら不在証明不可 |
| `get_file_metadata` | `file_id`、`name`、`cloud_content_verified`（metadataだけならfalse） | `mime_type`、`size`、`modified_time`、`parent_ids`、`sha256` | 同じmetadata群を取得時のみ出す | hash欠落/nullは未検証。必要なidentity/sizeがなければ後続安全判断を停止。resource不在とhash欠落は別 |
| `upload_file` | 返却対象の `file_id`、`name`、`cloud_content_verified`（API成功だけならfalse） | `parent_ids`、`size`、`sha256` 等、APIから実際に取得したmetadata | 同じmetadata群を取得時のみ出す | 応答identityが不足/矛盾なら完了扱い不可。expected hashのechoはクラウド検証ではない。応答喪失は既存の不明upload照合へ |
| `download_file` | `file_id`、`bytes_received` 非負整数候補、`cloud_content_verified`（独立検証前はfalse） | 実際に得たremote `size` / `sha256` 等 | 同じremote metadataを取得時のみ出す。ローカル `staging_sha256` を含めるかは別候補 | bytes数だけでは内容/identity検証にならない。PSは指定済みstagingのpath資格と実bytes/hashを独立検証し、最終配置を別判断 |

N1は「fieldは既知だが値なし」をnullで明示できる反面、取得不能/未要求/未検証の区別が必要なら別の理由表現が要る。N2はAPIが返した値だけを表しやすい反面、adapterの返し忘れと意図的欠落が区別できない。N1/N2をfield別に混用する場合は一覧を承認し、null・欠落を0/空配列/falseへ黙って変換しない。`parent_ids: []` は親情報不明の代用にしない。metadata欠落をエラーにする必須用途と、未検証として表示するだけの用途も分けて確定する。

`incomplete_listing` はRESTの `incompleteSearch` をどう変換するかという提案で、同名のAPI fieldではない。`incompleteSearch: true` は検索結果が欠け得ることを示す。[files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) `bytes_received` もAPI metadata fieldではなくclientが受信bytesを観測する提案である。`alt=media` の応答bodyはmetadataではなく内容bytesとなる。[files.get](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get) SDKからの正しい導出は未確認で、不能なら「false」や「0」を仮置きせず、nullable/別の状態表現を選ぶか停止する。必要な追加APIが1回試行原則に抵触する場合、暗黙に呼ばず契約設計へ戻す。download結果にローカル絶対pathをechoする必然性は未確定であり、上表では必須にしていない。

### 3.3 ページ成功、全一覧完了、検証成功を区別する

requestには `page_token` があるため、候補は**1 request＝1ページの1 API試行**。全ページをPython内部で取得して1回試行と数える案ではない。PSが次ページを要求し、それぞれの相関・exit・errorを検証する。再試行の所有者もPSのまま。ページ列のidentity/検索条件/継続tokenの整合、循環token、途中失敗、不完全listingを検査し、終端まで成功し必要な完全性を確認できた場合だけ全一覧の完了候補とする。pagination中の外部変更に対する整合保証は別途設計が必要で、終端tokenだけでsnapshotを証明しない。

RESTの `pageSize` は返却件数の上限であり、指定件数より少なく返ることがある。`nextPageToken` は追加ページを示し、終端では欠落する。token失効や列挙中の外部変更を無視して一覧完全性を保持したと解釈しない。[files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) `files: []` とtokenありは保守的な合成fixture候補であり、この組合せの具体的発生を保証する主張ではない。その入力を受けても不在証明にしない。1ページのREST応答とSDK内部の複数呼出しは区別して計測する。

終端でも不完全listingなら再uploadの許可にはならない。metadata取得成功、upload API成功、download bytes取得成功も、それぞれクラウド内容検証、両PC完了、archive認可を意味しない。内容検証の方法・根拠がない `cloud_content_verified: true` は拒否する。

### 3.4 Dry Run Aの計画形を別途確定する

上表のupload/download実行結果の必須fieldをDry Runの仮値で埋めない。候補は、(D1) 同一operationで `result_kind: "plan" / "executed"` 等の**提案候補**の識別子を定義し計画形を別に閉じる、(D2) 実行結果形と分離する契約を別途決めるまで当該Dry Run adapter接続を保留する、の比較となる。新operation/transportを本書で追加しない。

D1でも計画にfile ID・bytes数・検証成功を捏造せず、取得していないbytesを「0 bytes取得成功」としない。Aではdownload bytes取得（メモリ経由を含む）・upload・ファイル出力なし。mock/supplied snapshotの由来をlive観測に昇格させない。OSD-05のlive認証/接続、root/排他資格、単一JSON引数のencoding/引用/長さ/秘密除去とstdout/stderr捕捉のファイル不要IPCゲートを維持し、不成立なら停止する。

## 4. 互換性と移行の判断

現行request/responseは `schema_version: "1.0"` 固定。厳格化で既存のschema-valid例（relative pathやmetadataのIDのみresult）が不適合になり得る。現在adapter未実装であっても、文書・fixture・配布物の利用者との互換性を確認する。

| 移行候補 | 判断が必要なこと |
| --- | --- |
| 現行1.0を実装前に改訂 | 従来例の受理範囲が変わることを明記し、参照物とfixtureを同時更新するか。旧形を使うconsumerがないことをどう確認するか |
| 新versionへ分離 | 新version値、対応するrequest/responseの組合せ、旧versionを明示拒否する時期。未承認のversion番号は本書で割り当てない |
| 期間限定で両形を扱う | 正確なversion識別、各validatorとconsumerの対応表、廃止条件が必要。同じversionで曖昧に推測・fallbackしない |

R2のopen範囲を後でclosedへ変える場合も、この互換性判断を行う。schema変更の承認をIPC全体・runtime・実運用の承認と扱わない。

## 5. 独立した回答欄

未回答の項目を選択済みと扱わない。必要なら一方だけ回答し、もう一方は保留できる。

| 判断 | 選択欄（未回答） | 合わせて確定する事項 |
| --- | --- | --- |
| C-01構文 | P1 / P2 / 保留 | device等の詳細拒否形、UNCを選ぶ場合の設定側変更と資格計画 |
| C-01検査配置 | V1 / V2 / 保留 | 両言語の検査責務、schemaが保証しない範囲。追加allow-root値は別判断 |
| C-02閉鎖範囲 | R1 / R2 / 保留 | 操作ごとの最小field。R2なら未知field例外の範囲・期限・closed移行条件 |
| C-02不足表現 | N1 / N2 / field別指定 / 保留 | 各fieldの必須/任意/null、取得不能・未要求・未検証と失敗の区別 |
| C-02 Dry Run形 | D1 / D2 / 保留 | 計画/実行の識別とfield集合。Aの禁止は維持 |
| 移行 | 1.0改訂 / 新version / 期間限定併存 / 保留 | version値・組合せ・拒否/移行条件は別途明記 |

回答例の書式：`C-01: P1, V1（詳細条件…）`、`C-02: 保留`。これは記入形式の例であり推奨・承認記録ではない。

## 6. 承認後に行う作業と具体的fixture

1. 判断記録を残し、規範契約のpath/result/unknown-field/version条項を整合させる。未確定のAPI返却保証・path authority引継ぎは実装前に解決する。
2. request/response schemaを承認された範囲だけ変更する。操作別resultと必要な計画形、null/欠落、versionの正負fixtureを追加する。
3. C-01 fixture：drive-rooted/UNCの採否、relative/drive-relative/deviceの拒否、境界prefix、reparse/alias・差替え・未資格rootを合成で検査する。schema検査とPS/Python semantic検査の期待値を分ける。
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

C-01回答待ち、C-02のfield/不足表現/計画形/移行の承認待ちを維持する。上表をもって規範契約、schema、adapter、IPC全体レビューが完成したとは扱わない。
