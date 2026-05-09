## Why

After schema and pipeline exist, Harvester needs searchable output, stable fixture tests and a deployable home-lab contract. Without this slice, data can be collected but not reliably queried or smoke-tested.

## What Changes

- Implement keyword and pgvector search over latest item versions and chunks.
- Add URL normalization rules and tests.
- Add stable CDC/Sina raw object fixtures, frozen time and stubbed Firecrawl/model outputs.
- Add Docker Compose, `.env.example`, migration and healthcheck/smoke workflows.

## Capabilities

### New Capabilities
- `search-fixtures-deployment`: Search indexes/query behavior, deterministic fixtures, URL normalization and Docker Compose deployment smoke.

### Modified Capabilities

## Impact

- Adds search module, fixture files, deployment configuration and smoke tests.
- Depends on schema and pipeline outputs.
- Gives GLM/agents a final MVP verification target.
