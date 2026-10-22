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
