"""Tests for the real Firecrawl HTTP adapter.

Uses httpx.MockTransport to simulate Firecrawl API responses.
Covers: success, error, timeout, malformed, and missing config.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from harvester.adapters.firecrawl import (
    CrawlResult,
    FirecrawlAdapter,
    FirecrawlConfigError,
)


def _make_success_response(
    *,
    final_url: str = "https://example.com/page",
    status_code: int = 200,
    content_type: str = "text/html",
    payload: str = "<html><body>Hello</body></html>",
) -> dict:
    """Build a typical Firecrawl scrape success payload."""
    return {
        "success": True,
        "data": {
            "metadata": {
                "sourceURL": final_url,
                "statusCode": status_code,
            },
            "content": payload,
        },
    }


def _mock_transport(response_body: bytes, status_code: int = 200):
    """Create an httpx.MockTransport returning fixed response."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=response_body)

    return httpx.MockTransport(handler)


class TestFirecrawlAdapterSuccess:
    """Successful scrape responses."""

    def test_returns_crawl_result_on_success(self):
        payload = _make_success_response()
        transport = _mock_transport(json.dumps(payload).encode())

        adapter = FirecrawlAdapter(
            base_url="http://firecrawl:3000",
            client=httpx.Client(transport=transport),
        )
        result = adapter.crawl("https://example.com")

        assert isinstance(result, CrawlResult)
        assert result.original_url == "https://example.com"
        assert result.final_url == "https://example.com/page"
        assert result.status_code == 200
        assert result.payload_text == "<html><body>Hello</body></html>"
        assert result.error is None

    def test_extracts_content_type_from_html(self):
        payload = _make_success_response()
        transport = _mock_transport(json.dumps(payload).encode())

        adapter = FirecrawlAdapter(
            base_url="http://firecrawl:3000",
            client=httpx.Client(transport=transport),
        )
        result = adapter.crawl("https://example.com")

        assert result.content_type == "text/markdown"


class TestFirecrawlAdapterErrors:
    """Error responses from Firecrawl API."""

    def test_firecrawl_api_error(self):
        payload = {"success": False, "error": "Target site is down"}
        transport = _mock_transport(json.dumps(payload).encode(), status_code=502)

        adapter = FirecrawlAdapter(
            base_url="http://firecrawl:3000",
            client=httpx.Client(transport=transport),
        )
        result = adapter.crawl("https://example.com")

        assert result.error is not None
        assert result.status_code == 502

    def test_timeout_returns_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Connection timed out")

        transport = httpx.MockTransport(handler)
        adapter = FirecrawlAdapter(
            base_url="http://firecrawl:3000",
            client=httpx.Client(transport=transport),
        )
        result = adapter.crawl("https://example.com")

        assert result.error is not None
        assert "timed out" in result.error.lower() or "timeout" in result.error.lower()

    def test_malformed_response_returns_error(self):
        transport = _mock_transport(b"not json at all")

        adapter = FirecrawlAdapter(
            base_url="http://firecrawl:3000",
            client=httpx.Client(transport=transport),
        )
        result = adapter.crawl("https://example.com")

        assert result.error is not None

    def test_success_false_in_body_returns_error(self):
        payload = {"success": False, "error": "Blocked by robots.txt"}
        transport = _mock_transport(json.dumps(payload).encode())

        adapter = FirecrawlAdapter(
            base_url="http://firecrawl:3000",
            client=httpx.Client(transport=transport),
        )
        result = adapter.crawl("https://example.com")

        assert result.error is not None
        assert "robots" in result.error.lower() or "blocked" in result.error.lower()


class TestFirecrawlAdapterMissingConfig:
    """Missing Firecrawl configuration MUST fail explicitly."""

    def test_missing_base_url_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(FirecrawlConfigError):
                FirecrawlAdapter.from_env()

    def test_no_fallback_to_stub(self):
        """Adapter must not silently succeed when URL is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(FirecrawlConfigError):
                FirecrawlAdapter.from_env()

    def test_from_env_with_config(self):
        env = {
            "FIRECRAWL_API_URL": "http://firecrawl:3000",
            "FIRECRAWL_API_KEY": "test-key",
        }
        with patch.dict("os.environ", env, clear=True):
            adapter = FirecrawlAdapter.from_env()
            assert adapter._base_url == "http://firecrawl:3000"


class TestFirecrawlAdapterScrapePath:
    """Scrape path must be configurable."""

    def test_default_scrape_path(self):
        transport = _mock_transport(b"{}")
        adapter = FirecrawlAdapter(
            base_url="http://firecrawl:3000",
            client=httpx.Client(transport=transport),
        )
        assert adapter._scrape_path == "/v1/scrape"

    def test_custom_scrape_path(self):
        transport = _mock_transport(b"{}")
        adapter = FirecrawlAdapter(
            base_url="http://firecrawl:3000",
            scrape_path="/scrape",
            client=httpx.Client(transport=transport),
        )
        assert adapter._scrape_path == "/scrape"


class TestCrawlResultDataclass:
    """CrawlResult data structure."""

    def test_crawl_result_fields(self):
        result = CrawlResult(
            original_url="https://example.com",
            final_url="https://example.com/page",
            status_code=200,
            content_type="text/html",
            payload_text="<html></html>",
            metadata={"key": "value"},
            error=None,
        )
        assert result.original_url == "https://example.com"
        assert result.final_url == "https://example.com/page"
        assert result.status_code == 200
        assert result.content_type == "text/html"
        assert result.payload_text == "<html></html>"
        assert result.metadata == {"key": "value"}
        assert result.error is None

    def test_error_result(self):
        result = CrawlResult(
            original_url="https://example.com",
            final_url=None,
            status_code=None,
            content_type=None,
            payload_text=None,
            metadata=None,
            error="Timeout",
        )
        assert result.error == "Timeout"
        assert result.payload_text is None
