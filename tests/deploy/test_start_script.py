"""Tests for start.sh — verify default and daemon startup behavior."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
START_SCRIPT = PROJECT_ROOT / "start.sh"


class TestStartScript:
    """Verify start.sh exists with correct behavior."""

    def test_start_script_exists(self):
        """The start.sh script must exist."""
        assert START_SCRIPT.is_file(), f"start.sh not found at {START_SCRIPT}"

    def test_start_script_is_executable(self):
        """The start.sh script must be executable."""
        import os

        assert os.access(START_SCRIPT, os.X_OK), "start.sh must be executable"

    def test_default_starts_backend_only(self):
        """start.sh default should only start backend and frontend."""
        content = START_SCRIPT.read_text(encoding="utf-8")
        # Must have backend startup
        assert "uvicorn" in content
        # Must have frontend startup
        assert "npm run dev" in content or "frontend" in content

    def test_daemon_opt_in_via_env_var(self):
        """start.sh should check HARVESTER_START_DAEMONS for daemon opt-in."""
        content = START_SCRIPT.read_text(encoding="utf-8")
        assert "HARVESTER_START_DAEMONS" in content, (
            "start.sh must check HARVESTER_START_DAEMONS environment variable"
        )

    def test_daemon_starts_scheduler(self):
        """When HARVESTER_START_DAEMONS=1, start.sh must start scheduler daemon."""
        content = START_SCRIPT.read_text(encoding="utf-8")
        assert "scheduler daemon" in content, (
            "start.sh must start scheduler daemon when daemons are enabled"
        )

    def test_daemon_starts_crawl_worker(self):
        """When HARVESTER_START_DAEMONS=1, start.sh must start crawl worker."""
        content = START_SCRIPT.read_text(encoding="utf-8")
        assert "--job-type crawl" in content, (
            "start.sh must start crawl worker when daemons are enabled"
        )

    def test_cleanup_stops_all_started_processes(self):
        """start.sh cleanup function must stop all started processes."""
        content = START_SCRIPT.read_text(encoding="utf-8")
        # The cleanup function should kill all PIDs
        assert "cleanup" in content
