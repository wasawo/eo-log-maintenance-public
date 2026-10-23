# リポジトリ構成・文書索引

利用者向け概要は [README](../README.md)、Codexの開始規則は [AGENTS.md](../AGENTS.md)、現在地は [handoff](handoff/next-chat.md)。必要な分野だけを開き、全仕様・全履歴を開始時に一括読込しない。

## 全体配置

```text
AGENTS.md                   全担当共通の恒久規則
README.md                   目的・役割・導入概要
CHANGELOG.md / VERSION      変更履歴・版
requirements-*.txt          runtime / test依存
.agents/skills/             必要時に読む検証・PR/引き継ぎ手順
.codex/agents/              analyst / implementer / reviewerの役割・モデル設定
.codex/config.toml          プロジェクトの既定思考量（明示設定が優先され得る）
.github/workflows/          Validate / Package Validation
.github/scripts/            役割別packageビルダー
Config/                     公開exampleのみ（実設定は非追跡・配布対象外）
Common/                     PowerShell / Python共通helper
contracts/                  JSON Schema
scripts/                    正式運用入口の配置先（現在はREADMEのみ）
tests/                      合成テスト、ハーネス、公開可能な部分証拠
  evidence/                 匿名化済みの検証証拠（runtime原本ではない）
docs/
  development/              開発手順・役割・詳細仕様への参照表
  requirements/             要件・P0残課題・未決定事項
  design/                   機能仕様・データ契約・安全ゲート
  decisions/                承認記録・判断案・比較検討
  validation/               テスト計画・監査・受け入れ証拠
  release/                  配布・導入設計
  status/                   日付付き棚卸し
  handoff/                  変動する現在の進捗
    archive/                過去の引き継ぎ記録
```

## 探し方と配置ルール

- 実装を始める: [詳細仕様への参照表](development/development-guide.md) → 対象の要件・承認記録・仕様・テストを確認する。
- 分業する: [役割別運用](development/agent-workflow.md)。モデル/思考量の正本は `.codex/agents/` の各TOML。
- 検証する: [検証スキル](../.agents/skills/eolm-validation/SKILL.md)、[tests案内](../tests/README.md)。Git/CI/引き継ぎは [対応スキル](../.agents/skills/eolm-pr-handoff/SKILL.md)。
- 実装を探す: [Common案内](../Common/README.md)、[scripts案内](../scripts/README.md)、[schema](../contracts/)、[設定例](../Config/)。
- 文書の配置は用途で決める。`proposal` / `options` を含むファイルにも承認済み部分があるため、ディレクトリ名やファイル名だけで承認状態を判定しない。本文の適用範囲と承認記録を確認する。
- 履歴は削除しない。過去のCI・PRリンクや当時の状態を現行の指示/証明として実行しない。現在地はhandoff、日付付き棚卸しはその確認時点の記録。
- 新しい文書は該当分類へ置き、この索引と参照元を同じ変更で更新する。相対リンクは参照元ファイル基準、バッククォート内の `docs/...` はリポジトリルート基準とする。
- `Common/`、`Config/`、`contracts/`、`scripts/`、`tests/` はimport・CI・役割別配布の契約に関わる。今回その配置・allowlist・安全条件は変更しない。Codex検出用ディレクトリと `docs/handoff/next-chat.md` の入口も固定する。

## 文書一覧

### 開発・分業手順

- [役割別エージェントの運用](development/agent-workflow.md)
- [開発時の詳細仕様・手順の参照表](development/development-guide.md)
- [Implementation Workflow: ElectronicObserver Log Maintenance](development/implementation-workflow.md)

### 要件・P0残課題・未決定事項

- [P0 現行実装・仕様差分台帳](requirements/p0-gap-register.md)
- [P0 Open Specification Decisions and Acceptance Blockers](requirements/p0-open-specification-decisions.md)
- [Requirements Traceability Register](requirements/requirements-traceability.md)

### 機能仕様・契約・安全ゲート

