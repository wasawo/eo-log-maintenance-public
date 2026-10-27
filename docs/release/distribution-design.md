# Distribution Design: GitHub to Google Drive

- Status: E1 release-event/manual-approval gate and all-version retention/no automatic cleanup selected on 2026-10-24; PC/version-specific explicit file manifests and separate explicit configuration migration are also selected; remaining concrete distribution details are a proposed baseline. See [selection record](../decisions/selected-policy-decisions-20261024.md).
- Last updated: 2026-10-24 (policy selections and implementation limits; production workflow remains unimplemented)
- Repository: `wasawo/eo-log-maintenance-public`
- Canonical source: GitHub repository, `main` branch plus reviewed release tag
- Distribution target: Google Drive `_distribution/releases/<version>/`
- Direction: GitHub → Google Drive only

Current implementation/readiness: [2026-10-24 inventory](../status/first-release-readiness-20261024.md). The builder supports review packages and role guards; production release/authentication/upload/deployment remains incomplete.

## 1. Purpose and scope

This document defines the allowlist, exclusion rules, release package, and safety requirements for one-way distribution of approved maintenance files from GitHub to Google Drive.

GitHub is the only authoritative source for managed code and documentation. Google Drive is a distribution destination, not an editing source. Changes made to files in the Drive distribution area must never be synchronized back into GitHub.

This workflow is separate from ElectronicObserver log synchronization, manifests, archival, and deletion. A distribution failure must not trigger, skip, or otherwise change log maintenance or deletion behavior.

The workflow described here is a design. Google Drive API authentication and upload automation are not yet configured. The maintainer selected GitHub Actions as the publisher after the E1 approval gate (selection ㉘A); the distribution principal, authentication and provenance controls remain undecided. This does not reuse the desktop OAuth credential store or authorize live publication.

## 2. Distribution architecture

1. A change is reviewed and merged into `main`.
2. GitHub Actions validates the repository and builds a package from the explicit allowlist below.
3. A release is published from a reviewed version tag (for example, `v0.1.0`).
4. The package and SHA-256 manifest are uploaded to a version-specific Drive folder.
5. Only after upload and integrity checks succeed is `latest.json` updated.
6. PC-A and PC-B can retrieve and inspect a release. Applying it to a runtime directory remains a separate, manually approved operation.

A normal push or pull-request validation must not upload to Google Drive. The selected E1 gate uses a reviewed-tag release event plus explicit manual approval by the maintainer, followed by publication from GitHub Actions under selection ㉘A. Tag/VERSION/commit/package must agree; choosing this policy does not authorize an actual release or decide the distribution credential identity.

## 3. Package format and destination

Illustrative Drive layout (dummy names; configure the actual distribution folder privately):

```text
SharedLogs/_distribution/
├── latest.json
└── releases/
    └── <version>/
        ├── release.zip
        └── SHA256SUMS.txt
```

The package preserves repository-relative paths, such as `scripts/Example.ps1` and `Config/PC-A.example.json`.

- A release directory is immutable after publication; do not overwrite a previously published version.
- `latest.json` is updated last and points only to a fully uploaded and verified release.
- The repository-side builder and its tests live under `.github/scripts/` and `tests/`; they are not runtime package contents.
- For development only, a non-deployable review artifact may include a generated `PACKAGE-STATUS.txt` marker. This is the only generated-file exception to the source allowlist. It must explicitly state that the artifact is not deployable and must not be applied to either PC. A production release must not contain this marker.
- Retain all published release versions for rollback. No automatic cleanup, implicit expiry or default retained-version count is adopted. Changing this retention policy requires a new explicit decision.
- `SHA256SUMS.txt` records the SHA-256 digest of `release.zip`. The consumer must verify the downloaded ZIP before extraction.
- The package checksum proves integrity against the published checksum; it does not by itself prove that the source or release was trustworthy. Trust comes from repository review and release controls.

Example `latest.json`:

```json
{
  "version": "0.1.0",
  "sourceRepository": "wasawo/eo-log-maintenance-public",
  "releaseTag": "v0.1.0",
  "package": "releases/0.1.0/release.zip",
  "sha256Manifest": "releases/0.1.0/SHA256SUMS.txt"
}
```

This is a schema example, not a currently published Drive file.

## 4. Distribution allowlist

The selected final control model is an explicit PC-specific, version-specific file manifest. The table below remains the existing builder/design baseline, not the final approved runtime file list. Final required/optional dependencies and manifest serialization must be reviewed after official runtime entry points exist. Only reviewed allowlisted content may be included in `release.zip`.

