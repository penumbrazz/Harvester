"""Tests for .env.example — verify it contains all required configuration placeholders."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"


class TestEnvExample:
    """Verify .env.example file exists and contains required placeholders."""

    def test_env_example_exists(self):
        """The .env.example file must exist in the project root."""
        assert ENV_EXAMPLE.is_file(), f".env.example not found at {ENV_EXAMPLE}"

    def test_contains_database_url_placeholder(self):
        """The .env.example must contain HARVESTER_DATABASE_URL."""
        content = ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "HARVESTER_DATABASE_URL" in content

    def test_contains_api_token_placeholder(self):
        """The .env.example must contain HARVESTER_API_TOKEN."""
        content = ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "HARVESTER_API_TOKEN" in content

    def test_contains_archive_path_placeholder(self):
        """The .env.example must contain HARVESTER_ARCHIVE_PATH."""
        content = ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "HARVESTER_ARCHIVE_PATH" in content

    def test_contains_firecrawl_url_placeholder(self):
        """The .env.example must contain FIRECRAWL_API_URL."""
        content = ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "FIRECRAWL_API_URL" in content

    def test_contains_model_worker_url_placeholder(self):
        """The .env.example must contain HARVESTER_MODEL_WORKER_URL."""
        content = ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "HARVESTER_MODEL_WORKER_URL" in content
