# C-54: Sensitive Path Detection Policy

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

- Status: **Approved**
- Decision: **A — fixed patterns combined with sensitive path-segment checks**
- Scope: diagnostic-record path sanitization; this decision supplements C-53 and does not change the diagnostic record's required fields or NULLability contract.
- Approval: maintainer selection in the project conversation, 2026-10-21.

## Normative behavior

After C-53 path syntax validation succeeds, inspect the entire path and each path segment using this version-controlled policy. If any rule matches, emit `null` for the complete path field. Do not emit a partially redacted path, replace only the matching segment, or echo the rejected value in diagnostics.

The processing order is:

1. Validate path syntax according to C-53.
2. Apply the sensitive-path policy below.
3. Emit the original path only if both checks pass; otherwise emit `null`.

A syntax-validation failure remains a rejection under C-53 and does not bypass this policy. A match in any rule has the same outcome; there is no rule that can override a match from another rule.

## Determinism and comparison

- Policy rules are explicit, version-controlled constants; no OS-specific secret stores, environment variables, locale-sensitive comparisons, or runtime heuristics may alter the result.
- Compare ASCII policy tokens case-insensitively using ordinal/invariant semantics. Do not use the host OS's default path comparison.
- Split segments only according to the separators recognized by C-53. Do not normalize, resolve, or rewrite the input to make it appear safe.
- Apply token-boundary rules explicitly. For sensitive-name tokens, a token is bounded by the start/end of a segment or a non-alphanumeric character. Thus `api-token-prod.txt` matches, while `tokenizer.txt` does not match merely because it starts with the letters `token`.
- If a future rule needs Unicode-aware matching, define its normalization and case-folding behavior explicitly before adoption; until then, policy keywords are ASCII.

## Rule groups

Evaluate all groups against the path and its individual segments:

1. **Sensitive fixed names:** exact segment names including `.env`, `.npmrc`, `.pypirc`, `.netrc`, `.dockerconfigjson`, `.aws`, `.ssh`, `.gnupg`, `secrets`, `secret`, `credentials`, and `credential`. The list is illustrative of the initial fixed policy and must be represented as a maintained, testable constant in implementation.
2. **Sensitive-name tokens:** any segment containing a bounded token from this case-insensitive set: `token`, `password`, `passwd`, `secret`, `credential`, `credentials`, `apikey`, `api-key`, `private-key`, `access-key`, `client-secret`, `authorization`, or `bearer`. Token separators and compound forms must be explicitly covered by tests; hyphenated forms listed above are literal alternatives, not a general substring heuristic.
3. **Secret-value formats:** reject a path if it contains a recognizable credential-bearing form, including URI user-info (`scheme://user:password@`), bearer credential text, common provider-token prefixes (for example `ghp_`, `github_pat_`, `AKIA` followed by an access-key-like identifier), or PEM private-key header markers. Patterns must be anchored/bounded enough to avoid matching arbitrary ordinary words and must be tested with positive and negative fixtures.

The implementation must not log the matched token, secret value, or original path to explain a rejection. A safe fixed reason code may be recorded if the existing diagnostic contract allows it; do not add a new field or change existing NULL rules without a separate decision.

## Compatibility and change control

- C-53 syntax rules remain authoritative for path structure; C-54 adds a confidentiality check after syntax validation.
- Any addition, removal, or semantic change to a rule requires explicit review, an update to this decision record/policy version, and tests before acceptance.
- Existing diagnostic-record required fields, NULLability, and sanitization guarantees remain unchanged.
- This policy is not proof that all possible secrets can be recognized. Unknown secret formats must not be handled by heuristic rewriting; extend the reviewed fixed policy when a concrete format is identified.

## Required tests

Add deterministic fixtures for:
- Each fixed sensitive name, case variants, and ordinary similarly named files.
- Sensitive tokens at segment boundaries and within compound names, including `api-token-prod.txt`; ensure `tokenizer.txt` is not rejected solely due to a substring.
- Secret-value formats and near-miss negative cases.
- Sensitive values in directory segments as well as final file names.
- Every match producing a NULL path, never a partially redacted value.
- Syntax rejection occurring before sensitive-pattern evaluation, with no rejected input echoed into diagnostic output.
- Repeatability across Windows/Linux and locale settings where test infrastructure permits.

