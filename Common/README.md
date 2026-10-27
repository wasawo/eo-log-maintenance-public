# Common PowerShell functions

`PowerStatusObservation.py`は[Windows AC電源観測](../docs/design/power-status-observation.md)を読取専用で行います。成功時のACLineStatusだけを使い、不明・API失敗を接続済みにせず、実行/継続の許可やAC切断監視は行いません。

`CompletionWaitAttempt.py`は[確認予算の試行planと使用点検査](../docs/design/completion-wait-budget.md)を扱う純粋helperです。元checkpoint bytesに結び付けて1件だけ追加したcandidateを再読込検査し、保存前/記録後の観測bytes・scope・現在時計/期限・実行条件/ACを再検査します。実保存・確認は行わず、全may_* flagはfalseです。反復検査は一回限りのcommit receiptではなく、接続fixtureの比較更新もメモリmockです。

`CompletionWaitCheckpoint.py`は[確認予算checkpoint](../docs/design/completion-wait-budget.md)のclosed schemaと期待scope・現在UTCを使う純粋readerです。元bytes・時刻文字列・履歴順を保持し、欠落/破損から予算をリセットしません。既存helperへの変換で精度を失う時刻は拒否し、実保存・現在性/rollback防止・試行前永続計上は別ゲートです。

同moduleの`inspect_completion_wait_checkpoint_transition`は前後2記録のstart/既存履歴原文字列を保全し、exact再掲載か1試行だけの追記を検査します。既存試行plan生成へ接続済みで、短縮/置換/一括追記を拒否します。全許可false、実保存/CAS/rollback防止や確認receiptではありません。

`observe_completion_wait_checkpoint_file`は明示既存絶対pathとcaller指定bytes上限でread-only観測します。祖先/reparse・単一link・path/handle signature・初期size+1上限を検査し、schema読取り後もmetadataを確認します。元bytesを保持して全許可false、欠落時作成/更新なし。実root/FS/owner資格やrollback/ABA防止は別gateです。

`assess_completion_wait_checkpoint_file`は毎回のfile読取を既存予算のcheck_due/wait/hold判定へ接続します。元checkpoint/次候補UTCを保持する非認可観測で、試行消費・plan作成・sleep/taskを実行せず、全確認/待機/Archive/状態変更許可false。欠落/破損/不明を空履歴や通常waitへ補完しません。

`CompletionWaitAttempt.py`の`prepare_completion_wait_attempt_from_file`はこの読取から1試行planを構築します。`inspect_completion_wait_attempt_file_usepoint`はplan/資格の純粋事前検査後に毎回fileを再読取し、保存前はexpected/保存後はproposed bytesを再確認します。両方ともread-onlyで、確認/状態変更/Archiveを認可せず、正式CAS/providerの資格は別gateです。

`ManifestTransitionInspection.py`は[遷移表の前後snapshot検査](../docs/design/manifest-transition-inspection.md)を行う純粋helperです。schema/identity/凍結inventory、verificationと時刻整合、終端不変性、未掲載ペアを確認します。掲載ペアの結果も`requires_runtime_evidence`であり、所有権・staging・Drive・OSD-03集約・永続更新の認可にはなりません。

同moduleの`inspect_manifest_history`は初期登録からの明示snapshot tupleを検査し、登録pendingとUpload直前pendingをpath単位で区別します。登録pendingからuploaded/unknownへの飛越しやUpload pendingからのstaging再開を拒否し、retry pendingを別計数します。結果は件数のみ/全許可falseで、真正な履歴・event証拠・実writerの受け入れではありません。

履歴中のUpload pending境界にはfile別の最大4回上限を適用します。5回目は拒否し、重複snapshot/配列順で予算を消費/リセットしません。上限到達だけでunknownをfailedへ変えず、実API回数/待機/不在照合は認証しません。

`prepare_terminal_manifest_history`は独立contextで初期planを再構成し、exact先頭から終端までの連続履歴とB2/OSD-03/G1 report生成を接続します。終端の繰返しでも本来のrunning priorを保持し、途中省略や集約不備を拒否します。結果は専用非認可planで、event/永続化や実copy/Driveの証明ではありません。

`revalidate_terminal_manifest_history`は独立履歴/B2/現在running bytes/AC/contextを要求し、型/flagsとexact対応を確認して全plan/reportを毎回再導出します。結果は引き続き非認可で、実provider/現在性/write leaseではありません。tests専用の所有lock→別candidate保存/読戻し接続でも元runningを更新しません。

`DriveRequestPath.ps1`の`Test-DriveRequestFilePath`と`DriveRequestPath.py`の`is_drive_request_file_path`はC-01 P1/L1のrequestファイルパス字句だけを検査する純粋bool helperです。drive-rooted形と各componentを独立して検査し、予約stemはASCIIだけで大小比較します。文字列の修復/正規化、固定maxLength、file/root/FS照会は行いません。request schemaも同じgrammarを適用し、指定先/root/使用点の認可と正式adapter接続は別ゲートです。

