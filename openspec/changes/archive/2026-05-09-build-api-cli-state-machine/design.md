## Context

This change depends on `build-control-plane-schema`. The API is the source-of-truth mutation boundary. The CLI is an operator interface and agent interface, but it must not duplicate business logic or write the database directly.

## Goals / Non-Goals

**Goals:**
- Implement token-authenticated API mutations.
- Implement centralized status transitions and audit writing.
- Implement CLI commands through HTTP API.
- Add API and CLI tests for auth, audit and invalid transitions.

**Non-Goals:**
- No full fetch policy beyond token and audit.
- No real Firecrawl execution in `source test`; this endpoint may enqueue a `test_recipe` or `crawl_source` job depending on job implementation readiness.
- No search ranking beyond calling existing search endpoints if available.

## Decisions

1. **API token via header.** Use a header such as `Authorization: Bearer <token>` or `X-Harvester-API-Token` and document the chosen form in `CLAUDE.md`.
2. **Domain transition service owns state changes.** API handlers parse input and call domain services; they do not mutate statuses inline.
3. **Audit is written in the same transaction as the state change.** Rejected attempts also write audit when possible.
4. **CLI uses `httpx`.** Typer commands build requests and render responses. Tests use a local test server or mocked HTTP transport.

## Risks / Trade-offs

- **[Risk] CLI requires server to be running** → Mitigation: document this explicitly and keep all behavior consistent through one API path.
- **[Risk] Token-only auth is limited** → Mitigation: fetch policy remains a tracked TODO; MVP is personal home lab.
- **[Risk] State machine becomes too abstract** → Mitigation: implement explicit transition tables and small functions, not a generic framework.
