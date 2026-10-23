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
semantic consistency, current Drive content, or archive eligibility. Disk reader
enumeration/read/TOCTOU protection, safe filename-to-root binding, current clock
acquisition, actual recovery/new-run integration and end-to-end acceptance remain
unimplemented here. The schema file is read from the trusted repository/package;
runtime roots and manifests are never opened by this helper. No Tier B or P0
closure is claimed.
