---
name: eolm-validation
description: Validate eo-log-maintenance-public code, config, contracts, packages, or docs; review root's diff and report results, skips, and acceptance limits.
---

# Change-scoped validation

Run from repo root under [AGENTS.md](../../../AGENTS.md); select specs via [spec map](../../../docs/development/development-guide.md). Root works alone; self-check is not independent review. Record whether independent review occurred.

1. Scope checks to the diff/requirements. Authoritative commands: [Validate](../../../.github/workflows/validate.yml) and [Package Validation](../../../.github/workflows/package-validation.yml).
2. Docs-only: check links, consistency, and `git diff --check`; no unrelated suites or wording-matching tests.
3. Code/schema: relevant existing tests. Packaging: role-specific package regression. Use validated PowerShell 7.6.7 or 7.6.9 only; Python per CI, recording local differences. Dependencies: `requirements-test.txt` / `requirements-runtime.txt`. Follow CI for parsing/PSScriptAnalyzer.

```powershell
python -m unittest discover -s tests -p "test_*.py"
pwsh -NoProfile -File tests/Test-ReleasePackage.ps1
# Select individual tests/Test-*.ps1 as applicable.
git diff --check
```

4. No real logs/configs or production Drive. Use synthetic data, mock APIs, fixed dates, and isolated areas. Target-volume validation requires the [FS acceptance plan](../../../docs/validation/target-filesystem-acceptance.md) prerequisites and explicit approval.
5. Report commands, SHA or uncommitted diff, environment, results, skips/reasons, and unrun checks. After fixes, recheck affected scope; do not repeat successful checks without new grounds.

Unit/schema/package/CI success is not operational acceptance. Distinguish synthetic/live, Tier B/C, crash/power loss, and local visibility/cloud content verification. Read [eolm-pr-handoff](../eolm-pr-handoff/SKILL.md) only for CI/merge procedures.
