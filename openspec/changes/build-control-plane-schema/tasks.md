## 1. Alembic and Database Setup

- [ ] 1.1 Create `tests/db/test_settings.py` first; assert database settings read `HARVESTER_DATABASE_URL` and fail clearly when missing.
- [ ] 1.2 Add `harvester/db/settings.py` for database URL loading from `HARVESTER_DATABASE_URL` until settings tests pass.
- [ ] 1.3 Create `tests/db/test_migrations.py` first; assert Alembic can upgrade an isolated Postgres test database to head.
- [ ] 1.4 Add Alembic configuration under `alembic/` and `alembic.ini`.
- [ ] 1.5 Add `harvester/db/base.py` with SQLAlchemy metadata and declarative base.
- [ ] 1.6 Add a migration test database fixture that can run migrations against an isolated Postgres database.

## 2. Core Tables

- [ ] 2.1 Create `tests/db/test_core_schema.py` first; assert required columns and foreign keys exist for `sources`, `topic_watches`, `topic_sources`, `recipes`, `crawl_runs`, `raw_objects`.
- [ ] 2.2 Define `sources` with status, kind, trust level, auth requirement, default recipe, timestamps and failure counters.
- [ ] 2.3 Define `topic_watches` and `topic_sources` with TTL, status, source relationship and timestamps.
- [ ] 2.4 Define `recipes` with executor, config JSON, risk level, approval status, version and auth profile placeholder.
- [ ] 2.5 Define `crawl_runs` with source/topic/recipe references, status, fetch fingerprint, HTTP metadata, raw object reference and error fields.
- [ ] 2.6 Define `raw_objects` with metadata, hash, storage URI, retention fields and no embedded payload column.
- [ ] 2.7 Run `pytest tests/db/test_core_schema.py -q` and confirm it passes.

## 3. Content and Dedup Tables

- [ ] 3.1 Create `tests/db/test_content_schema.py` first; assert required columns and uniqueness constraints exist for content, observations, versions, dedup groups and chunks.
- [ ] 3.2 Define `content_items` with item type, external ID, original/final/canonical URL fields, source/topic links and status.
- [ ] 3.3 Define `item_observations` with content item, raw object, extraction run, position, observed URL, payload hash and snippet.
- [ ] 3.4 Define `item_versions` with content hash, simhash, normalized text, language, raw object link and dedup group link.
- [ ] 3.5 Define `dedup_groups` for grouping equivalent item versions.
- [ ] 3.6 Define `chunks` with item version, chunk index, text, token count, embedding model, embedding status and pgvector column.
- [ ] 3.7 Run `pytest tests/db/test_content_schema.py -q` and confirm it passes.

## 4. Queue, Frontier and Audit Tables

- [ ] 4.1 Create `tests/db/test_jobs_frontier_audit_schema.py` first; assert required columns and indexes exist for `jobs`, `source_frontiers`, `audit_events`.
- [ ] 4.2 Define `jobs` with status, type, priority, run_after, locked_by, locked_until, attempts, max_attempts, idempotency_key, payload JSON and last_error.
- [ ] 4.3 Define `source_frontiers` with source ID, cursor, frontier JSON, rewind window, last complete range and updated timestamp.
- [ ] 4.4 Define `audit_events` with actor, action, entity type, entity ID, before/after JSON, reason and timestamp.
- [ ] 4.5 Add indexes for status queries, job claim queries, source/topic filters, latest item versions and audit lookups.
- [ ] 4.6 Run `pytest tests/db/test_jobs_frontier_audit_schema.py -q` and confirm it passes.

## 5. Migration and Constraint Tests

- [ ] 5.1 Write migration test that upgrades an empty database successfully.
- [ ] 5.2 Write constraint test for `jobs.idempotency_key` uniqueness.
- [ ] 5.3 Write constraint test for `content_items(source_id, external_item_id)` when external ID exists.
- [ ] 5.4 Write constraint test for `item_versions(content_item_id, content_hash)` uniqueness.
- [ ] 5.5 Write schema test that `raw_objects` has retention metadata but no required payload blob column.
- [ ] 5.6 Run `pytest tests/db -q` and confirm all schema, migration and constraint tests pass.
- [ ] 5.7 Commit with message `feat: add harvester control plane schema`.
