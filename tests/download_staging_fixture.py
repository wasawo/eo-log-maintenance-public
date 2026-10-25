"""TEST ONLY: download into fresh owned OS-temp attempts; never a runtime writer."""
import os
from pathlib import Path
import stat
import tempfile
from uuid import uuid4

from Common.DriveContentComparison import DownloadRequirement, hash_downloaded_content
from Common.OwnedRunLock import acquire_owned_lock


class StagingFixtureError(ValueError):
    pass


def signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink, info.st_mode


def regular(info):
    return (stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and not getattr(info, "st_file_attributes", 0) & 0x400)


def safe_chunks(chunks):
    try:
        iterator = iter(chunks)
    except Exception:
        raise StagingFixtureError("fixture_download_interrupted") from None
    while True:
        try:
            chunk = next(iterator)
        except StopIteration:
            return
        except Exception:
            raise StagingFixtureError("fixture_download_interrupted") from None
        yield chunk


class DownloadStagingFixture:
    """Accepts no caller directory, destination, credentials or API client."""
    def __init__(self):
        self.parent = Path(tempfile.gettempdir()).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(prefix="eolm-download-staging-", dir=self.parent)
        self.root = Path(self.temp.name)
        info = self.root.lstat()
        self.identity = info.st_dev, info.st_ino
        self.nonce = uuid4().hex.encode()
        (self.root/".fixture-owner").write_bytes(self.nonce)
        self.scope = "synthetic-"+uuid4().hex
        self.attempts = []

    def guard(self):
        info = self.root.lstat()
        marker = self.root/".fixture-owner"
        if (self.root.parent != self.parent or not self.root.name.startswith("eolm-download-staging-")
                or self.root.resolve(strict=True) != self.root or not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
                or (info.st_dev, info.st_ino) != self.identity or not regular(marker.lstat())
                or marker.read_bytes() != self.nonce):
            raise StagingFixtureError("fixture_root_changed")

    def download(self, requirement, chunks, *, download_completed=True, before_create=None, before_verify=None):
        if (type(requirement) is not DownloadRequirement or type(requirement.file_id) is not str
                or not requirement.file_id or "\x00" in requirement.file_id
                or type(requirement.expected_size_bytes) is not int or requirement.expected_size_bytes < 0):
            raise StagingFixtureError("fixture_requirement_invalid")
        self.guard()
        with acquire_owned_lock(self.scope, self.root/"owner.json", timeout_seconds=0):
            self.guard()
            directory = Path(tempfile.mkdtemp(prefix="attempt-", dir=self.root))
            directory_info = directory.lstat()
            path = directory/"download.bin"
            self.attempts.append(path)

            def stage_guard():
                self.guard()
                info = directory.lstat()
                if (directory.parent != self.root or not stat.S_ISDIR(info.st_mode)
                        or getattr(info, "st_file_attributes", 0) & 0x400
                        or (info.st_dev, info.st_ino) != (directory_info.st_dev, directory_info.st_ino)):
                    raise StagingFixtureError("fixture_attempt_changed")

            if before_create is not None: before_create(path)
            stage_guard()
            size = 0
            try:
                with path.open("xb") as stream:
                    for chunk in safe_chunks(chunks):
                        if type(chunk) is not bytes or not chunk:
                            raise StagingFixtureError("fixture_chunk_invalid")
                        size += len(chunk)
                        if size > requirement.expected_size_bytes:
                            raise StagingFixtureError("fixture_size_exceeded")
                        if stream.write(chunk) != len(chunk):
                            raise StagingFixtureError("fixture_short_write")
                    stream.flush()
                    os.fsync(stream.fileno())
                    written = os.fstat(stream.fileno())
            except StagingFixtureError:
                raise
            except Exception:
                raise StagingFixtureError("fixture_download_interrupted") from None
            if before_verify is not None: before_verify(path)
            stage_guard()
            before = path.lstat()
            if not regular(before) or signature(before) != signature(written):
                raise StagingFixtureError("fixture_staging_changed")
            with path.open("rb") as stream:
                if signature(os.fstat(stream.fileno())) != signature(before):
                    raise StagingFixtureError("fixture_staging_changed")
                observed = hash_downloaded_content(requirement.file_id,
                    iter(lambda: stream.read(1024*1024), b""),
                    expected_size_bytes=requirement.expected_size_bytes, download_completed=download_completed)
                if signature(os.fstat(stream.fileno())) != signature(before):
                    raise StagingFixtureError("fixture_staging_changed")
            stage_guard()
            if signature(path.lstat()) != signature(before):
                raise StagingFixtureError("fixture_staging_changed")
            return observed

    def close(self):
        # Only this fixture's marked, resolved, identity-bound temp is removed.
        self.guard()
        self.temp.cleanup()