- [Derived Aggregation Report v1 Proposal](design/aggregation-report-v1-proposal.md)
- [PC-A確認予算の分離実装](design/completion-wait-budget.md)
- [Local maintenance artifact root](design/configuration-local-root.md)
- [明示回復コマンドの設計契約](design/explicit-recovery-command-design.md)
- [Filename and Period Selection Specification](design/filename-and-period-selection.md)
- [Latest manifest selection core](design/latest-manifest-selection.md)
- [Maintenance Manifest Schema v1 — Approved Field Specification](design/manifest-schema-v1-proposal.md)
- [Maintenance Manifest v1 — State-Transition Table Proposal](design/manifest-state-transition-v1-proposal.md)
- [承認済み月次時刻の分離観測](design/monthly-schedule-observation.md)
- [PowerShell・Python 責務分担／連携契約書](design/powershell-python-contract.md)
- [private証拠file ACLの限定形状](design/private-evidence-acl-profile.md)
- [回復用owner証拠 v2 の設計契約](design/recovery-owner-evidence-v2-contract.md)
- [private回復証拠の保存・検証契約](design/recovery-private-evidence-contract.md)
- [Run Input Evidence v1 Proposal](design/run-input-evidence-v1-proposal.md)
- [Runtime Entry-Point Validation Gate](design/runtime-entrypoint-validation-gate.md)
- [Staging File Lifecycle](design/staging-file-lifecycle.md)

### 承認記録・判断案・比較検討（承認状態は本文参照）

- [Aggregation Inventory Integrity — Decision Options](decisions/aggregation-inventory-integrity-options.md)
- [C-45 event identity conflict handling options](decisions/c45-event-identity-conflict-options.md)
- [C-50 structured condition input model — non-normative proposal](decisions/c50-condition-input-model-options.md)
- [C-51 structured processing-context input model options](decisions/c51-context-input-model-options.md)
- [C-53/C-54 secret-bearing path pattern proposal](decisions/c54-secret-pattern-proposal.md)
- [C-54: Sensitive Path Detection Policy](decisions/decision-record-c54-sensitive-path-detection.md)
- [Decision Register: C-18–C-32](decisions/decision-register-c18-c32.md)
- [OSD-02 — Crash, concurrency, and latest-manifest options](decisions/osd-02-crash-concurrency-options.md)
- [OSD-03 — Derived aggregation report contract decisions](decisions/osd-03-report-contract-options.md)
- [OSD-03: Run and Period Status Aggregation Options](decisions/osd-03-status-aggregation-options.md)
- [OSD-04: Dry Run副作用のA承認・比較記録](decisions/dry-run-side-effect-policy-proposal.md)
- [PC-Aの毎時完了確認に対する上限（判断案）](decisions/pc-a-completion-wait-budget-proposal.md)
- [stale lock の明示的回復フロー案](decisions/recovery-disposition-proposal.md)
- [実行accountとprivate証拠アクセス方針（判断案）](decisions/recovery-execution-account-policy-proposal.md)
- [回復用owner証拠と既存v1 lockの扱い（判断案）](decisions/recovery-owner-evidence-v2-proposal.md)
- [回復証拠の非公開保管方針（判断案）](decisions/recovery-private-evidence-policy-proposal.md)
- [OSD-08: タスクのログオン方式（判断案）](decisions/task-logon-mode-policy-proposal.md)
- [C-24 / OSD-08: 月次実行日時の具体案](decisions/task-monthly-schedule-policy-proposal.md)

### 検証計画・監査・受け入れ証拠

- [C-53/C-54 deterministic policy test matrix and audit](validation/c53-c54-policy-test-matrix.md)
- [Diagnostic contract C-45–C-54: implementation and test evidence](validation/diagnostic-contract-test-evidence.md)
- [Filename and Period Selection Test Plan](validation/filename-period-test-plan.md)
- [IPC Contract-to-Test Evidence Audit](validation/ipc-contract-evidence-audit.md)
- [Lock Ownership and Crash-Recovery Acceptance Gate](validation/lock-recovery-acceptance-gate.md)
- [P0 PowerShell/Python Contract Review Findings](validation/p0-contract-review-findings.md)
- [P0 Runtime Entrypoint and Deletion-Surface Audit](validation/p0-runtime-entrypoint-safety-audit.md)
- [P0 Source / Specification / Test Inventory](validation/p0-source-test-inventory.md)
- [Requirements Source Coverage Audit](validation/requirements-source-audit.md)
- [ランタイム安全性テストシナリオ](validation/runtime-safety-test-scenarios.md)
- [SEL-RT Fixture Traceability Audit](validation/sel-rt-fixture-traceability.md)
- [Target-Filesystem and Crash-Recovery Acceptance Plan](validation/target-filesystem-acceptance.md)

### 配布・導入設計

- [Distribution Design: GitHub to Google Drive](release/distribution-design.md)

### 日付付き棚卸し

- [初回配布までの実装棚卸し・作業順序](status/first-release-readiness-20261024.md)

### 引き継ぎ・過去記録

- [現在の進捗・次の作業](handoff/next-chat.md)
- [AGENTS導入前の履歴](handoff/archive/pre-agents-history.md)
- [2026-10-23までの検証・マージ記録](handoff/archive/validation-history-20261023.md)
