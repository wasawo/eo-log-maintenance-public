"""Pure content/naming observations; no API, provenance proof or authority."""
from dataclasses import dataclass, field
import hashlib
import re
from Common.DriveRequestPath import is_drive_request_file_path
from Common.SourceInventoryEvidenceBuilder import _classify_filename


@dataclass(frozen=True, repr=False)
class ComparisonSource:
    filename: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, repr=False)
class PcSuffixedNameObservation:
    original_filename: str
    proposed_filename: str
    pc_id: str
    log_type: str
    may_rename: bool = field(default=False, init=False)
    may_upload: bool = field(default=False, init=False)
    may_overwrite: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


class DriveNameObservationError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def observe_pc_suffixed_name(filename, *, pc_id, log_type):
    """Project the approved suffix from an original source basename only.

    No collision/origin discovery, alias matching or rename/upload is performed.
    A suffix in the source text is not inferred provenance and is not stripped.
    """
    if type(pc_id) is not str or pc_id not in ("PC-A", "PC-B"):
        raise DriveNameObservationError("naming_pc_invalid")
    if type(log_type) is not str or log_type not in ("BattleLog", "ErrorReport"):
        raise DriveNameObservationError("naming_log_type_invalid")
    if type(filename) is not str or "/" in filename or "\\" in filename:
        raise DriveNameObservationError("naming_filename_invalid")
    try:
        filename.encode("utf-8", errors="strict")
    except UnicodeError:
        raise DriveNameObservationError("naming_filename_invalid") from None
    # Dummy root is lexical only; passing L1 performs no filesystem access.
    if (not is_drive_request_file_path("C:\\Example\\Names\\"+filename)
            or _classify_filename(filename, log_type) is None):
        raise DriveNameObservationError("naming_filename_invalid")
    suffix = "_PCA" if pc_id == "PC-A" else "_PCB"
    return PcSuffixedNameObservation(filename, filename[:-4]+suffix+filename[-4:], pc_id, log_type)


@dataclass(frozen=True, repr=False)
class DriveFileObservation:
    file_id: str
    filename: str
    size_bytes: int | None
    sha256: str | None
    sha256_trusted: bool = False
    version: str | None = None


@dataclass(frozen=True, repr=False)
class DriveListingPage:
    folder_id: str
    requested_token: str | None
    next_token: str | None
    files: tuple[DriveFileObservation, ...]
    request_succeeded: bool


@dataclass(frozen=True, repr=False)
class DriveListingObservation:
    folder_id: str
    files: tuple[DriveFileObservation, ...]
    enumeration_completed: bool = field(default=True, init=False)
    may_restore: bool = field(default=False, init=False)
    may_report_sync_success: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


class DriveListingObservationError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def collect_drive_listing(pages, *, expected_folder_id, maximum_pages=None, maximum_files=None):
    """Validate supplied page continuity; no API calls or trust qualification.

    Return no observation on partial/failed/ambiguous pages. Exhaustion alone
    is not completion: exactly one terminal page is required, with no trailer.
    Caller owns transport, timeouts, resource cleanup and authentic page binding.
    """
    if not _text(expected_folder_id):
        raise DriveListingObservationError("listing_folder_invalid")
    if any(value is not None and (type(value) is not int or value < 1)
           for value in (maximum_pages, maximum_files)):
        raise DriveListingObservationError("listing_limit_invalid")
    try:
        iterator = iter(pages)
    except Exception:
        raise DriveListingObservationError("listing_read_failed") from None
    expected_token = None
    seen_tokens = set()
    file_ids = set()
    files = []
    terminal = False
    page_count = 0
    while True:
        try:
            page = next(iterator)
        except StopIteration:
            break
        except Exception:
            raise DriveListingObservationError("listing_read_failed") from None
        if terminal:
            raise DriveListingObservationError("listing_after_terminal")
        if type(page) is not DriveListingPage or type(page.files) is not tuple:
            raise DriveListingObservationError("listing_page_invalid")
        if not _text(page.folder_id) or page.folder_id != expected_folder_id:
            raise DriveListingObservationError("listing_folder_mismatch")
        if page.request_succeeded is not True:
            raise DriveListingObservationError("listing_request_unconfirmed")
        if ((page.requested_token is not None and not _text(page.requested_token))
                or (page.next_token is not None and not _text(page.next_token))):
            raise DriveListingObservationError("listing_token_invalid")
        if page.requested_token != expected_token:
            raise DriveListingObservationError("listing_token_discontinuous")
        if page.next_token is not None:
            if page.next_token in seen_tokens:
                raise DriveListingObservationError("listing_token_cycle")
            seen_tokens.add(page.next_token)
        if maximum_files is not None and len(files) + len(page.files) > maximum_files:
            raise DriveListingObservationError("listing_file_limit_exceeded")
        for item in page.files:
            if not _valid_drive_file(item):
                raise DriveListingObservationError("listing_file_invalid")
            if item.file_id in file_ids:
                raise DriveListingObservationError("listing_identity_ambiguous")
            file_ids.add(item.file_id)
            files.append(item)
        expected_token = page.next_token
        terminal = expected_token is None
        page_count += 1
        if not terminal and maximum_pages is not None and page_count >= maximum_pages:
            raise DriveListingObservationError("listing_page_limit_exceeded")
    if not terminal:
        raise DriveListingObservationError("listing_terminal_missing")
    return DriveListingObservation(expected_folder_id, tuple(files))


