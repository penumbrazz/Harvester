## Context

This change depends on `bootstrap-python-agent-docs`. It implements the schema contract accepted in the engineering review. It does not implement API handlers or job execution; it creates tables, constraints, migrations and tests.

## Goals / Non-Goals

**Goals:**
- Add SQLAlchemy model/table definitions for the MVP.
- Add Alembic migration that creates the schema from an empty Postgres database.
- Include pgvector extension setup and vector column for chunks.
- Add tests for migration, constraints and key schema invariants.

**Non-Goals:**
- No FastAPI endpoint behavior.
- No worker implementation.
- No real extraction or search ranking.
- No full fetch policy.

## Decisions

1. **Use SQLAlchemy 2.x models or tables with Alembic.** Keep model definitions close to database constraints and avoid ad hoc SQL in application code.
2. **Use enums or constrained strings for statuses.** Status values must match the reviewed state machine vocabulary and be validated in domain services later.
3. **Keep raw payload out of Postgres.** `raw_objects` stores metadata, hashes, retention fields and object URI. Payload lives in object storage or local archive.
4. **Add source frontier table.** Keep `source_frontiers` separate from `sources` so high-frequency state can evolve without bloating the source record.
5. **Use unique constraints for idempotency.** Jobs, item versions, observations and external IDs need database-level uniqueness, not just Python checks.

## Risks / Trade-offs

- **[Risk] Schema is broad for one slice** → Mitigation: this slice is schema-only and includes tests before API work.
- **[Risk] pgvector unavailable in local Postgres** → Mitigation: migration test documents required extension and fails clearly.
- **[Risk] URL canonicalization rules drift from schema** → Mitigation: schema stores all URL forms; normalization logic lands in later pipeline/API changes.
