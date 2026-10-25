# Common PowerShell functions

`PowerStatusObservation.py`は[Windows AC電源観測](../docs/design/power-status-observation.md)を読取専用で行います。成功時のACLineStatusだけを使い、不明・API失敗を接続済みにせず、実行/継続の許可やAC切断監視は行いません。

`CompletionWaitAttempt.py`は[確認予算の試行planと使用点検査](../docs/design/completion-wait-budget.md)を扱う純粋helperです。元checkpoint bytesに結び付けて1件だけ追加したcandidateを再読込検査し、保存前/記録後の観測bytes・scope・現在時計/期限・実行条件/ACを再検査します。実保存・確認は行わず、全may_* flagはfalseです。反復検査は一回限りのcommit receiptではなく、接続fixtureの比較更新もメモリmockです。

`CompletionWaitCheckpoint.py`は[確認予算checkpoint](../docs/design/completion-wait-budget.md)のclosed schemaと期待scope・現在UTCを使う純粋readerです。元bytes・時刻文字列・履歴順を保持し、欠落/破損から予算をリセットしません。既存helperへの変換で精度を失う時刻は拒否し、実保存・現在性/rollback防止・試行前永続計上は別ゲートです。

`ManifestTransitionInspection.py`は[遷移表の前後snapshot検査](../docs/design/manifest-transition-inspection.md)を行う純粋helperです。schema/identity/凍結inventory、verificationと時刻整合、終端不変性、未掲載ペアを確認します。掲載ペアの結果も`requires_runtime_evidence`であり、所有権・staging・Drive・OSD-03集約・永続更新の認可にはなりません。

`DriveRequestPath.ps1`の`Test-DriveRequestFilePath`と`DriveRequestPath.py`の`is_drive_request_file_path`はC-01 P1/L1のrequestファイルパス字句だけを検査する純粋bool helperです。drive-rooted形と各componentを独立して検査し、予約stemはASCIIだけで大小比較します。文字列の修復/正規化、固定maxLength、file/root/FS照会は行いません。request schemaも同じgrammarを適用し、指定先/root/使用点の認可と正式adapter接続は別ゲートです。

`DriveResponseSemantics.ps1` の `Test-DriveResponseSemantics` は、実request由来の期待ID/operation、decoded IDictionary response、整数exit codeを明示入力し、ordinal完全一致と契約§6のexit/envelope/error-code対応、固定code別retryable真偽表を検査します。IDをUUID正規化せず、int/long/BigInteger以外のexitはcoerceしません。`DRIVE_TRANSIENT_FAILURE`だけtrue、他8codeはfalseが必須で、非boolと矛盾を拒否します。出力は固定Status/ReasonCodeのみで、`consistent` / `correlation_exit_mapping_consistent` はこれらの整合を意味します。resultの信頼、運用続行、retry許可、cloud検証ではありません。transport/UTF-8/単一JSON/重複key/schema、C-01/C-02、RETRY-02のorchestration、IPC全体・runtime受け入れは残ゲートです。helperはprocess/file/network/auth/retry/sleep/lock/logを呼びません。

`AggregationReportBuilder.py` は、callerがメモリで供給する信頼済みmanifest/B2/report schemaとexact UTF-8入力bytesから、A2/B2整合・inventory照合・terminal verificationを検査し、期間別/全run集計と参照hashを導出して決定的UTF-8 bytesを返す純粋helperです。schemaの外部参照を拒否し、schemaロード・source再走査・時刻自動取得・ファイル/Drive/lock/publication/status変更は行いません。G1生成UTCはexact入力の終了時刻から導出し、同時ならmanifestの元表記を保持します。任意のcaller時刻は照合値に限り、不一致を拒否します。信頼できる現在UTC・未来許容は明示入力とし、11桁までの小数を保持します。B2 validationがincompleteの場合、供給件数の整合だけで全入力の網羅性を証明せず、失敗のない期間もindeterminateにします。completedの検証で全entry/errorがaccount済みなら、unclassifiable run-scope errorと独立した既知期間のcompleteを区別します。同じexact入力から同じbytesを再生成し、参照validatorもG1時刻を照合します。永続writer・公開・遷移強制とruntime/実root/cloud受け入れは別ゲートです。

PC-A / PC-Bで共有する関数と、レポートの参照先を検証するローカル補助モジュールを配置します。

現時点の実装状況と初回配布の実行順は [棚卸し](../docs/status/first-release-readiness-20261024.md) を参照してください。以下は補助処理の責務であり、正式ランタイムの完成を意味しません。

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

source builderは[列挙完了前の再確認](../docs/design/source-enumeration-stability.md)でdirectory/child集合・identity/属性を再走査し、途中変更や不明を検出すると既存targetを保持したままcoverageをincompleteにします。最終bytes再hash・atomic snapshot・後続使用までの保護を証明するものではありません。

`DriveContentComparison.py`は[OSD-01の同一内容比較](../docs/design/drive-content-comparison.md)を内部観測から判定する純粋helperです。完全列挙・信頼済みsource・exact name/size/hashを要求し、cloud SHA未確認ならdownload hashを要します。比較候補は復元・同期成功・archiveの認可ではありません。

`DriveContentComparison.py`の`hash_downloaded_content`は完了済みdownloadのchunk列から実byte数/SHAを計算し、既存比較観測へ渡します。途中失敗・size超過/不足・完了不明では返さず、stream所有権・解放と実Drive ID/成功の資格はcaller/provider側に残ります。

`DriveContentComparison.py`の`collect_drive_listing`は内部page観測のfolder・成功・token連続性/終端・ID重複を検査し、全pageが揃った場合だけ比較用観測を返します。部分列挙を0件へ変換せず、実API/応答の真正性・resource管理はprovider側の未完gateです。
