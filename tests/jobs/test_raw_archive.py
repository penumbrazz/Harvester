"""Tests for raw payload archive storage.

Covers: payload writing, content hash, byte size, storage URI,
retention metadata, and oversized payload rejection.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from harvester.jobs.archive import (
    ArchiveConfig,
    ArchiveOversizedError,
    ArchiveWriter,
)


@pytest.fixture
def archive_dir(tmp_path: Path) -> Path:
    """Create a temporary archive directory."""
    d = tmp_path / "archive"
    d.mkdir()
    return d


@pytest.fixture
def writer(archive_dir: Path) -> ArchiveWriter:
    """Create an ArchiveWriter with a temp directory."""
    config = ArchiveConfig(
        archive_path=str(archive_dir),
        max_payload_bytes=1024 * 1024,  # 1 MB
        default_retention_days=7,
    )
    return ArchiveWriter(config)


class TestArchiveWritePayload:
    """Writing raw payloads to archive storage."""

    def test_writes_payload_to_file(self, writer: ArchiveWriter, archive_dir: Path):
        payload = b"<html><body>Hello</body></html>"
        result = writer.write(
            payload=payload,
            source_id=uuid.uuid4(),
            crawl_run_id=uuid.uuid4(),
            content_type="text/html",
        )

        # File should exist
        assert (archive_dir / result.relative_path).is_file()
        # Content should match
        written = (archive_dir / result.relative_path).read_bytes()
        assert written == payload

    def test_content_hash_is_sha256(self, writer: ArchiveWriter):
        payload = b"test content"
        result = writer.write(
            payload=payload,
            source_id=uuid.uuid4(),
            crawl_run_id=uuid.uuid4(),
            content_type="text/html",
        )
        expected_hash = "sha256:" + hashlib.sha256(payload).hexdigest()
        assert result.content_hash == expected_hash

    def test_byte_size_matches_payload(self, writer: ArchiveWriter):
        payload = b"x" * 1234
        result = writer.write(
            payload=payload,
            source_id=uuid.uuid4(),
            crawl_run_id=uuid.uuid4(),
            content_type="text/html",
        )
        assert result.byte_size == 1234

    def test_storage_uri_is_file_uri(self, writer: ArchiveWriter, archive_dir: Path):
        payload = b"test"
        result = writer.write(
            payload=payload,
            source_id=uuid.uuid4(),
            crawl_run_id=uuid.uuid4(),
            content_type="text/html",
        )
        assert result.storage_uri.startswith("file://")
        assert result.relative_path in result.storage_uri

    def test_retention_metadata(self, writer: ArchiveWriter):
        payload = b"test"
        result = writer.write(
            payload=payload,
            source_id=uuid.uuid4(),
            crawl_run_id=uuid.uuid4(),
            content_type="text/html",
        )
        assert result.retention_days == 7
        assert result.retain_until is not None
        assert result.retain_until > datetime.now(UTC)

    def test_organizes_by_date_source(self, writer: ArchiveWriter, archive_dir: Path):
        """Archive files should be organized by date and source."""
        source_id = uuid.uuid4()
        payload = b"test"
        result = writer.write(
            payload=payload,
            source_id=source_id,
            crawl_run_id=uuid.uuid4(),
            content_type="text/html",
        )
        # Path should contain date and source ID components
        parts = Path(result.relative_path).parts
        assert len(parts) >= 2

    def test_pdf_keeps_original_filename_and_extension(
        self, writer: ArchiveWriter, archive_dir: Path
    ):
        """PDF assets should be readable on disk and keep the source filename."""
        source_id = uuid.uuid4()
        result = writer.write(
            payload=b"%PDF-1.7 test",
            source_id=source_id,
            crawl_run_id=uuid.uuid4(),
            content_type="application/pdf",
            original_url="https://example.org/files/WST%20875-2026.pdf",
        )

        relative_path = Path(result.relative_path)
        assert relative_path.parts[0:2] == ("assets", "pdf")
        assert relative_path.name == "WST 875-2026.pdf"
        assert relative_path.suffix == ".pdf"
        assert (archive_dir / relative_path).read_bytes() == b"%PDF-1.7 test"

    def test_category_override_adds_subdirectory(
        self, writer: ArchiveWriter, archive_dir: Path
    ):
        """Category override should add a subdirectory under the type directory."""
        source_id = uuid.uuid4()
        result = writer.write(
            payload=b"%PDF-1.7 test",
            source_id=source_id,
            crawl_run_id=uuid.uuid4(),
            content_type="application/pdf",
            original_url="https://example.org/files/report.pdf",
            category_override="职业健康",
        )

        relative_path = Path(result.relative_path)
        # path: assets/pdf/职业健康/DATE/SOURCE/report.pdf
        assert relative_path.parts[0:2] == ("assets", "pdf")
        assert relative_path.parts[2] == "职业健康"
        assert relative_path.name == "report.pdf"
        assert (archive_dir / relative_path).read_bytes() == b"%PDF-1.7 test"

    def test_category_override_sanitized(
        self, writer: ArchiveWriter, archive_dir: Path
    ):
        """Category with special characters should be sanitized."""
        source_id = uuid.uuid4()
        result = writer.write(
            payload=b"test",
            source_id=source_id,
            crawl_run_id=uuid.uuid4(),
            content_type="application/pdf",
            category_override="test/category:name",
        )

        relative_path = Path(result.relative_path)
        assert relative_path.parts[2] == "test_category_name"

    def test_no_category_override_uses_default_path(
        self, writer: ArchiveWriter, archive_dir: Path
    ):
        """Without category override, path should be the default structure."""
        source_id = uuid.uuid4()
        result = writer.write(
            payload=b"%PDF-1.7 test",
            source_id=source_id,
            crawl_run_id=uuid.uuid4(),
            content_type="application/pdf",
            original_url="https://example.org/files/test.pdf",
        )

        relative_path = Path(result.relative_path)
        assert relative_path.parts[0:2] == ("assets", "pdf")
        # Third part should be date, not a category name
        import re

        assert re.match(r"\d{4}-\d{2}-\d{2}", relative_path.parts[2])

    def test_filename_conflict_adds_short_suffix(
        self, writer: ArchiveWriter, archive_dir: Path
    ):
        """Conflicting asset names should keep the readable stem."""
        source_id = uuid.uuid4()
        original_url = "https://example.org/files/report.pdf"

        first = writer.write(
            payload=b"first",
            source_id=source_id,
            crawl_run_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            content_type="application/pdf",
            original_url=original_url,
        )
        second = writer.write(
            payload=b"second",
            source_id=source_id,
            crawl_run_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            content_type="application/pdf",
            original_url=original_url,
        )

        first_path = Path(first.relative_path)
        second_path = Path(second.relative_path)
        assert first_path.name == "report.pdf"
        assert second_path.name == "report-00000000.pdf"
        assert (archive_dir / first_path).read_bytes() == b"first"
        assert (archive_dir / second_path).read_bytes() == b"second"


class TestArchiveOversizedRejection:
    """Oversized payloads MUST be rejected."""

    def test_rejects_oversized_payload(self, tmp_path: Path):
        config = ArchiveConfig(
            archive_path=str(tmp_path / "archive"),
            max_payload_bytes=100,  # 100 bytes limit
            default_retention_days=7,
        )
        writer = ArchiveWriter(config)

        with pytest.raises(ArchiveOversizedError) as exc_info:
            writer.write(
                payload=b"x" * 200,
                source_id=uuid.uuid4(),
                crawl_run_id=uuid.uuid4(),
                content_type="text/html",
            )
        assert (
            "oversized" in str(exc_info.value).lower()
            or "exceeds" in str(exc_info.value).lower()
        )

    def test_accepts_exact_max_size(self, tmp_path: Path):
        config = ArchiveConfig(
            archive_path=str(tmp_path / "archive"),
            max_payload_bytes=100,
            default_retention_days=7,
        )
        writer = ArchiveWriter(config)

        result = writer.write(
            payload=b"x" * 100,
            source_id=uuid.uuid4(),
            crawl_run_id=uuid.uuid4(),
            content_type="text/html",
        )
        assert result.byte_size == 100


class TestArchiveConfig:
    """Archive configuration tests."""

    def test_config_from_env_defaults(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("HARVESTER_ARCHIVE_PATH", raising=False)
            config = ArchiveConfig.from_env()
            assert config.archive_path == ".harvester/archive"
            assert config.max_payload_bytes == 10 * 1024 * 1024
            assert config.default_retention_days == 7

    def test_config_from_env_custom(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("HARVESTER_ARCHIVE_PATH", "/data/archive")
            mp.setenv("HARVESTER_MAX_PAYLOAD_BYTES", "5242880")
            mp.setenv("HARVESTER_RAW_RETENTION_DAYS", "14")
            config = ArchiveConfig.from_env()
            assert config.archive_path == "/data/archive"
            assert config.max_payload_bytes == 5242880
            assert config.default_retention_days == 14


class TestArchivePayloadNotInPostgres:
    """Verify raw payload does NOT enter Postgres — only metadata."""

    def test_write_returns_no_inline_payload(self, writer: ArchiveWriter):
        payload = b"<html>content</html>"
        result = writer.write(
            payload=payload,
            source_id=uuid.uuid4(),
            crawl_run_id=uuid.uuid4(),
            content_type="text/html",
        )
        # The result only contains metadata, not the raw payload
        assert not hasattr(result, "payload") or result.payload is None
        assert result.content_hash is not None
        assert result.storage_uri is not None
        assert result.byte_size == len(payload)
