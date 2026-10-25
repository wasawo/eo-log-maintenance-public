# Manifest v1 transition snapshot inspection

2026-10-25。根拠は[採用済み遷移表](manifest-state-transition-v1-proposal.md)、[C1〜C4](../decisions/osd-02-crash-concurrency-options.md)、[OSD-03](../decisions/osd-03-status-aggregation-options.md)。実装は[ManifestTransitionInspection.py](../../Common/ManifestTransitionInspection.py)。

`inspect_manifest_transition(previous_bytes, proposed_bytes, manifest_schema=...)`はexact JSON bytesと信頼済みstatic schemaを受ける純粋検査である。`previous_bytes=None`は新規作成要求に限り、保存先の不在証拠ではない。

- schema/JSON/version、run識別情報・開始UTCの元表記、凍結inventory集合・filename/size/hashと重複pathを検査する。schema外部参照、重複JSON key、不正数値を拒否する。
- 新規runはrunning・各fileはpendingのみ。変更されたfileは掲載13ペア、既存runningからは掲載4ペアのみ。変化のないfileは遷移に数えず、同じfile状態のmetadata更新は拒否する。
- verificationのstatus/method/hash対応とrun内時系列を検査し、UTC小数11桁まで保持する。verifiedは同じ観測hash、mismatchは異なるhashを必要とする。unavailable/ambiguous/verification failedはunknownへ対応し、uploaded→failedはmismatchを要求する。
- 終端fileのfieldを保持する。終端runはexact bytes一致だけを変更なしとし、書式だけの変更も拒否する。入力を変更せず、I/Oや実行を行わない。

結果は固定metadataのみ。不正入力は固定reason_codeの`ManifestTransitionError`で、raw入力/path/run IDや例外chainを露出しない。通常結果は`status=requires_runtime_evidence` / `reason_code=listed_pairs_only`で、掲載ペアの検査に限る。`file_transition_count`は変更ペア数、`aggregation_required`はrun終端かを示す内部metadataで、manifestの新fieldではない。終端runの同一bytesは`status=unchanged`だが、archiveや実行の認可ではない。

実writerは別途、C1/C2の実所有権・mutex・原子的更新と現在性、metadata-first stagingと内容照合、実upload応答、OSD-01の完全なDrive内容/不在照合とretry条件、信頼できる現在UTC・未来/鮮度・root/FS/使用点を検証する。planning pendingとupload pendingは前状態とevent履歴で区別し、snapshotから履歴を補完しない。

run終端はexact immutable B2等による既存report builderのOSD-03集約検査が必要で、本helperは集約を認証しない。C3のcrash-left runningは保全し、回復後も新runを作る。掲載ペアを根拠に中断履歴を書き換えず、retry枯渇/timeout/不完全一覧だけでfailedや再送へ進めない。writer・証拠provider・永続化・runtime受け入れは未実装。[合成試験](../../tests/test_manifest_transition_inspection.py)はsnapshot/pair検査に限る。

## 終端planとB2／report生成の接続

同moduleの`prepare_terminal_manifest_transition`は、既存のexact prior/proposed manifest bytesと固定B2 bytes、参照先の安全な相対path、信頼済みstatic schema、現在UTCとreliableを要求する。先に上記遷移検査を実行し、続けて既存report builderでB2のdigest・scope・凍結inventory一致、終端fileの検証結果、OSD-03集約status/outcome、G1時刻と未来時刻条件を検査する。どちらかが不成立ならplanを返さず、入力statusや証拠を修正しない。

返すimmutable `TerminalManifestPlan`はexpected_bytes/proposed_bytes/evidence_bytes/report_bytesを結び付ける内部オブジェクトで、保存schemaのfield追加ではない。reportは**提案manifest**のexact bytesとB2 bytesをhash参照する。保存済みmanifestの証拠、commit receipt、publicationの成功ではなく、may_publish/may_archive/may_change_stateは常にfalse。reprへ内容を出さない。

missing priorを新規runへ置き換えず、running提案から終端reportも作らない。終端runの同一bytesは決定的に再生成できるが、再保存/再実行の許可にしない。参照pathは字句検査だけで、読取元rootや実保存先の資格は確認しない。B2が本当に固定・真正・最新であることは外部gateで、異なる呼出し間のB2差替えや同じbytesへのrollbackをこのplanだけで検出できるとはしない。

[接続試験](../../tests/test_terminal_manifest_plan.py)はT01〜T12相当の両log種別、PC-B、正しい集約でも不正遷移/凍結inventory変更、掲載ペアでも偽成功/未終端file、B2改変・関連errorとno_work、終端不変・欠落prior・時計/schema/path不正、exact非canonical bytes・決定性・I/Oなしを確認する。C1/C2の実比較更新、実upload/Drive内容、履歴event証拠、真正な使用点readback、marker-lastの実publication、Tier B/Cとruntime受け入れは引き続き未完。
