# B2 validation網羅性・report生成時刻の判断資料

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

- 状態：V1（B2 completedの意味）とG1（不変入力からの生成UTC導出）を利用者承認済み（2026-10-24）。[選択履歴と確定規則](selected-policy-decisions-20261024.md)に従い、代替案は未採用の比較履歴として保持する。資料merge自体を承認根拠にはしない。
- 確認基準：main `b3ad373`（PR #36）と停止記録 `a9b68a8`。PR #36のfloat拒否は完了した修正として維持し、数値canonical契約を再検討しない。
- 対象は独立して選択された二つの仕様。選択と実装完了を分離し、今回コード/schema/tests/設定の変更、実OS/Drive接続・保存/公開を開始しない。

2026-10-25実装追従：source producerはV1へ、report builderと参照validatorはG1へ追従した。以下の実装比較は選択時点の履歴として残す。正式writer/公開・runtime受け入れは未完了。

## 1. 選択時点の根拠と不足

| 根拠 | 確認した現況 | 決定と残る追従 |
| --- | --- | --- |
| [source builder](../../../Common/SourceInventoryEvidenceBuilder.py#L240-L246) | `validation` の生成で `"status": "completed" if not validation_errors else "incomplete"` とし、同じobjectに件数とerrorsを入れる | errorありという結果と、分類処理を全入力に尽くしたかというcoverageを分離していない |
| [B2契約](../../design/run-input-evidence-v1-proposal.md) §3–4、[B2 schema](../../../contracts/run-input-evidence-v1.schema.json) | completed/incomplete/failedを区別し、completed列挙の全entry分類・件数照合を要求 | V1でcompletedは全入力の分類処理完了、error有無と独立と確定。producer/consumer追従は未実装。count/digest一致だけでは網羅性を証明できない |
| [OSD-03承認とT-06](osd-03-status-aggregation-options.md) §2/6 | relevant errorを保持しrun成功を禁止。一方で、全対象集合とerror scopeが独立に確立した既知期間はcompleteになり得る | coverage根拠不足を、関係のない期間のcompleteへ補完してはならない |
| [report契約](../../design/reference/aggregation-report-v1-proposal.md) §4–7・R5-A、[現builder](../../../Common/AggregationReportBuilder.py) | exact manifest/B2 bytesとcaller指定生成UTC等から決定的bytesを返す実装 | G1で二入力の終了UTCをsourceとする規則が確定。導出・不一致拒否・正式再生成への追従は未実装 |

sourceの上記一行は実装の観察であり、V1へ追従した出力ではない。現builderはvalidation incompleteの網羅性を件数だけで補わず、既知の失敗がない期間をindeterminateとする。採用V1も過去incompleteを修復・昇格せず、completed validationでも独立したinventory・全entry/error accounting・error scope等を要求する。文字列statusだけではcompleteを認めない。

## 2. V: validation coverageの比較

| 候補 | 定義・変更候補 | 互換性と制約 | 承認後に必要な試験 |
| --- | --- | --- | --- |
| V1: 採用・既存completedの意味をformal化 | completedは「全入力の分類処理完了」でerrorの有無と独立。既存field集合/status値を維持し、新coverage field/versionを追加しない | 意味の選択は承認済み。現source/consumerの追従・互換性検証は未実装。過去incompleteをcount一致だけでcompletedへ変換せず、errorのあるcompletedもrun成功/no_workにしない | 全分類完了＋error、途中停止＋部分error、errorなし未完、T-06の独立期間を分ける。旧recordは原bytes保持・自動修復なし |
| V2: 未採用・新versionでcoverage情報を分離 | error結果と処理網羅性を別に表す情報を新versionへ追加する候補 | field名・型・source・必要証拠・新version値は未選定。v1に未知fieldを足さない。writer/reader/参照version/配布の対応と旧版扱いを明示判断する | 同じerrors/countでもcoverageが異なる入力、新旧版の受理/拒否、欠落・矛盾・重複key・不正型、snapshot転用を検査 |
| V3: 未採用・現行の保守的holdのみを維持 | coverage未証明のincomplete/failedからno_workやcompleteを出さない。errorと独立した進捗をreportに残す | V1採用後も、証拠不足時のholdは維持。現実装の未追従をV3採用と読み替えない | known failed/unknown/関連errorはincomplete、失敗のない期間も必要coverage不明ならindeterminate。only-invalid/列挙失敗をno_workにしない |

全案で、run statusは既承認OSD-03の集計に従う。verified進捗とrelevant errorがあればpartial_failureとしてerrorを保持する条件は維持し、列挙失敗等のfailure条件も変えない。unclassifiable errorから期間を推測せずrun scopeへ残す。既知期間のcompleteは承認済み条件を満たす場合だけで、V1/V2の名称やschema構造だけで資格を得ない。

## 3. G: generated_at_utcの永続出所と再生成

現builderの「同じexact bytes・同じ参照・同じcaller指定生成UTC等から同じreport bytes」と、G1/R5-Aの「exact manifest+B2から同じ生成UTCも導出して再生成」は異なる。G1のsourceと規則は確定したが、現builderの追従は未実装。同一report identityで異なるbytesはconflictで、上書きの理由にはならない。

| 候補 | 生成UTCのsource/意味の候補 | 変更・互換性・残る確認 | 承認後に必要な試験 |
| --- | --- | --- | --- |
| G1: 採用・immutable入力時刻をderived anchorにする | exact manifest.finished_at_utcとexact B2.enumeration.finished_at_utcをUTC instantとして比較し、遅い方の元文字列を採る。同instantならmanifestの元表記 | generatedは実書出時刻ではなく不変入力の基準時刻。丸め/切捨てなし。R5-Aのexact二入力・identity・冪等性/conflictを維持。現caller時刻input実装の追従は未完 | 同一入力からanchor再現、精度保持、同instantの表記tie、欠落/矛盾/順序不正、不一致caller時刻や変更入力の拒否 |
| G2: 未採用・immutable build intent/metadataを新設 | 初回に決めた生成UTC等を不変の追加artifact/metadataとして保持する候補 | 追加入力と新artifact、identity/束縛・lock・atomic publication・中断/再試行・ACLが必要。exact manifest+B2のみというR5の改訂も必要。field/source/格納先は未選定 | intent前後の中断、同一identity同一/別内容、原bytes/hash束縛、欠落/変更時のhold。保存成功を認可にしない |
| G3: 未採用・毎回の実clockを使う | 再build時点のclockを新たな生成UTCにする候補 | 同じidentityでもbytesが変わり得て現R5-Aに適合しない。採用には明示改訂が必要で、現在のconflict規則へ暗黙例外を追加しない | 異なる時刻なら異なるbytes/conflictとなる現挙動を確認。改訂後のidentity/保存規則は別途決定 |
| G4: 未採用・保留 | caller-supplied生成UTCの現builder範囲に留め、永続出所を確定しない比較案 | 現実装がcaller指定のままであることをG4選択と扱わない。旧reportはG1へ黙って書き換えない | 現pure builderの入力条件と追従未完を区別し、再生成を完了扱いしない |

採用G1でも既承認のUTC/信頼できる現在時刻・最大5分の未来許容、信頼不可時のfail-closedを維持する。historical evidenceの古さだけを失効理由にしない。生成UTCを丸めず、既存の対応精度を保つ。値の欠落・不正・時刻整合の矛盾は停止し、実時計/仮値/別保存物で補わない。identity/digest、start/finish順序、現在UTC/未来許容の検査は維持し、旧reportを書き換えない。

## 4. 独立した回答欄

| 論点 | 選択履歴 | 追従に必要な条件 |
| --- | --- | --- |
| validation coverage | V1採用（2026-10-24） | 既存field/status維持、error有無と分類完了を分離。旧incomplete保全、producer/consumer・合成試験追従 |
| report生成時刻 | G1採用（2026-10-24） | 二入力の終了UTCの遅い元文字列、同instantはmanifest表記。丸めなし、R5/identity/conflict維持、実装追従 |

[第1回回答](selected-policy-decisions-20261024.md#第1回回答)の②V1/③G1が根拠で、C-01のP1とは独立した選択。資料mergeや純粋schema検証の成功を実OS/Drive資格・本番適用の認可にしない。v1 manifestやB2数値canonical規則、source/root/排他/現在cloud内容の独立ゲートは維持する。

## 5. 承認後の作業と追加合成vectors

V1/G1の意味の選択は記録済みで、producer/consumer・純粋builder・合成試験の追従と互換性確認は未実施。既存field/statusとexact二入力を維持し、未知fieldや新versionを暗黙追加しない。純粋schema/semantic検証は実OS/Drive資格を代替せず、実保存/公開は別のlock・root/ACL・atomic publication・対象限定検証ゲートを満たす必要がある。

以下は**今回未実装・未実行の追加候補**であり、既存テストの成功を新しい意味の証拠として転用しない。

| vector | 確認する期待値 |
| --- | --- |
| T-06とcoverage | relevant unclassifiable errorを消さずrun partialを維持。独立inventory/error scopeを証明できた期間だけcomplete、未証明ならindeterminate |
| incomplete/failed | validation/列挙未完または失敗をno_work/completeへ昇格しない。既知の期間失敗はincompleteとして保持 |
| accounting矛盾 | count合計、invalid件数とerrors、error IDs重複/順序、inventory/digest/identity矛盾を拒否。数値floatのPR #36拒否は維持 |
| deterministic time | G1のexact二入力から同じ元時刻表記/bytesを再現。同instantならmanifest表記、小数精度保持。不一致caller時刻・変更入力を拒否し同一identityを上書きしない |
| clock境界 | 未来許容ちょうど/直後、時刻不明・信頼不可、finish前の生成UTC・start/finish逆転、小数末尾差、古い正当なhistorical入力を区別 |

今回の検証範囲は文書リンク・記述整合・diffのみ。V1/G1の承認記録と文書を整合する作業であり、実装追従・再生成受け入れの完了ではない。
