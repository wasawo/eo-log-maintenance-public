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
