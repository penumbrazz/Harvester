## Why

Harvester’s value depends on a reliable crawl-to-item pipeline. The engineering review identified queue lease/idempotency, source frontier rewind, transaction boundaries and dedup behavior as MVP requirements, not later optimizations.

## What Changes

- Implement Postgres-backed job claim, lease, retry, dead state and idempotency.
- Implement per-source and per-job-type concurrency controls.
- Implement source frontier/rewind behavior for high-frequency feeds.
- Implement raw object metadata creation, extraction pipeline transaction boundaries and dedup/versioning rules.
- Implement raw payload retention metadata and short-retention cleanup hook.

## Capabilities

### New Capabilities
- `job-pipeline-dedup`: Job runner, source frontier management, crawl/extract pipeline consistency, item observation/versioning and dedup behavior.

### Modified Capabilities

## Impact

- Adds worker process, repository methods and pipeline domain services.
- Depends on control-plane schema.
- Produces data consumed by search and deployment tests.
