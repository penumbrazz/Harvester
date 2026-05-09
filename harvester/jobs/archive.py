"""Raw payload archive storage for Harvester.

Writes crawl payloads to local filesystem archive. Postgres stores only
metadata (storage_uri, content_hash, byte_size, content_type, retention).
Raw payloads never enter the database.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        filename = f"{crawl_run_id.hex}.raw"

        relative_path = os.path.join(
            date_str,
            str(source_id),
            filename,
        )

        full_path = Path(self._config.archive_path) / relative_path
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