`DriveResponseSemantics.ps1` の `Test-DriveResponseSemantics` は、実request由来の期待ID/operation、decoded IDictionary response、整数exit codeを明示入力し、ordinal完全一致と契約§6のexit/envelope/error-code対応、固定code別retryable真偽表を検査します。IDをUUID正規化せず、int/long/BigInteger以外のexitはcoerceしません。`DRIVE_TRANSIENT_FAILURE`だけtrue、他8codeはfalseが必須で、非boolと矛盾を拒否します。出力は固定Status/ReasonCodeのみで、`consistent` / `correlation_exit_mapping_consistent` はこれらの整合を意味します。resultの信頼、運用続行、retry許可、cloud検証ではありません。transport/UTF-8/単一JSON/重複key/schema、C-01/C-02、RETRY-02のorchestration、IPC全体・runtime受け入れは残ゲートです。helperはprocess/file/network/auth/retry/sleep/lock/logを呼びません。

`AggregationReportBuilder.py` は、callerがメモリで供給する信頼済みmanifest/B2/report schemaとexact UTF-8入力bytesから、A2/B2整合・inventory照合・terminal verificationを検査し、期間別/全run集計と参照hashを導出して決定的UTF-8 bytesを返す純粋helperです。schemaの外部参照を拒否し、schemaロード・source再走査・時刻自動取得・ファイル/Drive/lock/publication/status変更は行いません。G1生成UTCはexact入力の終了時刻から導出し、同時ならmanifestの元表記を保持します。任意のcaller時刻は照合値に限り、不一致を拒否します。信頼できる現在UTC・未来許容は明示入力とし、11桁までの小数を保持します。B2 validationがincompleteの場合、供給件数の整合だけで全入力の網羅性を証明せず、失敗のない期間もindeterminateにします。completedの検証で全entry/errorがaccount済みなら、unclassifiable run-scope errorと独立した既知期間のcompleteを区別します。同じexact入力から同じbytesを再生成し、参照validatorもG1時刻を照合します。永続writer・公開・遷移強制とruntime/実root/cloud受け入れは別ゲートです。

PC-A / PC-Bで共有する関数と、レポートの参照先を検証するローカル補助モジュールを配置します。

