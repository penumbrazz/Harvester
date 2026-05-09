## ADDED Requirements

### Requirement: Mutating API calls require API token
The system SHALL require a configured API token for mutating HTTP endpoints.

#### Scenario: Missing token
- **WHEN** a caller sends `POST /sources/propose` without a valid token
- **THEN** the system returns 401 and does not create a source

### Requirement: State transitions are centralized
The system SHALL apply source, topic, recipe and crawl run status changes through a centralized transition service that writes audit events.

#### Scenario: Source is promoted
- **WHEN** a candidate source with an approved recipe is promoted
- **THEN** the source status changes to watched and an audit event records the transition

#### Scenario: Invalid transition is rejected
- **WHEN** a rejected source is promoted directly to watched
- **THEN** the system rejects the request and writes an audit event without changing status

### Requirement: CLI calls HTTP API
The system SHALL implement mutating CLI commands by calling HTTP API endpoints.

#### Scenario: CLI promotes source
- **WHEN** `harvester source promote <id>` runs
- **THEN** it sends an HTTP request to the API and does not open a database session

### Requirement: Failure inspection is available
The system SHALL expose recent crawl/extraction/job failures through API and CLI.

#### Scenario: Recent failures requested
- **WHEN** a user runs `harvester failures recent`
- **THEN** the CLI displays recent failed runs or jobs with error class, message and entity IDs
