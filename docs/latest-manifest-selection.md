# Latest manifest selection core

- Basis: approved C4-A in osd-02-crash-concurrency-options.md; EOLM-MAN-002 in requirements-traceability.md; staging-file-lifecycle.md section 8.
- Scope: supplied candidate observations only. No runtime enumeration, source/Drive access, manifest rewrite, lock disposition or operation authorization.

## Inputs and identity

Common/LatestManifestSelection.py provides ManifestCandidate(filename, content)
and select_latest_manifest. The caller supplies a complete exact-scope list or
tuple, explicit enumeration completion, reliable UTC observation and requested
scope. None content means an unreadable candidate and blocks the operation.

parse_manifest_filename independently parses the existing defined basename:
<PC-ID>_<LogType>_<TargetPeriod>_<run_id>.json. It rejects paths, malformed IDs,
wrong log-specific period forms and unknown names. The exact parsed PC/log/
period/run identity must match schema-validated JSON. No values are inferred
from JSON to manufacture filename agreement. This uses the existing name
contract; older notes saying the filename convention is open are historical,
not authorization to invent another form.

All candidates are validated before selection, including older candidates.
Duplicate JSON keys, unknown/unsupported fields or versions, read uncertainty,
scope mismatch and conflicting reuse of one UUID fail closed. Exceptions carry
fixed reason codes without candidate data, names, paths or exception details.

## Ordering and time

Only a unique maximum started_at_utc is selected. A tie is ambiguous, including
equivalent fractional spellings; enumeration order, UUID ordering, creation time
and LastWriteTime are never tie-breaks. Fractional timestamps retain every digit
allowed by the schema instead of truncating to Python microseconds.

Run times must parse as UTC ISO 8601 with uppercase Z; finish must not precede
start. Future tolerance is an explicit helper argument with the approved initial
five-minute default. Missing/unreliable current UTC blocks selection. Historical
manifest age alone is not a 24-hour expiration. The caller still must establish
clock reliability; this helper does not query or prove host time synchronization.
Current-execution freshness and per-file/cross-artifact temporal policy remain
separate gates.

By default a unique latest declared status must be success. Latest running,
partial_failure or failure blocks; no older success fallback occurs. Explicit
inspection mode can report the latest incomplete status, without permission to
recover, upload or archive. Results contain only index, run_id and declared status.

## Evidence and remaining gates

Thirty-two in-memory synthetic tests cover both PCs/log types, naming and identity
mismatch, malformed/read-error/duplicate candidates, ambiguity, conflict, order
independence, no-fallback behavior, UTC/future/finish boundaries, full schema
fraction precision, clock uncertainty and fixed reasons/input preservation.

Schema/selection success is not proof of aggregation correctness, full per-file
semantic consistency, current Drive content, or archive eligibility. The separate read-only directory adapter below adds bounded disk observations.
Approved-root authority, protection through later use, current clock acquisition,
actual recovery/new-run integration and end-to-end acceptance remain incomplete. The schema file is read from the trusted repository/package;
runtime roots and manifests are never opened by this helper. No Tier B or P0
closure is claimed.

## Read-only directory adapter

Common/ManifestDirectoryReader.py reads only the defined
<maintenanceLocal>/_maintenance/manifests/<PC-ID>/ directory. A caller must
supply an already trusted and qualified absolute local root and reliable UTC.
Relative/traversing roots are rejected; missing directories are not created.
Every directory entry must be a regular non-reparse file with a defined manifest
basename for this PC. Temporary/unknown entries and subdirectories block selection.
All entries, including other periods/log types for this PC, are schema/identity/
time validated before filtering the requested tuple. This conservative adapter
never silently drops a corrupt foreign-period candidate.

Root/ancestor identity is checked with lstat, with reparse rejection. Each file's
identity, size and timestamps must agree at enumeration, immediately before open,
on the opened descriptor before reading, after reading, and on the path after
close. The directory is scanned again after selection and must match. Read or
partial-enumeration failure blocks with fixed reasons. These are point-in-time
checks, not a namespace snapshot, protection against arbitrary metadata restoration,
or a guarantee about later path use.

The immutable result contains the selected basename, run ID, declared status,
SHA-256 and exact bytes already validated. Content is excluded from its normal
repr. Consumers must use those bytes rather than independently reopening a path.
Neither the hash nor selection grants recovery, Drive, or archive authorization.
The adapter has no write, creation, deletion or formal runtime entrypoint.
Nineteen synthetic tests include three actual Windows junction cases, descriptor
replacement before read, partial enumeration, final rescan mutation, no fallback,
scope filtering, byte preservation and sanitized errors. No Tier B extension or
P0 closure is claimed.
