# 残存staging直下entryの読取観測

<a id="caller-selected-entry-limit-2026-10-26"></a>
## 呼び出し元が選択したエントリ制限 (2026-10-26)

`observe_staging_residual_entries`はoptional `maximum_entries`を受け、Noneまたは正のexact intのみ許す。不正値はroot I/O前に`staging_residual_limit_invalid`のheld、enumeration_completed=falseとする。Noneではcaller上限なし、固定本番値・保持/cleanup方針は採用しない。

共通snapshotへ初回/最終とも同じ上限を渡す。全entryを列挙順で数え、最初の超過entryを保持・sort/metadata検査する前に停止してscanを閉じる。上限超過は`staging_residual_entry_limit_exceeded`のheldで部分成功にしない。初回snapshot未成立なら確定件数なし・0観測、最終scan超過なら初回の確定件数/warningを保持する。空directoryは正の上限内で従来の0件観測を返すが実行許可ではない。その他の列挙失敗は既存incomplete理由を維持する。

この制限は保持entry件数に限り、名前長/OS列挙遅延/全memoryやmetadataの真正性・現在性を保証しない。source builderの既定列挙は変更せず、任意の本番source上限へ転用しない。合成試験はexact境界、I/O前の不正値拒否、超過時の非metadata/非trailer消費とcontext closure、最終超過での件数/bytes保全、部分失敗を確認する。全may_*false、runtime受け入れは別gateのまま。

2026-10-26：[共通snapshotのexact同名重複拒否](source-inventory-revalidation.md#duplicate-names-in-shared-enumeration-snapshots-2026-10-26)を利用する。初回scanが重複で失敗した場合は未確定件数を推計せず0観測のheld、最終scan失敗では初回の確定件数/warningを保持したheldとする。いずれも完全0件/cleanup許可へ変換しない。scandirへの重複注入試験で両経路とbytes保全を確認する。

2026-10-25。[残存artifact規則](../staging-file-lifecycle.md#9-residual-staging-artifacts)を支える[StagingResidualObservation.py](../../../Common/StagingResidualObservation.py)。起動時の完全なmetadata検査・run status更新・cleanupの実装ではない。

`observe_staging_residual_entries`は明示された既存絶対directoryの直下を列挙し、regular file/directory/otherの件数を返す。子directoryへ再帰せず、内容やmetadata JSONを読まない。名前/内容/ID/pathを返却せず、固定kind/reasonと整数件数・flagだけを保持する。空/missing/relative rootを補完・作成せず、不明rootはheldとする。

既存Python metadata providerの祖先/reparse検査と前後directory/entry snapshotを利用する。列挙不能・reparse・名前重複・前後変化/再確認不能を検出したらenumeration_completed=false、heldとして止め、初回に確定した件数は保持する。最初の失敗で停止し、未観測の追加エラー数を推計しない。0観測でも不完全なら0件の完全検査とはしない。

初回に残存entryを観測した場合だけwarning_required=trueで、削除/復旧/再uploadを許さない。直下列挙が成立してもstatus=requires_runtime_evidenceで、metadataペアの正当性、出所、旧run所有権、子directory内容や正式startup検査の完了を証明しない。残存検出それ自体からrun失敗を作らず、検査不能時の運用failure/Upload停止の強制は正式entry pointで未実装である。

全may_create_staging/may_upload/may_cleanup/may_archiveはfalse。時刻/古さに基づくcleanup・run状態修復・metadata field集合を採用せず、元entryを変更しない。Pythonのmetadata identity/signatureは実root/ACL/FS/現在性/ABA/同時snapshotの資格ではなく、Windowsの128-bit native providerとの正式接続も未実装。

[合成試験](../../../tests/test_staging_residual_observation.py)は空/regular/metadata-like/temp/子dir、内容非読取、missing/file/relative root、不明/reparse provider、後続追加と再確認失敗での件数保全、非再帰、重複観測の停止と非認可を確認する。実ログ/本番Driveや実運用stagingを使わない。両roleのレビューpackageへ含めるが、配布用runtime/最終allowlistの受け入れではない。
