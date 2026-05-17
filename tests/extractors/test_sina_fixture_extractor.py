"""Tests for the Sina fixture extractor."""

import json

from harvester.extractors.base import CandidateItem
from harvester.extractors.sina_fixture import SinaFixtureExtractor

SAMPLE_PAYLOAD = json.dumps(
    {
        "statuses": [
            {
                "idstr": "1234567890",
                "text": "Hello world from Weibo!",
                "source": "iPhone",
                "created_at": "Fri Jan 01 00:00:00 +0800 2025",
            },
            {
                "idstr": "9876543210",
                "text": "Another post with more content.",
                "source": "Android",
                "created_at": "Fri Jan 02 00:00:00 +0800 2025",
            },
        ]
    }
)


class TestSinaFixtureExtractor:
    """Tests for the SinaFixtureExtractor."""

    def test_extracts_all_statuses(self):
        """Should extract one CandidateItem per status in the array."""
        extractor = SinaFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)
        assert len(items) == 2

    def test_extracts_status_fields(self):
        """Should map status fields to CandidateItem attributes."""
        extractor = SinaFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)

        first = items[0]
        assert first.external_item_id == "1234567890"
        assert first.item_type == "post"
        assert first.content_text == "Hello world from Weibo!"
        assert first.position == 0

    def test_stores_extra_metadata(self):
        """Should store source and created_at in extra dict."""
        extractor = SinaFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)

        first = items[0]
        assert first.extra["source"] == "iPhone"
        assert first.extra["created_at"] == "Fri Jan 01 00:00:00 +0800 2025"

    def test_generates_snippet(self):
        """Should generate a snippet from the text content."""
        extractor = SinaFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)
        assert items[0].snippet == "Hello world from Weibo!"

    def test_truncates_long_text_for_snippet(self):
        """Snippet should be truncated at 200 characters."""
        extractor = SinaFixtureExtractor()
        long_text = "x" * 300
        payload = json.dumps(
            {
                "statuses": [
                    {
                        "idstr": "1",
                        "text": long_text,
                        "source": "Web",
                        "created_at": "now",
                    }
                ]
            }
        )
        items = extractor.extract({}, payload)
        assert len(items[0].snippet) == 200

    def test_handles_bytes_payload(self):
        """Should accept bytes payload."""
        extractor = SinaFixtureExtractor()
        payload_bytes = SAMPLE_PAYLOAD.encode("utf-8")
        items = extractor.extract({}, payload_bytes)
        assert len(items) == 2

    def test_handles_empty_statuses(self):
        """Should return an empty list for empty statuses array."""
        extractor = SinaFixtureExtractor()
        items = extractor.extract({}, '{"statuses": []}')
        assert items == []

    def test_handles_missing_statuses_key(self):
        """Should return an empty list when statuses key is absent."""
        extractor = SinaFixtureExtractor()
        items = extractor.extract({}, "{}")
        assert items == []

    def test_returns_candidate_items(self):
        """All returned items should be CandidateItem instances."""
        extractor = SinaFixtureExtractor()
        items = extractor.extract({}, SAMPLE_PAYLOAD)
        for item in items:
            assert isinstance(item, CandidateItem)
