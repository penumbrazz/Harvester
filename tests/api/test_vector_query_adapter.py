"""Tests for vector search using configured embedding adapter.

Verifies that the search API uses the adapter factory instead of hardcoded
StubModelAdapter, and handles adapter errors gracefully.
"""

import os
import uuid
from unittest.mock import patch

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from tests.utils.factories import (
    insert_chunk,
    insert_content_item,
    insert_item_version,
    insert_source,
)


@pytest.fixture(scope="module")
def vec_adapter_test_db():
    """Create an isolated test database for vector adapter tests."""
    db_name = f"harvester_vec_adptr_{uuid.uuid4().hex[:8]}"
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
async def vec_api_client(vec_adapter_test_db):
    """Create an async API test client."""
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "test-secret",
            "HARVESTER_DATABASE_URL": vec_adapter_test_db,
        },
    ):
        from harvester.api.app import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


def _seed_vector_data(test_db, unique_suffix, query_text="Python"):
    """Seed a chunk with a StubModelAdapter embedding for the given query."""
    engine = create_engine(test_db)
    from harvester.adapters.stub_model import StubModelAdapter

    with Session(bind=engine) as session:
        src_id = insert_source(session, f"va-src-{unique_suffix}")
        ci_id = insert_content_item(
            session, src_id, f"Python Adapter Guide {unique_suffix}"
        )
        iv_id = insert_item_version(session, ci_id)
        adapter = StubModelAdapter()
        emb = adapter.embed(query_text)
        insert_chunk(
            session,
            iv_id,
            0,
            f"adapter test chunk {unique_suffix}",
            embedding=emb,
            embedding_status="ready",
        )
        session.commit()
    engine.dispose()


@pytest.mark.asyncio
async def test_vector_search_uses_adapter_factory(vec_api_client, vec_adapter_test_db):
    """Vector search uses adapter factory (defaults to StubModelAdapter)."""
    uid = uuid.uuid4().hex[:8]
    _seed_vector_data(vec_adapter_test_db, uid, "Python")

    response = await vec_api_client.get(
        "/items/search?q=Python&mode=vector",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_vector_search_adapter_error_returns_503(
    vec_api_client, vec_adapter_test_db
):
    """When the adapter factory raises an error, API returns 503 not empty results."""
    uid = uuid.uuid4().hex[:8]
    _seed_vector_data(vec_adapter_test_db, uid, "Python")

    with patch(
        "harvester.adapters.embedding_settings.create_embedding_adapter",
        side_effect=Exception("Adapter service unavailable"),
    ):
        response = await vec_api_client.get(
            "/items/search?q=Python&mode=vector",
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_keyword_search_unaffected_by_adapter_errors(
    vec_api_client, vec_adapter_test_db
):
    """Keyword search should work even when adapter factory raises."""
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(vec_adapter_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, f"kw-unaf-src-{uid}")
        ci_id = insert_content_item(session, src_id, f"Keyword Unaffected Test {uid}")
        insert_item_version(session, ci_id)
        session.commit()
    engine.dispose()

    with patch(
        "harvester.adapters.embedding_settings.create_embedding_adapter",
        side_effect=Exception("Should not be called"),
    ):
        response = await vec_api_client.get(
            f"/items/search?q={uid}&mode=keyword",
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 200
