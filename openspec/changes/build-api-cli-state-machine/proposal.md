## Why

Once the schema exists, Harvester needs a safe API and CLI surface for source/topic/recipe state changes. The CLI must call HTTP API so all state transitions, auth checks and audit events stay in one path.

## What Changes

- Implement API token authentication and audit for mutating endpoints.
- Implement centralized state transition services for source/topic/recipe/crawl run status changes.
- Implement MVP endpoints for source propose/test/promote/pause, topic create/attach/list, recipe create/test/approve and failure inspection.
- Implement Typer CLI commands that call the HTTP API, not the database.

## Capabilities

### New Capabilities
- `api-cli-state-machine`: HTTP API, CLI and centralized state transition behavior for Harvester MVP.

### Modified Capabilities

## Impact

- Adds FastAPI routers, auth dependency, domain services and CLI client.
- Depends on the control-plane schema.
- Provides entry points for later job runner and search behavior.
