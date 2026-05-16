"""Opt-in CDC live smoke test — disabled by default.

Set HARVESTER_CDC_LIVE_SMOKE=1 to enable real network access.
Without the flag, the test is skipped entirely.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("HARVESTER_CDC_LIVE_SMOKE"),
    reason="CDC live smoke disabled by default; set HARVESTER_CDC_LIVE_SMOKE=1 to enable",
)

from harvester.adapters.binary_fetch import fetch_binary
from harvester.extractors.cdc_weekly import (
    CdcWeeklyDetailExtractor,
    CdcWeeklyListExtractor,
)
from harvester.extractors.pdf_text import PdfTextExtractor

LIST_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/"


class TestCdcLiveSmoke:
    """Live smoke test for CDC weekly report pipeline."""

    def test_list_page_returns_html(self):
        """CDC list page should be reachable and parseable."""
        from httpx import Client

        with Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(LIST_URL)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

        output = CdcWeeklyListExtractor().extract({"source_url": LIST_URL}, resp.text)
        assert len(output.items) >= 1
        assert len(output.discovered_targets) >= 1

        # At least one detail target should be a valid URL
        detail_url = output.discovered_targets[0].target_url
        assert detail_url.startswith("https://www.chinacdc.cn/")

    def test_detail_page_returns_html_and_discovers_pdf(self):
        """CDC detail page should discover at least one PDF asset."""
        from httpx import Client

        # First get a detail URL from the list page
        with Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(LIST_URL)
        list_output = CdcWeeklyListExtractor().extract(
            {"source_url": LIST_URL}, resp.text
        )
        assert len(list_output.discovered_targets) >= 1
        detail_url = list_output.discovered_targets[0].target_url

        # Fetch the detail page
        with Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(detail_url)
        assert resp.status_code == 200

        detail_output = CdcWeeklyDetailExtractor().extract(
            {"source_url": LIST_URL, "target_url": detail_url}, resp.text
        )
        assert len(detail_output.items) >= 1
        assert len(detail_output.discovered_targets) >= 1

        pdf_target = detail_output.discovered_targets[0]
        assert pdf_target.media_type == "pdf"

    def test_pdf_binary_fetch_succeeds(self):
        """CDC PDF should be fetchable as binary."""
        from httpx import Client

        # Get a PDF URL through list -> detail
        with Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(LIST_URL)
        list_output = CdcWeeklyListExtractor().extract(
            {"source_url": LIST_URL}, resp.text
        )
        detail_url = list_output.discovered_targets[0].target_url

        with Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(detail_url)
        detail_output = CdcWeeklyDetailExtractor().extract(
            {"source_url": LIST_URL, "target_url": detail_url}, resp.text
        )
        pdf_url = detail_output.discovered_targets[0].target_url

        result = fetch_binary(pdf_url)
        assert result.error is None, f"Binary fetch failed: {result.error}"
        assert result.payload_bytes is not None
        assert len(result.payload_bytes) > 0
        assert result.content_type and "pdf" in result.content_type.lower()
