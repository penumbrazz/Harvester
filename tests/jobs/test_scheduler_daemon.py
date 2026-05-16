"""Tests for the scheduler daemon loop — run_scheduler_loop.

Covers: loop calls run_scheduler_once each round, passes poll_interval/limit,
closes session per round, sleeps on empty scan, respects should_stop,
and handles single-round exceptions with rollback and continued operation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from harvester.jobs.scheduler import SchedulerResult


class TestSchedulerLoopBasic:
    """Tests for run_scheduler_loop core behavior."""

    def test_loop_calls_run_scheduler_once_each_round(self):
        """Each loop iteration calls run_scheduler_once."""
        from harvester.jobs.scheduler import run_scheduler_loop

        call_count = 0

        def fake_run_once(session, *, now, limit):
            nonlocal call_count
            call_count += 1
            return SchedulerResult(scanned=1, enqueued=1)

        mock_session = MagicMock()

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            side_effect=fake_run_once,
        ):
            run_scheduler_loop(
                lambda: mock_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: call_count >= 3,
            )

        assert call_count == 3

    def test_loop_passes_limit_to_run_once(self):
        """Loop passes the configured limit to run_scheduler_once."""
        from harvester.jobs.scheduler import run_scheduler_loop

        captured_limit = None
        done = {"n": False}

        def fake_run_once(session, *, now, limit):
            nonlocal captured_limit
            captured_limit = limit
            done["n"] = True
            return SchedulerResult(scanned=1, enqueued=1)

        mock_session = MagicMock()

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            side_effect=fake_run_once,
        ):
            run_scheduler_loop(
                lambda: mock_session,
                poll_interval=0,
                limit=42,
                should_stop=lambda: done["n"],
            )

        assert captured_limit == 42

    def test_loop_closes_session_each_round(self):
        """Each loop iteration creates and closes a session."""
        from harvester.jobs.scheduler import run_scheduler_loop

        sessions = []
        call_count = 0

        def make_session():
            s = MagicMock()
            sessions.append(s)
            return s

        def fake_run_once(session, *, now, limit):
            nonlocal call_count
            call_count += 1
            return SchedulerResult(scanned=1, enqueued=1)

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            side_effect=fake_run_once,
        ):
            run_scheduler_loop(
                make_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: call_count >= 2,
            )

        assert len(sessions) == 2
        for s in sessions:
            s.close.assert_called()

    def test_loop_sleeps_on_empty_scan(self):
        """Loop sleeps when run_scheduler_once scans zero schedules."""
        from harvester.jobs.scheduler import run_scheduler_loop

        sleep_times = []
        call_count = 0

        def fake_run_once(session, *, now, limit):
            nonlocal call_count
            call_count += 1
            return SchedulerResult(scanned=0, enqueued=0)

        mock_session = MagicMock()

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once", side_effect=fake_run_once
        ):
            with patch(
                "harvester.jobs.scheduler.time.sleep",
                side_effect=lambda s: sleep_times.append(s),
            ):
                run_scheduler_loop(
                    lambda: mock_session,
                    poll_interval=5,
                    limit=10,
                    should_stop=lambda: call_count >= 2,
                )

        assert len(sleep_times) == 2
        assert all(t == 5 for t in sleep_times)

    def test_loop_no_sleep_when_schedules_scanned(self):
        """Loop does NOT sleep when run_scheduler_once found schedules."""
        from harvester.jobs.scheduler import run_scheduler_loop

        sleep_times = []
        call_count = 0

        def fake_run_once(session, *, now, limit):
            nonlocal call_count
            call_count += 1
            return SchedulerResult(scanned=1, enqueued=1)

        mock_session = MagicMock()

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once", side_effect=fake_run_once
        ):
            with patch(
                "harvester.jobs.scheduler.time.sleep",
                side_effect=lambda s: sleep_times.append(s),
            ):
                run_scheduler_loop(
                    lambda: mock_session,
                    poll_interval=5,
                    limit=10,
                    should_stop=lambda: call_count >= 2,
                )

        assert len(sleep_times) == 0

    def test_loop_respects_should_stop_before_iteration(self):
        """Loop checks should_stop before each iteration and exits."""
        from harvester.jobs.scheduler import run_scheduler_loop

        call_count = 0

        def fake_run_once(session, *, now, limit):
            nonlocal call_count
            call_count += 1
            return SchedulerResult(scanned=1, enqueued=1)

        mock_session = MagicMock()

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once", side_effect=fake_run_once
        ):
            run_scheduler_loop(
                lambda: mock_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: True,
            )

        assert call_count == 0

    def test_loop_logs_scheduler_daemon_identity(self):
        """Loop logger identifies itself as scheduler daemon."""
        from harvester.jobs.scheduler import run_scheduler_loop

        done = {"n": False}

        def fake_run_once(session, *, now, limit):
            done["n"] = True
            return SchedulerResult(scanned=3, enqueued=2, skipped=1)

        mock_session = MagicMock()

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once", side_effect=fake_run_once
        ):
            with patch("harvester.jobs.scheduler.logger") as mock_logger:
                run_scheduler_loop(
                    lambda: mock_session,
                    poll_interval=0,
                    limit=10,
                    should_stop=lambda: done["n"],
                )

                mock_logger.info.assert_called()


class TestSchedulerLoopErrorHandling:
    """Tests for run_scheduler_loop error handling."""

    def test_exception_rolls_back_and_closes_session(self):
        """On exception, loop rolls back and closes the session."""
        from harvester.jobs.scheduler import run_scheduler_loop

        mock_session = MagicMock()
        raised = {"n": False}

        def fake_run_once(session, *, now, limit):
            raised["n"] = True
            raise RuntimeError("DB connection lost")

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            side_effect=fake_run_once,
        ):
            run_scheduler_loop(
                lambda: mock_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: raised["n"],
            )

        mock_session.rollback.assert_called()
        mock_session.close.assert_called()

    def test_exception_continues_to_next_round(self):
        """After an exception, the loop continues to the next round."""
        from harvester.jobs.scheduler import run_scheduler_loop

        call_count = 0

        def fake_run_once(session, *, now, limit):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient failure")
            return SchedulerResult(scanned=1, enqueued=1)

        mock_session = MagicMock()

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            side_effect=fake_run_once,
        ):
            run_scheduler_loop(
                lambda: mock_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: call_count >= 2,
            )

        assert call_count == 2

    def test_exception_logs_error(self):
        """Loop logs the exception as an error."""
        from harvester.jobs.scheduler import run_scheduler_loop

        mock_session = MagicMock()
        raised = {"n": False}

        def fake_run_once(session, *, now, limit):
            raised["n"] = True
            raise RuntimeError("test error")

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            side_effect=fake_run_once,
        ):
            with patch("harvester.jobs.scheduler.logger") as mock_logger:
                run_scheduler_loop(
                    lambda: mock_session,
                    poll_interval=0,
                    limit=10,
                    should_stop=lambda: raised["n"],
                )

                mock_logger.error.assert_called()
                error_args = mock_logger.error.call_args
                assert "test error" in str(error_args)

    def test_exception_creates_new_session_next_round(self):
        """After exception, loop creates a fresh session for the next round."""
        from harvester.jobs.scheduler import run_scheduler_loop

        sessions = []
        call_count = 0

        def make_session():
            s = MagicMock()
            sessions.append(s)
            return s

        def fake_run_once(session, *, now, limit):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("fail first round")
            return SchedulerResult(scanned=1, enqueued=1)

        with patch(
            "harvester.jobs.scheduler.run_scheduler_once",
            side_effect=fake_run_once,
        ):
            run_scheduler_loop(
                make_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: call_count >= 2,
            )

        assert len(sessions) == 2
        for s in sessions:
            s.close.assert_called()
