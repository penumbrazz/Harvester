"""Migration and constraint tests for the control plane schema."""

import uuid

import pytest
import sqlalchemy as sa

_NOW = "now()"


def test_jobs_idempotency_key_unique(_test_db_engine):
    """Inserting duplicate idempotency_key should raise IntegrityError."""
    key = f"test-{uuid.uuid4()}"
    with _test_db_engine.connect() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO jobs (id, job_type, status, priority, attempts, max_attempts, idempotency_key, created_at, updated_at) "
                "VALUES (:id, 'crawl', 'pending', 0, 0, 3, :key, now(), now())"
            ),
            {"id": str(uuid.uuid4()), "key": key},
        )
        conn.commit()

    with _test_db_engine.connect() as conn:
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(
                sa.text(
                    "INSERT INTO jobs (id, job_type, status, priority, attempts, max_attempts, idempotency_key, created_at, updated_at) "
                    "VALUES (:id, 'crawl', 'pending', 0, 0, 3, :key, now(), now())"
                ),
                {"id": str(uuid.uuid4()), "key": key},
            )
            conn.commit()


def test_content_items_source_external_id_unique(_test_db_engine):
    """content_items(source_id, external_item_id) should be unique when external_id exists."""
    source_id = str(uuid.uuid4())
    ext_id = "ext-123"

    with _test_db_engine.connect() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO sources (id, name, kind, status, trust_level, auth_required, failure_count, created_at, updated_at) "
                "VALUES (:id, 'test-src', 'web', 'active', 'medium', false, 0, now(), now())"
            ),
            {"id": source_id},
        )
        conn.execute(
            sa.text(
                "INSERT INTO content_items (id, item_type, status, source_id, external_item_id, created_at, updated_at) "
                "VALUES (:id, 'post', 'active', :src, :ext, now(), now())"
            ),
            {"id": str(uuid.uuid4()), "src": source_id, "ext": ext_id},
        )
        conn.commit()

    with _test_db_engine.connect() as conn:
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(
                sa.text(
                    "INSERT INTO content_items (id, item_type, status, source_id, external_item_id, created_at, updated_at) "
                    "VALUES (:id, 'post', 'active', :src, :ext, now(), now())"
                ),
                {"id": str(uuid.uuid4()), "src": source_id, "ext": ext_id},
            )
            conn.commit()


def test_item_versions_content_hash_unique(_test_db_engine):
    """item_versions(content_item_id, content_hash) should be unique."""
    source_id = str(uuid.uuid4())
    item_id = str(uuid.uuid4())
    content_hash = "sha256abc"

    with _test_db_engine.connect() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO sources (id, name, kind, status, trust_level, auth_required, failure_count, created_at, updated_at) "
                "VALUES (:id, 'test-src2', 'web', 'active', 'medium', false, 0, now(), now())"
            ),
            {"id": source_id},
        )
        conn.execute(
            sa.text(
                "INSERT INTO content_items (id, item_type, status, source_id, created_at, updated_at) "
                "VALUES (:id, 'post', 'active', :src, now(), now())"
            ),
            {"id": item_id, "src": source_id},
        )
        conn.execute(
            sa.text(
                "INSERT INTO item_versions (id, content_item_id, content_hash, created_at) "
                "VALUES (:id, :item, :hash, now())"
            ),
            {"id": str(uuid.uuid4()), "item": item_id, "hash": content_hash},
        )
        conn.commit()

    with _test_db_engine.connect() as conn:
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(
                sa.text(
                    "INSERT INTO item_versions (id, content_item_id, content_hash, created_at) "
                    "VALUES (:id, :item, :hash, now())"
                ),
                {"id": str(uuid.uuid4()), "item": item_id, "hash": content_hash},
            )
            conn.commit()


def test_raw_objects_has_retention_no_payload(_test_db_engine):
    """raw_objects should have retention metadata but no payload column."""
    with _test_db_engine.connect() as conn:
        cols = conn.execute(
            sa.text(
                "SELECT attname FROM pg_attribute "
                "WHERE attrelid = "
                "(SELECT oid FROM pg_class WHERE relname = 'raw_objects' "
                " AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')) "
                "AND attnum > 0 AND NOT attisdropped"
            )
        )
        col_names = {row[0] for row in cols}
        assert "retention_policy" in col_names
        assert "retain_until" in col_names
        assert "payload" not in col_names
        assert "body" not in col_names
