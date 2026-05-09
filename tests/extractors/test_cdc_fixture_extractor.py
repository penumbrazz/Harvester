"""Tests for the CDC fixture extractor."""

import json

from harvester.extractors.base import CandidateItem
from harvester.extractors.cdc_fixture import CdcFixtureExtractor


SAMPLE_PAYLOAD = json.dumps([
    {
        "id": 1,
        "title": "First Article",
        "url": "https://example.com/1",
        "content": "Content of the first article.",
    },
    {
        "id": 2,
        "title": "Second Article",
        "url": "https://example.com/2",
        "content": "Content of the second article.",
    },
    {
        "id": 3,
        "title": "Third Article",
        "url": "https://example.com/3",
        "content": "Content of the third article.",
    },
])


class TestCdcFixtureExtractor:
    """Tests for the CdcFixtureExtractor."""

    def test_extracts_all_items(self):
        """Should extract one CandidateItem per entry in the JSON array."""
        extractor = CdcFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)
        assert len(items) == 3

    def test_extracts_item_fields(self):
        """Should map fixture fields to CandidateItem attributes."""
        extractor = CdcFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)

        first = items[0]
        assert first.external_item_id == "1"
        assert first.item_type == "article"
        assert first.title == "First Article"
        assert first.original_url == "https://example.com/1"
        assert first.final_url == "https://example.com/1"
        assert first.content_text == "Content of the first article."

    def test_sets_position_index(self):
        """Should set position to the array index of each item."""
        extractor = CdcFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)

        assert items[0].position == 0
        assert items[1].position == 1
        assert items[2].position == 2

    def test_handles_bytes_payload(self):
        """Should accept bytes as well as string payload."""
        extractor = CdcFixtureExtractor()
        payload_bytes = SAMPLE_PAYLOAD.encode("utf-8")
        items = extractor.extract({}, payload_bytes)
        assert len(items) == 3

    def test_handles_empty_array(self):
        """Should return an empty list for an empty JSON array."""
        extractor = CdcFixtureExtractor()
        items = extractor.extract({}, "[]")
        assert items == []

    def test_handles_missing_fields_gracefully(self):
        """Should handle items with missing optional fields."""
        extractor = CdcFixtureExtractor()
        payload = json.dumps([{"id": 42}])
        items = extractor.extract({}, payload)
        assert len(items) == 1
        assert items[0].external_item_id == "42"
        assert items[0].title is None
        assert items[0].content_text == ""

    def test_returns_candidate_items(self):
        """All returned items should be CandidateItem instances."""
        extractor = CdcFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)
        for item in items:
            assert isinstance(item, CandidateItem)
