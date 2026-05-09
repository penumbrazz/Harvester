"""Tests for CLI commands — verify they use httpx for HTTP requests."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from harvester.cli.main import app

runner = CliRunner()


class TestHealthCommand:
    """Tests for the 'health' CLI command."""

    @patch("httpx.get")
    def test_health_calls_httpx_get(self, mock_get):
        """CLI health command should call httpx.get, not a database session."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        # Act — single-command Typer app, no subcommand name needed
        result = runner.invoke(app, [])

        # Assert
        assert result.exit_code == 0
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "/health" in call_args[0][0]

    @patch("httpx.get")
    def test_health_uses_configured_base_url(self, mock_get):
        """CLI health should use the --base-url option."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        # Act
        result = runner.invoke(app, ["--base-url", "http://custom:9999"])

        # Assert
        assert result.exit_code == 0
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert call_url == "http://custom:9999/health"

    @patch("httpx.get")
    def test_health_reports_unhealthy_on_non_200(self, mock_get):
        """CLI health should exit with code 1 on non-200 status."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        # Act
        result = runner.invoke(app, [])

        # Assert
        assert result.exit_code == 1

    @patch("httpx.get")
    def test_health_handles_connection_error(self, mock_get):
        """CLI health should exit with code 1 on connection failure."""
        # Arrange
        import httpx

        mock_get.side_effect = httpx.ConnectError("Connection refused")

        # Act
        result = runner.invoke(app, [])

        # Assert
        assert result.exit_code == 1
