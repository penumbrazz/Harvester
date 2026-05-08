## Context

Harvester is starting from an empty repository with only OpenSpec configuration, `.claude/settings.json`, `TODOS.md` and the reviewed design document under `~/.gstack/projects/Harvester/`. The accepted stack is Python with FastAPI, Typer, SQLAlchemy/Alembic and pytest.

This change is the foundation. It should not implement the full crawler, database schema or search pipeline. It creates the repo shape and agent rules that later changes will depend on.

## Goals / Non-Goals

**Goals:**
- Create a minimal importable Python package.
- Establish directory boundaries for API, CLI, DB, jobs, adapters, extraction, search and domain logic.
- Add `AGENTS.md` and `CLAUDE.md` so GLM/Claude/Codex share the same project instructions.
- Add pytest and a minimal health test that proves the skeleton works.

**Non-Goals:**
- No full schema migration.
- No Firecrawl integration.
- No real source/topic/crawl API behavior.
- No Docker Compose beyond any minimal placeholder needed for later changes.

## Decisions

1. **Use `src`-less package layout for now.** The package lives at `harvester/` in repo root. This keeps early implementation simple and matches a small service project.
2. **Keep modules narrow.** Create empty or near-empty modules under `harvester/api`, `harvester/cli`, `harvester/db`, `harvester/jobs`, `harvester/adapters`, `harvester/extractors`, `harvester/search`, `harvester/domain`.
3. **Agent instruction files are real repo files.** `AGENTS.md` applies to all agents. `CLAUDE.md` adds Claude-specific project conventions without adding the gstack routing block previously declined.
4. **Health is the only runtime behavior in this slice.** A FastAPI app exposes `GET /health` and tests verify it.

## Risks / Trade-offs

- **[Risk] Empty modules invite broad edits later** → Mitigation: each later OpenSpec change names the exact module it owns.
- **[Risk] CLAUDE.md could conflict with prior routing decision** → Mitigation: include project conventions only, not automatic gstack skill routing.
- **[Risk] Too much setup before business behavior** → Mitigation: keep this slice limited to importability, health, test runner and agent instructions.
