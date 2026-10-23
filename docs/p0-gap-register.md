# P0 現行実装・仕様差分台帳

> 現況: [2026-10-24棚卸し](first-release-readiness-20261024.md)。以下の過去PR記録は当時の状態を含む。sentinel存在・schema未実装・CI待ち等を現況として扱わない。P0受け入れは未完了。


- 状態：初版。P0着手時の調査結果であり、全ソースの実行時検証完了を意味しない
- 対象ブランチ：`main` の確認時点
- 目的：現行ソース、仕様書、テスト、CI、配布処理の不整合を分類し、P0で修正・確認する対象を管理する
- 原則：仕様未確定事項を実装側の都合で確定しない。未実装機能を実装済みと扱わない。P0〜P2では元ログ削除・Drive削除を追加しない

## 分類

- **仕様差分**：実装・CI・配布手順が明文化された仕様と一致していない
- **未実装**：仕様上必要だがランタイム実装がない
- **仕様未確定**：設計上の決定・承認が残っており、実装前に合意が必要
- **テスト不足**：要件や実装はあるが、受け入れを証明する検査が不足
- **確認待ち**：この初回調査では実際の動作・全ファイルを検証できていない

## 優先度の定義

- **P0-A（最優先）**：実行環境・安全性の前提。後続実装の前に解消
- **P0-B（高）**：実装開始前の仕様・契約・CI整合性
- **P0-C（通常）**：既存関数・パッケージ・文書の整合性と回帰テスト

## 差分一覧

