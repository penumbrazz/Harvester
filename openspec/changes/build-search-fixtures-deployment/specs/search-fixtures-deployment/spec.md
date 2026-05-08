## ADDED Requirements

### Requirement: Search returns latest deduplicated item versions
The system SHALL search latest item versions and collapse duplicate groups by default.

#### Scenario: Duplicate content exists
- **WHEN** two item versions share a dedup group
- **THEN** default search returns one representative result

### Requirement: Embedding starts at chunks
The system SHALL generate embeddings only for chunks derived from normalized item versions.

#### Scenario: Raw object contains HTML
- **WHEN** raw HTML is stored as raw object payload
- **THEN** embedding jobs are not created for the raw payload

### Requirement: URL normalization is deterministic
The system SHALL normalize URLs consistently for dedup while preserving original and final URLs for audit.

#### Scenario: URL has tracking parameters
- **WHEN** a URL includes `utm_source`, fragment or reordered query parameters
- **THEN** canonical URL hash ignores tracking noise according to the normalization rules

### Requirement: Fixture tests are deterministic
The system SHALL use fixed raw object fixtures, frozen time and stubbed model/Firecrawl outputs for regression tests.

#### Scenario: CDC website changes externally
- **WHEN** the external CDC page changes after fixture creation
- **THEN** fixture regression tests still produce the same expected items

### Requirement: Deployment smoke validates service readiness
The system SHALL include Docker Compose configuration and smoke tests that verify config, migration, server health, worker health and one fixture crawl.

#### Scenario: Database is not ready
- **WHEN** Docker Compose starts services before Postgres is healthy
- **THEN** healthcheck gating prevents false success
