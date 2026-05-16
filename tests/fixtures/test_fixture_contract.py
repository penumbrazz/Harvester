"""Contract tests for fixture files — verify all expected files exist and are valid."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Base paths
FIXTURES_DIR = Path(__file__).parent
RAW_DIR = FIXTURES_DIR / "raw"
EXPECTED_DIR = FIXTURES_DIR / "expected"

# Required keys for every expected output item
REQUIRED_ITEM_KEYS = {"external_item_id", "item_type", "title"}

# Pattern for detecting 7x24 flash news items in Markdown
_FLASH_PATTERN = re.compile(r"\d{2}:\d{2}:\d{2}")


class TestCdcFixtureFiles:
    """Verify CDC fixture files exist and are valid."""

    def test_cdc_list_html_exists(self):
        """CDC list page fixture file must exist."""
        path = RAW_DIR / "cdc-list.html"
        assert path.is_file(), f"CDC list fixture not found at {path}"

    def test_cdc_list_html_is_valid_html(self):
        """CDC list page fixture must contain valid HTML structure."""
        path = RAW_DIR / "cdc-list.html"
        content = path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content.lower() or "<html" in content.lower()
        assert "</html>" in content.lower()

    def test_cdc_list_html_has_feed_items(self):
        """CDC list page fixture must contain at least 3 feed items."""
        path = RAW_DIR / "cdc-list.html"
        content = path.read_text(encoding="utf-8")
        assert content.count("feed-item") >= 3

    def test_cdc_detail_html_exists(self):
        """CDC detail page fixture file must exist."""
        path = RAW_DIR / "cdc-detail.html"
        assert path.is_file(), f"CDC detail fixture not found at {path}"

    def test_cdc_detail_html_is_valid_html(self):
        """CDC detail page fixture must contain valid HTML structure."""
        path = RAW_DIR / "cdc-detail.html"
        content = path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content.lower() or "<html" in content.lower()
        assert "</html>" in content.lower()


class TestSinaFixtureFiles:
    """Verify Sina fixture files exist and are valid."""

    def test_sina_feed_json_exists(self):
        """Sina feed fixture file must exist."""
        path = RAW_DIR / "sina-feed.json"
        assert path.is_file(), f"Sina feed fixture not found at {path}"

    def test_sina_feed_json_is_valid_json(self):
        """Sina feed fixture must be valid JSON with a statuses array."""
        path = RAW_DIR / "sina-feed.json"
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "statuses" in data
        assert isinstance(data["statuses"], list)
        assert len(data["statuses"]) >= 1

    def test_sina_feed_json_statuses_have_required_fields(self):
        """Each status in sina-feed.json must have idstr and text."""
        path = RAW_DIR / "sina-feed.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for status in data["statuses"]:
            assert "idstr" in status, f"Status missing 'idstr': {status}"
            assert "text" in status, f"Status missing 'text': {status}"


class TestSina7x24FixtureFiles:
    """Verify Sina 7x24 Markdown fixture file exists and is valid."""

    def test_sina_7x24_md_exists(self):
        """Sina 7x24 Markdown fixture file must exist."""
        path = RAW_DIR / "sina-7x24.md"
        assert path.is_file(), f"Sina 7x24 fixture not found at {path}"

    def test_sina_7x24_md_has_flash_items(self):
        """Sina 7x24 fixture must contain at least 3 flash news items."""
        path = RAW_DIR / "sina-7x24.md"
        content = path.read_text(encoding="utf-8")
        timestamps = _FLASH_PATTERN.findall(content)
        assert len(timestamps) >= 3, (
            f"Expected at least 3 flash items, found {len(timestamps)}"
        )

    def test_sina_7x24_md_has_markdown_links(self):
        """Sina 7x24 fixture must contain wap.cj.sina.cn links."""
        path = RAW_DIR / "sina-7x24.md"
        content = path.read_text(encoding="utf-8")
        links = re.findall(r"https://wap\.cj\.sina\.cn/pc/7x24/\d+", content)
        assert len(links) >= 3, f"Expected at least 3 news links, found {len(links)}"


class TestExpectedOutputFiles:
    """Verify expected output JSON files exist and have valid structure."""

    def test_cdc_detail_items_json_exists(self):
        """Expected CDC detail items output file must exist."""
        path = EXPECTED_DIR / "cdc-detail-items.json"
        assert path.is_file(), f"Expected CDC detail items not found at {path}"

    def test_cdc_detail_items_is_valid_list(self):
        """Expected CDC detail items must be a non-empty list."""
        path = EXPECTED_DIR / "cdc-detail-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_cdc_detail_items_have_required_keys(self):
        """Each expected CDC item must have required keys."""
        path = EXPECTED_DIR / "cdc-detail-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data:
            missing = REQUIRED_ITEM_KEYS - set(item.keys())
            assert not missing, f"Item missing keys: {missing} — item: {item}"

    def test_sina_feed_items_json_exists(self):
        """Expected Sina feed items output file must exist."""
        path = EXPECTED_DIR / "sina-feed-items.json"
        assert path.is_file(), f"Expected Sina feed items not found at {path}"

    def test_sina_feed_items_is_valid_list(self):
        """Expected Sina feed items must be a non-empty list."""
        path = EXPECTED_DIR / "sina-feed-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_sina_feed_items_have_required_keys(self):
        """Each expected Sina item must have required keys."""
        path = EXPECTED_DIR / "sina-feed-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data:
            missing = REQUIRED_ITEM_KEYS - set(item.keys())
            assert not missing, f"Item missing keys: {missing} — item: {item}"

    def test_sina_7x24_items_json_exists(self):
        """Expected Sina 7x24 items output file must exist."""
        path = EXPECTED_DIR / "sina-7x24-items.json"
        assert path.is_file(), f"Expected Sina 7x24 items not found at {path}"

    def test_sina_7x24_items_is_valid_list(self):
        """Expected Sina 7x24 items must be a non-empty list."""
        path = EXPECTED_DIR / "sina-7x24-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_sina_7x24_items_have_required_keys(self):
        """Each expected Sina 7x24 item must have required keys."""
        path = EXPECTED_DIR / "sina-7x24-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data:
            missing = REQUIRED_ITEM_KEYS - set(item.keys())
            assert not missing, f"Item missing keys: {missing} — item: {item}"

    def test_sina_7x24_items_have_flash_type(self):
        """Each expected Sina 7x24 item must have item_type 'flash'."""
        path = EXPECTED_DIR / "sina-7x24-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data:
            assert item["item_type"] == "flash", (
                f"Expected item_type 'flash', got '{item['item_type']}'"
            )

    def test_sina_7x24_items_have_extra_time(self):
        """Each expected Sina 7x24 item must have extra.time."""
        path = EXPECTED_DIR / "sina-7x24-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data:
            assert "extra" in item, f"Item missing 'extra': {item}"
            assert "time" in item["extra"], f"Item extra missing 'time': {item}"

    def test_sina_7x24_items_have_read_count(self):
        """Each expected Sina 7x24 item must have extra.read_count."""
        path = EXPECTED_DIR / "sina-7x24-items.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data:
            assert "extra" in item, f"Item missing 'extra': {item}"
            assert "read_count" in item["extra"], (
                f"Item extra missing 'read_count': {item}"
            )

    def test_sina_7x24_extractor_matches_expected(self):
        """Extractor output on fixture raw must match expected items."""
        from harvester.extractors.sina_7x24 import Sina7x24Extractor

        raw = (RAW_DIR / "sina-7x24.md").read_text(encoding="utf-8")
        expected = json.loads(
            (EXPECTED_DIR / "sina-7x24-items.json").read_text(encoding="utf-8")
        )
        items = Sina7x24Extractor().extract({}, raw)
        assert len(items) == len(expected)
        for item, exp in zip(items, expected):
            assert item.external_item_id == exp["external_item_id"], (
                f"ID mismatch: {item.external_item_id} != {exp['external_item_id']}"
            )
            assert item.title == exp["title"], (
                f"Title mismatch for {exp['external_item_id']}: "
                f"{item.title!r} != {exp['title']!r}"
            )
            assert item.final_url == exp["final_url"]
            assert item.extra["time"] == exp["extra"]["time"]
            assert item.extra["read_count"] == exp["extra"]["read_count"]
