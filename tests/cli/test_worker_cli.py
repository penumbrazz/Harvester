"""Tests for the worker CLI commands — verify worker once and worker run."""

import os
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

    @patch("harvester.workers.daemon.run_once")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_once_uses_stub_adapter_by_default(
        self, mock_session, mock_run_once
    ):
        """Worker once uses StubModelAdapter when no adapter is configured."""
        from harvester.adapters.stub_model import StubModelAdapter

        mock_session.return_value = MagicMock()
        mock_run_once.return_value = {"claimed": 0, "completed": 0, "failed": 0}

        result = runner.invoke(app, ["worker", "once", "--limit", "1"])

        assert result.exit_code == 0
        call_args = mock_run_once.call_args
        assert isinstance(call_args.args[1], StubModelAdapter)

    @patch("harvester.workers.daemon.run_once")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_once_default_model_name_is_stub(
        self, mock_session, mock_run_once
    ):
        """Worker once passes stub model name by default."""
        mock_session.return_value = MagicMock()
        mock_run_once.return_value = {"claimed": 0, "completed": 0, "failed": 0}

        result = runner.invoke(app, ["worker", "once", "--limit", "1"])

        assert result.exit_code == 0
        call_args = mock_run_once.call_args
        assert call_args.args[2] == "stub-embedding-1536"


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

    @patch("harvester.workers.daemon.run_loop")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_run_uses_stub_adapter_by_default(
        self, mock_session, mock_run_loop
    ):
        """Worker run uses StubModelAdapter when no adapter is configured."""
        from harvester.adapters.stub_model import StubModelAdapter

        mock_session.return_value = MagicMock()

        result = runner.invoke(app, ["worker", "run"])

        assert result.exit_code == 0
        call_args = mock_run_loop.call_args
        assert isinstance(call_args.args[1], StubModelAdapter)


class TestWorkerCLIWithQwenConfig:
    """Worker CLI uses QwenEmbeddingAdapter when configured."""

    @patch("harvester.workers.daemon.run_once")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_once_uses_qwen_adapter_when_configured(
        self, mock_session, mock_run_once
    ):
        """Worker once uses QwenEmbeddingAdapter when HARVESTER_EMBEDDING_ADAPTER=qwen."""
        from harvester.adapters.qwen_embedding import QwenEmbeddingAdapter

        mock_session.return_value = MagicMock()
        mock_run_once.return_value = {"claimed": 0, "completed": 0, "failed": 0}

        with patch.dict(
            os.environ,
            {
                "HARVESTER_EMBEDDING_ADAPTER": "qwen",
                "HARVESTER_EMBEDDING_MODEL": "text-embedding-v3",
                "HARVESTER_QWEN_EMBEDDING_BASE_URL": "http://localhost:8080",
            },
        ):
            result = runner.invoke(app, ["worker", "once", "--limit", "1"])

        assert result.exit_code == 0
        call_args = mock_run_once.call_args
        assert isinstance(call_args.args[1], QwenEmbeddingAdapter)
        assert call_args.args[2] == "text-embedding-v3"

    @patch("harvester.workers.daemon.run_loop")
    @patch("harvester.workers.daemon._make_session")
    def test_worker_run_uses_qwen_adapter_when_configured(
        self, mock_session, mock_run_loop
    ):
        """Worker run uses QwenEmbeddingAdapter when HARVESTER_EMBEDDING_ADAPTER=qwen."""
        from harvester.adapters.qwen_embedding import QwenEmbeddingAdapter

        mock_session.return_value = MagicMock()

        with patch.dict(
            os.environ,
            {
                "HARVESTER_EMBEDDING_ADAPTER": "qwen",
                "HARVESTER_EMBEDDING_MODEL": "text-embedding-v3",
                "HARVESTER_QWEN_EMBEDDING_BASE_URL": "http://localhost:8080",
            },
        ):
            result = runner.invoke(app, ["worker", "run"])

        assert result.exit_code == 0
        call_args = mock_run_loop.call_args
        assert isinstance(call_args.args[1], QwenEmbeddingAdapter)
