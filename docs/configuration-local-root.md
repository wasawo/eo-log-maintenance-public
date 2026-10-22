# Local maintenance artifact root

- Approved by the operator: 2026-10-23.
- Scope: required `maintenanceLocal` in both PC configurations; no production deployment authorization.
- Related: EOLM-CFG-001/006/007, approved local-authoritative/verified-Drive-copy storage direction, P0-006/P0-009/P0-010/P0-012.

## Meaning and separation

`maintenanceLocal` is the local authoritative root for the current PC's manifests,
frozen inventories/evidence and aggregation reports (including associated
publication markers/lock records where separately specified). It is not the
other PC's original storage and is not the Drive copy. PC-A and PC-B each
configure their own root; actual values stay in their untracked configuration.

Both examples require a non-empty absolute Windows drive path. Public defaults
are `C:\Example\PCA\Maintenance` and `C:\Example\PCB\Maintenance`.
The root must be distinct from, and neither contain nor be contained by,
runtimeRoot, local log roots, Drive roots, and PC-A archive roots.

The package builder validates required fields, path type/syntax and lexical
non-overlap after Windows full-path normalization, ignoring case and trailing
directory separators. A common string prefix without a directory boundary
is not containment. Errors do not echo configured path values.

## Evidence boundary

Package validation operates on public example strings, including paths that do
not exist. It does not create the root, read an active config, inspect actual
volumes/reparse aliases, prove physical separation or authorize an archive.
A runtime loader/path gate must perform its own strict validation and repeat
identity/reparse checks before side effects. Current approval does not resolve
all remaining OSD-09 deployment/migration decisions.

Deployment must create the target PC's active config from the example only when
absent; the operator only edits actual paths. Existing active configs are
preserved on updates. An older config missing maintenanceLocal must be upgraded
explicitly; do not infer a root from current directory, runtimeRoot or Drive.
This change does not implement that deployment flow yet.

## Regression evidence

The package tests cover both PCs: missing/wrong-type/relative maintenanceLocal,
equality with every other configured root, ancestor/descendant overlap,
case/trailing separators, normalized parent traversal, and a permitted sibling
with a shared string prefix. PC-A safe allowArchive default and PC-B archive
exclusion remain unchanged.


## Read-only configuration structure loader

`Common/MachineConfiguration.ps1` provides
`ConvertFrom-EoMachineConfigurationJson` and `Read-EoMachineConfiguration`.
The reader accepts strict UTF-8 (optional BOM), returns a fresh validated object,
and never creates configuration, root directories, manifests or other artifacts.

The parser rejects non-object/malformed JSON, duplicate/unknown/missing keys,
wrong primitive types, role mismatch, non-drive-qualified/ambiguous path syntax,
and maintenanceLocal equality/ancestor/descendant overlap after normalization.
PC-B must omit allowArchive; PC-A may explicitly set a boolean true or false.
A true value is configuration data only, never archive authorization.

Errors are fixed reason codes without rejected values, file contents or private
paths. The package builder shares this structural parser and additionally
requires safe template defaults (PC-A allowArchive false).

This is structural/lexical evidence, not an approved-root filesystem gate.
It does not inspect actual target volumes, resolve short-name/reparse aliases,
prove cross-root physical separation, acquire a runtime lock, contact Drive,
or integrate official entry points. Those checks remain mandatory before effects.
Bootstrap/create-once migration is a separate pending implementation.

## Create-only configuration bootstrap helper

Common/MachineConfigurationBootstrap.ps1 provides Initialize-EoMachineConfiguration
with explicit ConfigDirectory and MachineId. It operates only on an existing,
trusted extracted-package configuration directory, never by dot-sourcing alone.
It preserves any existing active entry without interpreting or changing its bytes.
A new configuration is validated from the matching safe example (PC-A
allowArchive must be false), staged in an exclusively created sibling temporary
file, flushed, and published with a non-overwriting same-directory move.

The helper creates no log/maintenance/Drive/archive directories and performs no
synchronization or archive. The operator edits actual paths only in the generated
untracked PC-A.json or PC-B.json. A preserved result does not validate old settings;
use the read-only loader separately. Missing maintenanceLocal requires an explicit
operator edit, never automatic migration. Do not run this helper in the source
checkout: the package builder intentionally rejects active configurations there.

Normal completion/failure cleans up only its own temporary file. Abrupt process
termination may leave a private .configuration-*.tmp containing configuration:
do not publish/package such leftovers, and do not infer permission to delete
unknown files. Flush/move does not establish power-loss durability. Reparse
ancestors/template are rejected at inspection time; this does not defend against
concurrent hostile directory replacement. Trusted package-directory ownership is
a prerequisite, and a physical runtime path gate remains separate. Concurrent
publication uses the non-overwrite API but adversarial race/crash acceptance is
not claimed by the basic bootstrap tests.

This is an opt-in helper with synthetic tests, not an installer invocation,
production deployment approval, final OSD-09 allowlist/migration decision or P0
closure. Active config remains excluded from source control and distribution.
