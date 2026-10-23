---
name: eolm-validation
description: eo-log-maintenance-publicの変更に応じたローカル検証を選び、結果・スキップ・受け入れ限界を記録する。コード・設定・契約・配布物・文書の変更検証や独立レビューで使用する。
---

# 変更に応じた検証

リポジトリルートを基準に実行する。共通規則は [AGENTS.md](../../../AGENTS.md)、対象仕様は [参照表](../../../docs/development-guide.md) を確認する。

1. 差分と対象要件から検証範囲を選ぶ。コマンドの正本は [.github/workflows/validate.yml](../../../.github/workflows/validate.yml) と [package-validation.yml](../../../.github/workflows/package-validation.yml)。
2. 文書だけならリンク・記述整合・`git diff --check` を確認する。無関係な全テストを実行したり、文言に一致するだけのテストを追加したりしない。
3. コード・schema変更は対応する既存テスト、配布変更は役割別package回帰を実行する。PowerShellは固定版7.6.7。PythonはCI定義の版を基準としローカルとの差を記録する。依存は `requirements-test.txt` / `requirements-runtime.txt`、構文解析・PSScriptAnalyzerの手順はCI定義に従う。

```powershell
python -m unittest discover -s tests -p "test_*.py"
pwsh -NoProfile -File tests/Test-ReleasePackage.ps1
# 対象に応じて tests/Test-*.ps1 の個別検証を選ぶ
git diff --check
```

4. 実ログ・実設定・本番Driveへ接続しない。合成データ・模擬API・固定日時・隔離領域を使う。対象volume検証は [対象FS受け入れ計画](../../../docs/target-filesystem-acceptance.md) の前提と明示承認を確認する。
5. コマンド、対象SHAまたは未コミット差分、環境、成功/失敗、skipと理由、未実施を報告する。失敗を直した後は影響範囲を再検証し、新しい根拠がなければ同じ成功検査を繰り返さない。

単体・schema・package・CI成功は実運用受け入れではない。合成/実環境、Tier B/C、クラッシュ/電源断、ローカル可視性/クラウド内容検証を区別する。CI確認・マージ手順が必要な場合だけ [eolm-pr-handoff](../eolm-pr-handoff/SKILL.md) を読む。