@dataclass(frozen=True, repr=False)
class DownloadHashObservation:
    file_id: str
    size_bytes: int
    sha256: str
    version: str | None = None


class DownloadObservationError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def hash_downloaded_content(file_id, chunks, *, expected_size_bytes, download_completed,
                            maximum_download_bytes=None, maximum_chunk_bytes=None):
    """Hash completed download chunks without retaining contents or owning transport.

    The caller must bind the stream and completion to the requested Drive ID.
    Neither a caller flag nor this digest authenticates that binding. Each chunk
    is nonempty exact bytes; an empty payload is represented by zero chunks.
    """
    if not _text(file_id) or not _size(expected_size_bytes):
        raise DownloadObservationError("download_context_invalid")
    if download_completed is not True:
        raise DownloadObservationError("download_completion_unconfirmed")
    if any(value is not None and (type(value) is not int or value < 1)
           for value in (maximum_download_bytes, maximum_chunk_bytes)):
        raise DownloadObservationError("download_limit_invalid")
    if maximum_download_bytes is not None and expected_size_bytes > maximum_download_bytes:
        raise DownloadObservationError("download_limit_exceeded")
    if isinstance(chunks, (bytes, bytearray, str)):
        raise DownloadObservationError("download_chunks_invalid")
    digest = hashlib.sha256()
    size = 0
    try:
        iterator = iter(chunks)
    except Exception:
        raise DownloadObservationError("download_read_failed") from None
    while True:
        try:
            chunk = next(iterator)
        except StopIteration:
            break
        except Exception:
            raise DownloadObservationError("download_read_failed") from None
        if type(chunk) is not bytes or not chunk:
            raise DownloadObservationError("download_chunk_invalid")
        if maximum_chunk_bytes is not None and len(chunk) > maximum_chunk_bytes:
            raise DownloadObservationError("download_chunk_limit_exceeded")
        size += len(chunk)
        if size > expected_size_bytes:
            raise DownloadObservationError("download_size_mismatch")
        digest.update(chunk)
    if size != expected_size_bytes:
        raise DownloadObservationError("download_size_mismatch")
    return DownloadHashObservation(file_id, size, digest.hexdigest())


@dataclass(frozen=True, repr=False)
class ContentComparison:
    status: str
    reason_code: str
    candidate_file_id: str | None = None
    may_restore: bool = field(default=False, init=False)
    may_report_sync_success: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


def _text(value):
    return type(value) is str and bool(value) and "\x00" not in value


def _size(value):
    return type(value) is int and value >= 0


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _version(value):
    return value is None or (type(value) is str and re.fullmatch('[1-9][0-9]*',value) is not None)


def _valid_drive_file(item):
    return (type(item) is DriveFileObservation and _text(item.file_id)
            and _text(item.filename) and (item.size_bytes is None or _size(item.size_bytes))
            and (item.sha256 is None or _hash(item.sha256))
            and type(item.sha256_trusted) is bool
            and _version(item.version))


