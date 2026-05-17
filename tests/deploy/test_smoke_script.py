"""Tests for scripts/smoke.sh — verify the smoke test script exists and has required content."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
SMOKE_SCRIPT = PROJECT_ROOT / "scripts" / "smoke.sh"


class TestSmokeScript:
    """Verify scripts/smoke.sh exists with required commands."""

    def test_smoke_script_exists(self):
        """The smoke.sh script must exist."""
        assert SMOKE_SCRIPT.is_file(), f"smoke.sh not found at {SMOKE_SCRIPT}"

    def test_smoke_script_is_executable(self):
        """The smoke.sh script must be executable."""
        assert os.access(SMOKE_SCRIPT, os.X_OK), "smoke.sh must be executable"

    def test_contains_migration_command(self):
        """The smoke.sh script must contain a database migration command."""
        content = SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "alembic" in content.lower() or "migration" in content.lower(), (
            "smoke.sh must contain an Alembic migration command"
        )

    def test_contains_healthcheck_command(self):
        """The smoke.sh script must contain a healthcheck command."""
        content = SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "health" in content.lower() or "curl" in content.lower(), (
            "smoke.sh must contain a healthcheck command"
        )

    def test_contains_compose_config_validation(self):
        """The smoke.sh script must validate docker compose config."""
        content = SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "docker compose" in content and "config" in content, (
            "smoke.sh must validate docker compose config"
        )
