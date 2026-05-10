"""Tests to verify CLI search command uses HTTP API, not direct DB access."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from harvester.cli.main import app

runner = CliRunner()


class TestSearchCLIHttpOnly:
    """CLI search command must use HTTP API, never direct DB session."""

    @patch("httpx.get")
    def test_search_calls_http_get(self, mock_get):
        """CLI search should GET /items/search via httpx."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        runner.invoke(app, ["search", "Python"])

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "/items/search" in call_url

    @patch("httpx.get")
    def test_search_passes_q_param(self, mock_get):
        """CLI search should pass q=Python as query parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        runner.invoke(app, ["search", "Python"])

        assert mock_get.called
        call_kwargs = mock_get.call_args.kwargs
        params = call_kwargs.get("params", {})
        assert params.get("q") == "Python"

    @patch("httpx.get")
    def test_search_passes_source_id_param(self, mock_get):
        """CLI should pass --source-id as query parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        runner.invoke(app, ["search", "Python", "--source-id", "src-uuid-123"])

        params = mock_get.call_args.kwargs.get("params", {})
        assert params.get("source_id") == "src-uuid-123"

    @patch("httpx.get")
    def test_search_passes_topic_watch_id_param(self, mock_get):
        """CLI should pass --topic-watch-id as query parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        runner.invoke(app, ["search", "Python", "--topic-watch-id", "tw-uuid-456"])

        params = mock_get.call_args.kwargs.get("params", {})
        assert params.get("topic_watch_id") == "tw-uuid-456"

    @patch("httpx.get")
    def test_search_passes_limit_and_offset(self, mock_get):
        """CLI should pass --limit and --offset as query parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        runner.invoke(app, ["search", "Python", "--limit", "5", "--offset", "10"])

        params = mock_get.call_args.kwargs.get("params", {})
        assert params.get("limit") == 5
        assert params.get("offset") == 10

    @patch("httpx.get")
    def test_search_outputs_title_and_ids(self, mock_get):
        """CLI should output title, item id, version id and source id."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "item_id": "item-001",
                    "version_id": "ver-001",
                    "source_id": "src-001",
                    "title": "Python Async Guide",
                    "canonical_url": "https://example.com/py",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ]
        }
        mock_get.return_value = mock_response

        result = runner.invoke(app, ["search", "Python"])

        assert "Python Async Guide" in result.output
        assert "item-001" in result.output
        assert "ver-001" in result.output
        assert "src-001" in result.output

    @patch("httpx.get")
    def test_search_outputs_no_results_message(self, mock_get):
        """CLI should show message when no results found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        result = runner.invoke(app, ["search", "nonexistent"])

        assert "No results" in result.output or "no results" in result.output.lower()

    @patch("httpx.get")
    def test_search_handles_api_error(self, mock_get):
        """CLI should exit with code 1 on non-200 API response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        result = runner.invoke(app, ["search", "Python"])

        assert result.exit_code == 1

    def test_search_does_not_import_db_session(self):
        """CLI module should not import db session directly."""
        cli_path = Path(__file__).parent.parent.parent / "harvester" / "cli" / "main.py"
        source = cli_path.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.ImportFrom, ast.Import)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "db" in node.module and "session" in str(
                        [alias.name for alias in (node.names or [])]
                    ):
                        pytest.fail(
                            f"CLI imports database session from {node.module}"
                        )
