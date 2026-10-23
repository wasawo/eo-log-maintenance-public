# C-53/C-54 deterministic policy test matrix and audit

- Status: non-normative audit and test-planning artifact; does not amend approved C-53 or C-54 decisions.
- Baseline: main commit `5b258fbdc775e5aa5db2dc2903108d7a4461bd29`.
- Scope: define deterministic fixture coverage before implementing diagnostic path sanitization.
- Safety: fixtures must be synthetic; never use actual credentials, user paths, logs, or Drive data.

## Audit result

C-53 and C-54 agree on the high-level processing contract:

1. Validate path type/text and relative-path syntax.
2. Check the validated candidate against fixed sensitive-path policy.
3. Emit the canonical relative path only when both checks pass; otherwise emit JSON null for the entire optional path.
4. Do not partially redact, resolve against a filesystem, inspect symlinks, use current directory, or echo rejected input.
5. Invalid required diagnostic fields reject finalization rather than being repaired.

No executable diagnostic sanitization function or dedicated test file currently exists in the tracked tree. Existing `Common/LogFunctions.ps1` covers runtime version, filename/date parsing, cutoffs, and eligibility only. Existing CI success therefore does not prove C-53/C-54 behavior.

## Deterministic fixture matrix

The eventual implementation tests should assert both the returned value and that rejected input is not included in any diagnostic output. All cases are synthetic.

| Area | Positive / control fixtures | Negative fixtures and expected outcome |
|---|---|---|
| Input type | Valid string relative path | Null, non-string, or invalid Unicode scalar text => path null |
| Separator handling | `a/b.txt`; `a\\b.txt` canonicalizes to `a/b.txt` | Mixed/repeated separators creating an empty segment => null |
| Rooted paths | Ordinary relative path | `/a`, `C:/a`, `C:a`, UNC and device prefixes => null |
| Segment grammar | `logs/2026/file.txt` | Empty path, empty segment, `.`, `..`, colon/ADS, NUL, or any control character => null |
| Fixed sensitive names | Ordinary `config.json`; ordinary names that merely resemble a protected name | Each C-54 fixed name, including case variants, in first/middle/final segment => null |
| Bounded sensitive tokens | `tokenizer.txt` must not match solely due to the substring `token` | `api-token-prod.txt`, `my_password.txt`, and each listed token bounded by segment edge or non-alphanumeric => null |
| Secret-bearing formats | Near-miss text that lacks the required credential structure | URI user-info credential form, bearer credential form, provider-token prefix form, and PEM private-key marker => null |
| Whole-path behavior | Safe path passes unchanged except separator canonicalization | Any one matching segment or whole-path pattern => the complete path is null, never partial redaction |
| Required fields | Valid allowlisted error_id/error_code/phase/operation and fixed C-52 message | Invalid required enum/identity or message code => diagnostic finalization rejected |
| Determinism | Repeat same fixtures under different current directories/locales | Identical results; no filesystem, symlink, locale, current-directory, or host path-rule dependency |
| Serialization / invariants | JSON serializer escapes valid values correctly | JSON escaping must not make unsafe input acceptable; path nulling must preserve event identity and classification |

## Concrete ambiguity found — requires maintainer decision before normative implementation

C-54 gives examples of secret-value formats but does not define exact matching grammars for every format. This is a concrete implementation/test ambiguity, not a reason to reopen the already-approved overall option A.

The following details need an explicit choice recorded before a normative implementation claims complete coverage:

1. **URI user-info:** which URI scheme syntax is in scope, whether empty usernames/passwords count, and the exact allowed user-info character grammar before `@`.
2. **Bearer credential text:** whether the matcher requires an explicit case-insensitive `Bearer` scheme plus a non-empty token, and which ASCII token characters are accepted.
3. **Provider-token prefixes:** minimum/maximum suffix length and permitted suffix characters for `ghp_`, `github_pat_`, and access-key-like `AKIA` values. The current record gives prefixes/examples but not a complete grammar.
4. **PEM private-key markers:** whether to match a fixed enumerated set of labels (for example, RSA, EC, OPENSSH, and generic PRIVATE KEY) or a bounded general label grammar.
5. **Token separators:** confirm fixtures for underscore, hyphen, dot, and other non-alphanumeric boundaries, because the rule says token boundaries are non-alphanumeric but compound hyphenated alternatives are literal entries.

### Recommended next decision

Keep the already-approved C-53/C-54 processing order and whole-field-null behavior unchanged. Approve a small, explicit regex/grammar table for the four secret-bearing format groups, including one valid positive fixture and near-miss negatives per grammar. Avoid broad substring matching, generic high-entropy detection, heuristic rewriting, and filesystem-dependent validation.

No choice in this recommendation is adopted by this audit. Until the exact patterns are approved and tested, report secret-format coverage as incomplete rather than silently choosing a grammar.

## Implementation gate

After the maintainer approves the exact pattern table:

- implement a pure, deterministic path-validation/sanitization function;
- add isolated synthetic fixtures to the PowerShell test suite;
- verify full-field nulling and non-disclosure, including tests that no rejected path is echoed;
- verify release packaging includes the function and tests run in CI;
- keep runtime integration, P0 acceptance, archive enablement, and deletion behavior separate. Passing unit tests alone must not close P0.


## Approved C-54 grammar test extension — 2026-10-21

P1–P6 were explicitly approved (option A for each). Exact regexes and interpretation are canonical in `docs/decisions/decision-record-c54-sensitive-path-detection.md`, section “C-54 approved secret-format grammars — P1–P6”. The new executable `tests/Test-C54PatternContract.ps1` covers synthetic positives, near misses, minimum lengths, ASCII boundaries, and case sensitivity.

This test is deliberately limited to the regex grammar. It does not assert that a runtime sanitizer invokes these patterns, nulls the whole optional path, or prevents diagnostic disclosure. Those runtime tests remain pending. URI-like path fixtures must continue to distinguish C-53 rejection from C-54 URI-matcher behavior.
