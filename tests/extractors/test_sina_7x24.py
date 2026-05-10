"""Tests for the Sina7x24Extractor."""

from harvester.extractors.base import CandidateItem
from harvester.extractors.sina_7x24 import Sina7x24Extractor


# Minimal sample with 3 items
SAMPLE_3_ITEMS = """\
[返回顶部](javascript:; "返回顶部")
[关闭](javascript:; "关闭")

21:37:33

[黎巴嫩总理纳瓦夫·萨拉姆：已与叙利亚方面达成协议。](https://wap.cj.sina.cn/pc/7x24/4869892)

43.74万 阅读

0

21:36:50

[第二条快讯](https://wap.cj.sina.cn/pc/7x24/4869891)

3200 阅读

0

21:35:24

[第三条快讯](https://wap.cj.sina.cn/pc/7x24/4869890)

86.60万 阅读

0
"""


class TestExtractsMultipleItems:
    """Should extract all flash news items from Markdown payload."""

    def test_extracts_3_items(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert len(items) == 3

    def test_returns_candidate_items(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        for item in items:
            assert isinstance(item, CandidateItem)


class TestExtractsIdAndUrl:
    """Should extract external_item_id and URLs from Markdown links."""

    def test_external_item_id(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[0].external_item_id == "4869892"
        assert items[1].external_item_id == "4869891"
        assert items[2].external_item_id == "4869890"

    def test_final_url(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[0].final_url == "https://wap.cj.sina.cn/pc/7x24/4869892"

    def test_original_url(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[0].original_url == "https://wap.cj.sina.cn/pc/7x24/4869892"


class TestExtractsTimestamp:
    """Should extract HH:MM:SS timestamps into extra.time."""

    def test_time_extracted(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[0].extra["time"] == "21:37:33"
        assert items[1].extra["time"] == "21:36:50"
        assert items[2].extra["time"] == "21:35:24"


class TestExtractsReadCount:
    """Should extract read counts, converting wan (万) to integers."""

    def test_wan_level_read_count(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[0].extra["read_count"] == 437400

    def test_normal_read_count(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[1].extra["read_count"] == 3200

    def test_large_wan_read_count(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[2].extra["read_count"] == 866000


class TestExtractsTitle:
    """Should extract title from Markdown link text."""

    def test_title_is_link_text(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[0].title == "黎巴嫩总理纳瓦夫·萨拉姆：已与叙利亚方面达成协议。"

    def test_content_text_matches_title(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[0].content_text == items[0].title


class TestItemType:
    """Should set item_type to 'flash'."""

    def test_flash_type(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        for item in items:
            assert item.item_type == "flash"


class TestPosition:
    """Should assign sequential position indices."""

    def test_positions(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        assert items[0].position == 0
        assert items[1].position == 1
        assert items[2].position == 2


class TestEmptyPayload:
    """Should return empty list for empty or non-matching payload."""

    def test_empty_string(self):
        items = Sina7x24Extractor().extract({}, "")
        assert items == []

    def test_no_flash_pattern(self):
        items = Sina7x24Extractor().extract({}, "Some random text without pattern")
        assert items == []

    def test_bytes_payload(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS.encode("utf-8"))
        assert len(items) == 3


class TestSkipsNoise:
    """Should skip non-flash content in the page header/footer."""

    def test_skips_header_noise(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        # All items should have valid URLs, not javascript: links
        for item in items:
            assert item.final_url is not None
            assert "javascript" not in item.final_url

    def test_only_extracts_valid_items(self):
        items = Sina7x24Extractor().extract({}, SAMPLE_3_ITEMS)
        for item in items:
            assert item.external_item_id is not None
            assert item.title is not None
            assert item.extra.get("time") is not None


class TestMissingReadCount:
    """Should handle items without read count gracefully."""

    def test_missing_read_count(self):
        payload = """\
21:37:33

[快讯标题](https://wap.cj.sina.cn/pc/7x24/1234567)

0
"""
        items = Sina7x24Extractor().extract({}, payload)
        assert len(items) == 1
        assert items[0].extra.get("read_count") is None


class TestReadCountPrecision:
    """Should parse wan-level read counts without float precision loss."""

    def test_057_wan(self):
        payload = """\
21:37:33

[快讯](https://wap.cj.sina.cn/pc/7x24/1000001)

0.57万 阅读

0
"""
        items = Sina7x24Extractor().extract({}, payload)
        assert items[0].extra["read_count"] == 5700

    def test_113_wan(self):
        payload = """\
21:37:33

[快讯](https://wap.cj.sina.cn/pc/7x24/1000002)

1.13万 阅读

0
"""
        items = Sina7x24Extractor().extract({}, payload)
        assert items[0].extra["read_count"] == 11300

    def test_integer_wan(self):
        payload = """\
21:37:33

[快讯](https://wap.cj.sina.cn/pc/7x24/1000003)

43万 阅读

0
"""
        items = Sina7x24Extractor().extract({}, payload)
        assert items[0].extra["read_count"] == 430000

    def test_four_decimal_wan(self):
        payload = """\
21:37:33

[快讯](https://wap.cj.sina.cn/pc/7x24/1000004)

1.0844万 阅读

0
"""
        items = Sina7x24Extractor().extract({}, payload)
        assert items[0].extra["read_count"] == 10844


class TestSkipsInvalidUrls:
    """Should skip items with non-sina or missing-ID URLs."""

    def test_skips_non_sina_link(self):
        payload = """\
21:37:33

[快讯](https://example.com/some/page)

0
"""
        items = Sina7x24Extractor().extract({}, payload)
        assert items == []

    def test_skips_javascript_link(self):
        payload = """\
21:37:33

[快讯](javascript:;)

0
"""
        items = Sina7x24Extractor().extract({}, payload)
        assert items == []

    def test_position_renumbers_after_skip(self):
        payload = """\
21:37:33

[快讯](https://example.com/page)

0

21:36:50

[有效快讯](https://wap.cj.sina.cn/pc/7x24/9988776)

3200 阅读

0
"""
        items = Sina7x24Extractor().extract({}, payload)
        assert len(items) == 1
        assert items[0].external_item_id == "9988776"
        assert items[0].position == 0
