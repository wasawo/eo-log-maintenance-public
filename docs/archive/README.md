# 判断・検証の履歴索引

現在の利用の入口は[要件定義書](../requirements/log-move-requirements.md)・[設計書](../design/log-move-design.md)・[実装計画](../development/implementation-workflow.md)。現在の決定と未決は[決定台帳](../decisions/decision-register-c18-c32.md)・[未決台帳](../requirements/p0-open-specification-decisions.md)を使う。

この配下は選択肢の比較、利用者の選択記録、過去基準の監査/証拠を保管する。移動は承認の撤回でも、未決候補の採用でもない。旧削除禁止/両PC待機等は正式要件が明示変更した範囲で置換済み。他の既承認条件は適用範囲を保つ。必要な根拠だけを読み、履歴にある次作業を自動実行しない。

## 判断の経緯

- [集約インベントリの整合性 - 意思決定オプション](decisions/aggregation-inventory-integrity-options.md)
- [B2 validation網羅性・report生成時刻の判断資料](decisions/b2-validation-coverage-report-time-options.md)
- [C-01/C-02: IPCパス・操作別resultの判断資料](decisions/c01-c02-ipc-contract-options.md)
- [C-01: drive-rooted file pathの詳細字句候補](decisions/c01-drive-rooted-lexical-candidate.md)
- [C-45 イベント ID の競合処理オプション](decisions/c45-event-identity-conflict-options.md)
- [C-50 構造化条件入力モデル — 非規範的な提案](decisions/c50-condition-input-model-options.md)
- [C-51 構造化処理コンテキスト入力モデルのオプション](decisions/c51-context-input-model-options.md)
- [C-53/C-54 秘密を含むパス パターンの提案](decisions/c54-secret-pattern-proposal.md)
- [C-54: 機密パス検出ポリシー](decisions/decision-record-c54-sensitive-path-detection.md)
- [OSD-04: Dry Runローカル副作用のA承認・比較記録](decisions/dry-run-side-effect-policy-proposal.md)
- [現行実装に基づく4件の具体決定（2026-10-24）](decisions/implementation-grounded-four-decisions-20261024.md)
- [OSD-02 — クラッシュ、同時実行、最新マニフェストのオプション](decisions/osd-02-crash-concurrency-options.md)
- [OSD-03 — 派生集計レポート契約の決定](decisions/osd-03-report-contract-options.md)
- [OSD-03: 実行および期間ステータス集計オプション](decisions/osd-03-status-aggregation-options.md)
- [OSD-05/C-23: Drive認証・identity・scopeの判断資料](decisions/osd-05-drive-auth-identity-scope-options.md)
- [owner-v2: field・identity・snapshot束縛の判断資料](decisions/owner-v2-field-binding-options.md)
- [PC-Aの毎時完了確認に対する上限（判断案）](decisions/pc-a-completion-wait-budget-proposal.md)
- [stale lock の明示的回復フロー案](decisions/recovery-disposition-proposal.md)
- [実行accountとprivate証拠アクセス方針（判断案）](decisions/recovery-execution-account-policy-proposal.md)
- [回復用owner証拠と既存v1 lockの扱い（判断案）](decisions/recovery-owner-evidence-v2-proposal.md)
- [回復証拠の非公開保管方針（判断案）](decisions/recovery-private-evidence-policy-proposal.md)
- [㉙〜㉜の比較案（2026-10-24）](decisions/remaining-policy-options-20261024.md)
- [2026-10-24 選択形式による仕様決定](decisions/selected-policy-decisions-20261024.md)
- [OSD-08: タスクのログオン方式（判断案）](decisions/task-logon-mode-policy-proposal.md)
- [C-24 / OSD-08: 月次実行日時の具体案](decisions/task-monthly-schedule-policy-proposal.md)

## 過去基準の監査・検証根拠

- [リポジトリ整理の再点検（2026-10-27、残存不整合）](validation/repository-organization-review-20261027.md)
- [診断契約 C-45–C-54: 実装およびテストの証拠](validation/diagnostic-contract-test-evidence.md)
- [IPC 契約からテストまでの証拠監査](validation/ipc-contract-evidence-audit.md)
- [P0 PowerShell/Python 契約レビューの結果](validation/p0-contract-review-findings.md)
- [P0 ランタイム エントリポイントと削除面の監査](validation/p0-runtime-entrypoint-safety-audit.md)
- [P0 ソース/仕様/テスト インベントリ](validation/p0-source-test-inventory.md)
- [要件ソース カバレッジ監査](validation/requirements-source-audit.md)
- [SEL-RT 治具トレーサビリティ監査](validation/sel-rt-fixture-traceability.md)
