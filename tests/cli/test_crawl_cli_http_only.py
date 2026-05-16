"""Tests to verify CLI crawl command uses HTTP API, not direct DB access.

The CLI MUST NOT create database sessions directly — all state changes
go through the HTTP API.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCrawlCLIHttpOnly:
    """CLI crawl command must use HTTP API, never direct DB session."""

    def test_crawl_run_calls_http_api(self):
        """CLI crawl run should POST to /crawl/run via httpx."""
        from typer.testing import CliRunner

        runner = CliRunner()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "crawl_run_id": "abc-123",
            "status": "completed",
            "raw_object_id": "def-456",
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            from harvester.cli.main import app

            result = runner.invoke(
                app,
                ["crawl", "run", "--source-id", "test-id", "--recipe-id", "test-id"],
            )

        # Should have made an HTTP POST
        assert mock_post.called

    def test_crawl_run_does_not_import_db_session(self):
        """CLI crawl command module should not import db session directly."""
        import ast
        from pathlib import Path

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

    def test_crawl_run_output_contains_ids(self):
        """CLI should output crawl_run_id, status, and raw_object_id."""
        from typer.testing import CliRunner

        runner = CliRunner()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "crawl_run_id": "abc-123",
            "status": "completed",
            "raw_object_id": "def-456",
        }

        with patch("httpx.post", return_value=mock_response):
            from harvester.cli.main import app

            result = runner.invoke(
                app,
                ["crawl", "run", "--source-id", "test-id", "--recipe-id", "test-id"],
            )

        assert "abc-123" in result.output or "completed" in result.output

    def test_crawl_run_passes_ids_in_request(self):
        """CLI should pass source_id and recipe_id in the POST body."""
        from typer.testing import CliRunner

        runner = CliRunner()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "crawl_run_id": "abc-123",
            "status": "completed",
            "raw_object_id": "def-456",
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            from harvester.cli.main import app

            result = runner.invoke(
                app,
                [
                    "crawl",
                    "run",
                    "--source-id",
                    "source-uuid",
                    "--recipe-id",
                    "recipe-uuid",
                ],
            )

        # Verify the POST was called with correct payload
        call_args = mock_post.call_args
        assert call_args is not None
        json_body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_body["source_id"] == "source-uuid"
        assert json_body["recipe_id"] == "recipe-uuid"
