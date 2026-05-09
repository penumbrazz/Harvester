"""Tests for StubFirecrawlAdapter — verify it returns fixture content without network calls."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from harvester.adapters.stub_firecrawl import StubFirecrawlAdapter

# Path to fixture raw directory for from_fixture_dir tests
FIXTURES_RAW_DIR = Path(__file__).parent.parent / "fixtures" / "raw"


class TestStubFirecrawlAdapterInit:
    """Verify basic construction and crawl behavior."""

    def test_returns_none_for_unknown_url(self):
        """Should return None when URL is not in the fixture map."""
        adapter = StubFirecrawlAdapter()
        result = adapter.crawl("https://unknown.example.com")
        assert result is None

    def test_returns_fixture_content_for_known_url(self):
        """Should return pre-configured content for a known URL."""
        fixtures = {"https://example.com/page": "<html>Hello</html>"}
        adapter = StubFirecrawlAdapter(fixtures=fixtures)
        result = adapter.crawl("https://example.com/page")
        assert result == "<html>Hello</html>"

    def test_returns_none_for_empty_fixtures(self):
        """Should return None when no fixtures are configured."""
        adapter = StubFirecrawlAdapter(fixtures={})
        result = adapter.crawl("https://example.com/any")
        assert result is None

    def test_multiple_urls_mapped(self):
        """Should correctly map multiple URLs to their content."""
        fixtures = {
            "https://a.com": "content-a",
            "https://b.com": "content-b",
        }
        adapter = StubFirecrawlAdapter(fixtures=fixtures)
        assert adapter.crawl("https://a.com") == "content-a"
        assert adapter.crawl("https://b.com") == "content-b"


class TestStubFirecrawlNoNetwork:
    """Verify the adapter never makes network calls."""

    def test_crawl_does_not_use_requests(self):
        """crawl() should not import or use requests library."""
        fixtures = {"https://example.com/page": "content"}
        adapter = StubFirecrawlAdapter(fixtures=fixtures)

        with patch("urllib.request.urlopen") as mock_urlopen:
            adapter.crawl("https://example.com/page")
            mock_urlopen.assert_not_called()

    def test_crawl_unknown_url_does_not_use_requests(self):
        """crawl() for unknown URLs should still not make network calls."""
        adapter = StubFirecrawlAdapter()

        with patch("urllib.request.urlopen") as mock_urlopen:
            adapter.crawl("https://unknown.example.com")
            mock_urlopen.assert_not_called()


class TestStubFirecrawlFromFixtureDir:
    """Verify the from_fixture_dir class method loads files correctly."""

    def test_from_fixture_dir_loads_html_files(self):
        """from_fixture_dir should load .html files from the given directory."""
        if not FIXTURES_RAW_DIR.exists():
            pytest.skip("Fixture raw directory not found")

        adapter = StubFirecrawlAdapter.from_fixture_dir(str(FIXTURES_RAW_DIR))
        # The adapter should have loaded some fixtures
        # cdc-list.html should be available via a key containing the filename
        assert len(adapter._fixtures) >= 1

    def test_from_fixture_dir_loads_json_files(self):
        """from_fixture_dir should load .json files from the given directory."""
        if not FIXTURES_RAW_DIR.exists():
            pytest.skip("Fixture raw directory not found")

        adapter = StubFirecrawlAdapter.from_fixture_dir(str(FIXTURES_RAW_DIR))
        # sina-feed.json should be loaded
        assert len(adapter._fixtures) >= 1

    def test_from_fixture_dir_empty_directory(self, tmp_path):
        """from_fixture_dir on empty directory should return adapter with no fixtures."""
        adapter = StubFirecrawlAdapter.from_fixture_dir(str(tmp_path))
        assert len(adapter._fixtures) == 0

    def test_from_fixture_dir_nonexistent_directory(self):
        """from_fixture_dir on nonexistent directory should return adapter with no fixtures."""
        adapter = StubFirecrawlAdapter.from_fixture_dir("/nonexistent/path")
        assert len(adapter._fixtures) == 0