@dataclass(frozen=True, repr=False)
class ContentComparisonBatch:
    status: str
    reason_code: str
    results: tuple[ContentComparison, ...] = ()
    may_restore: bool = field(default=False, init=False)
    may_report_sync_success: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


def _valid_content_comparison(item):
    if (type(item) is not ContentComparison or not _text(item.status) or not _text(item.reason_code)
            or any(flag is not False for flag in
                   (item.may_restore, item.may_report_sync_success, item.may_archive))):
        return False
    if item.status == "comparison_candidate":
        return _text(item.candidate_file_id)
    return item.status == "held" and item.candidate_file_id is None


def _valid_comparison_batch(batch):
    if (type(batch) is not ContentComparisonBatch or type(batch.results) is not tuple
            or not _text(batch.status) or batch.status not in ("held", "compared")
            or not _text(batch.reason_code)
            or any(flag is not False for flag in
                   (batch.may_restore, batch.may_report_sync_success, batch.may_archive))):
        return False
    if batch.status == "held" and batch.results:
        return False
    return all(_valid_content_comparison(item) for item in batch.results)


class _ComparisonInputError(ValueError):
    pass


def _valid_source(source):
    return (type(source) is ComparisonSource and _text(source.filename)
            and _size(source.size_bytes) and _hash(source.sha256))


def _index_files(files):
    if type(files) is not tuple:
        raise _ComparisonInputError("comparison_observations_invalid")
    by_id = {}
    for item in files:
        if not _valid_drive_file(item):
            raise _ComparisonInputError("comparison_observations_invalid")
        if item.file_id in by_id:
            raise _ComparisonInputError("comparison_identity_ambiguous")
        by_id[item.file_id] = item
    return by_id


def _index_downloads(downloads, by_id):
    if type(downloads) is not tuple:
        raise _ComparisonInputError("comparison_observations_invalid")
    downloaded = {}
    for item in downloads:
        if (type(item) is not DownloadHashObservation or not _text(item.file_id)
                or not _size(item.size_bytes) or not _hash(item.sha256) or not _version(item.version)):
            raise _ComparisonInputError("comparison_download_invalid")
        if item.file_id in downloaded or item.file_id not in by_id:
            raise _ComparisonInputError("comparison_download_unbound")
        if item.version is not None and item.version != by_id[item.file_id].version:
            raise _ComparisonInputError("comparison_download_version_mismatch")
        downloaded[item.file_id] = item
    return downloaded


def _group_files(by_id):
    by_name = {}
    for item in by_id.values():
        by_name.setdefault(item.filename, []).append(item)
    return by_name


def _compare_source(source, by_name, downloaded):
    def held(reason):
        return ContentComparison("held", reason)

    match_count = 0
    candidate_id = None
    for item in by_name.get(source.filename, ()):
        if item.size_bytes is None:
            return held("comparison_metadata_unavailable")
        if item.size_bytes != source.size_bytes:
            continue
        digest = item.sha256 if item.sha256_trusted else None
        fallback = downloaded.get(item.file_id)
        if fallback is not None:
            if fallback.size_bytes != item.size_bytes or (digest is not None and fallback.sha256 != digest):
                return held("comparison_download_mismatch")
            digest = fallback.sha256
        if digest is None:
            return held("comparison_hash_unavailable")
        if digest == source.sha256:
            match_count += 1
            candidate_id = item.file_id
    if match_count != 1:
        return held("comparison_no_match" if not match_count else "comparison_multiple_matches")
    return ContentComparison("comparison_candidate", "comparison_unique_content_match", candidate_id)


def _compare_sources(sources, by_name, downloaded):
    # Reuse only within this invocation's already-validated observations.
    # Keep one output slot per source, including repeated values/local paths.
    comparisons = {}
    results = []
    for source in sources:
        key = (source.filename, source.size_bytes, source.sha256)
        if key not in comparisons:
            comparisons[key] = _compare_source(source, by_name, downloaded)
        results.append(comparisons[key])
    return tuple(results)


