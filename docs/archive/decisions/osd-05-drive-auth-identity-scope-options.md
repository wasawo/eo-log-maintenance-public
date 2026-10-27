# OSD-05/C-23: Drive認証・identity・scopeの判断資料

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

- 状態：I1（同じGoogle principal）・A1（Desktop user OAuth）・S1（drive.file）は [利用者の第4回回答](selected-policy-decisions-20261024.md) で採用済み。T1（Windows user-bound保護store）も第5回回答で選択済み。暗号化専用fileとGoogle公式Python clientの方向も選択済み。具体store API/配置・SDK版/flow・実ACL/対象folder資格・限定試験の実施は未決/未検証。未採用案は比較履歴として保持する。
- 根拠：[OSD-05](../../requirements/p0-open-specification-decisions.md)、[決定台帳C-23/C-27](../../decisions/decision-register-c18-c32.md)、[PS/Python契約](../../design/powershell-python-contract.md) §2–3/9、[開発参照表](../../development/development-guide.md)。
- 本書は判断材料と将来の検証計画であり、コード/schema/CI/設定を変更せず、認証・consent・token取得・live接続・production uploadを実行または許可しない。実値、実path、mail、folder ID、client/token値は記載しない。

## 1. 既存承認と今回の判断の境界

[Windows実行account承認](recovery-execution-account-policy-proposal.md)は、**各PC内で**手動と将来taskを同じWindows accountにする方針で、PC-A/B間のWindows account一致を要求しない。[taskログオン方式承認](task-logon-mode-policy-proposal.md)は初期運用をログオン中に限定する。これらWindows方針だけではGoogle principal/認証方式の承認にはならない。今回の別回答でI1/A1を方針採用したが、実consent・credential保存・実接続の許可にはしない。

C-23はログ保守のDrive操作用。C-27のGitHub Actions/配布公開identityは別判断で、ログ保守のtoken、principal、scopeをそのまま配布CIへ渡さない。Google Workspace管理の有無、account種類、現在のfolder owner/sharingは未確認で、利用可能と推測しない。

判断は次の独立軸で行う。principal一致だけでPC由来・file所有者・両PC完了は証明できず、scopeだけで実folderの最小権限も証明できない。

| 軸 | 選択対象 | 依存する確認 |
| --- | --- | --- |
| Google ID | 同一principal / PCごと別principal / 保留 | 各folderの所有・共有・quota、PC別出所の検証 |
| 認証方式 | Desktop user OAuth / service account等の別構成 / 保留 | My Drive適合、consent、account/管理条件、task環境 |
| OAuth スコープ | per-file / read系 / 広範scopeの必要性 / 保留 | 4操作と既存fileへの実際のアクセス範囲 |
| 実Drive ACL | principalごとの対象folder/file権限 | 継承・limited access・capabilities、不要権限の範囲 |
| 認証情報ストア | user-bound保護store等 / 保留 | user/session境界、ACL、復旧、refresh更新、失効 |

## 2. Google principalと認証方式

### 2.1 principalの比較

| 候補 | 利点 | 注意点・必要な証拠 |
| --- | --- | --- |
| I1: 両PCで同じGoogle principal | 同じ対象へのアクセスを揃えやすい | 両PCのcredential露出が同一principalに及ぶ。各PCでのconsent/store/失効を設計し、tokenファイルのコピーで済ませない。同一principalでもfile所有・由来・quotaを実観測する |
| I2: PCごと別Google principal | PCごとのcredential境界とアクセスを分けられる | folder共有と既存fileの可視性、PCごとのupload所有/quota差を確認。片方のlistingだけで両者の全対象を見たと扱わない |
| I3: 保留 | account/folderの現況を確認してから判断できる | 依存する実認証とlive接続を保留する |

### 2.2 認証方式の比較

