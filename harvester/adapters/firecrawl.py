"""Real Firecrawl-compatible HTTP adapter for public web crawling.

Reads FIRECRAWL_API_URL, optional FIRECRAWL_API_KEY, timeout and scrape
path from environment/configuration. Never falls back to stub/fixture.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx


class FirecrawlConfigError(Exception):
    """Raised when Firecrawl adapter is misconfigured (missing URL, etc.)."""


@dataclass(frozen=True)
class CrawlResult:
    """Normalized result from a crawl operation."""

    original_url: str
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    payload_text: str | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class FirecrawlAdapter:
    """HTTP adapter for Firecrawl-compatible scrape APIs.

    Parameters
    ----------
    base_url : str
        Base URL of the Firecrawl instance (e.g. ``http://firecrawl:3000``).
    api_key : str or None
        Optional API key for authentication.
    scrape_path : str
        Path appended to base_url for scrape requests.
    timeout : float
        Request timeout in seconds.
    client : httpx.Client or None
        Pre-configured httpx client. If None, a default client is created.
    """

    _base_url: str
    _api_key: str | None = None
    _scrape_path: str = "/v1/scrape"
    _timeout: float = 30.0
    _client: httpx.Client = field(default_factory=httpx.Client)

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        scrape_path: str = "/v1/scrape",
        timeout: float = 30.0,
        max_bytes: int | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._scrape_path = scrape_path
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._client = client or httpx.Client(timeout=timeout)

    def crawl(self, url: str) -> CrawlResult:
        """Scrape a URL via the Firecrawl API.

        Returns a CrawlResult regardless of success or failure.
        """
        endpoint = f"{self._base_url}{self._scrape_path}"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        body = {"url": url}

        try:
            response = self._client.post(
                endpoint, json=body, headers=headers, timeout=self._timeout
            )
        except httpx.TimeoutException as exc:
            return CrawlResult(original_url=url, error=f"Request timed out: {exc}")
        except httpx.HTTPError as exc:
            return CrawlResult(original_url=url, error=f"HTTP error: {exc}")

        # Non-2xx status
        if response.status_code >= 400:
            return CrawlResult(
                original_url=url,
                status_code=response.status_code,
                error=f"Firecrawl returned HTTP {response.status_code}",
            )

        # Parse JSON
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            return CrawlResult(
                original_url=url,
                error=f"Malformed response: {exc}",
            )

        # Check Firecrawl-level success flag
        if not data.get("success", False):
            error_msg = data.get("error", "Unknown Firecrawl error")
            return CrawlResult(
                original_url=url,
                error=str(error_msg),
            )

        inner = data.get("data", {})
        metadata = inner.get("metadata", {})
        content = inner.get("content", "") or inner.get("markdown", "")

        final_url = metadata.get("sourceURL", url)
        status_code = metadata.get("statusCode", response.status_code)

        # Detect content type from metadata or infer from content
        content_type = metadata.get("contentType") or metadata.get("content_type")
        if not content_type and isinstance(content, str):
            content_type = "text/html"

        size_error = self._check_size_limit(content, url)
        if size_error:
            return size_error

        return CrawlResult(
            original_url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            payload_text=content,
            metadata=metadata,
        )

    def _check_size_limit(self, content: str, url: str) -> CrawlResult | None:
        """Return an error CrawlResult if content exceeds max_bytes, else None."""
        if self._max_bytes and len(content.encode("utf-8")) > self._max_bytes:
            return CrawlResult(
                original_url=url,
                error=f"Response payload exceeds max_bytes limit ({self._max_bytes})",
            )
        return None

    @classmethod
    def from_env(cls) -> FirecrawlAdapter:
        """Create an adapter from environment variables.

        Required:
            FIRECRAWL_API_URL

        Optional:
            FIRECRAWL_API_KEY, FIRECRAWL_SCRAPE_PATH,
            FIRECRAWL_TIMEOUT, FIRECRAWL_MAX_BYTES

        Raises FirecrawlConfigError if FIRECRAWL_API_URL is not set.
        """
        base_url = os.environ.get("FIRECRAWL_API_URL", "").strip()
        if not base_url:
            raise FirecrawlConfigError(
                "FIRECRAWL_API_URL is required for real crawl adapter"
            )

        api_key = os.environ.get("FIRECRAWL_API_KEY") or None
        scrape_path = os.environ.get("FIRECRAWL_SCRAPE_PATH", "/v1/scrape")
        timeout = float(os.environ.get("FIRECRAWL_TIMEOUT", "30"))
        max_bytes_str = os.environ.get("FIRECRAWL_MAX_BYTES")
        max_bytes = int(max_bytes_str) if max_bytes_str else None

        return cls(
            base_url=base_url,
            api_key=api_key,
            scrape_path=scrape_path,
            timeout=timeout,
            max_bytes=max_bytes,
        )
