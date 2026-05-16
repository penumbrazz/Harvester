"""Tests to verify CLI schedule command uses HTTP API, not direct DB access.

The CLI MUST NOT create database sessions directly for schedule creation —
all state changes go through the HTTP API.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestScheduleCLIHttpOnly:
    """CLI schedule command must use HTTP API, never direct DB session."""

    def test_schedule_create_calls_http_api(self):
        """CLI schedule create should POST to /schedules via httpx."""
        from typer.testing import CliRunner

        runner = CliRunner()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "sched-123",
            "schedule_key": "source:abc:recipe:def",
            "source_id": "abc",
            "recipe_id": "def",
            "status": "active",
            "interval_seconds": 3600,
            "next_run_at": "2026-05-10T12:00:00Z",
            "last_enqueued_at": None,
            "priority": 0,
            "lane": None,
            "created_at": "2026-05-10T12:00:00Z",
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            from harvester.cli.main import app

            result = runner.invoke(
                app,
                [
                    "schedule",
                    "create",
                    "--source-id",
                    "abc",
                    "--recipe-id",
                    "def",
                    "--interval",
                    "3600",
                ],
            )

        assert mock_post.called

    def test_schedule_create_does_not_import_db_session(self):
        """CLI schedule command module should not import db session directly."""
        cli_path = Path(__file__).parent.parent.parent / "harvester" / "cli" / "main.py"
        source = cli_path.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.ImportFrom, ast.Import)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "db" in node.module and "session" in str(
                        [alias.name for alias in (node.names or [])]
                    ):
                        pytest.fail(f"CLI imports database session from {node.module}")

    def test_schedule_create_output_contains_id(self):
        """CLI should output schedule id on success."""
        from typer.testing import CliRunner

        runner = CliRunner()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "sched-123",
            "schedule_key": "source:abc:recipe:def",
            "source_id": "abc",
            "recipe_id": "def",
            "status": "active",
            "interval_seconds": 3600,
            "next_run_at": "2026-05-10T12:00:00Z",
            "last_enqueued_at": None,
            "priority": 0,
            "lane": None,
            "created_at": "2026-05-10T12:00:00Z",
        }

        with patch("httpx.post", return_value=mock_response):
            from harvester.cli.main import app

            result = runner.invoke(
                app,
                [
                    "schedule",
                    "create",
                    "--source-id",
                    "abc",
                    "--recipe-id",
                    "def",
                    "--interval",
                    "3600",
                ],
            )

        assert "sched-123" in result.output

    def test_schedule_create_passes_ids_in_request(self):
        """CLI should pass source_id, recipe_id, interval_seconds in POST body."""
        from typer.testing import CliRunner

        runner = CliRunner()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "sched-123",
            "schedule_key": "source:abc:recipe:def",
            "source_id": "abc",
            "recipe_id": "def",
            "status": "active",
            "interval_seconds": 3600,
            "next_run_at": "2026-05-10T12:00:00Z",
            "last_enqueued_at": None,
            "priority": 0,
            "lane": None,
            "created_at": "2026-05-10T12:00:00Z",
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            from harvester.cli.main import app

            result = runner.invoke(
                app,
                [
                    "schedule",
                    "create",
                    "--source-id",
                    "source-uuid",
                    "--recipe-id",
                    "recipe-uuid",
                    "--interval",
                    "1800",
                ],
            )

        call_args = mock_post.call_args
        assert call_args is not None
        json_body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_body["source_id"] == "source-uuid"
        assert json_body["recipe_id"] == "recipe-uuid"
        assert json_body["interval_seconds"] == 1800

    def test_schedule_create_with_topic_watch_id(self):
        """CLI should pass optional topic_watch_id when provided."""
        from typer.testing import CliRunner

        runner = CliRunner()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "sched-456",
            "schedule_key": "topic:tw1:source:abc:recipe:def",
            "source_id": "abc",
            "topic_watch_id": "tw1",
            "recipe_id": "def",
            "status": "active",
            "interval_seconds": 1800,
            "next_run_at": "2026-05-10T12:00:00Z",
            "last_enqueued_at": None,
            "priority": 0,
            "lane": None,
            "created_at": "2026-05-10T12:00:00Z",
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            from harvester.cli.main import app

            result = runner.invoke(
                app,
                [
                    "schedule",
                    "create",
                    "--source-id",
                    "source-uuid",
                    "--topic-watch-id",
                    "topic-uuid",
                    "--recipe-id",
                    "recipe-uuid",
                    "--interval",
                    "1800",
                ],
            )

        call_args = mock_post.call_args
        assert call_args is not None
        json_body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_body["topic_watch_id"] == "topic-uuid"
