"""Tests for NHC health standards extractors."""

from __future__ import annotations

from pathlib import Path

import pytest

from harvester.extractors.base import ExtractionOutput
from harvester.extractors.nhc_wsbz import (
    NhcWsbzDetailExtractor,
    NhcWsbzListExtractor,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "raw"


def _read_fixture(name: str) -> str:
    path = FIXTURES_DIR / name
    if not path.exists():
        pytest.skip(f"Fixture {name} not found (requires live page fetch)")
    return path.read_text(encoding="utf-8")


class TestNhcWsbzListExtractor:
    """Test list page extractor with real HTML fixture."""

    def test_extracts_entries_from_real_html(self):
        html = _read_fixture("nhc-wsbz-list.html")
        extractor = NhcWsbzListExtractor()
        result = extractor.extract(
            raw_metadata={"source_url": "https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml"},
            raw_payload=html,
        )

        assert isinstance(result, ExtractionOutput)
        assert len(result.items) > 0, "Should extract at least one standard entry"
        assert len(result.discovered_targets) > 0, "Should discover detail targets"

        # Each item should have a corresponding discovered target
        assert len(result.items) == len(result.discovered_targets)

    def test_item_fields_populated(self):
        html = _read_fixture("nhc-wsbz-list.html")
        extractor = NhcWsbzListExtractor()
        result = extractor.extract(
            raw_metadata={"source_url": "https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml"},
            raw_payload=html,
        )

        first_item = result.items[0]
        assert first_item.external_item_id.startswith("nhc-wsbz:")
        assert first_item.item_type == "standard"
        assert first_item.title, "Title should not be empty"
        assert first_item.language == "zh"
        assert first_item.original_url.startswith("https://www.nhc.gov.cn/wjw/")
        assert first_item.position == 0

    def test_discovered_targets_are_detail_pages(self):
        html = _read_fixture("nhc-wsbz-list.html")
        extractor = NhcWsbzListExtractor()
        result = extractor.extract(
            raw_metadata={"source_url": "https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml"},
            raw_payload=html,
        )

        for target in result.discovered_targets:
            assert target.target_role == "detail"
            assert target.media_type == "html"
            assert target.content_type == "text/html"
            assert target.depth == 1
            assert target.target_url.startswith("https://www.nhc.gov.cn/wjw/")
            assert ".shtml" in target.target_url

    def test_discovered_targets_have_category(self):
        html = _read_fixture("nhc-wsbz-list.html")
        extractor = NhcWsbzListExtractor()
        result = extractor.extract(
            raw_metadata={"source_url": "https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml"},
            raw_payload=html,
        )

        # At least some targets should have a category derived from URL section
        categorized = [t for t in result.discovered_targets if t.category]
        assert len(categorized) > 0, "Should extract categories from detail page URLs"
        # Known sections in the fixture
        categories = {t.category for t in categorized}
        assert any(
            c in categories
            for c in ("医疗服务", "老年健康", "职业健康", "卫生健康信息", "临床检验")
        )

    def test_std_num_in_external_id(self):
        html = _read_fixture("nhc-wsbz-list.html")
        extractor = NhcWsbzListExtractor()
        result = extractor.extract(
            raw_metadata={"source_url": "https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml"},
            raw_payload=html,
        )

        # At least some items should have WS/T or GBZ standard numbers
        has_ws = any("WST" in item.external_item_id for item in result.items)
        has_gbz = any("GBZ" in item.external_item_id for item in result.items)
        assert has_ws or has_gbz, "Should find WS/T or GBZ standard numbers"

    def test_extra_metadata(self):
        html = _read_fixture("nhc-wsbz-list.html")
        extractor = NhcWsbzListExtractor()
        result = extractor.extract(
            raw_metadata={"source_url": "https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml"},
            raw_payload=html,
        )

        first_item = result.items[0]
        assert "std_num" in first_item.extra
        assert first_item.extra["std_num"], "Standard number should not be empty"

    def test_empty_html(self):
        extractor = NhcWsbzListExtractor()
        result = extractor.extract(
            raw_metadata={"source_url": "https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml"},
            raw_payload="<html><body></body></html>",
        )
        assert len(result.items) == 0
        assert len(result.discovered_targets) == 0


class TestNhcWsbzDetailExtractor:
    """Test detail page extractor with real HTML fixture."""

    def test_extracts_metadata_from_real_html(self):
        html = _read_fixture("nhc-wsbz-detail.html")
        extractor = NhcWsbzDetailExtractor()
        result = extractor.extract(
            raw_metadata={
                "target_url": "https://www.nhc.gov.cn/wjw/c100309/202509/7a598b25a04b4f7f901c104d5835cd82.shtml"
            },
            raw_payload=html,
        )

        assert isinstance(result, ExtractionOutput)
        assert len(result.items) == 1

        item = result.items[0]
        assert item.external_item_id.startswith("nhc-wsbz:")
        assert item.item_type == "standard"
        assert item.language == "zh"

    def test_extracts_pdf_target(self):
        html = _read_fixture("nhc-wsbz-detail.html")
        extractor = NhcWsbzDetailExtractor()
        result = extractor.extract(
            raw_metadata={
                "target_url": "https://www.nhc.gov.cn/wjw/c100309/202509/7a598b25a04b4f7f901c104d5835cd82.shtml"
            },
            raw_payload=html,
        )

        assert len(result.discovered_targets) >= 1, "Should discover at least one PDF"
        pdf_target = result.discovered_targets[0]
        assert pdf_target.target_role == "asset"
        assert pdf_target.media_type == "pdf"
        assert pdf_target.content_type == "application/pdf"
        assert pdf_target.depth == 2
        assert ".pdf" in pdf_target.target_url

    def test_pdf_target_has_category(self):
        html = _read_fixture("nhc-wsbz-detail.html")
        extractor = NhcWsbzDetailExtractor()
        result = extractor.extract(
            raw_metadata={
                "target_url": "https://www.nhc.gov.cn/wjw/c100309/202509/7a598b25a04b4f7f901c104d5835cd82.shtml"
            },
            raw_payload=html,
        )

        assert len(result.discovered_targets) >= 1
        pdf_target = result.discovered_targets[0]
        assert pdf_target.category == "医疗服务"

    def test_std_num_extracted(self):
        html = _read_fixture("nhc-wsbz-detail.html")
        extractor = NhcWsbzDetailExtractor()
        result = extractor.extract(
            raw_metadata={
                "target_url": "https://www.nhc.gov.cn/wjw/c100309/202509/7a598b25a04b4f7f901c104d5835cd82.shtml"
            },
            raw_payload=html,
        )

        item = result.items[0]
        assert "874" in item.external_item_id, "Should contain standard number"

    def test_empty_html(self):
        extractor = NhcWsbzDetailExtractor()
        result = extractor.extract(
            raw_metadata={
                "target_url": "https://www.nhc.gov.cn/wjw/c100309/202509/test.shtml"
            },
            raw_payload="<html><body></body></html>",
        )
        assert len(result.items) == 1  # Always creates one item
        assert len(result.discovered_targets) == 0  # No PDF found

    def test_bytes_payload(self):
        html = _read_fixture("nhc-wsbz-detail.html")
        extractor = NhcWsbzDetailExtractor()
        result = extractor.extract(
            raw_metadata={
                "target_url": "https://www.nhc.gov.cn/wjw/c100309/202509/7a598b25a04b4f7f901c104d5835cd82.shtml"
            },
            raw_payload=html.encode("utf-8"),
        )
        assert len(result.items) == 1


class TestNhcExtractorRegistry:
    """Test that NHC extractors are correctly registered."""

    def test_list_page_matches(self):
        from harvester.extractors.registry import get_extractor_for_url

        ext = get_extractor_for_url("https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml")
        assert isinstance(ext, NhcWsbzListExtractor)

    def test_detail_page_matches(self):
        from harvester.extractors.registry import get_extractor_for_url

        ext = get_extractor_for_url(
            "https://www.nhc.gov.cn/wjw/c100309/202509/7a598b25a04b4f7f901c104d5835cd82.shtml"
        )
        assert isinstance(ext, NhcWsbzDetailExtractor)

    def test_detail_page_different_section(self):
        from harvester.extractors.registry import get_extractor_for_url

        ext = get_extractor_for_url(
            "https://www.nhc.gov.cn/wjw/pyl/202602/2ce629a245af49f8ba8aa8ac40ab9d0e.shtml"
        )
        assert isinstance(ext, NhcWsbzDetailExtractor)

    def test_list_page_does_not_match_detail(self):
        from harvester.extractors.registry import get_extractor_for_url

        ext = get_extractor_for_url("https://www.nhc.gov.cn/wjw/wsbzxx/wsbz.shtml")
        assert not isinstance(ext, NhcWsbzDetailExtractor)
