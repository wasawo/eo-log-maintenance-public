# C-01: drive-rooted file pathの詳細字句候補

状態：P1・検査配置V1・L1全体・現行1.0の実装前改訂を [利用者の第1/第2回回答](selected-policy-decisions-20261024.md) で承認済み。以下は選択時に提示したL1の全文と比較条件を保全する。2026-10-25に現1.0 request schema・PS/Python字句helper・共通fixtureへ追従した。指定先/root/FS/使用点と正式runtimeは未実装・未受け入れで、公開・本番適用の承認ではない。

基準はmain c4de355（PR #37）。[C-01/C-02比較](c01-c02-ipc-contract-options.md) §2/4/5の「詳細字句規則」を具体化する。対象はuploadのlocal_pathとdownloadのstaging_pathというrequestのファイル名で、設定のroot directoryや内部handleのvolume表現とは区別する。選択時点にはコード/schema/fixtureを実装していなかった。現実装もroot・FS・Driveの資格を認可しない。

## 1. Windowsの事実とアプリ側選択を分ける

公式資料の確認日：2026-10-24 JST。以下の事実は、L1を採用する承認ではない。

| 一次資料 | 確認できる事実 | そこから自動決定しないこと |
| --- | --- | --- |
| [Naming Files, Paths, and Namespaces](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file) | 予約文字、NUL/control、DOS device名、拡張子付き予約名、COM/LPTのsuperscript ¹²³、末尾space/dot、namespaceを説明 | Windowsが扱う全pathをIPCが許すか、どの字句subsetをschemaで拒否するか |
| [Maximum Path Length Limitation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation) | 長さ上限はAPI・manifest・設定等に依存し、通常Win32ではslashがbackslashへ変換され得る。UnicodeはopaqueなWCHAR列として扱われる | 固定の安全な長さ上限、slash許可、Unicode正規化をアプリの既定にしない |
| [RtlIsDosDeviceName_U](https://learn.microsoft.com/en-us/windows/win32/devnotes/rtlisdosdevicename_u)、[CreateFile2](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfile2) | 別のnative/API資料にはCONIN$・CONOUT$のDOS device/console用途がある | Naming Filesの一覧と同じ条件で全ての拡張子形に適用されるとは断定しない。L1の追加拒否は採用したアプリ側の制約 |

[設定reader](../../Common/MachineConfiguration.ps1)はdrive prefix、一部文字、末尾space/dot、GetFullPath等を検査するが、requestファイル名の完全なgrammarではない。reserved basename、slash、dot segment、root-only等の意味をそのまま継承しない。schema成功を実体・包含・ローカル性の証拠にしない。

## 2. L1: 採用した通常drive-rootedファイル名の字句規則

以下のL1は全体として採用された。Windows全般の必須規則と主張せず、runtimeの正規化・認可も代行しない。選択時の追加制約・残る意味を保持する。

| 項目 | L1の確定規則 | 追加制約・残る意味 |
| --- | --- | --- |
| prefix | ASCII英字1文字、colon、backslash1文字で開始。drive letterの大文字/小文字を両方許可 | drive letterから実体やローカルvolumeを推定しない |
| component | prefixの後に1個以上の非空componentを置き、backslash1文字で区切る。root-only・連続separator・末尾separatorは拒否 | 最後のcomponentをファイル名位置とするだけ。既存fileかdirectoryか、新規staging先かはruntimeが検査 |
| separator | slashは位置を問わず拒否。UNC、relative、drive-relative、root-relative、device/extended namespaceも拒否 | slash拒否は通常Win32の変換より狭いアプリ側選択。内部handle表現の例外をrequestへ持ち込まない |
| 文字 | drive prefix以後のcolon、less/greater-than、quotation mark、pipe、question mark、asterisk、U+0000–001Fを拒否。U+007Fも追加して拒否する | ADSを許可しない。DEL拒否はこの提案の追加制約で、Windowsの一般必須規則とはしない |
| dot/space | componentが正確にdot1個または2個なら拒否。各component末尾のASCII dot/spaceも拒否 | dot segmentを正規化して通す方式は採らない。先頭dot、先頭/内部のspaceやdotは他条件を満たせば許可 |
| DOS basename | 最初のdotより前のstemを取り、判定用にstem末尾のASCII spaceだけを除いてASCII英字の大小を区別せず照合。CON/PRN/AUX/NUL、COM1–9/LPT1–9、COM¹/²/³とLPT¹/²/³なら拒否 | 拡張子あり・なしの双方を拒否。判定用処理は入力pathのtrim・修復ではなく、変換したpathを利用しない |
| console alias | 上と同じstem判定にCONIN$・CONOUT$も追加して拒否 | extension形やstem末尾space形も拒否するのは明示的なアプリ側追加制約 |
| Unicode/case | 他条件を満たすUnicodeを保持し、NFC/NFD変換、path全体のtrim、case foldingをしない | DOS判定用のASCII比較だけを区別する。異なる文字列がFS上でも別物か、aliasかは未証明。UTF-8輸送・有効な文字列の検証も別ゲート |
| length | L1では未承認の固定maxLengthを追加しない | 無制限の実処理を許可する意味ではない。選定API/transportの上限・安全な受理条件を別途確定し、不明なら使用を停止 |

字句結果が同じでも、mapped drive、短縮名、reparse、祖先差替え、FSのcase設定等により実体は異なり得る。uploadの読取りrootとdownloadの限定書込みrootを無条件に共通化しない。PS/Pythonの独立した指定先・使用点検査、内容照合、root authorityの引継ぎは未実装の別ゲートである。

## 3. 互換性・実装範囲の独立判断

選択時点のrequest schemaは両fieldを最小長3のstringとしていた。現[request schema](../../contracts/drive-request.schema.json)はL1を適用し、従来schema-validな一部入力を拒否する。[専用試験](../../tests/test_drive_request_path.py)は両fieldとDry Run true/falseへ共通正負fixtureを適用する。schema versionは1.0を維持し、外部consumer不在は未確認。

Common/scriptsの限定調査では現Drive adapter/request consumerは見つからず、schema loaderはtestsで確認した。これは外部consumerが存在しない証明ではない。

| 判断 | 回答・未実施の範囲 | 実施前に確認する内容 |
| --- | --- | --- |
| C-01検査配置 | P1・V1を選択済み。V2は未採用 | schemaにも字句制約を置くか。L1だけでPS/Python使用点検査を省略しない |
| 詳細字句 | L1全体を選択済み | DEL、console alias、stem判定、Unicode、separator、dot segment等の追加制約を含めて明示回答 |
| version互換 | 現1.0を実装前に改訂。新version/別案は未採用 | 受理範囲変更、repo外consumerの確認方針、例・schema・fixture・配布の移行。新version値を本書で割り当てない |
| 変更の実施 | schema/両言語字句helper/合成fixtureまで追従済み。runtimeは保留 | 承認された字句だけを同時更新。adapter、root/token field、実root・IPC全体・実運用の承認に拡張しない |

一部だけ回答して残りを保留できる。未回答の詳細をregexやライブラリの既定値で決めない。C-02、認証、retry、Dry Run A、PC-B archive禁止・削除なしの境界も維持する。

## 4. 承認後の合成fixture候補

通常形/path形/文字・名前/境界/versionの字句は共通fixtureとschema/PS/Python試験へ反映した。semantic行の実体・root・使用点資格は未実装であり、字句成功から認可しない。

| 対象 | L1採用時に確認する候補 |
| --- | --- |
| 通常形 | 大小drive letter、複数component、Unicode/NFC/NFDの原文字列保持、先頭dotや内部space、拡張子なしを許可。存在・file種別・authorityは証明しない |
| path形 | relative/drive-relative/root-relative、UNC/device/extended、root-only、二重/末尾separator、slash、dot/dotdot componentを拒否 |
| 文字・名前 | 禁止文字/control/DEL/ADS、各component末尾space/dot、混在caseのDOS stem、拡張子・stem末尾space付き、superscript、CONIN$/CONOUT$を拒否 |
| 境界 | COM10等の非予約stemを他条件内で区別し、部分一致で過剰拒否しない。caseやUnicodeの比較方式をfixtureで固定し、入力を修復しない |
| semantic | schemaを通るmapped/reparse/alias、allow-root境界prefix、検査後差替え、未資格root、staging既存物を合成観測で拒否。schema単独で実体の包含を証明したとしない |
| version | 選んだ移行方針の旧形/未知版/不正型/未知field、両path field、4操作の既存形を確認。C-02のresult形を同時に独断確定しない |

選択前比較の独立reviewは当時の対象だけの履歴である。今回のコード/schema/fixture追従はroot単独で検証・自己点検し、独立reviewは実施していない。runtime対応は未実装・未受け入れである。
