"""Tests for the extractor interface (CandidateItem and Extractor protocol)."""

from harvester.extractors.base import (
    CandidateItem,
    DiscoveredTarget,
    ExtractionOutput,
    normalize_extraction_output,
)


class TestCandidateItem:
    """Tests for the CandidateItem dataclass."""

    def test_default_values(self):
        """CandidateItem should have sensible defaults."""
        item = CandidateItem()
        assert item.external_item_id is None
        assert item.item_type == "post"
        assert item.title is None
        assert item.original_url is None
        assert item.final_url is None
        assert item.canonical_url is None
        assert item.canonical_url_hash is None
        assert item.content_text == ""
        assert item.language is None
        assert item.position is None
        assert item.observed_url is None
        assert item.payload_hash is None
        assert item.snippet is None
        assert item.extra == {}

    def test_custom_values(self):
        """CandidateItem should accept custom field values."""
        item = CandidateItem(
            external_item_id="ext-123",
            item_type="article",
            title="Test Article",
            original_url="https://example.com/article",
            content_text="Full article text",
            language="en",
            position=0,
            snippet="Short snippet",
            extra={"key": "value"},
        )
        assert item.external_item_id == "ext-123"
        assert item.item_type == "article"
        assert item.title == "Test Article"
        assert item.content_text == "Full article text"
        assert item.language == "en"
        assert item.position == 0
        assert item.snippet == "Short snippet"
        assert item.extra == {"key": "value"}

    def test_extra_dict_is_independent(self):
        """Each CandidateItem should have its own extra dict."""
        item1 = CandidateItem()
        item2 = CandidateItem()
        item1.extra["foo"] = "bar"
        assert "foo" not in item2.extra

    def test_is_dataclass(self):
        """CandidateItem should be a dataclass with proper attributes."""
        item = CandidateItem(title="hello")
        assert hasattr(item, "__dataclass_fields__")
        assert item.title == "hello"


class TestDiscoveredTarget:
    """Tests for the DiscoveredTarget dataclass."""

    def test_custom_values(self):
        """DiscoveredTarget should describe a crawl target candidate."""
        target = DiscoveredTarget(
            target_url="https://www.chinacdc.cn/detail.html",
            target_role="detail",
            media_type="html",
            content_type="text/html",
            depth=1,
            priority=5,
            external_item_id="cncdc-flu-weekly:2026:18",
        )

        assert target.target_url == "https://www.chinacdc.cn/detail.html"
        assert target.target_role == "detail"
        assert target.media_type == "html"
        assert target.content_type == "text/html"
        assert target.depth == 1
        assert target.priority == 5
        assert target.external_item_id == "cncdc-flu-weekly:2026:18"


class TestExtractionOutput:
    """Tests for combined extractor output."""

    def test_combines_items_and_discovered_targets(self):
        """ExtractionOutput should carry content candidates and target candidates."""
        output = ExtractionOutput(
            items=[CandidateItem(title="weekly report")],
            discovered_targets=[
                DiscoveredTarget(
                    target_url="https://www.chinacdc.cn/detail.html",
                    target_role="detail",
                    media_type="html",
                    content_type="text/html",
                )
            ],
        )

        assert len(output.items) == 1
        assert len(output.discovered_targets) == 1

    def test_legacy_candidate_list_is_normalized(self):
        """Existing extractors returning list[CandidateItem] should stay compatible."""
        legacy = [CandidateItem(title="legacy")]

        output = normalize_extraction_output(legacy)

        assert output.items == legacy
        assert output.discovered_targets == []


class TestExtractorProtocol:
    """Tests for the Extractor protocol interface."""

    def test_protocol_has_extract_method(self):
        """Extractor protocol should define an extract method."""
        from harvester.extractors.base import Extractor

        assert hasattr(Extractor, "extract")

    def test_concrete_implementation_satisfies_protocol(self):
        """A class with extract(metadata, payload) -> list[CandidateItem] should satisfy Extractor."""

        class DummyExtractor:
            def extract(self, raw_metadata: dict, raw_payload: str | bytes):
                return [CandidateItem(title="test")]

        extractor = DummyExtractor()
        items = extractor.extract({}, "test")
        assert len(items) == 1
        assert items[0].title == "test"

    def test_extract_receives_metadata_and_payload(self):
        """Extract should receive both metadata dict and raw payload."""
        received = {}

        class SpyExtractor:
            def extract(self, raw_metadata: dict, raw_payload: str | bytes):
                received["metadata"] = raw_metadata
                received["payload"] = raw_payload
                return []

        spy = SpyExtractor()
        spy.extract({"source": "test"}, "<html></html>")
        assert received["metadata"] == {"source": "test"}
        assert received["payload"] == "<html></html>"
