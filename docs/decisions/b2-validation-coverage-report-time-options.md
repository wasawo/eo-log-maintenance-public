# B2 validation網羅性・report生成時刻の判断資料

- 状態：未承認の比較資料。推奨・選択済みの案はなく、資料のmergeは方針承認ではない。
- 確認基準：main `b3ad373`（PR #36）と停止記録 `a9b68a8`。PR #36のfloat拒否は完了した修正として維持し、数値canonical契約を再検討しない。
- 対象は二つの独立した未決事項。コード/schema/tests/設定・規範承認状態を変更せず、実装・実OS/Drive接続・保存/公開を開始しない。

## 1. 現在の根拠と不足

| 根拠 | 確認した現況 | 未決事項 |
| --- | --- | --- |
| [source builder](../../Common/SourceInventoryEvidenceBuilder.py#L240-L246) | `validation` の生成で `"status": "completed" if not validation_errors else "incomplete"` とし、同じobjectに件数とerrorsを入れる | errorありという結果と、分類処理を全入力に尽くしたかというcoverageを分離していない |
| [B2契約](../design/run-input-evidence-v1-proposal.md) §3–4、[B2 schema](../../contracts/run-input-evidence-v1.schema.json) | completed/incomplete/failedを区別し、completed列挙の全entry分類・件数照合を要求 | validation.statusとerror集合の網羅性の関係は未確定。count/digest一致だけでは未観測errorがないと証明できない |
| [OSD-03承認とT-06](osd-03-status-aggregation-options.md) §2/6 | relevant errorを保持しrun成功を禁止。一方で、全対象集合とerror scopeが独立に確立した既知期間はcompleteになり得る | coverage根拠不足を、関係のない期間のcompleteへ補完してはならない |
| [report契約](../design/aggregation-report-v1-proposal.md) §4–7・R5-A、[現builder](../../Common/AggregationReportBuilder.py) | exact manifest/B2 bytesと明示生成UTC等から決定的bytesを返す。生成UTCを丸めず保持し、自動clock取得もfinish時刻への置換もしない | 後日、exact manifest+B2だけから同じ生成UTCを得る永続出所が未決 |

sourceの上記一行は実装の観察であり、validation.statusの意味を承認した記録ではない。現builderはvalidation incompleteの網羅性を件数だけで補わず、既知の失敗がない期間をindeterminateとする。completed validationでも独立したinventory・全entry/error accounting・error scope等の条件が必要で、文字列statusだけではcompleteを認めない。

## 2. V: validation coverageの比較

| 候補 | 定義・変更候補 | 互換性と制約 | 承認後に必要な試験 |
| --- | --- | --- | --- |
| V1: 既存completedの意味をformal化 | completedを「全対象の分類処理完了」と定義し、errorの有無と独立させる。v1にfieldを追加せず、source builderとconsumerのstatus生成/解釈を整合 | 現sourceの「errorあり→incomplete」を変更するため意味と互換性のレビュー・承認が必要。過去incompleteをcount一致だけでcompletedへ変換しない。errorのあるcompletedもrun成功にはしない | 全分類完了＋error、途中停止＋部分error、errorなし未完、T-06の独立期間を分ける。旧recordは原bytes保持・自動修復なし |
| V2: 新versionでcoverage情報を分離 | error結果と処理網羅性を別に表す情報を新versionへ追加する候補 | field名・型・source・必要証拠・新version値は未選定。v1に未知fieldを足さない。writer/reader/参照version/配布の対応と旧版扱いを明示判断する | 同じerrors/countでもcoverageが異なる入力、新旧版の受理/拒否、欠落・矛盾・重複key・不正型、snapshot転用を検査 |
| V3: 現行の保守的holdを維持 | coverage未証明のincomplete/failedからno_workやcompleteを出さない。errorと独立した進捗をreportに残す | 新しいcoverage成功経路を作らない。妥当な作業進捗を保存できても、期間資格不足は解消しない | known failed/unknown/関連errorはincomplete、失敗のない期間も必要coverage不明ならindeterminate。only-invalid/列挙失敗をno_workにしない |

全案で、run statusは既承認OSD-03の集計に従う。verified進捗とrelevant errorがあればpartial_failureとしてerrorを保持する条件は維持し、列挙失敗等のfailure条件も変えない。unclassifiable errorから期間を推測せずrun scopeへ残す。既知期間のcompleteは承認済み条件を満たす場合だけで、V1/V2の名称やschema構造だけで資格を得ない。

## 3. G: generated_at_utcの永続出所と再生成

現builderの「同じexact bytes・同じ参照・同じ生成UTC等から同じreport bytes」と、R5-Aの「exact manifest+B2だけから後日同一bytesを再生成」は異なる。生成UTCをcallerが再供給できるというだけでは、その値の永続出所・信頼性は証明されない。同一report identityで異なるbytesは現行契約上conflictで、上書きの理由にはならない。

| 候補 | 生成UTCのsource/意味の候補 | 変更・互換性・残る確認 | 承認後に必要な試験 |
| --- | --- | --- | --- |
| G1: immutable入力時刻をderived anchorにする | exact入力内の承認された時刻と導出規則を使う。どのfield/選択関数かは未選定 | `generated` を実build時刻ではなくderived anchorとする意味のレビューが必要。元finish時刻を黙って代入しない。入力間の順序・精度・未知値の拒否と、R5-Aへの適合を明記 | 同一入力からanchor再現、精度保持、入力時刻の欠落/矛盾/順序不正、変更された入力への転用拒否 |
| G2: immutable build intent/metadataを新設 | 初回に決めた生成UTC等を不変の追加artifact/metadataとして保持する候補 | 追加入力と新artifact、identity/束縛・lock・atomic publication・中断/再試行・ACLが必要。exact manifest+B2のみというR5の改訂も必要。field/source/格納先は未選定 | intent前後の中断、同一identity同一/別内容、原bytes/hash束縛、欠落/変更時のhold。保存成功を認可にしない |
| G3: 毎回の実clockを使う | 再build時点のclockを新たな生成UTCにする候補 | 同じidentityでもbytesが変わり得て現R5-Aに適合しない。採用には明示改訂が必要で、現在のconflict規則へ暗黙例外を追加しない | 異なる時刻なら異なるbytes/conflictとなる現挙動を確認。改訂後のidentity/保存規則は別途決定 |
| G4: 保留 | caller-supplied生成UTCの現builder範囲に留め、永続出所を確定しない | 後日の同一bytes再生成を保証しない。仮のclock、finish置換、別保存物を実装で追加しない | 現pure builderの入力条件と未保証範囲を区別し、出所不足の再生成を完了扱いしない |

どの候補でも、既承認のUTC/信頼できる現在時刻・最大5分の未来許容、信頼不可時のfail-closedを維持する。historical evidenceの古さだけを失効理由にしない。生成UTCを丸めず、現builderが保持する最大11桁の小数精度を失わない。候補だけで新しいfield・source・精度/正規化規則を確定しない。finishとの順序等、現builderの検査を省略する変更も本資料では行わない。

## 4. 独立した回答欄

| 論点 | 選択欄（未回答） | 回答に必要な条件 |
| --- | --- | --- |
| validation coverage | V1 / V2 / V3 / 保留 | completedの意味または新coverage情報の契約、source、旧版互換、error網羅性を支える証拠 |
| report生成時刻 | G1 / G2 / G3 / G4 / 保留 | 時刻の意味と永続source、導出/保存/再生成条件、必要なR5改訂とconflict扱い |

片方だけ回答して他方を保留できる。未回答を実装都合で埋めず、資料mergeや純粋schema検証の成功を契約承認・実OS/Drive資格・本番適用の認可にしない。v1 manifestやB2数値canonical規則、source/root/排他/現在cloud内容の独立ゲートは維持する。

## 5. 承認後の作業と追加合成vectors

契約の明示承認と必要な互換性判断を先に記録し、その範囲で契約/schema/純粋builder/producer/consumerの変更と合成試験を分ける。純粋schema/semantic検証は実OS/Drive資格を代替せず、保存/公開を伴う案は別のlock・root/ACL・atomic publication・対象限定検証ゲートを満たす必要がある。

以下は**今回未実装・未実行の追加候補**であり、既存テストの成功を新しい意味の証拠として転用しない。

| vector | 確認する期待値 |
| --- | --- |
| T-06とcoverage | relevant unclassifiable errorを消さずrun partialを維持。独立inventory/error scopeを証明できた期間だけcomplete、未証明ならindeterminate |
| incomplete/failed | validation/列挙未完または失敗をno_work/completeへ昇格しない。既知の期間失敗はincompleteとして保持 |
| accounting矛盾 | count合計、invalid件数とerrors、error IDs重複/順序、inventory/digest/identity矛盾を拒否。数値floatのPR #36拒否は維持 |
| deterministic time | 同一の承認済み入力と同一時刻でbytes一致。異なる時刻/出所で同一identityを上書きしない。G1/G2を採る場合はそのsource再現性を追加検証 |
| clock境界 | 未来許容ちょうど/直後、時刻不明・信頼不可、finish前の生成UTC・start/finish逆転、小数末尾差、古い正当なhistorical入力を区別 |

今回の検証範囲は文書リンク・索引・記述整合・diffのみ。B2 coverageや時刻の新しい意味を実装・承認したものではない。
