"""Tests for CDC weekly report discovery extractors."""

import json
from pathlib import Path

import pytest

from harvester.extractors.cdc_weekly import (
    CdcWeeklyDetailExtractor,
    CdcWeeklyListExtractor,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures"
SOURCE_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/"
DETAIL_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/202605/t20260514_1835783.html"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / "raw" / name).read_text(encoding="utf-8")


def _read_expected(name: str):
    return json.loads((FIXTURE_DIR / "expected" / name).read_text(encoding="utf-8"))


class TestCdcWeeklyListExtractor:
    """Tests for CDC weekly list page discovery."""

    @pytest.mark.parametrize(
        "fixture_file",
        ["cdc-weekly-list.html", "cdc-weekly-list.md"],
        ids=["html", "markdown"],
    )
    def test_extracts_weekly_items_and_detail_targets(self, fixture_file):
        """List extractor should create item identities and detail targets."""
        # Arrange
        payload = _read_fixture(fixture_file)
        expected = _read_expected("cdc-weekly-list-targets.json")

        # Act
        output = CdcWeeklyListExtractor().extract({"source_url": SOURCE_URL}, payload)

        # Assert
        assert len(output.items) == len(expected)
        assert len(output.discovered_targets) == len(expected)
        for idx, item in enumerate(output.items):
            assert item.external_item_id == expected[idx]["external_item_id"]
            assert item.title == expected[idx]["title"]
            assert item.item_type == "article"
            assert item.original_url == expected[idx]["detail_url"]
            assert item.extra["published_date"] == expected[idx]["published_date"]
            target = output.discovered_targets[idx]
            assert target.target_url == expected[idx]["detail_url"]
            assert target.target_role == "detail"
            assert target.media_type == "html"
            assert target.content_type == "text/html"
            assert target.external_item_id == item.external_item_id


class TestCdcWeeklyDetailExtractor:
    """Tests for CDC weekly detail page PDF asset discovery."""

    @pytest.mark.parametrize(
        "fixture_file",
        ["cdc-weekly-detail.html", "cdc-weekly-detail.md"],
        ids=["html", "markdown"],
    )
    def test_extracts_detail_item_and_pdf_asset_target(self, fixture_file):
        """Detail extractor should discover the weekly report PDF asset."""
        # Arrange
        payload = _read_fixture(fixture_file)
        expected = _read_expected("cdc-weekly-detail-targets.json")[0]

        # Act
        output = CdcWeeklyDetailExtractor().extract(
            {"source_url": SOURCE_URL, "target_url": DETAIL_URL},
            payload,
        )

        # Assert
        assert len(output.items) == 1
        item = output.items[0]
        assert item.external_item_id == expected["external_item_id"]
        assert item.title == expected["title"]
        assert item.original_url == DETAIL_URL
        assert "正文摘要" in item.content_text

        assert len(output.discovered_targets) == 1
        target = output.discovered_targets[0]
        assert target.target_url == expected["pdf_url"]
        assert target.target_role == "asset"
        assert target.media_type == "pdf"
        assert target.content_type == "application/pdf"
        assert target.external_item_id == item.external_item_id
