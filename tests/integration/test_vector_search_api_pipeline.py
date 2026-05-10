"""Integration test: embed_chunks job → worker → vector search API.

End-to-end verification that chunks embedded by the worker are
searchable through the public vector search API.
"""

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from harvester.adapters.stub_model import StubModelAdapter
from harvester.workers.daemon import run_once
from tests.utils.factories import (
    insert_chunk,
    insert_content_item,
    insert_item_version,
    insert_source,
)


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for integration tests."""
    db_name = f"harvester_vec_int_{uuid.uuid4().hex[:8]}"
    admin_url = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres"
    test_url = admin_url.rsplit("/", 1)[0] + "/" + db_name

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    env_backup = os.environ.pop("HARVESTER_DATABASE_URL", None)
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(cfg, "head")
    if env_backup:
        os.environ["HARVESTER_DATABASE_URL"] = env_backup

    yield test_url

    admin_engine2 = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine2.connect() as conn:
        conn.execute(
            text(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{db_name}'"
            )
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    admin_engine2.dispose()


@pytest.fixture()
async def api_client(api_test_db):
    """Create an async API test client with database configured."""
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "test-secret",
            "HARVESTER_DATABASE_URL": api_test_db,
        },
    ):
        from harvester.api.app import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


def _create_embed_job(
    session: Session, chunk_id: uuid.UUID, item_version_id: uuid.UUID
):
    from harvester.db.models import Job

    job = Job(
        job_type="embed_chunks",
        status="pending",
        payload={
            "chunk_id": str(chunk_id),
            "item_version_id": str(item_version_id),
        },
    )
    session.add(job)
    session.flush()
    return job


def _now() -> datetime:
    return datetime.now(UTC)


@pytest.mark.asyncio
async def test_vector_api_finds_embedded_chunk(api_client, api_test_db):
    """After worker embeds a chunk, GET /items/search?mode=vector finds it."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "vec-int-src")
        ci_id = insert_content_item(session, src_id, "Vector Integration Article")
        iv_id = insert_item_version(session, ci_id)
        chunk_id = insert_chunk(session, iv_id, 0, "vector integration test content")
        _create_embed_job(session, chunk_id, iv_id)
        session.commit()

        adapter = StubModelAdapter()
        stats = run_once(session, adapter, "stub-embedding-1536", limit=10)
        assert stats["completed"] >= 1

        session.expire_all()
        from harvester.db.models import Chunk

        chunk = session.get(Chunk, chunk_id)
        assert chunk.embedding_status == "ready"
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=vector%20integration&mode=vector",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert item["mode"] == "vector"
    assert item["title"] == "Vector Integration Article"


@pytest.mark.asyncio
async def test_vector_api_dedup_collapse(api_client, api_test_db):
    """Vector API collapses results from the same dedup group to canonical version."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "vec-dedup-src")
        ci_a_id = insert_content_item(session, src_id, "Dedup Canonical Article")
        ci_b_id = insert_content_item(session, src_id, "Dedup Duplicate Article")
        iv_a_id = insert_item_version(session, ci_a_id)
        iv_b_id = insert_item_version(session, ci_b_id)
        chunk_a_id = insert_chunk(session, iv_a_id, 0, "canonical chunk text")
        chunk_b_id = insert_chunk(session, iv_b_id, 0, "duplicate chunk text")
        _create_embed_job(session, chunk_a_id, iv_a_id)
        _create_embed_job(session, chunk_b_id, iv_b_id)
        session.commit()

        adapter = StubModelAdapter()
        run_once(session, adapter, "stub-embedding-1536", limit=10)

        # Create dedup group with iv_a as canonical
        dg_id = uuid.uuid4()
        session.execute(
            sa.text(
                "INSERT INTO dedup_groups (id, canonical_item_version_id, created_at, updated_at) "
                "VALUES (:id, :canonical_id, :ts, :ts)"
            ),
            {"id": dg_id, "canonical_id": iv_a_id, "ts": _now()},
        )
        session.execute(
            sa.text(
                "UPDATE item_versions SET dedup_group_id = :dg_id WHERE id = :iv_id"
            ),
            {"dg_id": dg_id, "iv_id": iv_a_id},
        )
        session.execute(
            sa.text(
                "UPDATE item_versions SET dedup_group_id = :dg_id WHERE id = :iv_id"
            ),
            {"dg_id": dg_id, "iv_id": iv_b_id},
        )
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=chunk&mode=vector",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    version_ids = {item["item_version_id"] for item in data["items"]}
    assert str(iv_a_id) in version_ids
    assert str(iv_b_id) not in version_ids
