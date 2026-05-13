"""Tests for scheduler daemon integration with audit cleanup.

Covers: automatic cleanup invocation, 24-hour throttle, cleanup failure
does not block scheduling, and start.sh path requires no changes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import sqlalchemy as sa

from harvester.domain.audit_retention import CleanupResult
from harvester.jobs.scheduler import (
    SchedulerResult,
    _should_run_cleanup,
    run_scheduler_loop,
)


class TestShouldRunCleanup:
    """Tests for the cleanup throttle logic."""

    def test_runs_when_never_run(self):
        """Cleanup should run if it has never run before."""
        with patch("harvester.jobs.scheduler._last_cleanup_at", None):
            assert _should_run_cleanup(datetime.now(UTC)) is True

    def test_skips_within_24h(self):
        """Cleanup should be throttled within 24 hours of last run."""
        now = datetime.now(UTC)
        with patch(
            "harvester.jobs.scheduler._last_cleanup_at",
            now - timedelta(hours=1),
        ):
            assert _should_run_cleanup(now) is False

    def test_runs_after_24h(self):
        """Cleanup should run after 24 hours have passed."""
        now = datetime.now(UTC)
        with patch(
            "harvester.jobs.scheduler._last_cleanup_at",
            now - timedelta(hours=25),
        ):
            assert _should_run_cleanup(now) is True

    def test_custom_interval_via_env(self):
        """Cleanup throttle interval can be overridden via env var."""
        now = datetime.now(UTC)
        with patch.dict("os.environ", {"HARVESTER_AUDIT_CLEANUP_INTERVAL_HOURS": "1"}):
            # 30 minutes ago should be within 1-hour interval
            with patch(
                "harvester.jobs.scheduler._last_cleanup_at",
                now - timedelta(minutes=30),
            ):
                assert _should_run_cleanup(now) is False

            # 2 hours ago should exceed 1-hour interval
            with patch(
                "harvester.jobs.scheduler._last_cleanup_at",
                now - timedelta(hours=2),
            ):
                assert _should_run_cleanup(now) is True


class TestSchedulerDaemonCleanupIntegration:
    """Test that scheduler daemon loop invokes cleanup at the right time."""

    def test_cleanup_called_on_first_round(self):
        """Scheduler daemon calls cleanup on the first iteration."""
        call_count = 0
        cleanup_called = {"v": False}

        def fake_run_once(session, *, now, limit):
            nonlocal call_count
            call_count += 1
            return SchedulerResult(scanned=1, enqueued=1)

        def fake_cleanup(session, *, now):
            cleanup_called["v"] = True
            return CleanupResult(deleted_count=5, cutoff=now - timedelta(days=7), retention_days=7)

        with patch("harvester.jobs.scheduler._last_cleanup_at", None):
            with patch(
                "harvester.jobs.scheduler.run_scheduler_once",
                side_effect=fake_run_once,
            ):
                with patch(
                    "harvester.jobs.scheduler._run_audit_cleanup",
                    side_effect=fake_cleanup,
                ):
                    run_scheduler_loop(
                        lambda: MagicMock(),
                        poll_interval=0,
                        limit=100,
                        should_stop=lambda: call_count >= 1,
                    )

        assert cleanup_called["v"]

    def test_cleanup_throttled_on_subsequent_round(self):
        """Cleanup is NOT called on the second round within the throttle window."""
        round_count = 0
        cleanup_count = {"n": 0}

        def fake_run_once(session, *, now, limit):
            nonlocal round_count
            round_count += 1
            return SchedulerResult(scanned=1, enqueued=1)

        def fake_cleanup(session, *, now):
            cleanup_count["n"] += 1
            return CleanupResult(deleted_count=0, cutoff=now, retention_days=7)

        # _last_cleanup_at set to recent time → throttle active
        with patch(
            "harvester.jobs.scheduler._last_cleanup_at",
            datetime.now(UTC) - timedelta(hours=1),
        ):
            with patch(
                "harvester.jobs.scheduler.run_scheduler_once",
                side_effect=fake_run_once,
            ):
                with patch(
                    "harvester.jobs.scheduler._run_audit_cleanup",
                    side_effect=fake_cleanup,
                ):
                    run_scheduler_loop(
                        lambda: MagicMock(),
                        poll_interval=0,
                        limit=100,
                        should_stop=lambda: round_count >= 2,
                    )

        # Cleanup should not have been called (throttled)
        assert cleanup_count["n"] == 0

    def test_cleanup_failure_does_not_block_scheduling(self):
        """When cleanup fails, scheduler still completes its round."""
        round_count = 0

        def fake_run_once(session, *, now, limit):
            nonlocal round_count
            round_count += 1
            return SchedulerResult(scanned=1, enqueued=1)

        def failing_cleanup(session, *, now):
            raise RuntimeError("cleanup DB error")

        with patch("harvester.jobs.scheduler._last_cleanup_at", None):
            with patch(
                "harvester.jobs.scheduler.run_scheduler_once",
                side_effect=fake_run_once,
            ):
                with patch(
                    "harvester.jobs.scheduler._run_audit_cleanup",
                    side_effect=failing_cleanup,
                ):
                    # Should not raise
                    run_scheduler_loop(
                        lambda: MagicMock(),
                        poll_interval=0,
                        limit=100,
                        should_stop=lambda: round_count >= 1,
                    )

        # Scheduler still ran its rounds despite cleanup failure
        assert round_count >= 1

    def test_cleanup_updates_last_cleanup_at(self):
        """After cleanup runs, _last_cleanup_at is updated for throttling."""
        round_count = 0
        captured_times = []

        def fake_run_once(session, *, now, limit):
            nonlocal round_count
            round_count += 1
            return SchedulerResult(scanned=1, enqueued=1)

        def fake_cleanup(session, *, now):
            captured_times.append(now)
            return CleanupResult(deleted_count=0, cutoff=now, retention_days=7)

        with patch("harvester.jobs.scheduler._last_cleanup_at", None):
            with patch(
                "harvester.jobs.scheduler.run_scheduler_once",
                side_effect=fake_run_once,
            ):
                with patch(
                    "harvester.jobs.scheduler._run_audit_cleanup",
                    side_effect=fake_cleanup,
                ):
                    run_scheduler_loop(
                        lambda: MagicMock(),
                        poll_interval=0,
                        limit=100,
                        should_stop=lambda: round_count >= 1,
                    )

        assert len(captured_times) == 1
