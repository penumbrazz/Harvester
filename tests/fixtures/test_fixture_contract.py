"""Contract tests for fixture files — verify all expected files exist and are valid."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Base paths
FIXTURES_DIR = Path(__file__).parent
RAW_DIR = FIXTURES_DIR / "raw"
EXPECTED_DIR = FIXTURES_DIR / "expected"

# Required keys for every expected output item
REQUIRED_ITEM_KEYS = {"external_item_id", "item_type", "title"}


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
