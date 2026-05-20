"""Playwright-based adapter for crawling anti-bot protected pages.

Uses headless Chromium with anti-detection measures to bypass JavaScript-based
protections like Ruishu (瑞数). Returns raw HTML content.

Uses the synchronous Playwright API to avoid event loop conflicts when called
from async contexts (e.g. FastAPI).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

from playwright.sync_api import Page, sync_playwright

from harvester.adapters.firecrawl import CrawlResult

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_DEFAULT_LOCALE = "zh-CN"

_CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-gpu",
    "--no-sandbox",
]

_MIN_CONTENT_LENGTH = 100
_MIN_LINK_COUNT = 3
_POLL_INTERVAL_S = 1


@dataclass(frozen=True)
class PlaywrightConfig:
    """Configuration for Playwright adapter."""

    timeout: float = 60.0
    wait_timeout: float = 30.0
    user_agent: str = _DEFAULT_USER_AGENT
    locale: str = _DEFAULT_LOCALE

    @classmethod
    def from_env(cls) -> PlaywrightConfig:
        timeout = float(os.environ.get("PLAYWRIGHT_TIMEOUT", "60"))
        wait_timeout = float(os.environ.get("PLAYWRIGHT_WAIT_TIMEOUT", "30"))
        user_agent = os.environ.get("PLAYWRIGHT_USER_AGENT", _DEFAULT_USER_AGENT)
        locale = os.environ.get("PLAYWRIGHT_LOCALE", _DEFAULT_LOCALE)
        return cls(
            timeout=timeout,
            wait_timeout=wait_timeout,
            user_agent=user_agent,
            locale=locale,
        )


class PlaywrightAdapter:
    """Crawl adapter using Playwright headless browser.

    Handles anti-bot protected pages by rendering JavaScript and waiting
    for dynamic content to load before extracting the HTML.

    Uses the synchronous Playwright API to avoid event loop conflicts.
    """

    def __init__(self, config: PlaywrightConfig | None = None) -> None:
        self._config = config or PlaywrightConfig()

    def crawl(self, url: str) -> CrawlResult:
        """Crawl a URL using Playwright headless browser.

        Returns a CrawlResult with HTML content, regardless of success or failure.
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=_CHROMIUM_ARGS,
                )
                try:
                    context = browser.new_context(
                        user_agent=self._config.user_agent,
                        locale=self._config.locale,
                    )
                    page = context.new_page()

                    # Navigate with error tolerance
                    try:
                        page.goto(
                            url,
                            wait_until="networkidle",
                            timeout=self._config.timeout * 1000,
                        )
                    except Exception:
                        # Anti-bot may cause navigation interruptions
                        logger.debug("playwright.goto_interrupted url=%s", url)
                        time.sleep(3)

                    loaded = self._wait_for_content(page)
                    if not loaded:
                        logger.info("playwright.reload url=%s", url)
                        try:
                            page.reload(
                                wait_until="networkidle",
                                timeout=self._config.timeout * 1000,
                            )
                        except Exception:
                            time.sleep(3)
                        loaded = self._wait_for_content(page)
                        if not loaded:
                            return CrawlResult(
                                original_url=url,
                                error="Page content did not load after retry",
                            )

                    content = self._safe_get_content(page)
                    final_url = page.url

                    return CrawlResult(
                        original_url=url,
                        final_url=final_url,
                        status_code=200,
                        content_type="text/html",
                        payload_text=content,
                    )
                finally:
                    browser.close()
        except Exception as exc:
            logger.error("playwright.crawl_failed url=%s error=%s", url, exc)
            return CrawlResult(original_url=url, error=str(exc))

    def _wait_for_content(self, page: Page) -> bool:
        """Poll until page has meaningful content (anti-bot resolved)."""
        deadline = time.time() + self._config.wait_timeout
        while time.time() < deadline:
            try:
                content = page.content()
                links = page.query_selector_all("a")
                if len(content) > _MIN_CONTENT_LENGTH and len(links) > _MIN_LINK_COUNT:
                    return True
            except Exception:
                pass
            time.sleep(_POLL_INTERVAL_S)
        return False

    def _safe_get_content(self, page: Page, max_retries: int = 3) -> str:
        """Safely get page content, retrying on navigation errors."""
        for attempt in range(max_retries):
            try:
                return page.content()
            except Exception as exc:
                if attempt < max_retries - 1:
                    logger.debug(
                        "playwright.content_retry attempt=%d error=%s",
                        attempt + 1,
                        exc,
                    )
                    time.sleep(2)
                else:
                    raise

    @classmethod
    def from_env(cls) -> PlaywrightAdapter:
        return cls(config=PlaywrightConfig.from_env())
