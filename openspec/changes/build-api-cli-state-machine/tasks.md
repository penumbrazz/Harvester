## 1. Auth and Audit Infrastructure

- [ ] 1.1 Create `tests/api/test_auth.py` first; assert missing or wrong token returns 401 for mutating endpoints and leaves database unchanged.
- [ ] 1.2 Add API settings for `HARVESTER_API_TOKEN`.
- [ ] 1.3 Add FastAPI auth dependency for mutating endpoints until `tests/api/test_auth.py` passes.
- [ ] 1.4 Create `tests/domain/test_audit.py` first; assert audit helper writes actor, action, entity, before/after JSON and reason inside a transaction.
- [ ] 1.5 Add `harvester/domain/audit.py` helper to write audit events inside an existing transaction.
- [ ] 1.6 Run `pytest tests/api/test_auth.py tests/domain/test_audit.py -q` and confirm it passes.

## 2. State Transition Services

- [ ] 2.1 Create `tests/domain/test_state_transitions.py` first; cover valid source transitions: candidate -> testing -> watched, watched -> paused, paused -> watched, any active state -> archived.
- [ ] 2.2 Extend `tests/domain/test_state_transitions.py` for invalid transitions and required audit event creation.
- [ ] 2.3 Add `harvester/domain/state.py` with explicit transition tables for source, topic, recipe and crawl run statuses.
- [ ] 2.4 Create `tests/api/test_source_promote_transaction.py`; assert promotion and audit happen in one transaction and rollback together on failure.
- [ ] 2.5 Run `pytest tests/domain/test_state_transitions.py tests/api/test_source_promote_transaction.py -q` and confirm it passes.

## 3. Source and Topic API

- [ ] 3.1 Create `tests/api/test_sources.py` first; cover source proposal, duplicate source behavior, promote, pause and audit events.
- [ ] 3.2 Create `tests/api/test_topics.py` first; cover topic creation with TTL and attaching an existing source.
- [ ] 3.3 Implement `POST /sources/propose` to create a candidate source and audit event.
- [ ] 3.4 Implement `POST /sources/{id}/promote` using the transition service.
- [ ] 3.5 Implement `POST /sources/{id}/pause` using the transition service.
- [ ] 3.6 Implement `POST /topics` to create topic watch with TTL and status.
- [ ] 3.7 Implement `POST /topics/{id}/sources` to attach an existing source to a topic.
- [ ] 3.8 Run `pytest tests/api/test_sources.py tests/api/test_topics.py -q` and confirm it passes.

## 4. Recipe and Failure API

- [ ] 4.1 Create `tests/api/test_recipes.py` first; cover draft recipe creation, approved executor validation and recipe approval audit.
- [ ] 4.2 Create `tests/api/test_failures.py` first; cover response shape for failed crawl runs, extraction runs and jobs.
- [ ] 4.3 Implement `POST /recipes` to create draft recipes for approved executor types.
- [ ] 4.4 Implement `POST /recipes/{id}/approve` through the transition service.
- [ ] 4.5 Implement `GET /failures/recent` returning recent failed crawl runs, extraction runs and jobs.
- [ ] 4.6 Run `pytest tests/api/test_recipes.py tests/api/test_failures.py -q` and confirm it passes.

## 5. CLI Commands

- [ ] 5.1 Create `tests/cli/test_cli_http_only.py` first; assert CLI commands use an HTTP transport mock and do not create database sessions.
- [ ] 5.2 Add HTTP API client helper using `httpx` and `HARVESTER_API_URL`.
- [ ] 5.3 Implement `harvester source propose`.
- [ ] 5.4 Implement `harvester source promote`.
- [ ] 5.5 Implement `harvester topic create`.
- [ ] 5.6 Implement `harvester failures recent`.
- [ ] 5.7 Run `pytest tests/api tests/domain tests/cli -q` and confirm it passes.
- [ ] 5.8 Commit with message `feat: add harvester api cli state machine`.