| Path / pattern | Include? | Purpose and constraints |
|---|---|---|
| `README.md` | Yes | Operator-facing overview and safety rules |
| `CHANGELOG.md` | Yes | User-visible change history |
| `VERSION` | Yes | Package version metadata |
| `scripts/**/*.ps1` | Yes, when present | Runtime and local update scripts |
| `scripts/README.md` | Yes | Script usage notes |
| `Common/**/*.ps1` | Yes, when present | Shared runtime functions |
| `Common/**/*.py` | Yes, when present | Implemented shared validation/publication helpers; final runtime scope still requires review |
| `requirements-runtime.txt` | Yes | Runtime JSON Schema validation dependency |
| `contracts/aggregation-report-v1.schema.json` | Yes | Implemented report contract |
| `contracts/manifest-v1.schema.json` | Yes | Implemented manifest structural contract |
| `contracts/run-input-evidence-v1.schema.json` | Yes | Implemented run-input evidence contract |
| `contracts/private-recovery-evidence-v1.schema.json` | Yes | Static preservation metadata schema only; never private runtime evidence |
| `Common/README.md` | Yes | Shared-function notes |
| `Config/PC-A.example.json` | Yes | Example/template only; never use as an automatic overwrite of a real config |
| `Config/PC-B.example.json` | Yes | Example/template only; never use as an automatic overwrite of a real config |

Rules:

- Build the package from this allowlist; do not ZIP the entire repository and then attempt to remove unwanted files.
- A listed path that does not exist may be omitted only when it is explicitly optional above. Required root files must exist or the release build fails.
- A usable runtime release must include `scripts/SyncLogs.ps1` and the PC-A-only `scripts/ArchiveLogs.ps1`. `ArchiveAndUploadLogs.ps1` is not an official entry point. The PC-B package must exclude `ArchiveLogs.ps1`.
- If a new runtime dependency is needed, add it to this table through review before including it.
- Preserve relative paths in the archive.
- Do not include empty directories unless a future runtime requirement explicitly needs them.

## 5. Exclusion rules

The following items are excluded from every distribution package.

| Path / pattern | Reason |
|---|---|
| `docs/**` | Design and development documents; repository-only unless separately approved |
| `.github/**` | CI workflows, pull-request templates, and repository automation are not runtime files |
| `tests/**` | Test code and test plans are not deployed to the PCs |
| `.git/**`, `.gitignore` | Git metadata and local repository rules |
| `Config/PC-A.json`, `Config/PC-B.json` | Machine-specific active configuration; never distribute or overwrite |
| Any other `Config/*.json` not explicitly allowlisted | Prevent accidental inclusion of local or sensitive configuration |
| Runtime manifests, state files, locks, and generated reports | Machine/runtime state must not be copied as release content |
| Log files and ElectronicObserver data | Operational data, not application distribution content |
| Temporary, backup, cache, and editor files | Not part of a release |
| Credentials, access tokens, private keys, OAuth files, service-account keys, and secrets | Must never be committed or packaged |
| Local environment files (for example, `.env*`) | May contain secrets or machine-specific values |
| Any file not listed in the allowlist | Deny by default |

The exclusion rules are defense in depth. The package builder must enumerate the allowlist explicitly and should fail if a candidate path is outside it. It must not rely solely on `.gitignore`.

## 6. Configuration handling

The example configuration files are reference templates only. They may contain example paths and safe default flags, but must not contain credentials.

- Do not replace `Config/PC-A.json` or `Config/PC-B.json` during package extraction or update.
- Updating a template must not silently change the active runtime configuration.
- The selected approach is a separate explicit migration procedure/command, with source/target version, backup, diff and explicit confirmation before execution. Normal updates preserve active configuration. Concrete migration mappings and any live migration require their own review/authorization; no automatic migration is implied.
- PC-A example config retains `allowArchive: false`; operational archive requires explicit PC-A true plus current per-file checks. PC-B omits `allowArchive`. No generic `allowDelete` override is adopted. Under the [2026-10-27 move policy](../requirements/log-move-requirements.md), each PC may delete only its verified eligible local move sources, and only A may delete cloud sources after verified archival. Current templates/schema and package tests are unchanged; new runtime/interface/package acceptance remains pending.

## 7. Validation and release gates

The release workflow must fail closed if any of these checks fails:

