## 1. Python Project Skeleton

- [ ] 1.1 Create `tests/test_package_import.py` first; assert `import harvester` works and exposes a string `__version__`.
- [ ] 1.2 Create `pyproject.toml` with project metadata, Python version, FastAPI, Typer, SQLAlchemy, Alembic, psycopg, pytest, httpx and ruff dependencies.
- [ ] 1.3 Create `harvester/__init__.py` exposing a package version string until `tests/test_package_import.py` passes.
- [ ] 1.4 Create package directories with `__init__.py`: `harvester/api`, `harvester/cli`, `harvester/db`, `harvester/jobs`, `harvester/adapters`, `harvester/extractors`, `harvester/search`, `harvester/domain`.
- [ ] 1.5 Create `tests/test_health.py` before app code; assert `GET /health` returns 200 and `{"status": "ok"}`.
- [ ] 1.6 Create `harvester/api/app.py` with a `create_app()` function and `GET /health` route until the health test passes.
- [ ] 1.7 Create `tests/test_cli_import.py` before CLI code; assert `python -m harvester.cli.main --help` exits 0.
- [ ] 1.8 Create `harvester/cli/main.py` with a Typer app and a `health` command that calls the configured HTTP API health endpoint.

## 2. Tests and Developer Commands

- [ ] 2.1 Create `tests/conftest.py` with shared pytest fixtures for future API tests.
- [ ] 2.2 Run `pytest tests/test_package_import.py tests/test_health.py tests/test_cli_import.py -q` and confirm all pass.
- [ ] 2.3 Run `python -m harvester.cli.main --help` and confirm the CLI imports without errors.
- [ ] 2.4 Run `ruff check .` if ruff is installed by the project extras; otherwise record that linting starts in a later dependency setup step.

## 3. Agent Instruction Files

- [ ] 3.1 Create root `AGENTS.md` with Chinese-only communication, OpenSpec workflow, TDD, raw/content separation and no direct production DB writes.
- [ ] 3.2 Create root `CLAUDE.md` with the same project conventions plus testing commands and warning not to add gstack routing unless explicitly requested.
- [ ] 3.3 Verify both files mention `raw_object` as short-retention evidence and `item_version -> chunks` as the only embedding input.

## 4. Validation

- [ ] 4.1 Run `openspec status --change bootstrap-python-agent-docs` and confirm artifacts are complete.
- [ ] 4.2 Run `pytest` and record the passing output in the implementation notes.
- [ ] 4.3 Run `python -m harvester.cli.main --help` and record the passing output.
- [ ] 4.4 Commit with message `chore: bootstrap harvester python project`.
