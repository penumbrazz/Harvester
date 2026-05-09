## ADDED Requirements

### Requirement: Sources and topics are first-class entities
The system SHALL store fixed sources and temporary topic watches in separate first-class tables.

#### Scenario: Topic source is attached
- **WHEN** a source is attached to a topic watch
- **THEN** the relationship is stored in `topic_sources` without converting the topic into a source

### Requirement: Raw evidence is separate from searchable content
The system SHALL store raw fetch evidence separately from content items, observations, item versions and chunks.

#### Scenario: Feed page contains many messages
- **WHEN** a Sina feed raw object contains multiple messages
- **THEN** each message can become its own `content_item` and `item_observation`

### Requirement: Raw payload retention is explicit
The system SHALL support short retention for raw payloads while keeping metadata, hashes and audit records.

#### Scenario: Extraction succeeds
- **WHEN** a raw object has been extracted into item versions and chunks
- **THEN** its payload can be compressed or deleted after the configured retention window while metadata remains

### Requirement: URL canonicalization fields exist
The system SHALL store `original_url`, `final_url`, `canonical_url` and `canonical_url_hash` where URL identity participates in deduplication.

#### Scenario: Tracking parameters differ
- **WHEN** two URLs differ only by tracking parameters or fragments
- **THEN** they can produce the same canonical URL hash while preserving original URLs for audit

### Requirement: Source frontier state exists
The system SHALL persist cursor/frontier state for high-frequency sources.

#### Scenario: Feed reorders messages
- **WHEN** a source backfills or reorders messages
- **THEN** the crawler can use a rewind window and last complete range rather than relying only on the latest cursor

### Requirement: Jobs support leases, retries and idempotency
The system SHALL include job fields for status, priority, run time, lease owner, lease expiry, attempts, max attempts, idempotency key and last error.

#### Scenario: Worker dies during job
- **WHEN** a worker dies before completing a leased job
- **THEN** another worker can reclaim it after `locked_until` expires

### Requirement: Audit events record state changes
The system SHALL store audit events for state transitions, rejected operations and important pipeline decisions.

#### Scenario: Invalid source transition is attempted
- **WHEN** a caller attempts an invalid source status transition
- **THEN** the system records an audit event and leaves source state unchanged