1. Existing repository validation succeeds.
2. Required package files exist.
3. JSON example configurations parse successfully.
4. PowerShell files parse and pass the configured static analysis.
5. Tests pass when test code is available; a missing test suite must not be represented as successful behavioral coverage.
6. The package file list contains only allowlisted paths.
7. No excluded file, active PC configuration, log, runtime manifest, or secret is included.
8. The release version is valid and agrees with the repository's `VERSION` and release tag.
9. The ZIP is created successfully and its SHA-256 is recorded.

The repository has synthetic behavioral tests and isolated helpers, but no official runtime scripts or full runtime acceptance. Therefore, CI success alone must not be treated as permission to deploy. Test success does not authorize implementing or enabling deletion.

## 8. Google Drive upload safety

- Use Google Drive API authentication stored as GitHub Actions secrets or an approved short-lived identity mechanism; never place credentials in the repository or package.
- Grant the workflow only the Drive permissions needed for the distribution folder.
- Do not expose secrets to pull-request jobs or print them to workflow logs.
- Upload the versioned ZIP and checksum first; verify the resulting files before updating `latest.json`.
- If upload or verification fails, leave the previous `latest.json` unchanged.
- Never update or delete log data as part of the release workflow.
- Google Drive for desktop's local file presence is not proof that the cloud upload has completed.

The exact authentication method is still to be selected and tested against the existing My Drive folder. Do not assume a service account can write to that folder without validating ownership, sharing, and quota constraints.

## 9. PC-side update and rollback policy

The distribution workflow does not automatically deploy files into either PC's runtime directory.

For each PC:

1. Retrieve a selected release.
2. Verify `release.zip` against `SHA256SUMS.txt`.
3. Extract to a staging directory, not directly over the active runtime.
4. Show the file-level diff and preserve active machine-specific configuration.
5. Require explicit operator approval before applying changes.
6. Keep a recoverable copy of the previous runtime version until post-update verification succeeds.

PC-B must never archive or delete cloud sources. Initial completion includes each PC's own local-source deletion after verified cloud placement and source-unchanged confirmation, and PC-A cloud-source deletion after the corresponding archive checks. Package tests must prove permitted routes and forbidden roles/targets, not perpetual absence of all deletion. This policy revision does not change the current package contents, authorize implementation resumption, or permit production installation/deletion.

## 10. Implementation sequence

1. Review and merge this design.
2. Implement an allowlist-based package builder and tests for inclusion/exclusion rules.
3. Add release-triggered GitHub Actions packaging and checksum generation.
4. Configure and test Google Drive API authentication and upload to a versioned folder.
5. Implement the final `latest.json` update only after successful upload verification.
6. Implement PC-side retrieval, hash verification, diff display, and manually approved application.
7. Consider README/CHANGELOG/VERSION generation separately; generated edits must not overwrite manually maintained documentation.

## 11. Decisions and open items

Decisions fixed by this design:

- GitHub is the canonical source.
- Distribution is one-way: GitHub → Google Drive.
- Releases are versioned and immutable.
- Runtime application is manual approval only.
- The package is allowlist-based and deny-by-default.
- Active PC-specific configurations and operational data are excluded.
- Distribution is isolated from log sync/archive operations and has no deletion capability for operational logs.

Open items before production distribution:

- Confirm the final Drive distribution folder ID/path and access model.
- Choose and validate the Google authentication method.
- Implement runtime scripts and meaningful tests before calling a package deployable.
- Implement the selected E1 release-event/manual-approval gate and finalize distribution identity/provenance details; retain reviewed tag/VERSION/commit/package checks.
- Preserve all release versions under the selected no-automatic-cleanup policy and verify rollback behavior.

## 12. Observed implementation limits (2026-10-24)

- The builder uses role-specific official entrypoint presence, not a legacy sentinel. Its deployable status is a structural check, not proof that the scripts are operationally safe. Both official entrypoints are currently absent.
- The tracked workflows are Validate and Package Validation; workflow_dispatch can build an explicitly non-deployable review artifact. No tracked production release or Drive upload workflow exists.
- Generated metadata currently uses sourceRef=local-build; reviewed tag/commit provenance and immutable publication still need implementation and acceptance (OSD-06).
- Drive request/response schemas are repository contracts but are not in the current package allowlist. Their role and any new adapter dependency must be reviewed before the adapter is distributed.
- The selected OSD-07 policy retains all release versions and has no automatic cleanup. It is separate from private recovery-evidence retention; neither policy authorizes deletion of operational logs.
