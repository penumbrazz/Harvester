## 1. URL Normalization

- [x] 1.1 Create `tests/domain/test_urls.py` first; cover lowercase scheme/host, fragment removal, tracking parameter removal, query parameter sorting and redirect final URL preservation.
- [x] 1.2 Add `harvester/domain/urls.py` with deterministic URL normalization rules.
- [x] 1.3 Preserve `original_url`, `final_url`, `canonical_url` and `canonical_url_hash` in item creation paths.
- [x] 1.4 Run `pytest tests/domain/test_urls.py -q` and confirm it passes.

## 2. Search Indexes and Query Code

- [x] 2.1 Create `tests/search/test_indexes.py` first; assert migrations define indexes for latest item version lookup by source, topic and time.
- [x] 2.2 Add migration/index definitions for latest item version lookup by source, topic and time.
- [x] 2.3 Create `tests/search/test_keyword_search.py` first; cover keyword search over latest item versions.
- [x] 2.4 Add keyword search implementation using Postgres full-text or trigram over latest item versions.
- [x] 2.5 Create `tests/search/test_vector_search.py` first; cover vector-ready chunks with fixed embedding model and dimension.
- [x] 2.6 Add vector search implementation over `chunks.embedding` with fixed embedding model and dimension.
- [x] 2.7 Create `tests/search/test_dedup_collapse.py` first; cover default dedup group collapse and latest-version-only behavior.
- [x] 2.8 Add default dedup group collapse in search results.
- [x] 2.9 Run `pytest tests/search -q` and confirm it passes.

## 3. Embedding Boundary

- [x] 3.1 Create `tests/search/test_chunking.py` first; assert chunks derive only from `item_versions.normalized_text`.
- [x] 3.2 Add chunking function that derives chunks only from `item_versions.normalized_text`.
- [x] 3.3 Create `tests/search/test_embedding_jobs.py` first; assert embedding jobs are created only for chunks with `embedding_status=pending` and never for raw payload.
- [x] 3.4 Add embedding job creation only for chunks with `embedding_status=pending`.
- [x] 3.5 Create `tests/adapters/test_stub_model.py` first; assert the stub model adapter returns deterministic vectors.
- [x] 3.6 Add stub model adapter returning deterministic vectors for tests.
- [x] 3.7 Run `pytest tests/search/test_chunking.py tests/search/test_embedding_jobs.py tests/adapters/test_stub_model.py -q` and confirm it passes.

## 4. Fixtures and Regression Tests

- [x] 4.1 Create `tests/fixtures/test_fixture_contract.py` first; assert CDC/Sina fixture files and expected JSON outputs exist.
- [x] 4.2 Add `tests/fixtures/raw/cdc-list.html` and expected extracted CDC detail links.
- [x] 4.3 Add `tests/fixtures/raw/cdc-detail.html` and expected article item/version.
- [x] 4.4 Add `tests/fixtures/raw/sina-feed.json` and expected news flash items.
- [x] 4.5 Add frozen-time pytest fixture for pipeline tests.
- [x] 4.6 Create `tests/adapters/test_stub_firecrawl.py` first; assert regression tests use stub Firecrawl and do not hit the network.
- [x] 4.7 Add stub Firecrawl adapter tests so regression tests do not hit the network.
- [x] 4.8 Create `tests/integration/test_sina_compressed_soak.py` first; loop fixture pages and prove no duplicate content items.
- [x] 4.9 Add compressed Sina soak test that loops fixture pages and proves no duplicate content items.
- [x] 4.10 Run `pytest tests/fixtures tests/adapters/test_stub_firecrawl.py tests/integration/test_sina_compressed_soak.py -q` and confirm it passes.

## 5. Docker Compose and Smoke

- [x] 5.1 Create `tests/deploy/test_env_example.py` first; assert `.env.example` includes database URL, API token, archive path, Firecrawl URL and model worker URL placeholders.
- [x] 5.2 Add `.env.example` with database URL, API token, archive path, Firecrawl URL and model worker URL placeholders.
- [x] 5.3 Create `tests/deploy/test_compose_config.py` first; assert `docker compose config` succeeds when `.env.example` values are supplied.
- [x] 5.4 Add `docker-compose.yml` for server, worker and Postgres/pgvector or external database configuration.
- [x] 5.5 Add healthchecks for server and worker readiness.
- [x] 5.6 Create `tests/deploy/test_smoke_script.py` first; assert `scripts/smoke.sh` exists, is executable and runs config/migration/health/fixture steps.
- [x] 5.7 Add `scripts/smoke.sh` to run `docker compose config`, migration, healthcheck and one fixture crawl.
- [x] 5.8 Add documentation for running smoke locally on the mini PC.
- [x] 5.9 Run `pytest tests/search tests/fixtures tests/adapters tests/integration tests/deploy -q` and confirm it passes.
- [x] 5.10 Run `docker compose config` and record output.
- [x] 5.11 Commit with message `feat: add search fixtures deployment smoke`.
