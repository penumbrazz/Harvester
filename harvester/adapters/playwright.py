"""Playwright-based adapter for crawling anti-bot protected pages.

Uses headless Chromium with anti-detection measures to bypass JavaScript-based
protections like Ruishu (瑞数). Returns raw HTML content.

Uses the synchronous Playwright API to avoid event loop conflicts when called
from async contexts (e.g. FastAPI).
"""

from __future__ import annotations

import logging
import math
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

    def crawl(self, url: str, config: dict | None = None) -> CrawlResult:
        """Crawl a URL using Playwright headless browser.

        Returns a CrawlResult with HTML content, regardless of success or failure.

        If config contains ``pagination.type == "nhc_ajax"``, fetches all AJAX
        pagination pages after the initial load and injects rows into the HTML.
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

                    # Apply AJAX pagination if configured
                    if (
                        config
                        and config.get("pagination", {}).get("type") == "nhc_ajax"
                    ):
                        content = self._apply_nhc_pagination(page, content, config)

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

    def _apply_nhc_pagination(self, page: Page, html: str, config: dict) -> str:
        """Fetch NHC AJAX pagination pages and inject rows into HTML."""
        pagination = config.get("pagination", {})
        max_pages = pagination.get("max_pages", 200)

        channel_id = page.evaluate(
            "() => typeof channelId !== 'undefined' ? channelId : null"
        )
        if not channel_id:
            logger.warning("nhc_pagination.no_channelId")
            return html

        logger.info(
            "nhc_pagination.start channel=%s max_pages=%d", channel_id, max_pages
        )
        all_results = _fetch_nhc_ajax_pages(page, channel_id, max_pages)
        logger.info("nhc_pagination.fetched total_items=%d", len(all_results))

        if not all_results:
            return html

        rows_html = _nhc_json_to_table_rows(all_results)
        return _inject_rows_into_html(html, rows_html)

    @classmethod
    def from_env(cls) -> PlaywrightAdapter:
        return cls(config=PlaywrightConfig.from_env())


def _nhc_meta_value(result: dict, name: str) -> str:
    """Extract a named value from NHC AJAX result's domainMetaList."""
    for meta in result.get("domainMetaList", []):
        for item in meta.get("resultList", []):
            if item.get("name") == name:
                return item.get("value", "")
    return ""


def _nhc_json_to_table_rows(results: list[dict]) -> str:
    """Convert NHC AJAX JSON results to HTML table rows.

    Each result becomes a ``<tr class="xx">`` row matching the format
    expected by :class:`NhcWsbzListExtractor`.
    """
    if not results:
        return ""

    rows: list[str] = []
    for result in results:
        title = result.get("title", "")
        url = result.get("url", "")
        std_num = _nhc_meta_value(result, "标准号")
        publish_date = _nhc_meta_value(result, "发布时间")
        impl_date = _nhc_meta_value(result, "实施时间")

        rows.append(
            f'<tr bgcolor="#ffffff" class="xx">'
            f'<td align="center" height="25">·</td>'
            f'<td align="left" style="padding-left:5px;">{std_num}</td>'
            f'<td align="left" style="padding-left:5px;">'
            f'<a href="{url}" target="_blank" title="{title}">{title}</a></td>'
            f'<td align="center">{publish_date}</td>'
            f'<td align="center">{impl_date}</td>'
            f"</tr>"
        )
    return "\n".join(rows)


def _inject_rows_into_html(html: str, rows: str) -> str:
    """Inject AJAX-generated table rows before the closing </tbody>."""
    if not rows:
        return html
    return html.replace("</tbody>", rows + "\n</tbody>", 1)


def _fetch_nhc_ajax_pages(
    page: Page, channel_id: str, max_pages: int = 200, page_size: int = 20
) -> list[dict]:
    """Fetch all NHC AJAX pagination pages via in-page fetch().

    Returns combined results from all pages.
    """
    all_results: list[dict] = []

    for page_num in range(1, max_pages + 1):
        ajax_url = (
            f"/search/{channel_id}"
            f"?_isAgg=true&_isJson=true"
            f"&_pageSize={page_size}&_template=index"
            f"&_rangeTimeGte=&_channelName=&page={page_num}"
        )
        js_expr = f"() => fetch('{ajax_url}').then(r => r.json())"

        try:
            data = page.evaluate(js_expr)
        except Exception as exc:
            logger.warning("nhc_ajax.fetch_failed page=%d error=%s", page_num, exc)
            break

        results = data.get("data", {}).get("results", [])
        total = data.get("data", {}).get("total", 0)
        all_results.extend(results)

        logger.debug(
            "nhc_ajax.page page=%d items=%d total=%d", page_num, len(results), total
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        if page_num >= total_pages:
            break

    return all_results
