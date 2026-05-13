"""Tests for the scheduler daemon CLI command.

Covers: harvester scheduler daemon --poll-interval --limit argument passing,
startup message, and one-shot harvester scheduler run behavior unchanged.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from harvester.cli.main import app

runner = CliRunner()


class TestSchedulerDaemonCLI:
    """Tests for the 'scheduler daemon' CLI command."""

    @patch("harvester.jobs.scheduler.run_scheduler_loop")
    @patch("harvester.workers.daemon._make_session")
    def test_daemon_passes_poll_interval(self, mock_session, mock_loop):
        """'scheduler daemon --poll-interval 5' passes poll_interval=5."""
        mock_session.return_value = MagicMock()

        result = runner.invoke(
            app, ["scheduler", "daemon", "--poll-interval", "5"]
        )

        assert result.exit_code == 0
        mock_loop.assert_called_once()
        assert mock_loop.call_args.kwargs["poll_interval"] == 5

    @patch("harvester.jobs.scheduler.run_scheduler_loop")
    @patch("harvester.workers.daemon._make_session")
    def test_daemon_passes_limit(self, mock_session, mock_loop):
        """'scheduler daemon --limit 20' passes limit=20."""
        mock_session.return_value = MagicMock()

        result = runner.invoke(
            app, ["scheduler", "daemon", "--limit", "20"]
        )

        assert result.exit_code == 0
        mock_loop.assert_called_once()
        assert mock_loop.call_args.kwargs["limit"] == 20

    @patch("harvester.jobs.scheduler.run_scheduler_loop")
    @patch("harvester.workers.daemon._make_session")
    def test_daemon_default_poll_interval(self, mock_session, mock_loop):
        """'scheduler daemon' uses default poll interval."""
        mock_session.return_value = MagicMock()

        result = runner.invoke(app, ["scheduler", "daemon"])

        assert result.exit_code == 0
        mock_loop.assert_called_once()
        assert mock_loop.call_args.kwargs["poll_interval"] == 30

    @patch("harvester.jobs.scheduler.run_scheduler_loop")
    @patch("harvester.workers.daemon._make_session")
    def test_daemon_shows_startup_message(self, mock_session, mock_loop):
        """'scheduler daemon' outputs a startup message identifying the daemon."""
        mock_session.return_value = MagicMock()

        result = runner.invoke(app, ["scheduler", "daemon"])

        assert result.exit_code == 0
        assert "scheduler daemon" in result.output.lower()


class TestSchedulerRunUnchanged:
    """Verify one-shot 'scheduler run' is unchanged by the daemon addition."""

    @patch("harvester.workers.daemon._make_session")
    def test_scheduler_run_still_works(self, mock_session):
        """'scheduler run' one-shot command still produces output."""
        from harvester.jobs.scheduler import SchedulerResult

        mock_sess = MagicMock()
        mock_session.return_value = mock_sess

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            return_value=SchedulerResult(scanned=1, enqueued=1),
        ):
            result = runner.invoke(app, ["scheduler", "run"])

        assert result.exit_code == 0
        assert "scanned" in result.output.lower() or "Scanned" in result.output

    @patch("harvester.workers.daemon._make_session")
    def test_scheduler_run_no_daemon_message(self, mock_session):
        """'scheduler run' does NOT show daemon startup message."""
        from harvester.jobs.scheduler import SchedulerResult

        mock_sess = MagicMock()
        mock_session.return_value = mock_sess

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            return_value=SchedulerResult(scanned=0, enqueued=0),
        ):
            result = runner.invoke(app, ["scheduler", "run"])

        assert result.exit_code == 0
        assert "starting scheduler daemon" not in result.output.lower()
