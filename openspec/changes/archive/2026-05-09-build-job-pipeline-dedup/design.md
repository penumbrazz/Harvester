## Context

This change depends on `build-control-plane-schema` and can run in parallel with API work after schema lands. It is the core data pipeline: jobs, frontiers, raw metadata, extraction, observations, versions and dedup.

## Goals / Non-Goals

**Goals:**
- Implement job runner mechanics with `FOR UPDATE SKIP LOCKED`.
- Implement concurrency fairness: per-source, per-job-type and protected manual/failure lanes.
- Implement source frontier and rewind window persistence.
- Implement idempotent extraction upsert behavior.
- Implement short raw payload retention metadata and cleanup entry point.

**Non-Goals:**
- No real high-risk browser/profile/custom script execution.
- No LightRAG.
- No production fetch policy beyond API auth and audit.
- No full search ranking.

## Decisions

1. **Use repository functions for job claim and completion.** Keep SQL locking in one place.
2. **Use stage-local transactions.** Each stage writes its own outputs and downstream jobs in one transaction or outbox-style function.
3. **Dedup starts before embedding.** `raw_object` is never embedded. Extracted `item_version` content becomes chunks later.
4. **Frontier state is advisory, dedup is authoritative.** Rewind can re-see old items; database uniqueness prevents duplicates.
5. **Payload retention is configurable.** Default raw payload retention is 7 days for normal public HTML/API payloads; important sources can override.

## Risks / Trade-offs

- **[Risk] Worker logic can become large** → Mitigation: split claim, execution dispatch and each job type into separate modules.
- **[Risk] Rewind increases repeated work** → Mitigation: batch observation upserts and rely on dedup keys.
- **[Risk] Outbox pattern is extra work** → Mitigation: use single transaction creation of downstream jobs for MVP, with an outbox-shaped helper so it can evolve.