| ID | 優先度 | 分類 | 対象 | 確認された現状／差分 | 対応方針 | 完了条件 |
|---|---|---|---|---|---|---|
| P0-001 | P0-A | 仕様差分・テスト不足 | `Common/LogFunctions.ps1`、全PowerShellスクリプト | PR #11で共通モジュールに厳密な7.6.7ガードと版判定テストを追加済み。現行追跡ツリーに `scripts/SyncLogs.ps1` は存在せず、正式なsync処理は未実装。`ArchiveLogs.ps1` とバッチエントリーポイントも未実装で、全実行経路への適用は未完了 | 共通ガードを正式エントリーポイントの処理開始前に適用し、すべての起動点を棚卸しする。バージョン情報取得失敗時は fail closed とする | 7.6.7で合格し、不一致版・取得不能・不正値ではファイル処理前に停止するテストがあり、全正式エントリーポイントに適用される。PR #11の共通ガードとテストは完了、エントリーポイント適用は未完了 |
| P0-002 | P0-A | 仕様差分・テスト不足 | `.github/workflows/validate.yml`、`.github/workflows/package-validation.yml` | PR #10で両ワークフローにPowerShell 7.6.7の取得・SHA-256検証・実行版確認を追加し、CI成功を確認済み | 変更はPR #10でマージ済み。CIの厳密な実行版検証を維持し、将来変更時も回帰確認する | 両ワークフローが7.6.7以外で失敗し、ログから実行バージョンを確認できる。PR #10のValidate #57とPackage Validation #49は成功 |
| P0-003 | P0-A | 仕様差分・確認待ち | バッチエントリーポイント、運用手順、パッケージ | PR #13後のtracked treeを静的確認。`.bat` / `.cmd` と正式運用エントリーポイントは存在せず、確認した実行可能ソース／CI設定に `powershell.exe` の参照はない。将来の運用起動方法は未検証。監査記録: `docs/p0-runtime-entrypoint-safety-audit.md` | 正式エントリーポイントの設計後に起動点を追加し、全 `.bat` / `.cmd` と手順書を検査。実在する起動点は `pwsh.exe -NoLogo -NoProfile -NonInteractive` を基準に統一 | 正式な起動点が存在し、静的検査と実行テストで指定起動方式およびバージョン不一致時の停止を確認する |
| P0-004 | P0-B | 未実装 | `scripts/`、README、実装ワークフロー | READMEは既存スクリプト移行・本番実行未完了と明記。同期、Drive内容検証、マニフェスト、アーカイブのランタイム処理は未完成 | P0でスコープと前提を確定し、実処理は後続フェーズで段階実装する。未実装のまま正式配布・本番適用しない | 各機能の状態が文書・パッケージ状態・テストで一貫して「未実装」または「実装済み」と識別できる |
| P0-005 | P0-B | 仕様未確定・テスト不足 | `docs/powershell-python-contract.md`、`contracts/drive-request.schema.json`、`contracts/drive-response.schema.json`、`tests/test_contract_schemas.py` | 契約の静的プレレビューを `docs/p0-contract-review-findings.md` に記録。絶対パスのスキーマ制約、操作別レスポンス結果形状、request_id／operation照合、終了コード・retryable意味論、Pythonの単一API試行の実装テストが未解決。運用者承認も未取得 | C-01/C-02の方針を運用者レビューで決定し、スキーマ／テストを更新。アダプター実装時にC-03〜C-05の結合・意味論テストを追加する | 契約レビュー承認が記録され、スキーマ検証と異常系・意味論テストがCIで実行される。レビュー文書の追加だけでは完了としない |
| P0-006 | P0-B | 仕様差分・テスト不足 | `.github/scripts/Build-ReleasePackage.ps1`、`tests/Test-ReleasePackage.ps1` | PR #74で旧 `scripts/ArchiveAndUploadLogs.ps1` をデプロイ可能判定・配布対象から除外。PR #76で `-TargetRole PC-A/PC-B` を必須化し、PC-Aは `SyncLogs.ps1` と `ArchiveLogs.ps1` の両方を要求、PC-Bは `ArchiveLogs.ps1` を除外する回帰テストを追加。正式ランタイム入口はmainに未実装で、本番配布可能ではない。最終的な役割別allowlist/デプロイ・移行動作はOSD-09の承認対象として残る | PR #74/#76の入口判定はマージ済み。残りは正式ランタイム入口、非配布用マーカー条件、OSD-09の最終allowlist/移行承認。PR #78ではC-20/C-28とCFG-001/006/007に基づき、example configの役割・許可/必須フィールド・絶対Windowsパス構文を検査するが、active config/runtime loaderとroot separationの検証とは分離する | 旧入口だけではデプロイ可能と判定されず、PC-A/PC-Bの入口差分がテストで検証される。正式入口未実装の間は本番配布を拒否する。役割別ビルドテストの成功をruntime acceptanceとは扱わない |
| P0-007 | P0-B | テスト不足 | `.github/workflows/validate.yml` | PR #10で `tests/Test-LogFunctions.ps1` をCIに組み込み済み。PR #10のValidate #57は成功 | CI実行を維持し、P0-001のバージョンガードテストと境界値テストを継続拡充する | CIログにPowerShellテストの結果が出て、失敗時にCIが失敗する。既存テストのCI組み込みはPR #10で確認済み |
| P0-008 | P0-C | テスト不足 | `Common/LogFunctions.ps1`、`tests/Test-LogFunctions.ps1` | PR #13でうるう日、月値異常、ファイル名構造、年跨ぎ、うるう年カットオフを追加。PR #31で `.TXT` 大文字拡張子拒否とInvariantCulture下の日付解析を追加。Validate #39376077352／Package Validation #39376077340 成功。PR #34の月末helper境界もValidate #39377619535／Package Validation #39377619696で成功 | CI実行を維持し、ファイル名日付とLastWriteTimeの不一致、混在ディレクトリの列挙、実行単位のエラー集約はランタイム入口未実装のため未検証。30日／31日月末と2月28日／29日のhelper境界はテスト済み。PR #38のSEL-RT-01–10は設計のみ.PR #40でOSD-03の候補方針と影響を比較するが、明示承認までは実装しない。決定後、OSD-02のmanifest schema/transition tableと整合させ、実装可能なentrypointに対するruntime testを追加する | 正常系・境界値・異常系がCIで再現可能であり、各テストが要件IDに対応付けられている。PR #13/#31/#34でhelper境界の一部をCI検証済み。PR #38でSEL-RT-01–10のruntime fixture設計を文書化するが、実行可能なentrypointがないためruntime coverageは未完了 |
| P0-009 | P0-C | 仕様差分・テスト不足 | `.github/scripts/Build-ReleasePackage.ps1`、パッケージテスト | PR #76でPC-A/PC-B別の公式入口要件とPC-BのArchiveLogs除外を追加。PR #78ではexample configのmachineId/role、許可/必須フィールド、絶対Windowsドライブパス構文、PC-Aの安全な `allowArchive: false`、PC-Bの `allowArchive` 不在、`allowDelete` 不在をビルダーで検査し、負例をテストする。配布物内の利用者向けバージョン要件の明示、release tag/VERSION整合、署名/provenance、正式リリース認可は未実装または未承認 | 役割別パッケージとexample configの固定意味論をCIで検査し、配布物の実行要件明示とリリース制御はOSD-06/09の決定・実装後に扱う | レビュー用成果物は非配布マーカー付きであり、正式パッケージは役割・入口要件・example configの安全な意味論を検証する。リリース認可・provenanceとactive config runtime validationの証拠は別ゲートとして検証される |
| P0-010 | P0-C | 確認待ち | 全仕様・実装・テスト・設定ファイル | PR #123 merge `6b543930f9a9805f50693bd6333a8278c416fe05` 時点の最新棚卸し。PR #82〜#106でIPC、manifest schema/state transition、staging、lock/residual、Dry Run、security logging、archive gate、Drive listing/identity、C-29 retry/unknown-upload、C-25テスト計画、契約レビュー、P0受け入れゲート状態、filename helper証拠、runtime sentinel/package-builder証拠境界を照合。PR #78のexample-config/package-builder検証はactive-config runtime authorizationではない。`scripts/SyncLogs.ps1` はsentinelのみでsync実装なし。`scripts/ArchiveLogs.ps1`、運用manifest schema・reader/writer、staging metadata、Python Drive adapter、retry orchestrator、runtime lock/orchestration/IPC/archive gateは未実装。C-29のRETRY-01〜06およびSEL-RT-01〜10は仕様・トレーサビリティのみで、実行時証拠はない。C-45の同一`error_id`属性衝突時はPR #145でOption A（証跡確定・公開を拒否するfail-closed方針）を承認・仕様化したが、イベント生成・伝播・衝突検出と拒否動作のランタイム実装／受け入れ証拠は未実装である。OSD-02/03とEOLM-MAN-011はmanifest schema/transitions、status aggregation、timestamp policy shapeは承認済みだが、EOLM-MAN-011の数値許容値・適用場面は未決である。 | `docs/requirements-source-audit.md`、`docs/p0-source-test-inventory.md`、`docs/requirements-traceability.md`を最新のmain baselineに整合し、C-29を含む残る条項を実装状態・実行可能テスト・客観的証拠・未決判断へ照合する。未実装／未実施を明記し、schema/package/docs CIをruntime証拠に格上げしない | 全適用条項に要件ID、実装または未実装状態、実行可能テストまたは未実施／blocked理由、客観的証拠が結び付くこと。docs-only reconciliation、helper/schema/package CIだけでは完了としない |
| P0-011 | P0-B | 仕様差分・確認待ち | `docs/implementation-workflow.md` §4、README、`docs/decision-register-c18-c32.md`、`docs/p0-open-specification-decisions.md`、本台帳 | PR #101時点で `docs/implementation-workflow.md` §4 にP0 readiness/acceptance gateが存在し、READMEも同節を参照する。ゲートはP0-001〜012のcomplete/blocked/incomplete分類、未決OSD、runtime evidence不足、docs-only evidenceの限界を明記する。一方、decision registerの先頭ステータスとgap registerのP0-011説明がゲートの存在・P0未受入れ状態を明確に反映していなかった | §4を規範的なP0受け入れゲートとして維持し、README、decision register、gap register、traceabilityの状態説明を同期する。全P0とOSDの実態に合うよう、P0未受入れと未完了のruntime evidenceを明示する | P0-001〜012が証拠付きでcomplete、または理由付きblocked/incompleteに分類され、未解決OSDと実行時証拠不足が明示される。README・workflow・decision register・gap registerに矛盾がない。P0受け入れは未完了であり、文書追加だけで完了扱いにしない |
| P0-012 | P0-A | 安全性確認 | 全ランタイム処理、テスト、配布物 | PR #84の `docs/p0-runtime-entrypoint-safety-audit.md` は限定的なtracked-path static review。PR #91のC-28更新も、PR #78のrole-aware example-config/package-builder testsと、未実装のruntime archive/no-delete evidenceを区別する。Drive request schemaは4つの非削除操作のみでschema testsがdelete操作を拒否し、`allowDelete`例示設定もbuilderで拒否する。一方、正式runtime入口・Python Drive adapter・runtime package acceptance・実行可能before/after mutation testsは存在せず、完全なsource/config/package/runtime negative-capability proofではない | 削除API・削除コマンドを追加しない。正式入口とPython adapterが実装される段階で、source/config/contracts/package全体のnegative testsとbefore/after mutation testsを追加し、生成パッケージの実際の内容を検査する | 元ログ削除／Drive削除の実行経路・設定がないことを実装済みソース、設定、契約、配布物、runtime境界にわたる検査とCIで確認すること。現状は限定的な静的部分証拠のみ |

