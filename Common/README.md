# Common PowerShell functions

PC-A / PC-Bで共有する関数と、レポートの参照先を検証するローカル補助モジュールを配置します。

- ファイル一覧の取得とファイル名からの対象期間判定
- SHA-256 の算出とコピー後の検証
- 実行マニフェストの作成・読み込み・スキーマ検証
- 集約レポートの参照先 manifest / B2 evidence の実バイト検証と identity 照合
- ログ出力と終了コードの統一
- エラー時に後続の破壊的処理を停止する共通制御

`AggregationReferencedArtifacts.ps1` は `validate_aggregation_artifacts.py` を呼び出し、`contracts/` の Draft 2020-12 schemaでレポートと参照先JSONを検証します。Python環境には `requirements-runtime.txt` の依存関係が必要です。検証対象は明示された信頼済みmaintenance root配下に限定し、失敗時は拒否します。

これらの補助関数は現時点で正式な同期・アーカイブエントリーポイントには未接続です。ロック、Drive再検証、アーカイブ許可、ソース列挙の完全性証明、原子的公開は未実装です。実ログ・Drive書き込み・削除は行いません。

PCごとのパスや権限は設定ファイルで与え、PC-Bではアーカイブ・削除機能を呼び出せない設計を維持します。

`RunInputEvidenceIntegrity.py` は既存のB2 evidenceオブジェクトに対して、承認済みA2 inventory digest、B2 canonical evidence digest、スキーマ、embedded inventoryの件数・順序整合性を検証する補助モジュールです。ソース列挙やファイル書き込みは行わず、公式エントリーポイントにも未接続です。manifestのtarget setとの照合、証跡の原子的公開、ロック／回復、Drive検証は別の未完了要件です。

`SourceInventoryEvidenceBuilder.py` は、明示されたローカルソースルートを読み取り専用で列挙し、ファイル名から同期対象期間を判定して、A2 inventory digest と B2 evidence を構築する合成テスト可能な補助モジュールです。ファイル内容の SHA-256 と読み取り前後の基本メタデータを照合し、列挙・読み取り・ハッシュ処理に不確実性があれば enumeration を incomplete にします。`serialize_evidence` はスキーマと A2/B2・件数整合性を検証して決定的な UTF-8 JSON bytes を返すだけで、ファイル公開や atomic write は行いません。正式なエントリーポイント、排他ロック、原子的公開、Drive 同期・再検証には未接続です。


`AtomicArtifactPublication.py` は、検証済み artifact bytes 1件を同一ディレクトリの一時ファイルに書き、flush/fsync 後にハードリンクの原子的な no-overwrite 作成で公開する補助モジュールです。同一内容の再試行のみ冪等扱いし、既存内容が異なる場合は拒否します。ファイルシステムがこの原子的作成を提供しない場合は fail-closed です。複数 artifact のトランザクション、run lock、クラッシュ回復、ディレクトリ永続化保証、正式エントリーポイントへの統合は別要件であり、未実装です。


`OwnedRunLock.py` は、Windows の machine-wide named mutex と exclusive create-only owner-token record を組み合わせた隔離ロック補助モジュールです。待機は最大60秒で、既存レコードや abandoned mutex は自動回復せず fail-closed とします。所有 token が一致する場合だけ自身のレコードを削除します。クラッシュ回復、manifest更新、Drive操作、公式エントリーポイント統合、アーカイブ・削除は行わず、これらは別の未完了要件です。


`CrashRecoveryDecision.py` はクラッシュ後の回復可否を証拠から分類する純粋な補助モジュールです。abandoned mutex、ロックレコードのscope/host整合性、旧所有者の終了確認、最新manifest候補の一意性、Manifest v1 schemaとidentity、Drive照合状態、未確定アップロード件数を fail-closed で判定します。許可結果は旧manifestを保持したまま新runとfresh inventoryを要求するだけで、ロック・manifest更新、run作成、ソース列挙、Drive、アーカイブ、削除、正式入口統合は行いません。合成テストとCI検証が完了するまでは受け入れ済みと扱いません。


`ArtifactSetRecovery.py` は、複数成果物の expected/staged/published SHA-256 と合成 commit marker を分類する純粋な補助モジュールです。marker と全 published artifact が厳密に一致した場合だけ `committed` を返します。部分公開や marker 欠落は未コミットとして照合を要求し、既存成果物を保持します。実際の公開・回復・manifest更新・Drive・アーカイブ・削除・正式入口統合は行わず、最終的な複数成果物プロトコルを確定するものでもありません。


`ArtifactSetPublication.py` は単一ファイルの no-overwrite 公開プリミティブを組み合わせ、成果物を決定的な順序で公開して最後に transaction marker を公開する補助モジュールです。途中失敗では公開済みファイルを保持し、ロールバックや削除をしません。複数ファイル全体の原子性を提供するものではなく、正式なエントリーポイントや Drive／manifest／アーカイブ／削除には未接続です。


`ArtifactSetDirectoryVerification.py` は、明示された1ディレクトリの実ファイル bytes を読み、SHA-256 と commit marker を照合して artifact-set classifier に渡す読み取り専用補助モジュールです。重複JSONキー、想定外エントリ、symlink、非通常ファイル、marker不正、読取失敗は fail-closed とします。修復・公開・上書き・削除は行いません。検証結果は一点時点の観測であり、ロック、検証後の変更防止、複数ファイル原子性、クラッシュ耐久性、Drive整合性を保証しません。正式エントリーポイント未接続であり、P0は未完了です。


`docs/target-filesystem-acceptance.md` defines the evidence boundary for artifact-set publication and recovery: hosted Windows CI, disposable local-volume qualification on PC-A/PC-B, and separately gated synchronized/network target qualification. Current CI results do not prove target filesystem behavior, remote visibility, or power-loss durability. No official entrypoint integration or destructive operation is authorized by these helper modules.


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
Bootstrap/create-once migration is a separate pending implementation.
