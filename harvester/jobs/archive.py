"""Raw payload archive storage for Harvester.

Writes crawl payloads to local filesystem archive. Postgres stores only
metadata (storage_uri, content_hash, byte_size, content_type, retention).
Raw payloads never enter the database.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import UUID


class ArchiveOversizedError(Exception):
    """Raised when a payload exceeds the configured maximum size."""


@dataclass(frozen=True)
class ArchiveConfig:
    """Configuration for archive storage."""

    archive_path: str = ".harvester/archive"
    max_payload_bytes: int = 10 * 1024 * 1024  # 10 MB
    default_retention_days: int = 7

    @classmethod
    def from_env(cls) -> ArchiveConfig:
        """Load configuration from environment variables."""
        return cls(
            archive_path=os.environ.get("HARVESTER_ARCHIVE_PATH", ".harvester/archive"),
            max_payload_bytes=int(
                os.environ.get("HARVESTER_MAX_PAYLOAD_BYTES", str(10 * 1024 * 1024))
            ),
            default_retention_days=int(
                os.environ.get("HARVESTER_RAW_RETENTION_DAYS", "7")
            ),
        )


@dataclass(frozen=True)
class ArchiveWriteResult:
    """Result of writing a payload to archive."""

    relative_path: str
    storage_uri: str
    content_hash: str
    byte_size: int
    content_type: str
    retention_days: int
    retain_until: datetime


class ArchiveWriter:
    """Writes raw crawl payloads to local filesystem archive."""

    def __init__(self, config: ArchiveConfig) -> None:
        self._config = config

    def write(
        self,
        payload: bytes,
        source_id: UUID,
        crawl_run_id: UUID,
        content_type: str,
        original_url: str | None = None,
        suggested_filename: str | None = None,
    ) -> ArchiveWriteResult:
        """Write a raw payload to archive storage.

        Raises ArchiveOversizedError if payload exceeds max_payload_bytes.
        """
        if len(payload) > self._config.max_payload_bytes:
            raise ArchiveOversizedError(
                f"Payload size {len(payload)} exceeds maximum "
                f"{self._config.max_payload_bytes} bytes"
            )

        content_hash = "sha256:" + hashlib.sha256(payload).hexdigest()
        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")
        category, extension = _archive_category(content_type)
        filename = _archive_filename(
            crawl_run_id=crawl_run_id,
            content_type=content_type,
            extension=extension,
            original_url=original_url,
            suggested_filename=suggested_filename,
        )

        relative_path = os.path.join(
            category,
            date_str,
            str(source_id),
            filename,
        )

        full_path = Path(self._config.archive_path) / relative_path
        full_path = _avoid_conflict(full_path, crawl_run_id)
        relative_path = os.path.relpath(full_path, self._config.archive_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(payload)

        abs_archive = Path(self._config.archive_path).resolve()
        storage_uri = f"file://{abs_archive / relative_path}"

        retention_days = self._config.default_retention_days
        retain_until = now + timedelta(days=retention_days)

        return ArchiveWriteResult(
            relative_path=relative_path,
            storage_uri=storage_uri,
            content_hash=content_hash,
            byte_size=len(payload),
            content_type=content_type,
            retention_days=retention_days,
            retain_until=retain_until,
        )


def _archive_category(content_type: str) -> tuple[str, str]:
    media_type = _media_type(content_type)
    if media_type == "application/pdf":
        return "assets/pdf", ".pdf"
    if media_type.startswith("image/"):
        image_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
        }.get(media_type, ".img")
        return "assets/images", image_ext
    if media_type == "text/html":
        return "pages/html", ".html"
    if media_type == "application/json":
        return "pages/json", ".json"
    if media_type.startswith("text/"):
        return "pages/text", ".txt"
    return "assets/files", _extension_for_media_type(media_type)


def _archive_filename(
    *,
    crawl_run_id: UUID,
    content_type: str,
    extension: str,
    original_url: str | None,
    suggested_filename: str | None,
) -> str:
    source_name = suggested_filename or _filename_from_url(original_url)
    if source_name:
        filename = _sanitize_filename(source_name)
    else:
        filename = (
            f"{_media_type(content_type).replace('/', '-')}-{crawl_run_id.hex[:8]}"
        )

    stem = Path(filename).stem or filename
    suffix = Path(filename).suffix.lower()
    if not suffix or suffix == ".raw":
        suffix = extension
    if suffix != extension and _media_type(content_type) == "application/pdf":
        suffix = ".pdf"

    return f"{stem}{suffix}"


def _filename_from_url(original_url: str | None) -> str | None:
    if not original_url:
        return None
    parsed = urlparse(original_url)
    name = Path(unquote(parsed.path)).name
    return name or None


def _sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f<>:\"/\\|?*]+", "_", filename)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(". ")
    if len(cleaned) > 180:
        path = Path(cleaned)
        stem = path.stem[:160].rstrip()
        cleaned = f"{stem}{path.suffix}"
    return cleaned or "payload"


def _avoid_conflict(path: Path, crawl_run_id: UUID) -> Path:
    if not path.exists():
        return path

    candidate = path.with_name(f"{path.stem}-{crawl_run_id.hex[:8]}{path.suffix}")
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = path.with_name(
            f"{path.stem}-{crawl_run_id.hex[:8]}-{index}{path.suffix}"
        )
        if not candidate.exists():
            return candidate
        index += 1


def _media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _extension_for_media_type(media_type: str) -> str:
    return {
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/zip": ".zip",
    }.get(media_type, ".bin")
