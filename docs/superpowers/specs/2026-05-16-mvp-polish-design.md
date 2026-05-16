# Harvester MVP Polish Design

Date: 2026-05-16
Status: Draft

## Goal

Polish and stabilize the Harvester MVP before adding new features (LightRAG/KG/MCP, fetch policy, auth profile). Focus on test coverage, code quality, bug fixes, UX polish, and documentation.

## Phases

Five sequential phases. Each phase produces a commit-worthy deliverable.

---

## Phase 1: Test Repair & Coverage Baseline

### 1.1 Run all tests, fix failures

- Run full backend test suite (`uv run pytest tests/`)
- Run frontend unit tests (`npm test`)
- Run frontend E2E tests (Playwright against live backend)
- Record and fix all failures; no skips, no silent failures

### 1.2 Measure coverage baseline

- Generate coverage report for backend (`uv run pytest --cov=harvester`)
- Identify modules below 40% coverage
- Record baseline numbers for tracking

### 1.3 Add missing backend API tests

**Sources** (`tests/api/test_sources.py` extension):
- PATCH /sources/{id} — edit name, URL, trust_level; verify audit event

**Recipes** (new test cases in `tests/api/test_recipes.py`):
- POST /recipes/{id}/reject — pending->rejected, verify state + audit
- POST /recipes/{id}/resubmit — rejected->pending, verify state + audit
- POST /recipes/{id}/deprecate — approved->deprecated, verify state + audit
- PATCH /recipes/{id} — edit name, config; verify audit
- Invalid transitions: reject approved recipe, resubmit non-rejected, deprecate pending

**Schedules** (new test cases in `tests/api/test_watch_schedules.py`):
- POST /schedules/{id}/pause — active->paused, verify state + audit
- POST /schedules/{id}/resume — paused->active, verify state + audit
- POST /schedules/{id}/disable — active/paused->disabled, verify state + audit
- PATCH /schedules/{id} — edit interval_seconds, verify audit
- Invalid transitions: pause already paused, resume non-paused, disable already disabled

### 1.4 Add missing frontend E2E tests

**Content page** (`frontend/e2e/content-library.spec.ts`):
- Navigate to content page
- List content items, verify table renders
- Filter by source, item_type, status
- Keyword search and verify results
- Vector search and verify results (or 503 when adapter unavailable)
- Empty state when no content exists

**Source resume** (extend `frontend/e2e/source-management.spec.ts`):
- Resume paused source, verify state change

### 1.5 Acceptance criteria

- All tests green (backend + frontend unit + E2E)
- Coverage baseline documented
- No API endpoint lacks at least one test
- Every entity state transition has backend API test coverage

---

## Phase 2: End-to-End Live Smoke Tests

### 2.1 Sina 7x24 live crawl smoke test

New file: `tests/integration/test_sina_7x24_live_crawl_smoke.py`

- Marked `@pytest.mark.live`, requires `HARVESTER_ENABLE_LIVE_CRAWL=1`
- Calls real Firecrawl adapter to fetch Sina 7x24 page
- Runs Sina7x24Extractor on real HTML
- Verifies: content_item created, item_version has content, observations linked
- Verifies: keyword search finds extracted items

### 2.2 CDC Weekly live crawl smoke test

Already partially exists in `test_cdc_public_crawl_smoke.py`. Extend or create new:
- Real CDC weekly page fetch via Firecrawl
- CDCWeeklyExtractor on real HTML
- Verify full pipeline: raw_object -> content_item -> item_version -> keyword searchable

### 2.3 Full workflow smoke test

New file: `tests/integration/test_full_workflow_smoke.py`

- Marked `@pytest.mark.live`
- Complete lifecycle through API:
  1. Propose source (Sina or CDC)
  2. Promote source to watched
  3. Create recipe
  4. Approve recipe
  5. Trigger crawl via POST /crawl/run
  6. Wait for crawl completion (poll with timeout)
  7. Verify raw_objects exist
  8. Verify content_items extracted
  9. Search and verify results findable
  10. Verify audit trail records key transitions

### 2.4 Acceptance criteria

- Live smoke tests pass against real backend + real external sources
- Non-live tests remain unaffected
- Smoke tests are opt-in (env var gate), don't run in normal CI

---

## Phase 3: Bug Fixes & UX Polish

### 3.1 Bug inventory

- Collect bugs from Phase 1-2 test runs
- Audit API error handling consistency (are all errors proper JSON with detail?)
- Check frontend edge cases:
  - Empty states for all list pages
  - Loading states during API calls
  - Error message display on API failures
  - Form validation (required fields, format checks)

### 3.2 API error handling

- Ensure all 4xx/5xx responses have consistent JSON shape: `{"detail": "..."}`
- Verify state machine transition errors return 400 with clear message
- Verify not-found returns 404 (not 500)

### 3.3 Frontend UX

- Empty state components for: content list, audit log, jobs, crawls
- Loading spinners/skeletons during data fetch
- Error boundary / error toast on API failures
- Form validation feedback (required fields, invalid input)

### 3.4 Acceptance criteria

- No unhandled errors in normal workflows
- All list pages show meaningful empty state
- All forms validate before submission
- API errors show user-friendly messages

---

## Phase 4: Code Quality Cleanup

### 4.1 Dead code removal

- Find and remove unused imports (`ruff check --select F401`)
- Find and remove unused functions/classes (cross-reference with grep)
- Remove commented-out code blocks

### 4.2 Extract duplicated logic

- Scan for repeated patterns across files
- Extract shared utilities where 3+ occurrences found
- Check extractors for common base patterns

### 4.3 File size audit

- List files over 500 lines; assess if any need splitting
- Priority: files over 1000 lines must be split

### 4.4 Type hints and style

- Ensure all public functions have type hints
- Run `black . && isort .` (backend)
- Run `npm run format && npm run lint` (frontend)
- Fix all lint warnings

### 4.5 Acceptance criteria

- No files over 1000 lines
- No lint errors (backend + frontend)
- No dead code (unused imports, unreachable code)
- Duplicated logic extracted to shared utilities

---

## Phase 5: Documentation

### 5.1 README update

- Verify README matches current API endpoints
- Update architecture diagrams if needed
- Verify setup instructions are accurate (ports, env vars, commands)

### 5.2 API documentation

- Verify OpenAPI schema is complete (FastAPI auto-generates)
- Add description and examples to endpoint docstrings
- Ensure all request/response schemas have descriptions

### 5.3 Project conventions review

- Review CLAUDE.md / AGENTS.md: are conventions still accurate?
- Review DESIGN.md: does frontend still match design system?
- Update TODOS.md if priorities have shifted

### 5.4 Acceptance criteria

- README accurately reflects current state
- All API endpoints have docstrings with descriptions
- Project conventions docs are up to date

---

## Out of Scope

- New extractors (RSS, Weibo, WeChat)
- LightRAG / KG / MCP integration
- Fetch policy (URL safety boundary)
- Auth profile / sandbox
- New CLI commands
- Performance optimization
- Login / authentication
