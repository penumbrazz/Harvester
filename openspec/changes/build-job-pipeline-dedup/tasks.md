## 1. Job Claim and Lease

- [ ] 1.1 Create `tests/jobs/test_claim.py` first; use two concurrent DB sessions and assert the same job is not claimed twice.
- [ ] 1.2 Add `harvester/jobs/repository.py` with `claim_next_jobs(worker_id, limit, lanes)` using `FOR UPDATE SKIP LOCKED`.
- [ ] 1.3 Create `tests/jobs/test_lease_retry.py` first; cover expired lease reclaim, retry reschedule and dead after max attempts.
- [ ] 1.4 Add lease expiry handling so jobs with expired `locked_until` can be reclaimed.
- [ ] 1.5 Add retry handling: failed jobs increment attempts, reschedule when attempts remain, become dead after max attempts.
- [ ] 1.6 Create `tests/jobs/test_idempotency.py` first; prove duplicate `idempotency_key` cannot create two effective jobs.
- [ ] 1.7 Run `pytest tests/jobs/test_claim.py tests/jobs/test_lease_retry.py tests/jobs/test_idempotency.py -q` and confirm it passes.

## 2. Queue Fairness

- [ ] 2.1 Create `tests/jobs/test_fairness.py` first; prove Sina-like P1 jobs do not starve CDC/manual jobs.
- [ ] 2.2 Add per-source `max_in_flight` enforcement when claiming source-scoped jobs.
- [ ] 2.3 Add per-job-type concurrency caps.
- [ ] 2.4 Add queue depth cap behavior for high-frequency source jobs.
- [ ] 2.5 Add protected manual/failure lane for `test_recipe` and retry jobs.
- [ ] 2.6 Run `pytest tests/jobs/test_fairness.py -q` and confirm it passes.

## 3. Source Frontier and Crawl Metadata

- [ ] 3.1 Create `tests/jobs/test_frontier.py` first; cover reordered, backfilled and repeated feed items.
- [ ] 3.2 Add `harvester/jobs/frontier.py` to read/update source frontier state.
- [ ] 3.3 Implement rewind window logic using `cursor`, `frontier`, `rewind_window` and `last_complete_range`.
- [ ] 3.4 Create `tests/jobs/test_raw_object_metadata.py` first; assert raw object metadata includes storage URI, hash, retention and extraction status without embedding payload.
- [ ] 3.5 Implement raw object metadata creation with storage URI, hash, retention and extraction status fields.
- [ ] 3.6 Run `pytest tests/jobs/test_frontier.py tests/jobs/test_raw_object_metadata.py -q` and confirm it passes.

## 4. Extraction and Dedup Pipeline

- [ ] 4.1 Create `tests/extractors/test_extractor_interface.py` first; assert extractors accept a raw object and return normalized candidate item records.
- [ ] 4.2 Add extractor interface that accepts a raw object and returns normalized candidate item records.
- [ ] 4.3 Create `tests/extractors/test_cdc_fixture_extractor.py` first using fixed raw fixture input.
- [ ] 4.4 Add CDC fixture extractor for list/detail shape using fixed raw fixture input.
- [ ] 4.5 Create `tests/extractors/test_sina_fixture_extractor.py` first using fixed raw fixture input.
- [ ] 4.6 Add Sina fixture extractor for feed messages using fixed raw fixture input.
- [ ] 4.7 Create `tests/jobs/test_pipeline_idempotency.py` first; cover external ID upsert, weak key upsert, observation-only repeats, changed content versioning and downstream job creation.
- [ ] 4.8 Implement idempotent content item upsert using external ID or weak key.
- [ ] 4.9 Implement item observation insert with unique key and last_seen update.
- [ ] 4.10 Implement item version insert only when content hash changes.
- [ ] 4.11 Implement downstream job creation in the same transaction as item/version writes.
- [ ] 4.12 Create `tests/jobs/test_pipeline_crash_retry.py` first; prove partial extraction retries do not duplicate items or lose downstream jobs.
- [ ] 4.13 Run `pytest tests/extractors tests/jobs/test_pipeline_idempotency.py tests/jobs/test_pipeline_crash_retry.py -q` and confirm it passes.

## 5. Raw Payload Retention

- [ ] 5.1 Create `tests/jobs/test_raw_payload_retention.py` first; prove metadata, hashes and audit remain after payload cleanup.
- [ ] 5.2 Add configurable default raw payload retention of 7 days.
- [ ] 5.3 Add cleanup function that deletes or compresses payload only after successful extraction and item/version persistence.
- [ ] 5.4 Run `pytest tests/jobs tests/extractors -q` and confirm all job and pipeline tests pass.
- [ ] 5.5 Commit with message `feat: add harvester job pipeline dedup`.
