"""Pure OSD-01 comparison observations; no API, provenance proof or authority."""
from dataclasses import dataclass, field
import hashlib
import re


@dataclass(frozen=True, repr=False)
class ComparisonSource:
    filename: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, repr=False)
class DriveFileObservation:
    file_id: str
    filename: str
    size_bytes: int | None
    sha256: str | None
    sha256_trusted: bool = False


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


def collect_drive_listing(pages, *, expected_folder_id):
    """Validate supplied page continuity; no API calls or trust qualification.

    Return no observation on partial/failed/ambiguous pages. Exhaustion alone
    is not completion: exactly one terminal page is required, with no trailer.
    Caller owns transport, timeouts, resource cleanup and authentic page binding.
    """
    if not _text(expected_folder_id):
        raise DriveListingObservationError("listing_folder_invalid")
    try:
        iterator = iter(pages)
    except Exception:
        raise DriveListingObservationError("listing_read_failed") from None
    expected_token = None
    seen_tokens = set()
    file_ids = set()
    files = []
    terminal = False
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
        for item in page.files:
            if not _valid_drive_file(item):
                raise DriveListingObservationError("listing_file_invalid")
            if item.file_id in file_ids:
                raise DriveListingObservationError("listing_identity_ambiguous")
            file_ids.add(item.file_id)
            files.append(item)
        expected_token = page.next_token
        terminal = expected_token is None
    if not terminal:
        raise DriveListingObservationError("listing_terminal_missing")
    return DriveListingObservation(expected_folder_id, tuple(files))


@dataclass(frozen=True, repr=False)
class DownloadHashObservation:
    file_id: str
    size_bytes: int
    sha256: str


class DownloadObservationError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def hash_downloaded_content(file_id, chunks, *, expected_size_bytes, download_completed):
    """Hash completed download chunks without retaining contents or owning transport.

    The caller must bind the stream and completion to the requested Drive ID.
    Neither a caller flag nor this digest authenticates that binding. Each chunk
    is nonempty exact bytes; an empty payload is represented by zero chunks.
    """
    if not _text(file_id) or not _size(expected_size_bytes):
        raise DownloadObservationError("download_context_invalid")
    if download_completed is not True:
        raise DownloadObservationError("download_completion_unconfirmed")
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


def _valid_drive_file(item):
    return (type(item) is DriveFileObservation and _text(item.file_id)
            and _text(item.filename) and (item.size_bytes is None or _size(item.size_bytes))
            and (item.sha256 is None or _hash(item.sha256))
            and type(item.sha256_trusted) is bool)


def compare_drive_content(source, files, *, source_trusted, expected_folder_id,
                          observed_folder_id, enumeration_completed, downloads=()):
    """Find exactly one name/size/SHA-256 match in supplied complete observations.

    Trust/completeness flags are caller observations, never authenticated here.
    Missing/untrusted cloud SHA requires a completed download hash observation.
    No result authorizes sync, restore, rename, overwrite, archive or deletion.
    These internal dataclasses do not define the unresolved IPC result fields.
    """
    def held(reason):
        return ContentComparison("held", reason)

    if source_trusted is not True:
        return held("comparison_source_untrusted")
    if (type(source) is not ComparisonSource or not _text(source.filename)
            or not _size(source.size_bytes) or not _hash(source.sha256)):
        return held("comparison_source_invalid")
    if (not _text(expected_folder_id) or not _text(observed_folder_id)
            or expected_folder_id != observed_folder_id):
        return held("comparison_folder_unconfirmed")
    if enumeration_completed is not True:
        return held("comparison_listing_incomplete")
    if type(files) is not tuple or type(downloads) is not tuple:
        return held("comparison_observations_invalid")
    by_id = {}
    for item in files:
        if not _valid_drive_file(item):
            return held("comparison_observations_invalid")
        if item.file_id in by_id:
            return held("comparison_identity_ambiguous")
        by_id[item.file_id] = item
    downloaded = {}
    for item in downloads:
        if (type(item) is not DownloadHashObservation or not _text(item.file_id)
                or not _size(item.size_bytes) or not _hash(item.sha256)):
            return held("comparison_download_invalid")
        if item.file_id in downloaded or item.file_id not in by_id:
            return held("comparison_download_unbound")
        downloaded[item.file_id] = item
    matches = []
    for item in files:
        if item.filename != source.filename:
            continue
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
            matches.append(item.file_id)
    if len(matches) != 1:
        return held("comparison_no_match" if not matches else "comparison_multiple_matches")
    return ContentComparison("comparison_candidate", "comparison_unique_content_match", matches[0])


def compare_reobserved_drive_content(source, before, after, *, source_trusted,
                                     expected_folder_id, downloads=()):
    """Compare only unchanged complete listing observations around a download.

    File order is immaterial; every observed file ID and metadata must agree.
    This performs no re-query and does not authenticate freshness or prevent ABA.
    Reused/saved observations and matching results are never execution receipts.
    """
    def held(reason):
        return ContentComparison("held", reason)

    if source_trusted is not True:
        return held("comparison_source_untrusted")
    if not _text(expected_folder_id):
        return held("comparison_folder_unconfirmed")
    snapshots = []
    for listing in (before, after):
        if (type(listing) is not DriveListingObservation or type(listing.files) is not tuple
                or any(flag is not False for flag in (listing.may_restore,
                    listing.may_report_sync_success, listing.may_archive))):
            return held("comparison_listing_invalid")
        if listing.enumeration_completed is not True:
            return held("comparison_listing_incomplete")
        if not _text(listing.folder_id) or listing.folder_id != expected_folder_id:
            return held("comparison_folder_unconfirmed")
        files = {}
        for item in listing.files:
            if not _valid_drive_file(item):
                return held("comparison_observations_invalid")
            if item.file_id in files:
                return held("comparison_identity_ambiguous")
            files[item.file_id] = item
        snapshots.append(files)
    if snapshots[0] != snapshots[1]:
        return held("comparison_listing_changed")
    return compare_drive_content(source, after.files, source_trusted=source_trusted,
        expected_folder_id=expected_folder_id, observed_folder_id=after.folder_id,
        enumeration_completed=after.enumeration_completed, downloads=downloads)
