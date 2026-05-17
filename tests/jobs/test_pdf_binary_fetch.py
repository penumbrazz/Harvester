"""Tests for PDF binary fetch/archive in crawl execution.

Covers: content type, bytes hash, payload size limit, and raw payload
not entering Postgres.
"""

import hashlib
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa

from harvester.db.models import CrawlTarget, RawObject
from harvester.domain.fetch_policy import FetchPolicyResult
from harvester.jobs.archive import ArchiveWriteResult
from harvester.jobs.crawl_execution import (
    CrawlExecutionError,
    execute_crawl,
)
from harvester.jobs.crawl_targets import upsert_crawl_target


def _insert_source(db_session, *, url=None):
    source_id = uuid.uuid4()
    db_session.execute(
        sa.text(
            "INSERT INTO sources (id, name, kind, url, status, trust_level, "
            "auth_required, failure_count, created_at, updated_at) "
            "VALUES (:id, :name, :kind, :url, :status, :trust_level, "
            ":auth_required, :failure_count, :created_at, :updated_at)"
        ),
        dict(
            id=source_id,
            name=f"cdc-source-{source_id.hex[:8]}",
            kind="web",
            url=url or "https://www.chinacdc.cn/jksj/jksj04_14249/",
            status="watched",
            trust_level="medium",
            auth_required=False,
            failure_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    )
    return source_id


def _insert_recipe(db_session):
    recipe_id = uuid.uuid4()
    db_session.execute(
        sa.text(
            "INSERT INTO recipes (id, name, executor, config, risk_level, "
            "approval_status, version, created_at, updated_at) "
            "VALUES (:id, :name, :executor, :config, :risk_level, "
            ":approval_status, :version, :created_at, :updated_at)"
        ),
        dict(
            id=recipe_id,
            name=f"cdc-recipe-{recipe_id.hex[:8]}",
            executor="firecrawl",
            config='{"discovery":{"enabled":true}}',
            risk_level="low",
            approval_status="approved",
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    )
    return recipe_id


def _seed_pdf_target(db_session):
    source_id = _insert_source(db_session)
    recipe_id = _insert_recipe(db_session)
    db_session.commit()
    target, _ = upsert_crawl_target(
        db_session,
        source_id=source_id,
        recipe_id=recipe_id,
        target_url=(
            "https://www.chinacdc.cn/jksj/jksj04_14249/202605/"
            "P020260514670474006354.pdf"
        ),
        target_role="asset",
        media_type="pdf",
        depth=2,
    )
    db_session.commit()
    return source_id, recipe_id, target


def _make_archive_result(**overrides):
    defaults = dict(
        relative_path="2026-05-16/test.raw",
        storage_uri="file:///archive/2026-05-16/test.raw",
        content_hash="sha256:abc123",
        byte_size=1024,
        content_type="application/pdf",
        retention_days=7,
        retain_until=datetime.now(UTC),
    )
    defaults.update(overrides)
    return ArchiveWriteResult(**defaults)


class TestPdfBinaryFetchArchive:
    """PDF target crawl should use direct binary fetch and archive raw bytes."""

    def test_pdf_target_uses_binary_fetch_not_firecrawl(self, db_session):
        """PDF target should use fetch_binary instead of execute_adapter_crawl."""
        source_id, recipe_id, target = _seed_pdf_target(db_session)
        pdf_bytes = b"%PDF-1.4 fake content"

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ),
            patch(
                "harvester.jobs.crawl_execution.fetch_binary",
                return_value=MagicMock(
                    payload_bytes=pdf_bytes,
                    content_type="application/pdf",
                    status_code=200,
                    final_url=None,
                    error=None,
                ),
            ) as mock_binary,
            patch(
                "harvester.jobs.crawl_execution.execute_adapter_crawl",
            ) as mock_adapter,
            patch(
                "harvester.jobs.crawl_execution.write_archive",
                return_value=_make_archive_result(byte_size=len(pdf_bytes)),
            ),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                target_id=target.id,
                actor="test",
            )

        assert result.status == "completed"
        mock_binary.assert_called_once()
        mock_adapter.assert_not_called()

    def test_pdf_raw_object_has_pdf_content_type(self, db_session):
        """Raw object for PDF should have application/pdf content type."""
        source_id, recipe_id, target = _seed_pdf_target(db_session)
        pdf_bytes = b"%PDF-1.4 fake content"

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ),
            patch(
                "harvester.jobs.crawl_execution.fetch_binary",
                return_value=MagicMock(
                    payload_bytes=pdf_bytes,
                    content_type="application/pdf",
                    status_code=200,
                    final_url=None,
                    error=None,
                ),
            ),
            patch(
                "harvester.jobs.crawl_execution.write_archive",
                return_value=_make_archive_result(
                    content_hash="sha256:" + hashlib.sha256(pdf_bytes).hexdigest(),
                    byte_size=len(pdf_bytes),
                    content_type="application/pdf",
                ),
            ),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                target_id=target.id,
                actor="test",
            )

        raw = db_session.get(RawObject, result.raw_object_id)
        assert raw.content_type == "application/pdf"

    def test_pdf_bytes_hash_matches_archive(self, db_session):
        """Content hash should match SHA-256 of the raw PDF bytes."""
        source_id, recipe_id, target = _seed_pdf_target(db_session)
        pdf_bytes = b"%PDF-1.4 test hash content"
        expected_hash = "sha256:" + hashlib.sha256(pdf_bytes).hexdigest()

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ),
            patch(
                "harvester.jobs.crawl_execution.fetch_binary",
                return_value=MagicMock(
                    payload_bytes=pdf_bytes,
                    content_type="application/pdf",
                    status_code=200,
                    final_url=None,
                    error=None,
                ),
            ),
            patch(
                "harvester.jobs.crawl_execution.write_archive",
                return_value=_make_archive_result(
                    content_hash=expected_hash,
                    byte_size=len(pdf_bytes),
                ),
            ),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                target_id=target.id,
                actor="test",
            )

        raw = db_session.get(RawObject, result.raw_object_id)
        assert raw.content_hash == expected_hash

    def test_oversized_pdf_is_rejected(self, db_session):
        """PDF exceeding payload limit should fail without saving raw object."""
        source_id, recipe_id, target = _seed_pdf_target(db_session)
        oversized_bytes = b"x" * (11 * 1024 * 1024)  # 11 MB > default 10 MB

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ),
            patch(
                "harvester.jobs.crawl_execution.fetch_binary",
                return_value=MagicMock(
                    payload_bytes=oversized_bytes,
                    content_type="application/pdf",
                    status_code=200,
                    final_url=None,
                    error=None,
                ),
            ),
            patch(
                "harvester.jobs.crawl_execution.write_archive",
                side_effect=Exception("Should not be called for oversized payload"),
            ),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                target_id=target.id,
                actor="test",
            )

        assert result.status == "failed"
        assert result.raw_object_id is None
        updated = db_session.get(CrawlTarget, target.id)
        assert updated.status == "failed"
        assert "exceeds" in updated.last_error.lower()

    def test_raw_payload_not_in_postgres(self, db_session):
        """PDF bytes should be in archive only, never in the raw_object row."""
        source_id, recipe_id, target = _seed_pdf_target(db_session)
        pdf_bytes = b"%PDF-1.4 sensitive data"

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ),
            patch(
                "harvester.jobs.crawl_execution.fetch_binary",
                return_value=MagicMock(
                    payload_bytes=pdf_bytes,
                    content_type="application/pdf",
                    status_code=200,
                    final_url=None,
                    error=None,
                ),
            ),
            patch(
                "harvester.jobs.crawl_execution.write_archive",
                return_value=_make_archive_result(byte_size=len(pdf_bytes)),
            ),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                target_id=target.id,
                actor="test",
            )

        raw = db_session.get(RawObject, result.raw_object_id)
        assert raw.storage_uri is not None
        assert raw.byte_size == len(pdf_bytes)
        # raw_object has no column for inline payload
        assert not hasattr(raw, "payload") or raw.payload is None

    def test_binary_fetch_error_fails_target(self, db_session):
        """Binary fetch error should mark target as failed."""
        source_id, recipe_id, target = _seed_pdf_target(db_session)

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ),
            patch(
                "harvester.jobs.crawl_execution.fetch_binary",
                return_value=MagicMock(
                    payload_bytes=None,
                    content_type=None,
                    status_code=None,
                    final_url=None,
                    error="Connection refused",
                ),
            ),
        ):
            with pytest.raises(CrawlExecutionError) as exc_info:
                execute_crawl(
                    session=db_session,
                    source_id=source_id,
                    recipe_id=recipe_id,
                    target_id=target.id,
                    actor="test",
                )

        assert exc_info.value.retryable is True
        updated = db_session.get(CrawlTarget, target.id)
        assert updated.status == "failed"
        assert updated.failure_count == 1
