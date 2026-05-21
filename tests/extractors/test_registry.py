"""Tests for the extractor registry."""

from harvester.extractors.cdc_weekly import (
    CdcWeeklyDetailExtractor,
    CdcWeeklyListExtractor,
)
from harvester.extractors.pdf_text import PdfTextExtractor
from harvester.extractors.registry import get_extractor, get_extractor_for_url
from harvester.extractors.sina_7x24 import Sina7x24Extractor


class TestRegistryCdcWeekly:
    """CDC weekly extractor routing based on URL patterns."""

    def test_list_page_matches_list_extractor(self):
        """Source list page URL should match CdcWeeklyListExtractor."""
        extractor = get_extractor_for_url("https://www.chinacdc.cn/jksj/jksj04_14249/")
        assert isinstance(extractor, CdcWeeklyListExtractor)

    def test_list_page_without_trailing_slash(self):
        """List URL without trailing slash should also match list extractor."""
        extractor = get_extractor_for_url("https://www.chinacdc.cn/jksj/jksj04_14249")
        assert isinstance(extractor, CdcWeeklyListExtractor)

    def test_detail_page_matches_detail_extractor(self):
        """Detail page URL should match CdcWeeklyDetailExtractor."""
        extractor = get_extractor_for_url(
            "https://www.chinacdc.cn/jksj/jksj04_14249/202605/t20260514_1835783.html"
        )
        assert isinstance(extractor, CdcWeeklyDetailExtractor)

    def test_another_detail_page_matches_detail_extractor(self):
        """A different detail page URL should also match detail extractor."""
        extractor = get_extractor_for_url(
            "https://www.chinacdc.cn/jksj/jksj04_14249/202605/t20260508_1835622.html"
        )
        assert isinstance(extractor, CdcWeeklyDetailExtractor)

    def test_unrelated_url_returns_none(self):
        """An unrelated URL should not match any CDC extractor."""
        extractor = get_extractor_for_url("https://example.com/page.html")
        assert extractor is None

    def test_sina_still_matches(self):
        """Existing Sina extractor registration should remain intact."""
        extractor = get_extractor_for_url("https://finance.sina.com.cn/7x24/")
        assert isinstance(extractor, Sina7x24Extractor)

    def test_detail_takes_priority_over_list(self):
        """Detail pattern should be checked before list pattern."""
        detail_url = (
            "https://www.chinacdc.cn/jksj/jksj04_14249/202605/t20260514_1835783.html"
        )
        extractor = get_extractor_for_url(detail_url)
        # Should get detail extractor, not list extractor
        assert isinstance(extractor, CdcWeeklyDetailExtractor)


class TestRegistryPdfFallback:
    """PDF extractor should be matched via content type fallback."""

    def test_pdf_content_type_matches_pdf_extractor(self):
        """application/pdf content type should match PdfTextExtractor."""
        extractor = get_extractor(
            "https://example.com/unknown.pdf",
            content_type="application/pdf",
        )
        assert isinstance(extractor, PdfTextExtractor)

    def test_pdf_content_type_takes_priority_over_url_match(self):
        """Binary content types (PDF) should use dedicated extractors regardless of URL."""
        extractor = get_extractor(
            "https://www.chinacdc.cn/jksj/jksj04_14249/",
            content_type="application/pdf",
        )
        assert isinstance(extractor, PdfTextExtractor)

    def test_no_match_without_content_type(self):
        """Unknown URL without content type should return None."""
        extractor = get_extractor("https://example.com/unknown")
        assert extractor is None

    def test_no_match_for_non_pdf_content_type(self):
        """Non-PDF content type on unknown URL should return None."""
        extractor = get_extractor(
            "https://example.com/unknown",
            content_type="text/html",
        )
        assert extractor is None