実装資産と不足は[実装計画§9](../docs/development/implementation-workflow.md#9-既存の実装資産と不足)、実行順は同計画§3を参照してください。以下は補助処理の責務であり、正式ランタイムの完成を意味しません。

- ファイル名の実日付・保持期間判定、PowerShell版ガード、診断コード
- 設定の厳密な読込・未作成時のみ生成、既存rootの分離メタデータ検査
- 読み取り専用source inventory・A2/B2 digest・参照JSONの実バイト照合
- 単一/複数成果物の公開・検証、所有token lockと復旧分類
- 最新manifestの選択・読取、診断結果、private証拠形式と限定ACL形状
- 月次境界とPC-A確認予算の副作用なし観測

`AggregationReferencedArtifacts.ps1` は `validate_aggregation_artifacts.py` を呼び出し、`contracts/` の Draft 2020-12 schemaでレポートと参照先JSONを検証します。Python環境には `requirements-runtime.txt` の依存関係が必要です。検証対象は明示された信頼済みmaintenance root配下に限定し、失敗時は拒否します。

これらの補助関数は現時点で正式な同期・アーカイブエントリーポイントには未接続です。ロック・ソース列挙・公開には分離した部分実装がありますが、正式な制御経路への統合と実環境の受け入れは未完了です。Driveアダプター・現在内容の再検証・アーカイブ入口は未実装です。実ログ・Drive書き込み・削除は行いません。

PCごとのパスや権限は設定ファイルで与え、PC-Bではアーカイブ・削除機能を呼び出せない設計を維持します。

`RunInputEvidenceIntegrity.py` は既存のB2 evidenceオブジェクトに対して、承認済みA2 inventory digest、B2 canonical evidence digest、スキーマ、embedded inventoryの件数・順序整合性を検証する補助モジュールです。ソース列挙やファイル書き込みは行わず、公式エントリーポイントにも未接続です。manifestのtarget setとの照合、証跡の原子的公開、ロック／回復、Drive検証は別の未完了要件です。

`SourceInventoryEvidenceBuilder.py` は、明示されたローカルソースルートを読み取り専用で列挙し、ファイル名から同期対象期間を判定して、A2 inventory digest と B2 evidence を構築する合成テスト可能な補助モジュールです。ファイル内容の SHA-256 と読み取り前後の基本メタデータを照合し、列挙・読み取り・ハッシュ処理に不確実性があれば enumeration を incomplete にします。`serialize_evidence` はスキーマと A2/B2・件数整合性を検証して決定的な UTF-8 JSON bytes を返すだけで、ファイル公開や atomic write は行いません。正式なエントリーポイント、排他ロック、原子的公開、Drive 同期・再検証には未接続です。


`AtomicArtifactPublication.py` は、検証済み artifact bytes 1件を同一ディレクトリの一時ファイルに書き、flush/fsync 後にハードリンクの原子的な no-overwrite 作成で公開する補助モジュールです。同一内容の再試行のみ冪等扱いし、既存内容が異なる場合は拒否します。ファイルシステムがこの原子的作成を提供しない場合は fail-closed です。複数 artifact のトランザクション、run lock、クラッシュ回復、ディレクトリ永続化保証、正式エントリーポイントへの統合は別要件であり、未実装です。


`OwnedRunLock.py` は、Windows の machine-wide named mutex と exclusive create-only owner-token record を組み合わせた隔離ロック補助モジュールです。待機は最大60秒で、既存レコードや abandoned mutex は自動回復せず fail-closed とします。所有 token が一致する場合だけ自身のレコードを削除します。クラッシュ回復、manifest更新、Drive操作、公式エントリーポイント統合、アーカイブ・削除は行わず、これらは別の未完了要件です。


`CrashRecoveryDecision.py` はクラッシュ後の回復可否を証拠から分類する純粋な補助モジュールです。abandoned mutex、ロックレコードのscope/host整合性、旧所有者の終了確認、最新manifest候補の一意性、Manifest v1 schemaとidentity、Drive照合状態、未確定アップロード件数を fail-closed で判定します。許可結果は旧manifestを保持したまま新runとfresh inventoryを要求するだけで、ロック・manifest更新、run作成、ソース列挙、Drive、アーカイブ、削除、正式入口統合は行いません。合成テストとCI検証が完了するまでは受け入れ済みと扱いません。


`ArtifactSetRecovery.py` は、複数成果物の expected/staged/published SHA-256 と合成 commit marker を分類する純粋な補助モジュールです。marker と全 published artifact が厳密に一致した場合だけ `committed` を返します。部分公開や marker 欠落は未コミットとして照合を要求し、既存成果物を保持します。実際の公開・回復・manifest更新・Drive・アーカイブ・削除・正式入口統合は行わず、最終的な複数成果物プロトコルを確定するものでもありません。


`ArtifactSetPublication.py` は単一ファイルの no-overwrite 公開プリミティブを組み合わせ、成果物を決定的な順序で公開して最後に transaction marker を公開する補助モジュールです。途中失敗では公開済みファイルを保持し、ロールバックや削除をしません。複数ファイル全体の原子性を提供するものではなく、正式なエントリーポイントや Drive／manifest／アーカイブ／削除には未接続です。


`ArtifactSetDirectoryVerification.py` は、明示された1ディレクトリの実ファイル bytes を読み、SHA-256 と commit marker を照合して artifact-set classifier に渡す読み取り専用補助モジュールです。重複JSONキー、想定外エントリ、symlink、非通常ファイル、marker不正、読取失敗は fail-closed とします。修復・公開・上書き・削除は行いません。検証結果は一点時点の観測であり、ロック、検証後の変更防止、複数ファイル原子性、クラッシュ耐久性、Drive整合性を保証しません。正式エントリーポイント未接続であり、P0は未完了です。


`docs/validation/target-filesystem-acceptance.md` defines the evidence boundary for artifact-set publication and recovery: hosted Windows CI, disposable local-volume qualification on PC-A/PC-B, and separately gated synchronized/network target qualification. Current CI results do not prove target filesystem behavior, remote visibility, or power-loss durability. No official entrypoint integration or destructive operation is authorized by these helper modules.


## Read-only configuration structure loader

`Common/MachineConfiguration.ps1` provides
`ConvertFrom-EoMachineConfigurationJson` and `Read-EoMachineConfiguration`.
The reader accepts strict UTF-8 (optional BOM), returns a fresh validated object,
and never creates configuration, root directories, manifests or other artifacts.

The parser rejects non-object/malformed JSON, duplicate/unknown/missing keys,
wrong primitive types, role mismatch, non-drive-qualified/ambiguous path syntax,
and maintenanceLocal equality/ancestor/descendant overlap after normalization.
PC-B must omit allowArchive; PC-A may explicitly set a boolean true or false.
A true value is configuration data only, never archive authorization.

Errors are fixed reason codes without rejected values, file contents or private
paths. The package builder shares this structural parser and additionally
requires safe template defaults (PC-A allowArchive false).

This is structural/lexical evidence, not an approved-root filesystem gate.
It does not inspect actual target volumes, resolve short-name/reparse aliases,
prove cross-root physical separation, acquire a runtime lock, contact Drive,
or integrate official entry points. Those checks remain mandatory before effects.
The create-only bootstrap helper is implemented below; official installation/update integration and migration remain pending.

## Create-only configuration bootstrap helper

See [configuration specification](../docs/design/configuration-local-root.md#create-only-configuration-bootstrap-helper) for Initialize-EoMachineConfiguration, safety boundaries and pending deployment integration. Run tests/Test-MachineConfigurationBootstrap.ps1 for synthetic create-once and preservation checks.

SourceInventoryEvidenceBuilder checks source pathname and open-handle identity before/after hashing. Observable mismatch or unavailable identity keeps enumeration incomplete. This is not a snapshot or a guard covering later use; see [filesystem evidence](../docs/validation/target-filesystem-acceptance.md#source-hash-handle-identity-2026-10-23).

Source inventory rejects lstat symlink/reparse root/ancestors, rechecks queued directories, classifies fresh entry attributes and checks file paths before/after hashing. Unknown attributes fail closed. See [source reparse evidence and limits](../docs/validation/target-filesystem-acceptance.md#source-inventory-reparse-rejection-2026-10-23).

Lock/recovery evidence parsing rejects duplicate JSON keys and wrong primitive types; malformed lock records are preserved while the mutex is released. See [strict evidence scope](../docs/validation/lock-recovery-acceptance-gate.md#strict-lock-and-recovery-evidence-2026-10-23). This does not implement stale-lock disposition or operational recovery.

MachineConfigurationRootInspection.ps1 adds opt-in read-only metadata inspection of existing configuration roots. It is not runtime authorization; see [configuration scope](../docs/design/configuration-local-root.md#read-only-existing-root-metadata-inspection).

LatestManifestSelection.py independently parses the defined manifest basename and selects a unique validated latest start time from supplied observations. It never falls back to old success. See [selection scope and gates](../docs/design/latest-manifest-selection.md).

ManifestDirectoryReader.py adds read-only observations of the defined per-PC manifest directory and returns the exact validated byte snapshot plus SHA-256. Unknown/reparse entries, read uncertainty and observed changes block selection. Approved-root authority and runtime integration remain pending; see [selection scope](../docs/design/latest-manifest-selection.md).

Both directory-reader entry points accept caller-selected per-candidate/aggregate byte ceilings. All initial entry sizes, including older/foreign periods, are checked before payload opens; reads stop at initial size plus one byte on growth. Defaults do not impose a new schema ceiling. Report/evidence validator reads and entry/JSON complexity are outside these resource bounds.

RecoveryDiagnostic.py classifies supplied fixed gate observations into a sanitized, immutable, non-authorizing diagnostic result. Even all-satisfied observations produce review_required with may_change_state=false. It performs no I/O and does not establish the truth of its supplied observations.

RecoveryDiagnosticMutex.py acquires the existing global scope mutex without ownership-record I/O or token generation. It reports abandonment as non-authorizing evidence and releases/closes on completion or failure. It is an isolated diagnosis lease, not normal lock acquisition, approved-root qualification, or an operational recovery entrypoint.

PrivateRecoveryEvidence.py builds/validates private preservation metadata against supplied raw lock bytes, without runtime reads/writes or recovery authority. Only the trusted package schema is read. Opaque invalid lock bytes can be preserved without being accepted as a supported lock. See [private evidence contract](../docs/design/recovery-private-evidence-contract.md).

PrivateEvidenceAclProfile.py classifies a narrow supplied file-ACL shape using fixed trusted principal roles and explicit file read/write bits. It does not query SIDs/ACLs, evaluate complete Windows access, qualify roots or grant persistence. See [scope and unsupported cases](../docs/design/private-evidence-acl-profile.md).

PrivateFileSecurityDescriptor.ps1 normalizes supplied binary file descriptors for the narrow Python ACL profile. It preserves deny/order/flags/unsigned masks, rejects unsupported features, and performs no filesystem/token query or ACL writes. Its SID-bearing output is private internal data, not a public diagnostic.

MonthlyScheduleObservation.py observes the approved monthly boundary from supplied reliable UTC/session/account claims. It uses day 1 PC-B 20:00 / PC-A 21:00 JST; all results keep may_start_run=false. It never queries the host, reads completion records, creates tasks or starts work. See [observation scope](../docs/design/monthly-schedule-observation.md).

CompletionWaitBudget.py assesses the approved PC-A 24-hour/25-attempt hourly budget and returns immutable updated attempt histories only after revalidation. All advice denies archive/state-change authority. It performs no waits/tasks/Drive/persistence; trusted state binding and durable crash-safe accounting remain pending. See [budget scope](../docs/design/completion-wait-budget.md).

比較更新の[実Win32負例probe・資格調査](../docs/design/checkpoint-compare-provider-qualification.md)はtests専用で、実runtime providerとして配布しません。

同moduleの`Get-DriveRetryObservation`は[再試行観測](../docs/design/drive-retry-observation.md)として、完了した試行1〜4と応答整合から1/5/15分の候補を返します。upload一時失敗/timeoutは照合待ち、不正応答は拒否し、全結果MayRetry=falseです。実counter・sleep・再送・結果照合は実装しません。

`ManifestTransitionInspection.py`の`prepare_terminal_manifest_transition`は[終端plan](../docs/design/manifest-transition-inspection.md)として遷移検査とB2/OSD-03/G1 report生成を接続し、exact元/提案/証拠/report bytesを保持します。提案reportを実保存の証拠にせず、全may_*はfalseです。

`derive_aggregation_report`は現在時計を要求しない履歴reportの純粋な再導出です。参照validatorは読取済みexact manifest/B2から再導出し、reportの全field・件数・period/error順序を比較します。JSON whitespace/key順は許容し、偽集約や整数fieldのfloat表現を拒否します。通常builderの明示時計/未来時刻検査は維持し、履歴再導出から現在の適格性を推定しません。

参照validatorはreport/manifest/B2/schemaをpath・handle・親chain・前後metadataに結び付けて読み、成功直前にexact bytesを再確認します。resolve前のreparse属性とschema外部参照も拒否します。これは検出防御で、実効ACL/root認可・原子的snapshot・ABA排除の証明ではありません。

`ManifestDirectoryReader.py`の`read_latest_manifest_with_report`は[最新snapshotとreportのbinding](../docs/design/latest-manifest-selection.md)を行います。独立した選択bytes/pathとの一致と全report意味論を検査し、最後に同じ最新候補を再確認します。別run/別pathの正常reportを流用せず、新しい未完runから古い成功へfallbackしません。読取観測でありruntime/archiveの認可ではありません。

artifact-set classifier/directory verifierはoptionalな`expected_transaction_id`をexact比較し、期待hash集合のcopyとpath/handle・全file/marker・directoryの再観測を行います。未指定時の従来分類は保持します。期待値の真正性やreceiptの一回性、atomic snapshot・ABA排除を保証せず、実操作の認可にはしません。

`AtomicArtifactPublication.py`は公開前stagingと公開後finalのexact bytes/identity/親chainを検査し、同一既存fileもhandleと前後metadataに結び付けます。cleanupは同じ所有tempを再確認できる場合だけ行い、不明・差替え・内容変更tempは保全します。敵対的raceの完全排除、電源断耐久性、正式manifest比較更新の資格は与えません。

`ManifestTransitionInspection.py`の`prepare_initial_manifest`は独立run contextとexact B2から初期running/pending候補を構築し、schema・digest・scope/inventory・時系列を照合します。空/不完全/失敗B2を成功/no_workへ変えず、元bytesを保持します。全may_*はfalseで、run ID・時計・保存先不在を補完/認証しません。

初期plan生成でも既存filename分類を使い、内部整合するB2のeligible targetであっても文法外/実在しない日付は拒否します。source builderからの[隔離接続試験](../tests/test_initial_source_integration.py)は候補保存までを検証し、source使用点や実run/clockの資格は別gateに残します。

`SourceInventoryRevalidation.py`は[凍結B2とsourceの再観測](../docs/design/source-inventory-revalidation.md)を比較する読取専用helperです。独立scope/reference dateと完全な元coverageを要求し、再列挙/hashで観測が変わったら拒否します。元B2を更新せず、対象外fileの内容や後続使用点までの不変性を認証しません。全may_*はfalseです。

同moduleの`revalidate_initial_manifest_source`は、独立run contextで初期planを再構成し、AC/plan/flagsの不整合をsource I/O前に拒否してから毎回sourceを再観測します。全may_*はfalseで、旧観測をreceiptとして再利用する経路は設けません。使用点後の変化や実provider資格は別gateです。

`observe_initial_staging_copy`は独立run contextで初期planを再構成し、明示target/sequenceに対応する既存stagingの祖先chain・regular/単一link・前後identity/size/hashを確認します。source payloadを読まず、全操作許可falseの観測を返します。正式metadata/history、root分離/資格、コピー時に確保したidentityとの対応、後続Uploadの使用点は別gateです。

複数fileは`observe_initial_staging_copies`へ明示allocation tupleを渡します。全指定の事前検査・全sizeのhash前検査・全hash後のsignature/祖先chain照合で、全観測tupleか拒否のどちらかを返します。凍結sizeから変わったfileはopen前に拒否。空選択はno_workではなく、全結果は引き続き非認可です。

`inspect_initial_staged_drive_contents`は毎回のstaging一括再読取を、独立source信頼確認・Drive前後完全列挙・不足hash計画/完了集合の比較へ接続します。元basenameをexact比較し、PC suffixや出所を推測しません。共通Drive不備はlocal copy観測を保持して比較集合なしのheld。全Upload/retry/同期成功/状態変更/Archive許可falseで、API/正式metadata/Upload結果の証明ではありません。

source builderは[列挙完了前の再確認](../docs/design/source-enumeration-stability.md)でdirectory/child集合・identity/属性を再走査し、途中変更や不明を検出すると既存targetを保持したままcoverageをincompleteにします。最終bytes再hash・atomic snapshot・後続使用までの保護を証明するものではありません。

`DriveContentComparison.py`は[OSD-01の同一内容比較](../docs/design/drive-content-comparison.md)を内部観測から判定する純粋helperです。完全列挙・信頼済みsource・exact name/size/hashを要求し、cloud SHA未確認ならdownload hashを要します。比較候補は復元・同期成功・archiveの認可ではありません。

`DriveContentComparison.py`の`hash_downloaded_content`は完了済みdownloadのchunk列から実byte数/SHAを計算し、既存比較観測へ渡します。途中失敗・size超過/不足・完了不明では返さず、stream所有権・解放と実Drive ID/成功の資格はcaller/provider側に残ります。

`DriveContentComparison.py`の`collect_drive_listing`は内部page観測のfolder・成功・token連続性/終端・ID重複を検査し、全pageが揃った場合だけ比較用観測を返します。部分列挙を0件へ変換せず、実API/応答の真正性・resource管理はprovider側の未完gateです。

`SourceInventoryRevalidation.py`の`revalidate_comparison_source`はPC-A凍結B2の指定targetと毎回の実source再観測を比較元へ結び付けます。同名別pathを推測せず、sourceの独立信頼確認を必須とし、返却観測も復元・同期成功・archiveを認可しません。

`DriveContentComparison.py`の`compare_reobserved_drive_content`は前後2つの完全列挙観測を全file ID/metadataで照合し、変化なしの場合だけ既存比較を行います。順序差は許し、古い一意候補で変化を覆い隠しません。実再取得・観測の鮮度/真正性・ABA排除の証明や実行許可にはなりません。

`revalidate_comparison_sources`は複数の明示targetを1回の全source再観測へまとめ、比較元を指定順で返します。単一target APIも委譲して互換性を維持し、空選択・選択外変更・不完全coverageでも再検査を省略しません。

`compare_reobserved_drive_contents`は複数sourceの共通列挙/downloadを一括検査し、名前別indexから指定順に各比較結果を返します。共通不備は部分結果なしのheld、file固有不明は各結果のheldとし、batchのcomparedを同期成功へ変えません。

`plan_content_downloads`は完全列挙中の同名同size・cloud SHA欠落/未確認候補をIDごとにまとめ、不足hash観測の計画を返します。may_downloadもfalseで、計画や対象0件はdownload実行・同期成功・upload再送の認可になりません。

`compare_planned_drive_contents`は計画の再導出と、完了download ID集合・期待sizeの全件一致を要求して一括比較へ接続します。不足/余分/改変で部分結果を返さず、計画やhash一致を実行権限にしません。

`LogFunctions.ps1`の`Get-EoStagingCapacityObservation`はupload用の既承認容量式をBigIntegerで計算します。信頼未確認/不足を保留し、全結果MayCreateStaging/MayUpload=falseです。実空き容量の取得・予約・download容量方針は含みません。

`Get-EoStagingCapacityFromSizes`はcallerが明示選択した残りtargetのsize配列を全件検査し、BigInteger合計を容量観測へ渡します。残り対象やmanifest状態を推測せず、不正memberから部分合計を返しません。

`ManifestTransitionInspection.py`の`inspect_staging_target_sizes`はrunning manifest/B2のexact整合とscope/coverage/clockを検査し、明示path群のsize集合・合計だけを返します。pending等から対象を選ばず、元bytesを保持し、作成/Upload/Archiveの許可やPS transportを提供しません。

`MachineConfigurationRootInspection.ps1`の`Get-EoStagingFreeSpaceObservation`は既存directoryのcaller利用可能bytesをWindows APIから観測します。前後canonical/volume serial/file index観測を比較し、出力はBigInteger・FreeSpaceReliable=false・作成/Upload不可です。実root/FS/token資格や容量予約を証明しません。

空きbytes観測の内部directory identityはFileIdInfoの64-bit volume serial＋128-bit file IDも要求します。未取得/前後不一致は保留し、legacy 64-bit照合へfallbackしません。既存canonical文字列APIは互換を維持し、FS資格や権限は付与しません。

空きbytes観測はleafからdrive rootまでの祖先chainも前後照合します。leafのIDが同じでも親の差替え・chain欠落/長さ変化を保留し、内部path/IDを公開結果へ出しません。同時snapshot/ABA排除やroot資格は証明しません。

`observe_pc_suffixed_name`は元source basenameを保持してDrive候補名の_PCA/_PCBを拡張子前へ付けます。出所や衝突を判定せず、rename/Upload/上書き/Archive許可はfalse。候補名でB2を変更したりOSD-01のname照合を別名化したりしません。

`inspect_initial_inventory`は[初期inventory専用の読取観測](../docs/design/initial-inventory-observation.md)として、PC-A source再観測とDrive計画/hash/前後比較をpathへ結び付けます。共通不備でも選択/B2を保持し、運用manifest/同期成功/復元/Archiveへ昇格しません。

`summarize_initial_inventory`は専用観測とB2/対象対応を検査し、候補/保留/未比較・既知error等の件数だけを返します。path/ID/hash/bytes/reasonを転記せず、歴史要約を現在性や同期成功・復元/Archive許可にしません。

`StagingResidualObservation.py`は[残存staging直下entry](../docs/design/staging-residual-observation.md)を内容非読取・非再帰で件数観測します。不明/変化は保留して初回件数を保持し、metadata検査やcleanup/Upload/Archiveを許可しません。

## Shared marker-last basename validation (2026-10-27)

`ArtifactSetRecovery.is_artifact_basename`は既存marker-last publisherの名前条件を共通化します。空/非文字列、先頭dot、slash/backslash/NUL、末尾ASCII空白/dotを拒否し、Unicode・内部空白/dotを変更せず判定します。trim・casefold・Unicode正規化や自動修正は行いません。これは既存の限定したleaf文法であり、全Windows予約名/禁止文字/長さや実FS資格の検査を追加するものではありません。

publisherは全payload名/marker名を単一file公開前に同じ関数で検査し、既存の`artifact_name_invalid` / `commit_marker_name_invalid`を返します。pure classifierはexpected/published/staged/marker hash集合にも同条件を適用し、不正名は各集合の既存invalid/mismatch reasonでblockedとします。directory verifierはmarker名と期待集合を同条件でpreflightし、directory走査・payload読取前に拒否します。末尾空白/dotがpublisherで拒否されるのにconsumerで受理される不整合を解消し、既存成果物を変更しません。

[公開試験](../tests/test_artifact_set_publication.py)・[分類試験](../tests/test_artifact_set_recovery.py)・[directory試験](../tests/test_artifact_set_directory_verification.py)で不正名の全件事前拒否、非I/O・保全、Unicode/内部空白の公開→marker→検証と文字列の原形保持を確認します。単一file primitiveのtemp名方針や公開/復旧認可を変更せず、同時snapshot/ABA・FS/provider真正性・正式runtime/Drive・電源断/Tier B/C受け入れやP0閉鎖は証明しません。

## Caller-selected marker-last publication byte budgets (2026-10-27)

`publish_artifact_set_marker_last`はoptional `maximum_artifact_bytes` / `maximum_total_bytes`を受け、Noneまたは正のexact intだけを許します。不正値は既存transaction文法検査後、payload Mappingのsnapshot・hash・単一file公開前に`artifact_publish_limit_invalid`で拒否します。固定本番値・新schema/配布契約は追加しません。

既存の全payload名/型検査とbytes派生型の実buffer固定後、各payloadの実lenと合計を検査します。超過は`artifact_publish_file_limit_exceeded` / `artifact_publish_total_limit_exceeded`でhash前に拒否します。その後、通常どおりhashとmarker JSONを生成し、marker自身のsizeとmarker込み合計にも同じ上限を適用します。全件予算確認後だけ最初のfile公開へ進み、超過を部分公開・skip・切詰め成功へ変換しません。既存partial/complete setも読取り・書換え・cleanupせず保持します。

予算内は既存の決定的順序・marker-last・同一内容冪等・競合拒否を維持します。空payloadでもmarker分の予算が必要で、公開後は同じ値をdirectory verifierへ独立指定して検査できます。予算はmarkerへ保存せず、後続呼出しへ自動伝播しません。Noneでは従来動作。対象は一式の論理bytesであり、既存payload/コピー済みbytes・生成済みmarkerのmemory、hash/JSON生成の時間、一時fileとreadbackを含む実I/O総量やdisk容量を制限するものではありません。

[公開回帰](../tests/test_artifact_set_publication.py)でexact境界の公開/再公開/読戻し、不正値の非snapshot、payload超過の非hash、markerだけの超過・非部分公開、bytes派生型と空payloadを確認します。root/FS/provider資格・所有権/真正性、同時snapshot/ABA・電源断/Tier B/C/runtime受け入れや公開/Archiveの認可は追加しません。

## Bounded stable owner-record observations (2026-10-27)

`acquire_owned_lock`はoptional `maximum_record_bytes`を受け、Noneまたは正のexact intだけを許します。不正値はscope検査後・token/path/mutex準備前に`lock_record_limit_invalid`で拒否します。生成recordが超過する場合は所有mutex内で`lock_record_limit_exceeded`としてrecord作成前に拒否し、mutexを解放します。固定本番値・schemaやowner-v2/provider契約を追加しません。

作成後と解放前の`_record_matches`は同じ上限でmetadata sizeを先に検査し、超過recordを開きません。既存directory verifierの安定読取を再利用し、regular/non-reparse、path/handleのidentity・size/timestamp・link数と祖先chainの前後一致を検査します。観測size+1 byteの増大probeを維持し、変化/不明・解析不能・deep JSONのRecursionErrorは所有確認失敗として扱います。作成後の確認失敗は既存`lock_record_ownership_unverified`で停止し、解放時の失敗はrecordを保全してmutex解放/closeへ進みます。

strict field集合、scope/tokenとpid/hostの従来検査は維持し、canonical JSON表記や作成時のexact bytes一致を新しい削除条件にしません。Noneでも安定読取は行いますがcaller上限はありません。実I/O/時間/全memory、認可root/ACL/FS/owner真正性・一回性、観測からunlinkまでの競合/ABA、実Drive/runtime・電源断/Tier B/C受け入れは証明しません。既存recordの自動採用/復旧や新しい削除能力も追加しません。

[owner lock試験](../tests/test_owned_run_lock.py)でexact境界・不正値の早期拒否・作成前超過・解放時超過の非読取/保全、path→handle間増大、不明観測/deep JSONでもmutex解放、JSON表記互換を確認します。

## Owner-record creation failure preservation (2026-10-27)

owner recordの`write`は戻り値がexact intかつ全payload長と一致することを要求し、short/過大/不正値は`lock_record_write_incomplete`で停止します。続くcloseもOSErrorになった場合は元の固定reasonを保持します。write/flush/fsync/closeのOSErrorは従来の`lock_record_create_failed`を維持し、呼出し元へowner tokenを渡しません。

解放時のrecord cleanupは、作成・flush/fsync/closeと最初の安定所有確認を全て通過した場合だけ行います。作成中や初回確認に失敗したrecordは、たとえ完全なJSONや正しいtokenが残っていても、finallyで所有確認を再試行して削除しません。通常の所有中例外では従来どおり、解放時に同じscope/tokenを安定確認できるrecordだけをcleanupします。mutexのrelease/closeはどちらの場合も行い、不明な残存recordを自動採用・修復しません。

[単体回帰](../tests/test_owned_run_lock.py)と[隔離保存接続](../tests/test_terminal_bundle_integration.py)で、各書込件数・二重close失敗、write/flush/fsync/closeの失敗、初回確認失敗、parse可能な不完全recordの保全・候補非作成と同一mutexの再取得を確認します。これはmutex解放の合成証拠であり、残存recordの復旧/次run認可、root/FS/provider資格、ABA排除・電源断/Tier B/C/runtime受け入れやP0閉鎖を示しません。

## Strict owned-mutex adapter observations (2026-10-27)

`acquire_owned_lock`は既存`_NamedMutex`/診断mutexと同じadapter契約を前提とし、`acquire`の戻り値をexact boolとして検査します。数値/文字列/None等を`bool()`で所有確認へ変換しません。不正値と待機例外は固定`named_mutex_wait_failed`で、record payload生成・作成・bodyへ進みません。確定Falseは従来の`lock_timeout`でcloseのみ、確定Trueだけが次の観測へ進みます。

待機呼出し前からcleanup対象として扱い、不正応答/例外・KeyboardInterrupt等で結果が不明でもreleaseを試み、その成否にかかわらずcloseを試みます。既存adapterのreleaseは未所有ならno-opです。真偽の待機結果やこのcleanup試行は、新しいprovider資格/所有権証明にはなりません。

取得後の`abandoned`もexact boolを要求し、欠落・取得不能・不正型をFalseへ補完せず`named_mutex_observation_invalid`で停止します。Trueは従来どおり`abandoned_mutex_requires_recovery`で保全停止、Falseだけが既存record作成境界へ進みます。[単体回帰](../tests/test_owned_run_lock.py)で不正型/例外/中断とcleanup・非record作成を検査し、実mutexを使う隔離保存/診断接続で既存正常動作を確認します。正式runtime、owner-v2/provider真正性、復旧/次run認可、電源断/Tier B/C受け入れやP0閉鎖は追加しません。

## Mutex cleanup after record-cleanup interruption (2026-10-27)

owned lockのrecord解放時確認とunlinkを外側のfinallyで囲み、その途中のKeyboardInterrupt/SystemExit等でもmutex release・closeを試みます。release自身が失敗/中断してもcloseを試みる既存順序を維持し、中断を正常終了へ変換しません。record cleanupのOSErrorを保全へ落とす既存動作と、通常の所有確認/cleanup条件は変更しません。

[単体回帰](../tests/test_owned_run_lock.py)で解放時観測/unlinkの中断、release失敗/中断、unlinkのOSErrorとbody例外の保全を確認します。[隔離保存接続](../tests/test_terminal_bundle_integration.py)は両PCの候補公開後にrecord解放確認を中断し、prior・候補・recordを保全したまま別合成record pathで同一mutexを再取得して解放を確認します。これは中断後のmutex解放に関する合成証拠であり、残存recordの採用/復旧・次run認可、敵対的競合/ABA・強制process終了や電源断耐久性、正式runtime/Tier B/C受け入れやP0閉鎖を示しません。

## Local-only recovery schema references (2026-10-27)

`PrivateRecoveryEvidence`のbuild/validateと`CrashRecoveryDecision`のprior manifest検査も、既存manifest selectorのlocal-only参照検査・取得禁止Registryを使用します。schema全treeの`$ref` / `$dynamicRef`は`#`で始まる文字列だけを許し、HTTP/file/相対resource・不正型を、未使用のdefs内でも拒否します。validator自身にもresource retrievalを拒否するRegistryを明示し、事前検査だけに依存しません。

正常なlocal fragment・既存repository schemaは維持し、壊れたlocal参照/invalid schemaも拒否します。private evidenceは従来の`private_evidence_invalid`、crash classifierは`prior_manifest_invalid_or_not_running`へ閉じ、URL・raw lock・schema例外をreasonへ出しません。元metadata/raw bytes・prior manifestを変更せず、外部取得を新しい受け入れや復旧認可の根拠にしません。

[private evidence試験](../tests/test_private_recovery_evidence.py)と[crash判定試験](../tests/test_crash_recovery_decision.py)で、非local/未使用/不正参照、正常/破損local参照、invalid schemaとRegistryの独立拒否をsocket非呼出しで確認します。これはschema参照取得の制限で、schema自身の真正性/資源上限・owner/provider資格、実保存/復旧・runtime/Tier B/C受け入れやP0閉鎖を示しません。既存依存・配布file集合は変更しません。