| 候補 | 公式資料で確認した事実 | projectへの適合条件・未確認 |
| --- | --- | --- |
| A1: デスクトップ ユーザー OAuth | Desktop clientはpublic clientで秘密を保持できず、PKCE、system browser/loopbackを用いる方式が説明される。refresh tokenは長期の安全な保存が必要。[ネイティブ アプリ OAuth](https://developers.google.com/identity/protocols/oauth2/native-app) | 初回の明示consentと通常taskの非対話動作を分ける。lib、client登録、PKCE/loopback実装、principal照合、storeは未選定。credentialの存在だけで実行を認可しない |
| A2: service account等の別構成 | shared drives説明とstorageQuotaExceeded説明は、service accountにstorage quotaがなくfile所有不可とし、shared driveまたはuserを代理する方式を示す。[共有ドライブ](https://developers.google.com/workspace/drive/api/guides/about-shareddrives)、[ストレージクォータ超過](https://developers.google.com/workspace/drive/api/guides/handle-errors#storageQuotaExceeded)。ただし公式資料間に逆の記述がある（直下参照） | 現My Drive構成への適合、所有、quotaは未確認。shared drive/Workspace管理/delegation利用可否を確認し、必要なら配置・所有・管理承認を別途判断。service accountへの自動fallbackは不可 |
| A3: 保留 | 認証方式未選定 | SDK・store・scopeを実装都合で先に固定しない |

2026-10-24 JSTの再照合では、[create fileのFile ownership節](https://developers.google.com/workspace/drive/api/guides/create-file#file_ownership)は、service account自身がfile ownerとなり専用Drive storageに配置されると記載しており、A2で挙げた二資料と整合しない。本projectでどちらを正しいと決着させず、service accountの現構成適合・所有・quotaを未確認として保留する。この不整合を認証方式選択や自動fallbackの根拠にしない。

My Driveへuser OAuthでcreateするfileはuser所有となりquotaを消費する。[ファイルを作成](https://developers.google.com/workspace/drive/api/guides/create-file#file_ownership) この説明はuser OAuthに限定し、service accountへ拡張しない。共有folderのownerとupload fileのownerを同一と仮定せず、I1/I2それぞれで確認する。公式資料の確認はREST/認証設計の材料であり、現在のSDKやtaskが適合する証拠ではない。

## 3. OAuth scopeと実folder権限を分ける

以下のscope名はGoogle側の比較材料であり、採用する設定値ではない。`drive.file` はアプリ作成、アプリで開く、Picker等でアプリへ共有されたfileを対象とするper-file scope。folder IDやACLがあるだけで、全既存配下fileがscope対象になるとは保証できない。[API スコープを駆動する](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)

| scope候補 | リスト / メタデータ | アップロード | ダウンロード/ハッシュ | projectの判断点 |
| --- | --- | --- | --- | --- |
| S1: `drive.file` | アプリの対象となるfileの範囲で評価 | 対象/作成条件とACLを確認 | 対象fileのcontentアクセスを確認 | 既存file・他PC作成file・未mark fileの可視性を実証する。見えないことを不在としない |
| S2: `drive.metadata.readonly` | metadata読取り用 | 不可 | content取得不可 | 4操作全体をこれだけでは満たさない。診断用と通常実行用を分けるなら別の方式判断が必要 |
| S3: `drive.readonly` | 読取り範囲を評価 | 不可 | 読取り対象contentを評価 | upload要件を満たさず、read-onlyでも広い可視性の影響を確認 |
| S4: `drive` | 広範なfileアクセス | scopeとしては対応可能 | scopeとしては対応可能 | 広範権限の必要性と実ACLを個別レビュー。S1の適合不明を理由に自動拡大しない |

上表はscopeの機能分類の要約であり、各操作の成功を保証しない。実ACL、resource状態、API返却条件、quotaの検証が別途必要。[API スコープを駆動する](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) checksumがない場合の通常実行download/hashも含めて評価し、C-01/C-02の[path方針は選択済み・result詳細未決](c01-c02-ipc-contract-options.md)をscope選択で迂回しない。

| 実Drive権限の確認 | 確認する理由・停止条件 |
| --- | --- |
| 対象folderと既存fileのowner/sharing | OAuth scopeは実Drive ACLとは別。principal別に許可対象と見える対象を確認する。[共有を管理](https://developers.google.com/workspace/drive/api/guides/manage-sharing) |
| 親からの継承とlimited-access例外 | folderへのアクセスだけで全配下へ同じアクセスがあると判断しない。[限定的かつ広範なアクセス](https://developers.google.com/workspace/drive/api/guides/limited-expansive-access) |
| roleと実capabilities | My Drive folderのwriterはcreate/edit/delete等の能力を持ち得る。最小scopeだけで最小実権限とはいえない。[の役割](https://developers.google.com/workspace/drive/api/guides/ref-roles) |
| アプリの能力境界 | ACLがdeleteを許しても、初期アプリには削除コード・操作・設定を提供しない。PC-B archive禁止も維持。実削除を試して検証しない |

実ACLを変更する権限は本書から得られない。scope追加・共有追加・owner移転で試験を通す変更も、明示した別の承認範囲が必要。

## 4. credential storeとライフサイクルの比較候補

T1の方向は承認済みだが、project用の具体的なcredential storeは未実装である。新しいcredential file設定を追加せず、store API/lib/配置を選択済みとしない。token、鍵、client情報をrepo/package、通常運用log、共有Drive、IPC引数/JSONへ入れない。clientがpublic clientであることはrefresh tokenを公開してよい理由にならない。

| store候補 | 利点 | 復旧・運用上の判断事項 |
| --- | --- | --- |
| T1: Windows user-bound保護store | 各PCの承認済み実行userと結び付ける候補。手動/task同一account方針と整合させやすい | API/libとuser-bound性は未選定・未検証。別user/profile、OS再導入、backup/restore後に復号できるかを仮定しない。ACL・profile/session条件・再consent手順を検証 |
| T2: 専用secret管理provider | credentialの更新/監査/失効を集約する候補 | providerへの認証、network依存、利用権限、復旧、費用・管理条件が別途必要。利用可能なserviceがあると仮定しない |
| T3: 保留 | 保存形式や配置を先に固定しない | 通常task用token取得・保存・refresh実装は停止 |

T1/T2とも保護storeはrepo/package外に置く設計が必要で、固定の実pathを本書で指定しない。暗号化だけで十分とせず、実行user/必要管理者以外の読取り、継承、reparse/alias、backupへの露出、秘密除去を確認する。平文JSONの共有・自動配布は承認候補に含めない。

| ライフサイクル | 承認・実装前に決める事項 |
| --- | --- |
| 初回consent | principalの取り違え防止、許可scopeの照合、非対話task内でloginを開始しない停止動作 |
| refreshとstore更新 | 通常実行での更新資格、排他・更新途中失敗、保存失敗時のhold。refreshの成功だけで操作権限を判断しない |
| 失効・permission revoked・refresh失敗 | 自動scope拡大・別principal fallback・秘密の再出力をせず停止し、必要な運用者判断を返す |
| 再同意 | 誰が何を承認し直すか。scope変更を既存consentの延長として黙認しない |
| backup/restore・PC移行 | tokenを共有Drive/packageへコピーしない。復旧可能性と漏洩時の失効を設計し、復旧不能なら明示的reconsentを行う手順を判断 |

refresh tokenを安全に長期保存する必要性は公式資料にあるが、T1/T2の具体的実装はproject候補である。[ネイティブ アプリ OAuth](https://developers.google.com/identity/protocols/oauth2/native-app)

## 5. 合成試験と限定した実folder検証の計画

本節は**未実施の計画候補**。実環境試験には対象principal・専用test-folder・許可操作・保存範囲・停止条件を明示した限定計画の承認が別途必要。本書作成や方式選択から実認証/接続を開始しない。実ログ・本番folderを通常テストに使わない。

| 段階 | 対象・具体例 | 期待する証拠・停止条件 |
| --- | --- | --- |
| 合成 | principal不一致、scope不足、token失効、refresh/store失敗、permission revoked、quotaエラーをmock注入 | scope拡大・login・再upload・別identity fallbackなし。固定理由でhold、秘密を出さない。暗黙retryは契約どおり禁止 |
| 合成 | no-delete能力検査、PC-B archive要求、Dry Run依存auth/network/store/write/download要求 | 削除API/操作/設定がなく、禁止依存に到達しない。実file削除試験は行わない |
| 実folder事前確認 | 隔離した専用test-folderと合成fileのみ。principalごとのowner、共有、継承、limited-access、capabilities、quota条件を観測 | 非公開の証拠に実値を保持し、公開文書には匿名化した結果だけ。対象・権限不明ならhold/no upload。共有やACLを無断修復しない |
| 4操作の適合 | list全ページ、metadata、合成fileの新規upload、承認済みstagingへのdownload/hash。principalごとに評価 | list可視性と完全性、identity、内容hash、owner/quotaを独立確認。API成功をcloud検証・archive認可としない |
| 既存file適合 | 初回app consentより前の合成file、他principal/他PC作成file、アプリ対象への明示共有有無を比較 | 特にdrive.fileの対象範囲を確認。見えない/不完全なlistingは不在証明にならず、scope不足不明ならhold/no upload |
| 失敗時適合 | scope不足、permission revoked、失効/refresh失敗、quota不足 | 実試験での権限変更・失効操作も限定計画で個別承認。quotaを実際に枯渇させず、発生試験はmockを基本とする。既存file/元データを保持 |

実folder試験でも削除、実ログupload、既存運用物の上書きは計画しない。専用test-folderの後片付けをアプリのcleanup能力として追加しない。試験物の保持・後処理は別の明示手順で扱う。

I1/A1/S1は選択済みだが、残るstore/実ACL等の判断、対象folderの証拠と限定実施の承認が整う前はproduction uploadとlive接続を禁止する。限定試験の例外は承認された対象・操作だけに限定し、本番運用への認可へ昇格させない。

## 6. Dry Run Aと残るゲート

Dry Run Aはmock/supplied dataのみで、live auth/network、refresh、store更新、download bytes取得、意図的ファイル書込みを行わない。資格・認証・root不足を作成/修復で補わず停止する。T1/T2の存在や有効なtokenをAの接続許可にしない。[A承認](dry-run-side-effect-policy-proposal.md)、[Dry Run設計](../../design/dry-run-execution-design.md)

通常実行の将来設計でも、C-01/C-02、単一JSON引数等の安全なIPC、role/root/排他、request/response相関、1 API試行・PS-only retry、両PC証拠と現在cloud検証は別ゲートである。認証選択、公式資料の確認、helper/schema/CI成功だけではruntime受け入れにならない。

## 7. 独立した回答欄と承認後の次作業

| 判断 | 選択済み/残る回答 | 併せて確定する条件 |
| --- | --- | --- |
| Google プリンシパル | I1を選択済み。I2/I3は未採用 | 実principalを公開文書へ記載せず、PC別照合・共有・所有/quotaの確認方法 |
| 認証方式 | A1を選択済み。A2/A3は未採用 | Desktop client/consent条件、または別構成のMy Drive適合・管理条件 |
| スコープ | S1を選択済み。S2/S3/S4等への自動拡大なし | 4操作と既存fileに必要な範囲。read系だけではupload不可。不足時は停止し自動拡大なし |
| 実folder ACL | 最小実権限の確認方針 / 保留 | principal別の継承・limited-access・capabilities、変更する場合の独立承認 |
| ストア | T1を選択済み。T2/T3は未採用 | provider/user境界・ACL・復旧・backup・refresh/失効/reconsent手順 |
| 限定実試験 | 計画具体化へ進む / 保留 | この回答だけで実行せず、対象・操作・証拠保管・停止条件を別途承認 |

一部だけ回答し他を保留できる。未回答項目を実装都合で補完せず、適合確認が不足する依存作業は停止する。推奨・承認記録を本書から推定しない。

承認後は、(1) 判断記録と規範契約の整合、(2) SDK選定とpublic-client flow/principal照合/暗黙retry/refresh副作用の実装前調査、(3) store保護・復旧の具体設計、(4) 合成fixture、(5) 個別承認された専用test-folder計画と実施証拠、の順に具体化する。成功しても対象外folder・別principal・本番適用を自動認可しない。C-27配布identityの決定は別途残す。

## 8. 公式資料の確認範囲

公式資料の確認日は2026-10-24 JST。各節のURLはanalystが確認した一次資料の短い要約であり、SDK、現account、実folder、store、task動作を検証した証拠ではない。候補の利点・復旧設計はproject上の比較で、Google/Windowsの保証ではない。I1/A1/S1/T1の方針採用と、具体SDK/store/provider・実folder資格の未決/未検証を区別する。