def compare_drive_content(source, files, *, source_trusted, expected_folder_id,
                          observed_folder_id, enumeration_completed, downloads=()):
    """Find one exact name/size/hash candidate, without provenance or authority."""
    def held(reason):
        return ContentComparison("held", reason)

    if source_trusted is not True:
        return held("comparison_source_untrusted")
    if not _valid_source(source):
        return held("comparison_source_invalid")
    if (not _text(expected_folder_id) or not _text(observed_folder_id)
            or expected_folder_id != observed_folder_id):
        return held("comparison_folder_unconfirmed")
    if enumeration_completed is not True:
        return held("comparison_listing_incomplete")
    try:
        by_id = _index_files(files)
        downloaded = _index_downloads(downloads, by_id)
        return _compare_source(source, _group_files(by_id), downloaded)
    except _ComparisonInputError as exc:
        return held(str(exc))


def _listing_snapshot(listing, expected_folder_id):
    if not _text(expected_folder_id):
        raise _ComparisonInputError("comparison_folder_unconfirmed")
    if (type(listing) is not DriveListingObservation or type(listing.files) is not tuple
            or any(flag is not False for flag in (listing.may_restore,
                listing.may_report_sync_success, listing.may_archive))):
        raise _ComparisonInputError("comparison_listing_invalid")
    if listing.enumeration_completed is not True:
        raise _ComparisonInputError("comparison_listing_incomplete")
    if not _text(listing.folder_id) or listing.folder_id != expected_folder_id:
        raise _ComparisonInputError("comparison_folder_unconfirmed")
    return _index_files(listing.files)


def _unchanged_listings(before, after, expected_folder_id):
    old = _listing_snapshot(before, expected_folder_id)
    new = _listing_snapshot(after, expected_folder_id)
    if old != new:
        raise _ComparisonInputError("comparison_listing_changed")
    return new


def compare_reobserved_drive_contents(sources, before, after, *, source_trusted,
                                      expected_folder_id, downloads=()):
    """Validate shared observations once and compare explicit sources in order.

    Global input/listing failure returns no partial results. Per-source held
    results remain held, and compared never means sync success or no_work.
    No API re-query, provenance/freshness proof, cross-call cache or receipt is provided.
    """
    def held(reason):
        return ContentComparisonBatch("held", reason)

    if source_trusted is not True:
        return held("comparison_source_untrusted")
    if type(sources) is not tuple:
        return held("comparison_sources_invalid")
    if any(not _valid_source(source) for source in sources):
        return held("comparison_source_invalid")
    try:
        by_id = _unchanged_listings(before, after, expected_folder_id)
        downloaded = _index_downloads(downloads, by_id)
        by_name = _group_files(by_id)
        return ContentComparisonBatch("compared", "comparison_batch_observations_consistent",
            _compare_sources(sources, by_name, downloaded))
    except _ComparisonInputError as exc:
        return held(str(exc))


def compare_reobserved_drive_content(source, before, after, *, source_trusted,
                                     expected_folder_id, downloads=()):
    """Single-source compatibility API; matching metadata is never a receipt."""
    result = compare_reobserved_drive_contents((source,), before, after,
        source_trusted=source_trusted, expected_folder_id=expected_folder_id, downloads=downloads)
    if result.status == "held":
        return ContentComparison("held", result.reason_code)
    return result.results[0]


@dataclass(frozen=True, repr=False)
class DownloadRequirement:
    file_id: str
    expected_size_bytes: int


@dataclass(frozen=True, repr=False)
class ContentDownloadPlan:
    status: str
    reason_code: str
    requirements: tuple[DownloadRequirement, ...] = ()
    may_download: bool = field(default=False, init=False)
    may_restore: bool = field(default=False, init=False)
    may_report_sync_success: bool = field(default=False, init=False)
    may_archive: bool = field(default=False, init=False)


def _valid_download_plan_limits(maximum_downloads, maximum_total_download_bytes):
    return all(value is None or (type(value) is int and value > 0)
               for value in (maximum_downloads, maximum_total_download_bytes))


