## ADDED Requirements

### Requirement: Python project skeleton exists
The system SHALL provide a Python project skeleton for Harvester using FastAPI, Typer, SQLAlchemy/Alembic, pytest and ruff-compatible formatting.

#### Scenario: Developer installs project
- **WHEN** a developer runs the documented install command
- **THEN** Python dependencies are installed and `harvester` imports successfully

#### Scenario: Test runner starts
- **WHEN** a developer runs `pytest`
- **THEN** pytest discovers the test suite and runs without import errors

### Requirement: Source layout is explicit
The system SHALL separate API, CLI, database, job, adapter, extraction, search and domain code into focused modules.

#### Scenario: New worker locates job code
- **WHEN** an agent needs to implement the job runner
- **THEN** it can find the intended module under `harvester/jobs/`

#### Scenario: New API route is added
- **WHEN** an agent needs to implement an HTTP endpoint
- **THEN** it can place FastAPI router code under `harvester/api/`

### Requirement: Health command exists
The system SHALL include a minimal health endpoint or command that can be used by Docker Compose smoke tests.

#### Scenario: Health check runs before full implementation
- **WHEN** the server is started during the bootstrap slice
- **THEN** a health route returns a successful status without requiring crawl data
