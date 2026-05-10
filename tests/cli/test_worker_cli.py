"""Tests for the worker CLI commands — verify worker once and worker run."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from harvester.cli.main import app

runner = CliRunner()


class TestWorkerOnce:
    """Tests for the 'worker once' CLI command."""

    @patch("harvester.workers.daemon.run_once")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_once_calls_run_once(self, mock_session, mock_run_once):
        """'harvester worker once --limit 1' calls run_once with limit=1."""
        mock_session.return_value = MagicMock()
        mock_run_once.return_value = {"claimed": 1, "completed": 1, "failed": 0}

        result = runner.invoke(app, ["worker", "once", "--limit", "1"])

        assert result.exit_code == 0
        mock_run_once.assert_called_once()
        assert mock_run_once.call_args.kwargs["limit"] == 1

    @patch("harvester.workers.daemon.run_once")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_once_outputs_stats(self, mock_session, mock_run_once):
        """'harvester worker once' outputs processing statistics."""
        mock_session.return_value = MagicMock()
        mock_run_once.return_value = {"claimed": 2, "completed": 2, "failed": 0}

        result = runner.invoke(app, ["worker", "once", "--limit", "2"])

        assert result.exit_code == 0
        assert "claimed=2" in result.output
        assert "completed=2" in result.output


class TestWorkerRun:
    """Tests for the 'worker run' CLI command."""

    @patch("harvester.workers.daemon.run_loop")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_run_passes_poll_interval(self, mock_session, mock_run_loop):
        """'harvester worker run --poll-interval 5' passes poll_interval=5."""
        mock_session.return_value = MagicMock()

        result = runner.invoke(app, ["worker", "run", "--poll-interval", "5"])

        assert result.exit_code == 0
        mock_run_loop.assert_called_once()
        assert mock_run_loop.call_args.kwargs["poll_interval"] == 5

    @patch("harvester.workers.daemon.run_loop")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_run_default_poll_interval(self, mock_session, mock_run_loop):
        """'harvester worker run' uses default poll interval."""
        mock_session.return_value = MagicMock()

        result = runner.invoke(app, ["worker", "run"])

        assert result.exit_code == 0
        mock_run_loop.assert_called_once()
        assert mock_run_loop.call_args.kwargs["poll_interval"] == 10
