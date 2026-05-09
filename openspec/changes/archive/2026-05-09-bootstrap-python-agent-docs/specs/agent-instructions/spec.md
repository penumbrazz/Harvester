## ADDED Requirements

### Requirement: Agent instructions are present
The repository SHALL include root `AGENTS.md` and `CLAUDE.md` files describing project-specific behavior for AI coding agents.

#### Scenario: Agent starts work
- **WHEN** an AI coding agent starts in the repository
- **THEN** it can read root instructions that require Chinese communication, OpenSpec change discipline and TDD

### Requirement: Agents do not bypass Harvester API boundaries
Agent instructions SHALL prohibit direct production database writes from agent workflows and require state changes to go through Harvester API or approved migration code.

#### Scenario: Agent implements CLI behavior
- **WHEN** an agent creates a CLI command that mutates Harvester state
- **THEN** the CLI calls HTTP API instead of writing database rows directly

### Requirement: Agents preserve raw/content separation
Agent instructions SHALL state that `raw_object` is evidence cache and `content_item` / `item_version` / `chunk` are the searchable knowledge layer.

#### Scenario: Agent adds extraction code
- **WHEN** an agent implements a timeline or feed extractor
- **THEN** it extracts independent content items rather than treating the whole page as one document
