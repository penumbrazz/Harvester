## Context

This change depends on schema and pipeline work. It turns extracted items into useful search results and makes the system deployable on the mini PC with Postgres/pgvector, Firecrawl and optional model worker stubs.

## Goals / Non-Goals

**Goals:**
- Add deterministic URL normalization.
- Implement keyword and vector search contracts.
- Add stable CDC/Sina fixtures and smoke tests.
- Add Docker Compose and `.env.example`.
- Verify migration, server health, worker health and fixture crawl.

**Non-Goals:**
- No LightRAG.
- No production-quality ranking beyond MVP filters and dedup collapse.
- No live 24-hour CI soak.
- No login/high-risk recipe support.

## Decisions

1. **Search latest item versions.** Search does not scan raw objects or historical versions by default.
2. **Use fixture-first tests.** Real network and real Qwen service only appear in smoke tests, not regression assertions.
3. **URL normalization is a tested utility.** It lives in a small module and is used before `canonical_url_hash` is computed.
4. **Compose is a deployment contract.** It validates service wiring, env vars, healthchecks and migrations, not public distribution.

## Risks / Trade-offs

- **[Risk] Chinese keyword search quality can vary** → Mitigation: start with Postgres full-text or trigram contract and keep vector search available for semantic retrieval.
- **[Risk] pgvector index tuning premature** → Mitigation: create explicit index migration and document model/dimension; tune HNSW/IVFFlat later based on data.
- **[Risk] Compose smoke can get slow** → Mitigation: keep fixture crawl small and deterministic.
