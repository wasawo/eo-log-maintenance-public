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
        if (type(item) is not DriveFileObservation or not _text(item.file_id)
                or not _text(item.filename) or (item.size_bytes is not None and not _size(item.size_bytes))
                or (item.sha256 is not None and not _hash(item.sha256))
                or type(item.sha256_trusted) is not bool):
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