def plan_content_downloads(sources, listing, *, source_trusted, expected_folder_id,
                           maximum_downloads=None, maximum_total_download_bytes=None):
    """Describe missing hash observations; never initiate or authorize download.

    Plan from explicit sources and complete listing only. Requirements are
    unique by file ID, sorted deterministically, and are not IPC requests.
    No requirement does not mean no_work, absence, sync success or retry rights.
    """
    def held(reason):
        return ContentDownloadPlan("held", reason)

    if source_trusted is not True:
        return held("comparison_source_untrusted")
    if type(sources) is not tuple:
        return held("comparison_sources_invalid")
    if not _valid_download_plan_limits(maximum_downloads, maximum_total_download_bytes):
        return held("comparison_download_limit_invalid")
    if any(not _valid_source(source) for source in sources):
        return held("comparison_source_invalid")
    try:
        by_name = _group_files(_listing_snapshot(listing, expected_folder_id))
        requested_sizes = {}
        for source in sources:
            requested_sizes.setdefault(source.filename, set()).add(source.size_bytes)

        def missing_hash_files():
            # Listing IDs are already unique. Visit each named bucket once,
            # even when many sources share its name, size or differing hashes.
            for name, sizes in requested_sizes.items():
                for item in by_name.get(name, ()):
                    if item.size_bytes is None:
                        raise _ComparisonInputError("comparison_metadata_unavailable")
                    if item.size_bytes in sizes and (item.sha256 is None or not item.sha256_trusted):
                        yield item

        count, total_bytes = 0, 0
        for item in missing_hash_files():
            count += 1
            total_bytes += item.size_bytes
        # Preserve metadata-before-count-before-bytes failure precedence and
        # build no requirement dictionary until the entire budget is known.
        if maximum_downloads is not None and count > maximum_downloads:
            return held("comparison_download_count_limit_exceeded")
        if maximum_total_download_bytes is not None and total_bytes > maximum_total_download_bytes:
            return held("comparison_download_bytes_limit_exceeded")
        if count:
            needed = {item.file_id: item.size_bytes for item in missing_hash_files()}
            return ContentDownloadPlan("requires_download_observations", "comparison_hash_observations_missing",
                                       tuple(DownloadRequirement(key, needed[key]) for key in sorted(needed)))
        return ContentDownloadPlan("comparison_inputs_available", "comparison_no_download_required")
    except _ComparisonInputError as exc:
        return held(str(exc))


def compare_planned_drive_contents(sources, before, after, plan, *, source_trusted,
                                   expected_folder_id, downloads,
                                   maximum_downloads=None, maximum_total_download_bytes=None):
    """Re-derive the plan and require its exact completed download set.

    This stricter batch API returns no partial comparison on missing/extra
    download observations. Plans and hashes still grant no execution authority.
    """
    def held(reason):
        return ContentComparisonBatch("held", reason)

    if (type(plan) is not ContentDownloadPlan or any(flag is not False for flag in
            (plan.may_download, plan.may_restore, plan.may_report_sync_success, plan.may_archive))
            or not _text(plan.status) or not _text(plan.reason_code) or type(plan.requirements) is not tuple
            or any(type(item) is not DownloadRequirement or not _text(item.file_id)
                   or not _size(item.expected_size_bytes) for item in plan.requirements)):
        return held("comparison_download_plan_invalid")
    restored = plan_content_downloads(sources, before, source_trusted=source_trusted,
        expected_folder_id=expected_folder_id, maximum_downloads=maximum_downloads,
        maximum_total_download_bytes=maximum_total_download_bytes)
    if restored.status == "held":
        return held(restored.reason_code)
    if restored != plan:
        return held("comparison_download_plan_changed")
    try:
        by_id = _unchanged_listings(before, after, expected_folder_id)
        downloaded = _index_downloads(downloads, by_id)
        expected = {item.file_id: item.expected_size_bytes for item in restored.requirements}
        if expected.keys() != downloaded.keys():
            return held("comparison_download_set_mismatch")
        if any(downloaded[key].size_bytes != size for key, size in expected.items()):
            return held("comparison_download_size_mismatch")
        by_name = _group_files(by_id)
        return ContentComparisonBatch("compared", "comparison_planned_observations_consistent",
            _compare_sources(sources, by_name, downloaded))
    except _ComparisonInputError as exc:
        return held(str(exc))