## Related decisions

- C-53: invalid/dangerous path handling — the entire path becomes `null`.
- Existing diagnostic-record contract: required fields, NULLability, and sanitization remain unchanged.


## C-54 approved secret-format grammars — P1–P6 (2026-10-21)

The maintainer explicitly approved **Option A for each of P1–P6** on 2026-10-21. This section makes the concrete grammars normative. It does not claim that every possible secret format is detectable, and it does not implement the C-53/C-54 path sanitizer.

All regexes are .NET-compatible and are applied to the complete C-53-validated candidate path as well as each validated segment where applicable. Any match rejects the entire optional path field as JSON `null`. Do not trim, normalize, rewrite, resolve against a filesystem, inspect symlinks, or emit matched input.

| Decision | Normative rule |
|---|---|
| P1 — URI user-info | `(?i)\b[A-Za-z][A-Za-z0-9+.-]*://[^:/@\s][^/@\s]*:[^/@\s]+@` — scheme starts with an ASCII letter and continues with ASCII letters/digits/`+`/`.`/`-`; username and password are non-empty; the first username character excludes colon, slash, at-sign, and whitespace, while later username characters exclude slash, at-sign, and whitespace (so a colon is permitted after the first character); password characters exclude slash, at-sign, and whitespace. Percent-encoded characters are allowed. |
| P2 — Bearer | `(?i)(?<![A-Za-z0-9_-])Bearer[ \t]+[A-Za-z0-9._~+/-]+=*(?![A-Za-z0-9._~+/-])` — scheme matching is case-insensitive; token is non-empty and restricted to the listed ASCII alphabet with optional trailing equals padding. |
| P3 — GitHub classic token-like values | `(?<![A-Za-z0-9_])ghp_[A-Za-z0-9]{20,}(?![A-Za-z0-9])` — case-sensitive prefix; suffix is ASCII alphanumeric and at least 20 characters; explicit ASCII boundaries as shown. |
| P3 — GitHub fine-grained token-like values | `(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{20,}(?![A-Za-z0-9_])` — case-sensitive prefix; suffix is ASCII alphanumeric/underscore and at least 20 characters; explicit ASCII boundaries as shown. |
| P4 — AWS access-key-ID-like values | `(?<![A-Za-z0-9])AKIA[A-Z0-9]{16}(?![A-Za-z0-9])` — exact uppercase `AKIA` plus 16 uppercase ASCII letters/digits. Other AWS access-key prefixes are **out of scope** for this approved grammar unless separately approved. This detects identifier-like material, not proof that the paired secret key is present. |
| P5 — PEM private-key markers | Case-sensitive fixed marker list: `-----BEGIN PRIVATE KEY-----`, `-----BEGIN RSA PRIVATE KEY-----`, `-----BEGIN EC PRIVATE KEY-----`, `-----BEGIN DSA PRIVATE KEY-----`, `-----BEGIN OPENSSH PRIVATE KEY-----`. No general label grammar or other PEM labels are implied. |
| P6 — boundaries/case | Use the ASCII boundaries embedded in the regexes exactly. URI and Bearer scheme matching is case-insensitive; `ghp_`, `github_pat_`, and `AKIA` patterns are case-sensitive; PEM markers are case-sensitive. Do not broaden to substring matching, Unicode boundary/case folding, trimming, or generic entropy heuristics. |

**C-53 interaction:** path syntax validation remains first. A URI-like full path may be rejected by C-53 before the URI matcher is reached. A full-path integration test must assert the final safe outcome without claiming C-54 matched; test the URI regex directly in the pure pattern-contract test.

**Coverage limit:** these patterns are fixed reviewed detection rules, not a universal secret detector. New prefixes, alphabets, PEM labels, or boundary semantics require explicit approval, decision-record/specification updates, and tests.

**Executable test boundary:** `tests/Test-C54PatternContract.ps1` verifies the approved regex grammar and synthetic positive/negative/boundary fixtures directly. It is a pattern-contract test only; it does not prove that runtime path sanitization, full-field nulling, or diagnostic non-disclosure is implemented. Those runtime tests remain pending.
