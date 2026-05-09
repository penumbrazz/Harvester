## 1. Job Claim and Lease

- [x] 1.1 Create `tests/jobs/test_claim.py` first; use two concurrent DB sessions and assert the same job is not claimed twice.
- [x] 1.2 Add `harvester/jobs/repository.py` with `claim_next_jobs(worker_id, limit, lanes)` using `FOR UPDATE SKIP LOCKED`.
- [x] 1.3 Create `tests/jobs/test_lease_retry.py` first; cover expired lease reclaim, retry reschedule and dead after max attempts.
- [x] 1.4 Add lease expiry handling so jobs with expired `locked_until` can be reclaimed.
- [x] 1.5 Add retry handling: failed jobs increment attempts, reschedule when attempts remain, become dead after max attempts.
- [x] 1.6 Create `tests/jobs/test_idempotency.py` first; prove duplicate `idempotency_key` cannot create two effective jobs.
- [x] 1.7 Run `pytest tests/jobs/test_claim.py tests/jobs/test_lease_retry.py tests/jobs/test_idempotency.py -q` and confirm it passes.

## 2. Queue Fairness

- [x] 2.1 Create `tests/jobs/test_fairness.py` first; prove Sina-like P1 jobs do not starve CDC/manual jobs.
- [x] 2.2 Add per-source `max_in_flight` enforcement when claiming source-scoped jobs.
- [x] 2.3 Add per-job-type concurrency caps.
- [x] 2.4 Add queue depth cap behavior for high-frequency source jobs.
- [x] 2.5 Add protected manual/failure lane for `test_recipe` and retry jobs.
- [x] 2.6 Run `pytest tests/jobs/test_fairness.py -q` and confirm it passes.

## 3. Source Frontier and Crawl Metadata

- [x] 3.1 Create `tests/jobs/test_frontier.py` first; cover reordered, backfilled and repeated feed items.
- [x] 3.2 Add `harvester/jobs/frontier.py` to read/update source frontier state.
- [x] 3.3 Implement rewind window logic using `cursor`, `frontier`, `rewind_window` and `last_complete_range`.
- [x] 3.4 Create `tests/jobs/test_raw_object_metadata.py` first; assert raw object metadata includes storage URI, hash, retention and extraction status without embedding payload.
- [x] 3.5 Implement raw object metadata creation with storage URI, hash, retention and extraction status fields.
- [x] 3.6 Run `pytest tests/jobs/test_frontier.py tests/jobs/test_raw_object_metadata.py -q` and confirm it passes.

## 4. Extraction and Dedup Pipeline

- [x] 4.1 Create `tests/extractors/test_extractor_interface.py` first; assert extractors accept a raw object and return normalized candidate item records.
- [x] 4.2 Add extractor interface that accepts a raw object and returns normalized candidate item records.
- [x] 4.3 Create `tests/extractors/test_cdc_fixture_extractor.py` first using fixed raw fixture input.
- [x] 4.4 Add CDC fixture extractor for list/detail shape using fixed raw fixture input.
- [x] 4.5 Create `tests/extractors/test_sina_fixture_extractor.py` first using fixed raw fixture input.
- [x] 4.6 Add Sina fixture extractor for feed messages using fixed raw fixture input.
- [x] 4.7 Create `tests/jobs/test_pipeline_idempotency.py` first; cover external ID upsert, weak key upsert, observation-only repeats, changed content versioning and downstream job creation.
- [x] 4.8 Implement idempotent content item upsert using external ID or weak key.
- [x] 4.9 Implement item observation insert with unique key and last_seen update.
- [x] 4.10 Implement item version insert only when content hash changes.
- [x] 4.11 Implement downstream job creation in the same transaction as item/version writes.
- [x] 4.12 Create `tests/jobs/test_pipeline_crash_retry.py` first; prove partial extraction retries do not duplicate items or lose downstream jobs.
- [x] 4.13 Run `pytest tests/extractors tests/jobs/test_pipeline_idempotency.py tests/jobs/test_pipeline_crash_retry.py -q` and confirm it passes.

## 5. Raw Payload Retention

- [x] 5.1 Create `tests/jobs/test_raw_payload_retention.py` first; prove metadata, hashes and audit remain after payload cleanup.
- [x] 5.2 Add configurable default raw payload retention of 7 days.
- [x] 5.3 Add cleanup function that deletes or compresses payload only after successful extraction and item/version persistence.
- [x] 5.4 Run `pytest tests/jobs tests/extractors -q` and confirm all job and pipeline tests pass.
- [x] 5.5 Commit with message `feat: add harvester job pipeline dedup`.
