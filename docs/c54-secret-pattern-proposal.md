# C-53/C-54 secret-bearing path pattern proposal

- Status: **Historical proposal; P1–P6 were explicitly approved on 2026-10-21.** The normative grammars and decision semantics are now recorded in `docs/decision-record-c54-sensitive-path-detection.md`; this file remains the proposal record and is not the canonical normative source.
- Baseline: main commit `1bc71ace6871ee4682655ae8463f7986ef1edccf`.
- Purpose: provide concrete candidate grammars for maintainer review before any normative change or runtime implementation.
- Safety: all examples are synthetic. Never place real credentials, real user paths, logs, or Drive data in fixtures.

## Existing approved behavior remains unchanged

C-53 syntax validation runs first. C-54 Option A then applies fixed sensitive names/tokens and secret-bearing format checks. If the path is invalid or any sensitive rule matches, the entire optional path is JSON `null`; do not partially redact, echo the rejected value, resolve paths against a filesystem, or inspect symlinks. This proposal does not amend that decision.

## Candidate matching table — approval required

Regexes below are .NET-compatible illustrative candidates, applied to the complete candidate path string using ordinal/invariant case handling where specified. They are not ready for production until approved, implemented, and tested. ASCII boundaries are used deliberately; Unicode normalization/case folding is out of scope.

| Format | Candidate grammar | Synthetic positive fixture | Near-miss/control | Main trade-off |
|---|---|---|---|---|
| URI user-info with password | `(?i)\b[A-Za-z][A-Za-z0-9+.-]*://[^:/@\s][^/@\s]*:[^/@\s]+@` | `https://demo-user:demo-pass@example.invalid/a.txt` | `https://example.invalid/a.txt`; `https://demo-user@example.invalid/a.txt` | Requires non-empty username, password, and `@`; excludes whitespace and slash inside user-info. Percent-encoded values are permitted. |
| Bearer credential | `(?i)(?<![A-Za-z0-9_-])Bearer[ \t]+[A-Za-z0-9._~+/-]+=*(?![A-Za-z0-9._~+/-])` | `Bearer demoToken_123==` | `Bearer`; `Bearer `; `Bearerish demoToken` | Requires a case-insensitive scheme word and non-empty ASCII token. A conservative ASCII grammar may miss non-standard credential encodings. |
| GitHub classic token-like value | `(?<![A-Za-z0-9_])ghp_[A-Za-z0-9]{20,}(?![A-Za-z0-9])` | `ghp_AbCdEf0123456789GhIjKlMn` | `ghp_`; `xghp_AbCdEf0123456789GhIjKlMn` | Minimum suffix length reduces false positives but can miss shorter or future token formats. Confirm the threshold against supported token types. |
| GitHub fine-grained token-like value | `(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{20,}(?![A-Za-z0-9_])` | `github_pat_demo0123456789_AbCdEf0123456789` | `github_pat_`; `xgithub_pat_demo0123456789_AbCdEf0123456789` | Allows underscore in the suffix; threshold may need adjustment for current/future formats. |
| AWS access-key-ID-like value | `(?<![A-Za-z0-9])AKIA[A-Z0-9]{16}(?![A-Za-z0-9])` | `AKIAIOSFODNN7EXAMPLE` | `AKIA123`; `xAKIAIOSFODNN7EXAMPLE` | Exact 16-character suffix is narrow and may not cover other AWS key prefixes. Treat as identifier-like sensitive material, not proof that the paired secret key is present. |
| PEM private-key header | `-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----` (case-sensitive) | `-----BEGIN PRIVATE KEY-----`; `-----BEGIN OPENSSH PRIVATE KEY-----` | `-----BEGIN CERTIFICATE-----`; `-----BEGIN PUBLIC KEY-----` | Fixed allowlist of common labels is deterministic but does not recognize every vendor-specific key label. Add labels only by explicit review. |

### URI rule interaction with C-53

The URI example contains a colon and URI delimiters, which C-53 path syntax may reject before C-54 runs. Therefore, the full-path positive fixture should assert the final safe outcome (path becomes `null`) without falsely claiming the C-54 URI matcher ran. If unit-level coverage of the URI matcher is desired, test the pure matcher separately with synthetic input; do not change the C-53-before-C-54 processing order.

## Boundary and application rules proposed for review

1. Apply format matchers to the complete candidate path string as well as any segments, consistent with the approved C-54 wording; any match nulls the complete path.
2. Do not trim whitespace or normalize/rewrite input before matching. Syntax validation is responsible for rejecting prohibited controls and invalid path forms.
3. Use the exact ASCII boundaries in each candidate. Do not replace them with broad substring matching or generic high-entropy heuristics.
4. Treat PEM marker matching as case-sensitive; URI and Bearer schemes are case-insensitive. Provider-token prefix matching is case-sensitive unless maintainers explicitly approve case-insensitive matching.
5. Rejected path values and matched substrings must never be included in error text, telemetry, test failure messages, or logs. Tests should assert absence of a distinctive synthetic canary value from all emitted diagnostics.
6. Keep positive/negative fixture strings synthetic and obviously non-operational. Never copy real tokens or credentials into tests.

## Questions requiring explicit approval

- **P1 — URI user-info:** approve the scheme/user/password grammar above, or specify different character restrictions.
- **P2 — Bearer:** approve the ASCII token alphabet and case-insensitive scheme handling.
- **P3 — GitHub token-like prefixes:** approve suffix alphabets and the proposed minimum length of 20, or choose a documented alternative. The threshold is a heuristic boundary for a known prefix, not a guarantee of complete detection.
- **P4 — AWS:** approve matching exactly `AKIA` plus 16 uppercase alphanumeric characters, and confirm whether other access-key prefixes are in scope.
- **P5 — PEM:** approve the fixed marker list (`PRIVATE KEY`, `RSA PRIVATE KEY`, `EC PRIVATE KEY`, `DSA PRIVATE KEY`, `OPENSSH PRIVATE KEY`) or provide an explicit replacement list.
- **P6 — boundary tests:** approve ASCII boundaries and case-sensitivity as listed, including the stated negative controls.

Decision status: the maintainer explicitly approved option A for each P1–P6 on 2026-10-21. The approved expressions are now normative only as recorded in `docs/decision-record-c54-sensitive-path-detection.md`. Do not infer broader coverage or additional patterns. Runtime sanitizer implementation and end-to-end tests remain pending.

## Required tests after approval

- Direct unit tests for every pattern with positive, near-miss, prefix-boundary, suffix-boundary, and case-variant fixtures as applicable.
- Integration tests proving C-53 syntax rejection occurs before C-54 checks and that either failure produces whole-field `null`.
- A secret-canary assertion proving rejected inputs are absent from all diagnostic output.
- Repeatability tests independent of OS, locale, current directory, and filesystem state.
- CI tests and release-package inclusion for the eventual pure sanitization helper.

Passing these tests alone does not constitute runtime end-to-end acceptance and does not close any P0 gap.
