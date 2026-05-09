## Why

Harvester needs a durable control-plane schema before API, jobs or search can be built. The design review locked the core entities, raw/content separation, source frontiers, retention policy, URL canonicalization and audit requirements.

## What Changes

- Add SQLAlchemy models and Alembic migration for the MVP control-plane tables.
- Include topic watches as first-class entities.
- Include `source_frontiers`, job lease/idempotency fields, audit events and URL canonicalization fields.
- Define database constraints for item identity, observations, versions, chunks and jobs.

## Capabilities

### New Capabilities
- `control-plane-schema`: Database schema for sources, topics, recipes, crawl runs, raw evidence, content items, observations, versions, chunks, dedup groups, source frontiers, jobs and audit events.

### Modified Capabilities

## Impact

- Adds Alembic migration setup and SQLAlchemy table definitions.
- Establishes schema contract for all later API, queue, extraction and search work.
- Requires Postgres with pgvector extension in local/test environments.