## 仕様書で既に明確な基準

1. PowerShell 7.6.7必須。Windows PowerShell 5.1互換は対象外。
2. バッチエントリーポイントは `pwsh.exe` を使用する。
3. 実行開始時にPowerShellバージョンを検証し、要件を満たさなければファイル処理前に停止する。
4. PythonはDrive APIアダプターとして1リクエストにつき1回だけAPIを試行し、再試行判断はPowerShellが担当する。
5. PC-Aは同期・検証に加え、条件を満たした場合のみアーカイブ。PC-Bはアーカイブ禁止。
6. P0〜P2の初期実装にはローカル元ログ削除・Drive削除を含めない。

## 初回調査で確認した主なファイル

- `Common/LogFunctions.ps1`
- `tests/Test-LogFunctions.ps1`
- `.github/workflows/validate.yml`
- `.github/workflows/package-validation.yml`
- `.github/scripts/Build-ReleasePackage.ps1`
- `docs/powershell-python-contract.md`
- `docs/staging-file-lifecycle.md`
- `README.md`

## 作業順序と依存関係

1. P0-010：ソースと仕様条項の棚卸しを完成させる。
2. P0-001〜003：7.6.7必須、起動方式、CIの実行環境検査を揃える。
3. P0-007〜008：既存PowerShellテストをCIへ組み込み、境界テストを補完する。
4. P0-005：契約レビューと結合テスト条件を整理する。
5. P0-006、P0-009：正式エントリーポイント確定後にパッケージ判定・役割別許可リストを修正する。
6. P0-011：P0受け入れ条件を関連文書へ反映する。
7. P0-012：削除処理が初期実装に含まれないことを検証する。
8. 全項目の状態とテスト証跡を更新し、P0完了を判定する。

## ステータス更新ルール

各項目は次のいずれかで管理する。

- `未着手`
- `作業中`
- `レビュー待ち`
- `完了`
- `保留（理由を記載）`

完了にする際は、変更ファイル、テストコマンド／CI実行結果、関連PRを記録する。文書を更新しただけではランタイム動作の検証完了としない。


## Current audit disposition — PR #70 merge baseline

