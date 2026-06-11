"""Tests for ScraplingAdapter.

All Scrapling calls are mocked — no real browser/network required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from harvester.adapters.scrapling_adapter import ScraplingAdapter, ScraplingConfig
from harvester.adapters.types import CrawlResult


def _mock_fetcher_response(
    url: str = "https://example.com/page",
    status: int = 200,
    html: str = "<html><body>Hello</body></html>",
) -> MagicMock:
    """Build a mock Scrapling Response object."""
    resp = MagicMock()
    resp.url = url
    resp.status = status
    resp.html_content = html
    return resp


class TestScraplingConfig:
    """ScraplingConfig environment variable parsing."""

    def test_from_env_defaults(self):
        with patch.dict("os.environ", {}, clear=True):
            config = ScraplingConfig.from_env()
            assert config.timeout == 30.0
            assert config.impersonate == "chrome"
            assert config.headless is True
            assert config.solve_cloudflare is False

    def test_from_env_custom(self):
        env = {
            "SCRAPLING_TIMEOUT": "60",
            "SCRAPLING_IMPERSONATE": "safari",
            "SCRAPLING_HEADLESS": "false",
        }
        with patch.dict("os.environ", env, clear=True):
            config = ScraplingConfig.from_env()
            assert config.timeout == 60.0
            assert config.impersonate == "safari"
            assert config.headless is False


class TestFetcherMode:
    """ScraplingAdapter with Fetcher (default HTTP + TLS mode)."""

    @patch("scrapling.fetchers.Fetcher")
    def test_crawl_fetcher_mode(self, mock_fetcher_cls):
        """Mock Fetcher.get() and verify CrawlResult fields."""
        mock_fetcher_cls.get.return_value = _mock_fetcher_response()

        adapter = ScraplingAdapter()
        result = adapter.crawl("https://example.com")

        assert isinstance(result, CrawlResult)
        assert result.original_url == "https://example.com"
        assert result.final_url == "https://example.com/page"
        assert result.status_code == 200
        assert result.payload_text == "<html><body>Hello</body></html>"
        assert result.content_type == "text/html"
        assert result.error is None

    @patch("scrapling.fetchers.Fetcher")
    def test_default_mode_is_fetcher(self, mock_fetcher_cls):
        """Empty config routes to fetcher."""
        mock_fetcher_cls.get.return_value = _mock_fetcher_response(
            url="https://example.com", html="<html></html>"
        )

        adapter = ScraplingAdapter()
        result = adapter.crawl("https://example.com", config={})

        assert result.error is None
        mock_fetcher_cls.get.assert_called_once()

    @patch("scrapling.fetchers.Fetcher")
    def test_fetcher_error_handling(self, mock_fetcher_cls):
        """Scrapling exception returns CrawlResult(error=...)."""
        mock_fetcher_cls.get.side_effect = ConnectionError("Network unreachable")

        adapter = ScraplingAdapter()
        result = adapter.crawl("https://example.com")

        assert result.error is not None
        assert "Network unreachable" in result.error


class TestStealthyMode:
    """ScraplingAdapter with StealthyFetcher."""

    @patch("scrapling.fetchers.StealthyFetcher")
    def test_crawl_stealthy_mode(self, mock_cls):
        mock_response = MagicMock()
        mock_response.url = "https://example.com/protected"
        mock_response.status = 200
        mock_response.html_content = "<html><body>Protected content</body></html>"
        mock_cls.fetch.return_value = mock_response

        adapter = ScraplingAdapter()
        result = adapter.crawl(
            "https://example.com/protected",
            config={"scrapling_mode": "stealthy"},
        )

        assert result.error is None
        assert result.final_url == "https://example.com/protected"
        assert result.payload_text == "<html><body>Protected content</body></html>"
        mock_cls.fetch.assert_called_once()

    @patch("scrapling.fetchers.StealthyFetcher")
    def test_stealthy_passes_headless_and_cloudflare(self, mock_cls):
        mock_response = MagicMock()
        mock_response.url = "https://example.com"
        mock_response.status = 200
        mock_response.html_content = "<html></html>"
        mock_cls.fetch.return_value = mock_response

        adapter = ScraplingAdapter(
            config=ScraplingConfig(
                headless=False,
                solve_cloudflare=True,
            )
        )
        adapter.crawl(
            "https://example.com",
            config={"scrapling_mode": "stealthy"},
        )

        call_kwargs = mock_cls.fetch.call_args[1]
        assert call_kwargs["headless"] is False
        assert call_kwargs["solve_cloudflare"] is True


class TestDynamicMode:
    """ScraplingAdapter with DynamicFetcher."""

    @patch("scrapling.fetchers.DynamicFetcher")
    def test_crawl_dynamic_mode(self, mock_cls):
        mock_response = MagicMock()
        mock_response.url = "https://example.com/dynamic"
        mock_response.status = 200
        mock_response.html_content = "<html><body>Dynamic content</body></html>"
        mock_cls.fetch.return_value = mock_response

        adapter = ScraplingAdapter()
        result = adapter.crawl(
            "https://example.com/dynamic",
            config={"scrapling_mode": "dynamic"},
        )

        assert result.error is None
        assert result.final_url == "https://example.com/dynamic"
        mock_cls.fetch.assert_called_once()

    @patch("scrapling.fetchers.DynamicFetcher")
    def test_dynamic_passes_headless(self, mock_cls):
        mock_response = MagicMock()
        mock_response.url = "https://example.com"
        mock_response.status = 200
        mock_response.html_content = "<html></html>"
        mock_cls.fetch.return_value = mock_response

        adapter = ScraplingAdapter(
            config=ScraplingConfig(headless=False)
        )
        adapter.crawl(
            "https://example.com",
            config={"scrapling_mode": "dynamic"},
        )

        call_kwargs = mock_cls.fetch.call_args[1]
        assert call_kwargs["headless"] is False


class TestRouting:
    """Verify executor='scrapling' reaches ScraplingAdapter."""

    @patch("scrapling.fetchers.Fetcher")
    def test_execute_adapter_crawl_routes_to_scrapling(self, mock_fetcher_cls):
        mock_response = MagicMock()
        mock_response.url = "https://example.com"
        mock_response.status = 200
        mock_response.html_content = "<html></html>"
        mock_fetcher_cls.get.return_value = mock_response

        from harvester.jobs.crawl_execution import execute_adapter_crawl

        result = execute_adapter_crawl(
            "https://example.com",
            executor="scrapling",
        )

        assert isinstance(result, CrawlResult)
        assert result.error is None
        assert result.original_url == "https://example.com"
