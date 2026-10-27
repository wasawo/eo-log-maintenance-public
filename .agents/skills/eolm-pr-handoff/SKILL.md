---
name: eolm-pr-handoff
description: Maintain eo-log-maintenance-public handoffs and prepare commits, PRs, CI checks, and merges within user authorization. Grants no GitHub write or merge permission.
---

# Git, PR, and handoff

Root alone; no subagents/other AI tasks. Follow current user instructions and [AGENTS.md](../../../AGENTS.md), performing only requested stages. Do not extend prior PR permissions, CI alternatives, or automatic continuation to other operations.

## コミット・PR

- Reconcile `git status --short --branch`, `git branch -vv`, `git remote -v`, and relevant live GitHub state. Preserve staged/unstaged changes and check user-requested inclusions.
- No direct main push. After a merge, branch from latest main; never reuse a merged branch. Accumulate units/commits on that branch until a PR is requested.
- Never set main as work-branch upstream; e.g. `git switch --no-track -c codex/<name> origin/main`. Before authorized push, check branch/destination and specify both: `git push -u origin <work-branch>`. No main-targeted refspecs or ambiguous destinations.
- Review diff/staging for real values, secrets, runtime evidence, or prohibited package files. Confirm the existing GitHub noreply author email.
- Group related specs/code/tests/handoff in one PR. State requirement-ID/P0 impact and acceptance limits. PR body: problem, resulting behavior, validation, remaining work.
- Use [eolm-validation](../eolm-validation/SKILL.md) as needed. PR permission is not merge permission; external operations stay within user authorization.

## CI・マージ

- When available, check Validate and Package Validation on latest PR HEAD; old-SHA success does not cover new commits.
- After the initial CI check, recheck at 90-second intervals, at most 5 times. Split waits to receive user input. If incomplete/failed, report status/URL and do not merge.
- If CI is unavailable, report why, local coverage, environment differences, and unrun CI. Local alternatives are not CI success; do not relax merge conditions or reuse another PR's exception approval.
- Even with merge approval, verify latest-HEAD checks and actual merge requirements. After merging, confirm actual SHA and main CI.

## 引き継ぎ

- Root updates [next-chat.md](../../../docs/handoff/next-chat.md) each work unit: date, checked baseline SHA, branch/PR, changes, validation/results/URLs, incomplete/pending decisions, concrete next work, and unproven scope.
- Put current state first. Distinguish uncommitted/unpushed/unmerged/unrun; never pre-record success. Preserve approval/pause status.
- Do not duplicate permanent rules/model settings in handoff. Archive long history in `docs/handoff/archive/`; old instructions are not current authorization.
