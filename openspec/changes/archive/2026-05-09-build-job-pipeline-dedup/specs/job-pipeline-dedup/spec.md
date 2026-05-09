## ADDED Requirements

### Requirement: Jobs are claimed safely
The system SHALL claim queued jobs using Postgres row locking with lease expiry and idempotency protection.

#### Scenario: Two workers claim jobs
- **WHEN** two workers attempt to claim jobs concurrently
- **THEN** each claimed job is assigned to only one worker

### Requirement: Jobs retry and eventually become dead
The system SHALL retry failed jobs up to `max_attempts` and mark exhausted jobs as dead with the last error.

#### Scenario: Job fails repeatedly
- **WHEN** a job fails more times than `max_attempts`
- **THEN** its status becomes dead and `GET /failures/recent` can report it

### Requirement: Source frontiers support rewind
The system SHALL crawl high-frequency sources using persisted frontier state plus rewind windows.

#### Scenario: Feed backfills an item
- **WHEN** a feed returns an older item inside the rewind window
- **THEN** the item is processed without creating duplicates

### Requirement: Pipeline writes are idempotent
The system SHALL define transaction boundaries and unique keys so retries do not duplicate content items, observations, versions or jobs.

#### Scenario: Worker crashes after item upsert
- **WHEN** an extraction job is retried after a partial failure
- **THEN** the retry completes missing observations, versions and downstream jobs without duplicate items

### Requirement: Raw object is evidence cache
The system SHALL treat raw payload as short-retention evidence while preserving extracted item data.

#### Scenario: Raw payload expires
- **WHEN** raw payload retention expires after successful extraction
- **THEN** the system can delete or compress payload while preserving raw metadata, hash, audit and item versions
