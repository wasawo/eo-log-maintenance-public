# テスト計画

テストは実ログや本番パスに依存しないように構成します。

## 実装済み：JSON Schema 契約テスト

`test_contract_schemas.py` は、Drive アダプターのリクエスト／レスポンス JSON Schema の定義と適合性を検証します。

- Draft 2020-12 スキーマ自体の妥当性
- 4つの許可操作の正常リクエスト
- 必須フィールド、型、UUID、SHA-256 形式
- 未知の操作（削除操作を含む）と未知のフィールドの拒否
- 成功／失敗レスポンスの整合性
- 未知のエラーコードの拒否

ローカル実行方法（Python 3.11 以降を想定）：

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -p "test_contract_schemas.py" -v
```

GitHub Actions の `Validate` ワークフローでも同じテストを実行します。

## 未実装のランタイム安全性テスト

1. コピー元とコピー先の SHA-256 が一致する。
2. ファイルが欠落・破損・変更された場合に検証が失敗する。
3. PC-B のマニフェストが存在しない、失敗状態、古い、期間不一致、ログ種別不一致の場合に PC-A のアーカイブがブロックされる。
4. クラウド同期完了または内容検証を確認できない場合にアーカイブがブロックされる。
5. アーカイブ先の検証が失敗した場合にDrive上の元ファイルが残る。
6. PC-B にアーカイブ入口が含まれず、PC-B設定に allowArchive があれば設定検証で停止する。
7. 初期実装にローカル元ファイル削除・Drive削除のコード、操作、設定が存在しないことを確認する。Dry Run はデータ変更を行わない。
8. 0件の正常実行と、スクリプト未実行をマニフェストで区別できる。

これらのランタイムテストは未実装です。削除機能の実装・有効化をテスト合格条件に含めません。テスト合格は将来の削除機能を許可するものではありません。JSON Schema テストの成功は、ランタイム処理の安全性や Google Drive の同期完了を保証しません。

再試行テストでは、PowerShell が初回を含む最大4回（待機1分・5分・15分）を管理し、Python/HTTPクライアントに暗黙の再試行がないことを確認します。アップロード結果が不明な場合は、再アップロード前にDrive上の状態を照合します。


## C-54 approved pattern-contract tests

`Test-C54PatternContract.ps1` checks the approved C-54 URI user-info, Bearer, GitHub token-like, AWS AKIA, and PEM private-key marker grammars using synthetic positive, negative, boundary, and case fixtures.

Run with PowerShell 7.6.7:

```powershell
./tests/Test-C54PatternContract.ps1
```

This is a contract-level regex test, not a runtime sanitizer test. It does not prove C-53/C-54 path processing, whole-field nulling, or diagnostic non-disclosure. Those runtime tests remain pending.

## C-53/C-54 diagnostic path sanitizer tests

The test script `Test-DiagnosticPathSanitization.ps1` checks the deterministic optional-path sanitizer against the approved C-53 syntax contract and C-54 sensitive-name/token/value-format policy, using synthetic paths only.

Run with PowerShell 7.6.7:

```powershell
./tests/Test-DiagnosticPathSanitization.ps1
```

These tests cover the standalone path sanitizer's return value. They do not yet prove diagnostic-record schema validation, JSON serialization to a literal `null`, preservation of event identity/classification through finalization, or non-disclosure by a runtime diagnostic pipeline. No Google Drive or real-log operations are performed.

## Diagnostic record schema-v1 finalizer tests

Run the standalone C-47–C-53 schema-v1 finalizer tests with PowerShell 7.6.7 using:

    ./tests/Test-DiagnosticRecordFinalizer.ps1

The finalizer accepts an already-structured dictionary with exactly seven fields, validates schema version, event ID, allowlisted error code, the approved phase/operation pair, and the exact fixed message template. It emits a fresh ordered JSON object; an unsafe optional path becomes an explicit JSON null. The C-47 path maximum is 1024 Unicode scalar values; over-limit paths fail closed to null.

This is a pure structured-record finalizer and synthetic test suite. It does not parse arbitrary input JSON, generate event IDs, infer failure mappings from exceptions, implement runtime orchestration, access logs or Google Drive, or prove end-to-end P0 acceptance. Duplicate JSON properties must be rejected by any future raw-JSON ingestion boundary before a dictionary is materialized.

## Diagnostic event ID allocation tests

Run the synthetic C-45/C-46 event ID allocation tests with PowerShell 7.6.7 using:

    ./tests/Test-DiagnosticErrorId.ps1

The allocator mutates a caller-owned per-run Int32/Int64 sequence by reference, emits invariant-culture IDs in the exact ERR-000001 format, and fails closed after ERR-999999. The runtime caller remains responsible for allocating once per distinct event and preserving that ID through wrappers and later observers. The helper is not thread-safe by itself and does not define event correlation or runtime orchestration.


## Crash-recovery decision gate (synthetic only)

`test_crash_recovery_decision.py` covers the pure recovery decision helper using synthetic manifest bytes and lock records. It checks fail-closed behavior for lock/owner/latest-manifest/identity/Drive reconciliation failures and confirms that an eligible decision preserves the old manifest and requires a new run with fresh inventory. It does not perform recovery, mutate files, access Drive, archive, or delete. CI validation is required before acceptance.


## Artifact-set recovery classifier (synthetic only)

`test_artifact_set_recovery.py` covers exact staged sets, valid marker + complete published set, missing marker, partial publication, digest mismatch, unexpected artifacts, and malformed markers. It uses synthetic hashes only; no filesystem publication, recovery, Drive, archive, or deletion is performed. CI validation is required before acceptance.


## Marker-last artifact-set publication (synthetic filesystem tests)

`test_artifact_set_publication.py` covers marker-last success, injected mid-set failure, idempotent retry, existing-content conflict, invalid inputs, and concurrent identical publishers using temporary directories only. Partial publication must leave no marker and must not be treated as committed. These tests do not access production paths or Drive and do not prove cross-file atomicity.


## Artifact-set directory verification (synthetic filesystem tests)

`test_artifact_set_directory_verification.py` inspects temporary directories and hashes actual artifact bytes before classifying the commit marker. It covers valid publication, missing marker, partial sets, tampering, duplicate JSON keys, unexpected entries, symlinks, invalid inputs, and empty state. The verifier is read-only and does not repair or remove artifacts. These tests do not establish crash durability, cross-file atomicity, cross-process locking, target/network filesystem behavior, source stability, Drive consistency, or runtime acceptance. CI validation is required before acceptance.


### Cross-process artifact publication race

The marker-last publication test suite includes a spawned-process race in which two publishers target the same directory with conflicting bytes for one artifact. The expected result is one complete committed winner and one fail-closed destination conflict, with the marker matching the winner's actual bytes. This is synthetic local-filesystem coverage, not evidence for network shares, Google Drive, power-loss durability, run-lock integration, or runtime entrypoint safety.
