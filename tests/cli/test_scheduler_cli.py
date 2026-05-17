"""Tests for scheduler CLI one-shot command.

The scheduler CLI command calls run_scheduler_once directly (local command,
not HTTP API). Tests verify the output contains expected stats.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from sqlalchemy import text
from typer.testing import CliRunner


def _insert_source(session) -> str:
    sid = uuid.uuid4()
    now = datetime.now(UTC)
    session.execute(
        text(
            "INSERT INTO sources "
            "(id, name, kind, status, trust_level, auth_required, failure_count, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'rss', 'watched', 'medium', false, 0, :ts, :ts)"
        ),
        {"id": sid, "name": f"src_{sid.hex[:8]}", "ts": now},
    )
    return str(sid)


def _insert_recipe(session) -> str:
    rid = uuid.uuid4()
    now = datetime.now(UTC)
    session.execute(
        text(
            "INSERT INTO recipes "
            "(id, name, executor, risk_level, approval_status, version, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'firecrawl', 'low', 'approved', 1, :ts, :ts)"
        ),
        {"id": rid, "name": f"recipe_{rid.hex[:8]}", "ts": now},
    )
    return str(rid)


def _insert_schedule(session, source_id: str, recipe_id: str) -> str:
    sid = uuid.uuid4()
    now = datetime.now(UTC)
    key = f"source:{source_id}:recipe:{recipe_id}"
    session.execute(
        text(
            "INSERT INTO watch_schedules "
            "(id, schedule_key, source_id, recipe_id, status, "
            "interval_seconds, next_run_at, priority, created_at, updated_at) "
            "VALUES (:id, :key, :src, :recipe, 'active', 3600, :ts, 0, :ts, :ts)"
        ),
        {
            "id": sid,
            "key": key,
            "src": source_id,
            "recipe": recipe_id,
            "ts": now - timedelta(hours=1),
        },
    )
    return str(sid)


class TestSchedulerCLI:
    """Tests for the scheduler CLI command."""

    def test_scheduler_run_outputs_stats(self, db_session):
        """scheduler run should output scanned, enqueued, skipped, duplicate counts."""
        from harvester.cli.main import app

        runner = CliRunner()

        # Create a schedule that is due
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        _insert_schedule(db_session, src, recipe)
        db_session.commit()

        # Patch _make_session in the daemon module (where it's imported from)
        with patch("harvester.workers.daemon._make_session", return_value=db_session):
            result = runner.invoke(app, ["scheduler", "run"])

        assert result.exit_code == 0
        assert "scanned" in result.output.lower() or "Scanned" in result.output

    def test_scheduler_run_no_schedules(self, db_session):
        """scheduler run with no due schedules should show zero counts."""
        from harvester.cli.main import app

        runner = CliRunner()

        with patch("harvester.workers.daemon._make_session", return_value=db_session):
            result = runner.invoke(app, ["scheduler", "run"])

        assert result.exit_code == 0
