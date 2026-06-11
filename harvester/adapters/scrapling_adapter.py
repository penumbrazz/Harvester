"""Scrapling-based adapter for web crawling.

Wraps three Scrapling fetcher modes behind a single crawl() interface:
- fetcher (default): HTTP + TLS fingerprint impersonation
- stealthy: Headless browser + Cloudflare Turnstile bypass
- dynamic: Full browser automation (Playwright-based)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from harvester.adapters.types import CrawlResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScraplingConfig:
    """Configuration for Scrapling adapter."""

    timeout: float = 30.0
    impersonate: str = "chrome"
    headless: bool = True
    solve_cloudflare: bool = False

    @classmethod
    def from_env(cls) -> ScraplingConfig:
        timeout = float(os.environ.get("SCRAPLING_TIMEOUT", "30"))
        impersonate = os.environ.get("SCRAPLING_IMPERSONATE", "chrome")
        headless = os.environ.get("SCRAPLING_HEADLESS", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        solve_cloudflare = os.environ.get("SCRAPLING_SOLVE_CLOUDFLARE", "").lower() in (
            "true",
            "1",
            "yes",
        )
        return cls(
            timeout=timeout,
            impersonate=impersonate,
            headless=headless,
            solve_cloudflare=solve_cloudflare,
        )


def _extract_content_type(response: object) -> str:
    """Extract content type from Scrapling response headers."""
    headers = getattr(response, "headers", None)
    if isinstance(headers, dict):
        ct = headers.get("content-type") or headers.get("Content-Type")
        if isinstance(ct, str) and ct.strip():
            return ct.split(";")[0].strip()
    return "text/html"


class ScraplingAdapter:
    """Crawl adapter using Scrapling fetcher library."""

    def __init__(self, config: ScraplingConfig | None = None) -> None:
        self._config = config or ScraplingConfig()

    def crawl(self, url: str, config: dict | None = None) -> CrawlResult:
        """Crawl a URL using Scrapling.

        Routes to internal method based on config['scrapling_mode']:
        'fetcher' (default), 'stealthy', or 'dynamic'.
        """
        mode = (config or {}).get("scrapling_mode", "fetcher")
        if mode not in ("fetcher", "stealthy", "dynamic"):
            logger.warning("scrapling.unknown_mode mode=%s url=%s", mode, url)
            mode = "fetcher"
        logger.info("scrapling.crawl mode=%s url=%s", mode, url)
        if mode == "stealthy":
            return self._crawl_stealthy(url, config)
        if mode == "dynamic":
            return self._crawl_dynamic(url, config)
        return self._crawl_fetcher(url, config)

    def _crawl_fetcher(self, url: str, config: dict | None = None) -> CrawlResult:
        """HTTP fetch with TLS fingerprint impersonation."""
        try:
            from scrapling.fetchers import Fetcher
        except ImportError:
            return CrawlResult(
                original_url=url,
                error="scrapling is not installed. Install with: uv pip install 'scrapling[fetchers]'",
            )

        opts: dict = {}
        if self._config.impersonate:
            opts["impersonate"] = self._config.impersonate
        if config and "timeout" in config:
            opts["timeout"] = config["timeout"]
        else:
            opts["timeout"] = self._config.timeout
        if config and config.get("stealthy_headers"):
            opts["stealthy_headers"] = True

        try:
            response = Fetcher.get(url, **opts)
            return CrawlResult(
                original_url=url,
                final_url=response.url,
                status_code=response.status,
                content_type=_extract_content_type(response),
                payload_text=str(response.html_content or ""),
            )
        except Exception as exc:
            logger.error("scrapling.fetcher_failed url=%s error=%s", url, exc)
            return CrawlResult(original_url=url, error=str(exc))

    def _crawl_stealthy(self, url: str, config: dict | None = None) -> CrawlResult:
        """Headless browser with Cloudflare Turnstile bypass."""
        try:
            from scrapling.fetchers import StealthyFetcher
        except ImportError:
            return CrawlResult(
                original_url=url,
                error="scrapling is not installed. Install with: uv pip install 'scrapling[fetchers]'",
            )

        opts: dict = {
            "headless": self._config.headless,
            "timeout": self._config.timeout,
        }
        if self._config.solve_cloudflare:
            opts["solve_cloudflare"] = True
        if config and config.get("network_idle"):
            opts["network_idle"] = True

        try:
            response = StealthyFetcher.fetch(url, **opts)
            return CrawlResult(
                original_url=url,
                final_url=response.url,
                status_code=response.status,
                content_type=_extract_content_type(response),
                payload_text=str(response.html_content or ""),
            )
        except Exception as exc:
            logger.error("scrapling.stealthy_failed url=%s error=%s", url, exc)
            return CrawlResult(original_url=url, error=str(exc))

    def _crawl_dynamic(self, url: str, config: dict | None = None) -> CrawlResult:
        """Full browser automation via Playwright."""
        try:
            from scrapling.fetchers import DynamicFetcher
        except ImportError:
            return CrawlResult(
                original_url=url,
                error="scrapling is not installed. Install with: uv pip install 'scrapling[fetchers]'",
            )

        opts: dict = {
            "headless": self._config.headless,
            "timeout": self._config.timeout,
        }
        if config and config.get("disable_resources"):
            opts["disable_resources"] = True
        if config and config.get("network_idle"):
            opts["network_idle"] = True

        try:
            response = DynamicFetcher.fetch(url, **opts)
            return CrawlResult(
                original_url=url,
                final_url=response.url,
                status_code=response.status,
                content_type=_extract_content_type(response),
                payload_text=str(response.html_content or ""),
            )
        except Exception as exc:
            logger.error("scrapling.dynamic_failed url=%s error=%s", url, exc)
            return CrawlResult(original_url=url, error=str(exc))

    @classmethod
    def from_env(cls) -> ScraplingAdapter:
        return cls(config=ScraplingConfig.from_env())