- Tracked-tree baseline: `2b5d4266df9130ad532707dec8727a7623b3c9e2` (PR #70 merge).
- P0-010: **作業中／未完了**。The source audit §2.1 currently has no source-section row marked `Unmapped`, but this only records source-to-requirement ID coverage. Remaining Partial rows need clause-level disposition across implementation state, executable test state, and objective evidence. Runtime entry points, orchestration, and IPC harness remain absent; SEL-RT-01–10 and IPC-01–06 are not implemented/not run. Documentation CI is not runtime acceptance evidence.
- P0-012: **未完了**。The current static safety audit is partial evidence only. Python Drive adapter and official runtime entry points are absent; no full runtime/package negative-capability proof exists. Keep deletion functionality excluded; do not close this item based on schema or source scans alone.
- Status consistency rule: use each requirement row's actual evidence state; never promote a requirement to verified based only on documentation, schema shape, or package-builder checks when the requirement concerns runtime behavior.
- Next focus: reconcile the highest-risk traceability rows for CFG-001/004/005/006/007, ARC-001–006, DRV-011–016, MAN-004–012 against the source audit and open-specification decisions. Preserve blocked decisions and do not infer schemas, status aggregation, freshness, auth, release, or scheduler policies.


### P0-010 follow-up — C-29 retry and unknown upload outcome (PR #95 scope)

- Source audit and runtime scenario catalogue cross-reference EOLM-DRV-001/002/003/006/008/009/010 and RETRY-01–06.
- The current tree still has no Python Drive adapter, official PowerShell retry orchestrator, complete Drive listing/reconciliation, or executable retry/unknown-outcome tests. This is a documentation and traceability improvement only.
- A failed or partial Drive query is unknown, not proof of absence. Retry is permitted only after complete reconciliation establishes the contract-defined safe condition; OSD-01 still blocks trust decisions for pre-existing unmarked objects.
- P0-010 remains **作業中／未完了**. P0-012 remains **未完了**; no deletion-capability claim is upgraded by this change.


### P0-010 follow-up — C-26 manifest schema and status evidence (PR #100 scope)

- The maintenance manifest is specified in prose, but no dedicated manifest schema, reader/writer, latest-run resolver, transition validator, or runtime archive gate exists.
- contracts/drive-response.schema.json is the Drive adapter response envelope; it is not the maintenance manifest schema.
- OSD-02 blocks the schema/transition baseline; OSD-03 blocks exhaustive run/period aggregation; EOLM-MAN-011 blocks freshness-dependent archive acceptance. Do not infer values or transitions.
- P0-010 and P0-012 remain open. This audit update is not runtime acceptance evidence.


### P0-010 follow-up — manifest and IPC evidence reconciliation (PR #124 scope)

- The maintenance manifest v1 field specification and narrow policy clarifications are approved; the complete transition table is not fully normative. EOLM-MAN-011 numeric policy is approved: configurable 5-minute future tolerance, configurable 24-hour freshness threshold applied to current-execution timestamps only, and fail-closed behavior when reliable current UTC is unavailable. Runtime enforcement and executable tests remain pending.
- OSD-03 aggregation policy and the separate derived-report representation are approved. Report schema, frozen-inventory canonicalization, atomic publication/recovery/consistency validation, implementation, and executable tests remain pending. PR #116 remains proposal-only and has a stale base.
- MAN-01–10 and IPC-01–06 remain not implemented/not run. Drive request/response schema tests are not maintenance-manifest validation or process-boundary tests.
- P0-010/P0-012 remain open; no runtime acceptance or deletion-capability absence is inferred from docs CI.


### P0-010 follow-up — diagnostic C-45–C-54 helper evidence (PRs #140/#141)

- docs/diagnostic-contract-test-evidence.md now maps the approved C-45–C-54 clauses to current helper code, synthetic tests, CI evidence, and explicit gaps.
- PR #140 implements a standalone schema-v1 finalizer and the approved 1024-Unicode-scalar path cap; PR #141 implements a per-run event-ID counter helper. Neither integrates these helpers into runtime orchestration.
- PR #144 adds the pure C-50 token-to-code helper under approved Option A; PR #146 adds the pure C-51 operation-to-phase resolver under approved input Option C and synthetic CI tests. Producer-side precedence enforcement, semantic operation selection, event ID propagation, conflicting event identity detection, raw JSON duplicate-property rejection, runtime sink non-disclosure, and end-to-end diagnostic evidence remain unimplemented/not run.
- Exact-head helper/schema/package CI does not close P0-008 or P0-010; P0-012 remains open because complete source/config/contract/package/runtime no-delete proof is absent.


### OSD-02 timestamp/freshness policy decision — PR scope (2026-10-21)

- Resolved by maintainer approval: UTC ISO 8601 `Z` timestamps; reject malformed, offset-form, timezone-less, and unparseable values; reject finish-before-start.
- Approved configurable defaults: future-time tolerance 5 minutes; freshness threshold 24 hours.
- Freshness checks cover timestamps generated/updated during the current execution only. Historical manifests are not rejected solely due to age.
- Assume host OS time synchronization is configured; if current UTC cannot be obtained reliably, time-dependent operations fail closed. No separate monitoring service is required.
- Remaining gap: executable fixed-clock tests and runtime validation are not implemented/evidenced. OSD-02 still has crash/concurrency/latest-manifest and transition work; OSD-03/P0-008/P0-010/P0-012 remain open.


## OSD-02 approved crash/concurrency/latest-manifest policy (2026-10-21)

Maintainer approved C1-A/C2-C/C3-B/C4-A. C1-A requires validated same-directory temporary writes, atomic create-if-absent, compare-before-replace, and fail-closed behavior when guarantees are unavailable. C2-C requires a per-scope OS named mutex plus exclusive ownership-token lock record; stale lock recovery is explicit and must verify the owner is gone. C3-B preserves crash-left `running` history and creates a new `run_id` only after recovery checks, with a fresh inventory and reconciliation of uncertain uploads. C4-A selects only a unique maximum validated `started_at_utc` for the exact PC/log-type/period scope; ties, malformed/conflicting candidates, read errors, or incomplete enumeration block operation, and there is no fallback to an older success. Timestamp freshness/future tolerance are not lock or retry timeouts.

Synthetic tests for crash points, concurrent create/update, lock ownership/recovery, interrupted runs, uncertain uploads, and resolver ambiguity are required but **not yet executed/evidenced**. These decisions do not claim runtime implementation or close P0-008/P0-010/P0-012.


## Maintainer-approved OSD-03 report contract (2026-10-21)

The maintainer explicitly approved **R1-B, R2-A, R3-B, R4-A, R5-A, R6-A, R7-A**. This settles the report-contract options but does not constitute an executable JSON Schema, runtime implementation, or test evidence.

- **R1-B — summaries only:** period entries contain counts and completion state, not duplicated per-target rows. Validate the eligible inventory and per-file outcomes against immutable run-input evidence and the originating manifest.
- **R2-A — tuple identity:** report identity is exactly (pc_id, log_type, run_id, report_schema_version). Omit report_id; derive the canonical filename from that tuple. Do not add fields to manifest v1.
- **R3-B — content-bound references:** manifest_ref and evidence_ref each include canonical relative path, schema version, and lowercase 64-character SHA-256 of exact validated bytes. Validate referenced artifact identity against the report tuple. Reject absolute paths, traversal, identity mismatch, malformed digest, or changed bytes.
- **R4-A — reuse OSD-02 controls:** use unique same-directory temp files, flush/close, read-back validation, and atomic create-if-absent; reuse the existing per-PC maintenance lock during normal publication. Regeneration/recovery must acquire the same named mutex plus ownership-token lock record. Existing same-identity identical bytes are idempotent; different bytes are a conflict and are never overwritten. Remove a temp file only when ownership is proven; orphan temp files are non-authoritative and must not be removed based on age alone.
- **R5-A — deterministic regeneration:** regenerate only from the exact validated manifest plus immutable B2 run-input evidence. Never re-scan mutable source directories to reconstruct historical inventory. Validate identity, inventory digest, all counts, and error scope. If inputs are incomplete/unavailable, remain unresolved. Identical output is idempotent; different content for the same identity is a conflict.
- **R6-A — three-state period completion:** complete only if all eligible targets for the period are verified and no relevant error affects it; incomplete for known failed/unknown targets or known relevant errors; indeterminate if required evidence is missing, malformed, conflicting, or unverifiable. Never map indeterminate to complete. These are report-only values and must not be added to manifest run-status enums.
- **R7-A — separate local/Drive states:** local validated publication is authoritative. Drive replication is a separate verified step; replication failure does not invalidate/delete the local artifact. Do not claim cross-PC availability until the Drive copy's identity and exact content are verified.
- Recompute all summary counts from the referenced manifest and B2 evidence. Reject missing/duplicate period rows, target accounting mismatch, inventory digest/count mismatch, report/manifest/evidence identity mismatch, and inconsistent error scope. generated_at_utc uses UTC ISO 8601 uppercase Z and approved future-time validation; report age alone does not invalidate immutable historical evidence.
- Required synthetic acceptance tests are specified but **not yet executed/evidenced**. Runtime implementation, executable schema, and operational evidence remain pending. No P0 item is closed by this documentation change.


## OSD-03 executable schema implementation slice — PR #150 (2026-10-21)

- Added `contracts/aggregation-report-v1.schema.json` as a strict Draft 2020-12 structural schema candidate for the approved R1–R7 report shape. It rejects unknown properties, `report_id`, unsupported/non-integer report schema versions, invalid enums/count types, non-UTC-Z timestamps, malformed lowercase SHA-256 values, and non-canonical relative paths.
- Added schema-definition and synthetic structural-contract tests in `tests/test_contract_schemas.py`. They cover partial-failure and zero-work examples, all three period completion values, strict versioning, unknown fields, reference path/hash validation, timestamp form, enums/counts, and run-scope error shape.
- These tests are authored but **not yet executed/evidenced** in this PR. CI must pass on the exact latest PR HEAD before merge. No runtime report reader/writer, cross-artifact digest verification, tuple/path binding, count recomputation, deterministic regeneration, atomic publication, lock integration, or Drive replication implementation is included in this slice.
- The JSON Schema validates structure only. Cross-field and cross-artifact invariants remain mandatory fail-closed runtime checks; schema acceptance alone is not proof of report correctness or authorization for any side effect.
- No manifest v1 fields, B2 evidence contract, A2 digest contract, or OSD-02 safety boundaries are changed. No real logs, credentials, production paths, Drive writes, archive enablement, or deletion.


## PR #151 status note — OSD-03 internal consistency slice (2026-10-22)

PR #150 merged the structural aggregation-report v1 JSON Schema and its synthetic schema tests; PR-head and post-merge CI passed. PR #151 adds a report-local PowerShell consistency validator and synthetic tests for period uniqueness, safe reference paths/digest shape, summary count reconciliation, completion consistency, run-scope error count, and zero-work/success consistency. Until PR #151 CI passes on its exact latest HEAD, these tests are authored but not yet verified. This slice does not validate exact referenced manifest/evidence bytes, B2/A2 integrity, full target-set completeness, cross-artifact identity, deterministic regeneration, atomic publication, lock ownership, or Drive replication. P0 acceptance remains open.

## OSD-03 status correction — 2026-10-22

PR #151 is merged at `e93f0ea552496831c69efb1e8dd2818ac86f4e5b`. Validate and Package Validation passed on exact PR HEAD `846cfdbb1ce76f3ec1363460c4f0576b7c10a2b6` (runs `39635268289`, `39635268115`) and on the post-merge commit (runs `39636402422`, `39636402408`). The report-local consistency validator is now implemented and CI-verified within its stated scope. PR #152 adds a narrow exact-byte reference verifier; its tests are not yet CI-verified. Neither PR implements full manifest/B2 schema validation, identity binding, A2 digest recomputation, exhaustive target/count reconciliation, deterministic report regeneration, atomic publication, lock recovery, or Drive replication. P0 acceptance remains open.

## PR #155 update — referenced-artifact schema and identity validation

PR #155 introduces a standalone validation path for derived aggregation reports: it validates the report and the exact manifest/evidence bytes referenced by it, checks raw-byte SHA-256 values, and compares `run_id`, `pc_id`, and `log_type`. The runtime package builder is extended to include the validator, three schemas, and the declared `jsonschema` dependency. This is a bounded runtime helper, not completion of the corresponding P0 acceptance gate: official entry-point integration, live Drive revalidation, locks/recovery, A2/B2 canonical digest computation and exhaustive count reconciliation, and production-like end-to-end acceptance remain open. No deletion capability is added.


## OSD-03 / B2 evidence integrity update — 2026-10-22

PR #155 is merged at `2cd982ddd19cb3b1d19dec0051b1d8a0cf0993c0`; its report-referenced artifact schema/identity helper passed exact-head Validate and Package Validation. PR #156 adds a separate validation-only helper for A2 inventory digest recomputation, B2 canonical evidence digest recomputation, strict evidence schema validation, and completed-enumeration count reconciliation. Its CI and merge status must be verified from the exact PR head. Neither helper currently proves source enumeration completeness, reconciles the embedded evidence inventory against the originating manifest, integrates with official sync/archive entry points, or provides lock/recovery/Drive revalidation. P0 remains open.


## OSD-03 cross-artifact inventory binding update — 2026-10-22

PR #156 merged at `7881fe0f74699dd8aceb1e72e48a4c583c6597cd`. Exact-head Validate run `39644692787` and Package Validation run `39644693181` succeeded on `21fa869f222f2b88b7c0ecef20f2313b9ce7c515`. PR #157 connects A2/B2 digest and count validation to the report-referenced artifact verifier and compares the embedded B2 target set against manifest `files` by relative path, filename, size, and SHA-256. PR #157 CI is pending; verify its exact latest head before merge. This still does not prove complete source enumeration or implement official sync/archive entry points, atomic publication, locks/recovery, or Drive revalidation. P0 remains open.


## PR #157 verified; runtime entry-point gate — 2026-10-22

PR #157 merged at `33eb450e226914130c34e80cb3bd140776195fd5`. Exact-head Validate run `39645428388` and Package Validation run `39645428425` both passed on `a6efdeb4fc31e1f5be1607cc15bd44a229fbed98`. Post-merge main workflows `39645706354` and `39645706352` require final-status confirmation.

The repository still has no official `scripts/SyncLogs.ps1` or `scripts/ArchiveLogs.ps1`; the artifact/report validators remain standalone helpers. PR #158 documents the minimum runtime integration gate, validation ordering, sync/archive separation, failure behavior, locking/publication/recovery requirements, and synthetic acceptance criteria. This is a design contract, not an implementation. Source enumeration/frozen inventory, evidence writer, lock/recovery, atomic publication, current Drive verification, and official runtime integration remain open. P0 remains open.


## PR #159 — read-only source inventory and B2 evidence construction (2026-10-22)

PR #159 adds `Common/SourceInventoryEvidenceBuilder.py` and synthetic tests for deterministic source traversal, filename/date eligibility, SHA-256 target records, invalid filename diagnostics, safe relative paths, and B2 evidence serialization. The builder marks enumeration incomplete when traversal, file reads, or stable-hash checks fail; `serialize_evidence` validates the existing strict schema plus A2/B2 integrity and count invariants, then returns bytes without writing them. This does not yet implement atomic publication, locking/recovery, official entry-point integration, Drive operations, archive, or deletion. Exact-head CI and post-merge CI must be verified before considering this slice complete. P0 remains open.


## PR #160 — atomic no-overwrite artifact publication primitive (2026-10-22)

PR #160 adds a single-artifact publication helper that writes a same-directory temporary file, flushes and fsyncs it, then uses atomic hard-link creation to expose complete bytes without replacing an existing destination. An exact-byte retry is idempotent; conflicting bytes, non-regular destinations, and unsupported atomic-link behavior fail closed. Synthetic tests cover success, idempotency, conflict preservation, atomic-link failure, and symlink rejection. This is not a multi-artifact transaction and does not implement run locks, crash recovery, directory durability guarantees, official entrypoint integration, Drive operations, archive, or deletion. Exact-head and post-merge CI remain mandatory. P0 remains open.


## PR #161 — lock ownership and crash-recovery acceptance gate (2026-10-22)

`docs/lock-recovery-acceptance-gate.md` records the approved OSD-02 lock/recovery safety boundary and a synthetic acceptance matrix. It requires a per-PC OS named mutex paired with an exclusive ownership-token record, bounded acquisition, fail-closed ownership mismatch handling, no age/PID-only stale-lock takeover, immutable crash-left `running` manifests, new `run_id` and fresh inventory after validated recovery, and reconciliation of uncertain Drive outcomes before retry. This PR is documentation/planning only: no lock implementation, recovery mutation, Drive operations, archive, deletion, or official entry-point integration. P0 remains open; runtime acceptance is not established.


## PR #162 — isolated owned-run lock primitive (2026-10-22; pending CI)

Adds `Common/OwnedRunLock.py` and synthetic tests for a Windows named mutex paired with an exclusive owner-token record. It uses a maximum 60-second acquisition timeout, strict record shape/token validation, and only removes the record when its token still matches the current owner. Existing records and abandoned-mutex state fail closed; this slice does not recover stale/crash-left records, mutate manifests, enumerate sources, call Drive, archive/delete, or integrate official entry points. CI must be checked on the exact PR HEAD. P0 remains open.


## PR #163 — pure crash-recovery decision gate (2026-10-22; pending CI)

Adds `Common/CrashRecoveryDecision.py` and synthetic tests. Recovery is eligible only when the mutex is abandoned, the lock record is structurally valid and matches the expected scope/host, prior-owner termination is confirmed, the latest manifest candidate is unique, the prior manifest passes strict Manifest v1 schema validation and identity checks as a crash-left `running` record, and Drive reconciliation is complete or not required with zero unresolved uploads. The helper only returns a decision; it does not mutate records/manifests, create runs, enumerate sources, call Drive, archive/delete, or integrate entry points. P0 remains open.


## PR #164 — pure artifact-set recovery classifier (2026-10-22; pending CI)

Adds `Common/ArtifactSetRecovery.py` and synthetic tests to classify expected, staged, published, and commit-marker evidence using SHA-256 values. It reports committed only when the marker is strict and matches the complete published artifact set. Partial publication or marker-missing states remain uncommitted, require reconciliation, and preserve existing artifacts. This is not a finalized multi-artifact transaction protocol and performs no filesystem publication/recovery, manifest writes, Drive calls, archive, deletion, or entry-point integration. P0 remains open.


## PR #165 — marker-last artifact-set publication helper (2026-10-22; pending CI)

Adds a bounded helper composing the single-artifact atomic no-overwrite primitive. It publishes named artifacts in deterministic order and publishes a transaction marker last. Synthetic filesystem tests cover normal completion, injected mid-set failure, idempotent retry, content conflict, invalid input, and concurrent identical publishers. Failure preserves already-published artifacts; there is no rollback/cleanup and no cross-file atomicity. The helper is not integrated with manifests, Drive, archive/delete, or official entry points. P0 remains open.


## PR #166 — artifact-set directory verification evidence (2026-10-22)

The isolated `Common/ArtifactSetDirectoryVerification.py` helper verifies a single on-disk directory snapshot using observed file bytes and strict marker parsing; synthetic tests cover valid, missing-marker, partial, tampered, malformed, unexpected-entry, and symlink states. It is read-only and does not close P0 runtime safety gaps. Verification is point-in-time only; lock-protected use, target-filesystem durability/concurrency, official entrypoint integration, Drive revalidation, end-to-end acceptance, archive, and deletion remain open. Do not mark P0 complete from these helper tests.


## Cross-process artifact publication evidence (PR #167; verified 2026-10-22)

The spawned-process synthetic test for competing marker-last publishers with conflicting bytes is merged. PR-head Validate `39701085065` and Package Validation `39701084975` succeeded; post-merge main Validate `39702034526` and Package Validation `39702034521` succeeded on merge commit `f979a5200d48a7ccccfed6ad31de07529bd340df`. This evidence is limited to the hosted Windows runner's temporary local filesystem. It does not close network/Drive semantics, power-loss durability, lock integration, verification-to-use race prevention, official entrypoint integration, runtime no-deletion proof, or E2E acceptance.

## Target-filesystem acceptance gate (2026-10-22)

`docs/target-filesystem-acceptance.md` defines Tier A hosted CI, Tier B disposable local-volume tests on each operator PC, and Tier C separately gated synchronized/network target qualification. Tier B and Tier C have not been run. Do not treat CI success as proof of operator-PC, Google Drive for desktop, network filesystem, remote visibility, or power-loss durability. P0 remains open.

## Actual process-crash boundary evidence (2026-10-23)

P0-010/P0-012 remain open. The test-only crash harness adds fresh-process verification and idempotent retry after actual termination at each completed-file publication boundary. No runtime module, Drive operation, archive or source/Drive deletion is introduced. This is synthetic OS-temp evidence only, not Tier B/C or power-loss qualification.

## Owned publication/recovery integration evidence (2026-10-23)

Real Windows mutex tests now compose ownership, publication, directory revalidation and pure recovery decisions using synthetic temporary files. Contention, abandonment, owner mismatch and changed bytes fail closed; prior manifests/records remain intact. This does not implement operational stale-record adoption or close P0-010/P0-012. Tier B/C and official runtime integration remain open.

## Read-only active configuration structure slice (2026-10-23)

Common/MachineConfiguration.ps1 adds a shared strict structure parser/read-only UTF-8 reader and 285 synthetic assertions for required fields, duplicate/unknown/type/role failures, maintenanceLocal overlap and non-mutation. P0-006/P0-009/P0-010/P0-012 remain open: no physical approved-root gate, actual-volume authorization, bootstrap/migration or official runtime integration is established. Template defaults remain separately restricted.

Create-only bootstrap helper (2026-10-23): Common/MachineConfigurationBootstrap.ps1 adds opt-in safe-example initialization and byte-preservation for existing settings. Tests cover both PC roles and sanitized failures. This is not a production installer, migration/OSD-09 approval, physical runtime gate, or P0 closure; the earlier read-only-loader note describes PR #9 scope.

Source inventory follow-up (2026-10-23): opened-handle identity checks (PR #12) and lstat root/ancestor/entry reparse rejection close reproduced read/traversal gaps. They do not establish an atomic source snapshot, cross-root physical separation or protection through later use. P0 acceptance and full Tier B/C remain open.

Existing-root inspection slice (2026-10-23): a read-only PowerShell helper adds existing-directory/reparse checks and maintenanceLocal comparison in normalized volume-GUID paths. This is partial metadata evidence, not approved-root authority, filesystem qualification, later-use protection, official runtime integration or P0 closure. OS-temp root tests do not extend the recorded intended-volume Tier B suite.

Latest selection slice (2026-10-23): [C4 selection core](latest-manifest-selection.md) adds defined filename/JSON identity checks, unique-start-time selection and no older-success fallback, with 32 supplied-observation tests. The separate directory adapter below adds bounded enumeration/read checks; approved-root authority, protection through later use, full semantic/Drive checks and operational recovery remain incomplete. P0-010/P0-012 remain open.

Read-only directory slice (2026-10-23): ManifestDirectoryReader adds fixed per-PC directory observations, descriptor/path identity checks, final rescan and an exact validated byte snapshot. Nineteen synthetic tests cover bounded failures; approved-root authority, protection through later use, full semantic/Drive validation and operational recovery remain incomplete. P0-010/P0-012 remain open.

Recovery composition slice (2026-10-23): seven synthetic latest-directory/classifier tests and the existing real Windows abandonment scenario now use checked byte snapshots. Read ambiguity and latest failure block classification; stale acquisition still blocks after a positive decision. Snapshot-to-use protection and actual disposition/new-run creation remain incomplete. P0-010/P0-012 stay open.

Explicit recovery design (2026-10-23): the dedicated-command direction is approved, with normal sync refusal retained. [Diagnosis/planning contract](explicit-recovery-command-design.md) defines DIAG-01 through DIAG-10 as pending tests, not executed evidence. No stale-lock state change or runtime entrypoint is added. P0-010/P0-012 remain open.

Recovery diagnostic model slice (2026-10-23): a pure non-authorizing result model accepts explicit fixed gate observations and exports allowlisted scope/reasons only. Twelve synthetic boundary tests do not establish real evidence acquisition, diagnostic mutex lifecycle, the full DIAG command matrix, runtime acceptance or P0 closure.

Diagnostic lease slice (2026-10-23): record-free mutex helper and 13 synthetic tests add bounded DIAG-03/04/05 evidence. Existing normal ownership refusal, old records, formal entrypoint/role guards and P0 gaps remain. Legacy v1 records still lack persistent process identity; the proposed v2-only recovery direction needs maintainer judgment.

Owner-evidence design (2026-10-23): approved v1-preserve/v2-only direction now has a logical evidence contract and pending OWNER-01 through OWNER-06. No executable provider/schema/migration or production recovery is added. Private evidence storage/ACL/retention policy is the next maintainer decision; P0 remains open.

Private evidence slice (2026-10-23): approved private maintenanceLocal/no-auto-deletion design now has strict metadata schema and in-memory raw-size/SHA-256 validation (13 synthetic tests). Static schema is packaged; synthetic private originals are excluded. Actual persistence, ACLs, protected publication, execution-account policy, STORE matrix and P0/Tier B acceptance remain incomplete.

Private ACL profile slice (2026-10-23): same-account-per-PC direction is approved. A pure conservative file-ACL profile adds 13 synthetic observation tests, without real descriptor/token queries, effective access, directory ancestry or safe creation. Matching is non-authorizing; actual ACL/STORE-01/P0/Tier B acceptance remains incomplete.

Descriptor normalization slice (2026-10-23): six PowerShell/Python tests use sixteen synthetic binary descriptors to connect normalization to the conservative file ACL profile. SID-bearing observations remain internal; real OS ACL/token acquisition, effective access, ancestors, safe creation and STORE-01 remain unimplemented. Initial logged-on-only operation is approved; exact C-24 staggered monthly times remain a maintainer decision.

Monthly-time observation slice (2026-10-23): C-24 monthly dates/times are approved and a pure non-authorizing boundary helper has 12 fixed-clock tests. Task/completion records, missed-run compensation, PC-A hourly budget, retry and runtime rollout remain incomplete. No P0/Tier B closure.

PC-A confirmation-budget slice (2026-10-23): the 24-hour/25-attempt upper bound is approved and a pure assessment/immutable-history helper has 16 synthetic tests. Runtime persistence/binding, atomic attempt accounting, latest-manifest/Drive integration, actual hourly tasks and explicit resume remain incomplete. Deadline expiry only holds; P0/Tier B stay open.
