"""Integration test — pipeline write + search API retrieval.

Verifies that items written through the ORM pipeline can be found
via GET /items/search, including dedup collapse behavior.
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
from harvester.db.models import (
    ContentItem,
    DedupGroup,
    ItemVersion,
    Source,
)


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for integration tests."""
    db_name = f"harvester_search_int_{uuid.uuid4().hex[:8]}"
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


def _make_source(session: Session, name: str) -> Source:
    src = Source(name=name, kind="rss", status="watched")
    session.add(src)
    session.flush()
    return src


def _make_item(
    session: Session,
    source_id: uuid.UUID,
    title: str,
    *,
    canonical_url: str | None = None,
    topic_watch_id: uuid.UUID | None = None,
) -> ContentItem:
    ci = ContentItem(
        item_type="article",
        title=title,
        source_id=source_id,
        topic_watch_id=topic_watch_id,
        canonical_url=canonical_url,
        status="active",
    )
    session.add(ci)
    session.flush()
    return ci


def _make_version(
    session: Session,
    content_item_id: uuid.UUID,
) -> ItemVersion:
    iv = ItemVersion(
        content_item_id=content_item_id,
        content_hash=uuid.uuid4().hex,
    )
    session.add(iv)
    session.flush()
    return iv


@pytest.mark.asyncio
async def test_pipeline_items_searchable_via_api(api_client, api_test_db):
    """Items written via ORM pipeline should be searchable through the API."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src = _make_source(session, "int-src-1")
        ci = _make_item(session, src.id, "Python Concurrency Deep Dive")
        _make_version(session, ci.id)
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=Python",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Python Concurrency Deep Dive"


@pytest.mark.asyncio
async def test_dedup_collapse_returns_canonical_only(api_client, api_test_db):
    """Dedup group members should be collapsed to the canonical version."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src = _make_source(session, "int-dedup-src")
        ci_a = _make_item(session, src.id, "Dedup Python Article Original")
        ci_b = _make_item(session, src.id, "Dedup Python Article Duplicate")
        v_a = _make_version(session, ci_a.id)
        v_b = _make_version(session, ci_b.id)

        dg = DedupGroup(canonical_item_version_id=v_a.id)
        session.add(dg)
        session.flush()
        v_a.dedup_group_id = dg.id
        v_b.dedup_group_id = dg.id
        session.commit()

        v_a_id = str(v_a.id)
        v_b_id = str(v_b.id)
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=Dedup",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    version_ids = {item["version_id"] for item in data["items"]}
    assert v_a_id in version_ids
    assert v_b_id not in version_ids
