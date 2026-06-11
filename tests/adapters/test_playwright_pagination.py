"""Tests for Playwright AJAX pagination — JSON→HTML conversion."""

from __future__ import annotations

from harvester.adapters.playwright import (
    _fetch_nhc_ajax_pages,
    _nhc_json_to_table_rows,
    _nhc_meta_value,
)


def _sample_result(
    *,
    title: str = "测试标准",
    url: str = "/wjw/s9493/202604/abc123.shtml",
    std_num: str = "WS/T 875—2025",
    publish_date: str = "2025年9月12日",
    impl_date: str = "2026年3月1日",
    published: str = "2025-09-12",
) -> dict:
    """Build a single NHC AJAX JSON result item."""
    return {
        "title": title,
        "url": url,
        "publishedTimeStr": published,
        "domainMetaList": [
            {
                "resultList": [
                    {"name": "标准号", "value": std_num},
                    {"name": "发布时间", "value": publish_date},
                    {"name": "实施时间", "value": impl_date},
                ]
            }
        ],
    }


class TestNhcJsonToTableRows:
    """Convert NHC AJAX JSON results to HTML table rows."""

    def test_single_result_produces_tr(self):
        results = [_sample_result()]
        html = _nhc_json_to_table_rows(results)
        assert '<tr bgcolor="#ffffff" class="xx">' in html
        assert "</tr>" in html

    def test_includes_std_num(self):
        results = [_sample_result(std_num="WS/T 875—2025")]
        html = _nhc_json_to_table_rows(results)
        assert "WS/T 875—2025" in html

    def test_includes_title_link(self):
        results = [
            _sample_result(
                title="血液净化标准",
                url="/wjw/s9493/202604/abc123.shtml",
            )
        ]
        html = _nhc_json_to_table_rows(results)
        assert 'href="/wjw/s9493/202604/abc123.shtml"' in html
        assert 'title="血液净化标准"' in html
        assert "血液净化标准" in html

    def test_includes_dates(self):
        results = [
            _sample_result(publish_date="2025年9月12日", impl_date="2026年3月1日")
        ]
        html = _nhc_json_to_table_rows(results)
        assert "2025年9月12日" in html
        assert "2026年3月1日" in html

    def test_multiple_results(self):
        results = [
            _sample_result(title="标准A"),
            _sample_result(title="标准B"),
        ]
        html = _nhc_json_to_table_rows(results)
        assert html.count('class="xx"') == 2

    def test_empty_results(self):
        html = _nhc_json_to_table_rows([])
        assert html == ""

    def test_missing_meta_fields(self):
        """Result without domainMetaList should still produce a row."""
        results = [{"title": "无元数据标准", "url": "/wjw/test/123.shtml"}]
        html = _nhc_json_to_table_rows(results)
        assert 'class="xx"' in html
        assert "无元数据标准" in html

    def test_row_format_matches_extractor(self):
        """Generated HTML must be parseable by NhcWsbzListExtractor."""
        from harvester.extractors.nhc_wsbz import _parse_list_html

        results = [
            _sample_result(
                std_num="WS/T 875—2025",
                title="临床检验标准",
                url="/wjw/s9493/202604/abc123.shtml",
                publish_date="2025年9月12日",
                impl_date="2026年3月1日",
            )
        ]
        rows_html = _nhc_json_to_table_rows(results)
        # Wrap in a minimal table like the real page
        full_html = (
            "<html><body><table>"
            '<tbody id="listContent">' + rows_html + "</tbody></table></body></html>"
        )
        entries = _parse_list_html(full_html)
        assert len(entries) == 1
        assert entries[0]["std_num"] == "WS/T 875—2025"
        assert entries[0]["title"] == "临床检验标准"
        assert "/wjw/s9493/202604/abc123.shtml" in entries[0]["href"]
        assert entries[0]["publish_date"] == "2025年9月12日"
        assert entries[0]["impl_date"] == "2026年3月1日"


class TestNhcMetaValue:
    """Extract named values from NHC domainMetaList."""

    def test_extracts_std_num(self):
        result = _sample_result()
        assert _nhc_meta_value(result, "标准号") == "WS/T 875—2025"

    def test_extracts_publish_date(self):
        result = _sample_result()
        assert _nhc_meta_value(result, "发布时间") == "2025年9月12日"

    def test_extracts_impl_date(self):
        result = _sample_result()
        assert _nhc_meta_value(result, "实施时间") == "2026年3月1日"

    def test_missing_key_returns_empty(self):
        result = _sample_result()
        assert _nhc_meta_value(result, "不存在") == ""

    def test_no_domain_meta_list(self):
        result = {"title": "test"}
        assert _nhc_meta_value(result, "标准号") == ""


class TestInjectRowsIntoHtml:
    """Inject AJAX rows into original page HTML."""

    def test_injects_before_closing_tbody(self):
        from harvester.adapters.playwright import _inject_rows_into_html

        original = (
            "<html><body>"
            '<tbody id="listContent">'
            '<tr class="xx"><td>existing</td></tr>'
            "</tbody>"
            "</body></html>"
        )
        rows = '<tr class="xx"><td>new row</td></tr>'
        result = _inject_rows_into_html(original, rows)
        assert result.index("existing") < result.index("new row")
        assert result.index("new row") < result.index("</tbody>")

    def test_preserves_original_content(self):
        from harvester.adapters.playwright import _inject_rows_into_html

        original = (
            "<html><head><title>Test</title></head><body>"
            '<tbody id="listContent"><tr><td>keep</td></tr></tbody>'
            "</body></html>"
        )
        rows = '<tr class="xx"><td>injected</td></tr>'
        result = _inject_rows_into_html(original, rows)
        assert "<title>Test</title>" in result
        assert "keep" in result
        assert "injected" in result

    def test_empty_rows_returns_original(self):
        from harvester.adapters.playwright import _inject_rows_into_html

        original = "<html><body><tbody></tbody></body></html>"
        result = _inject_rows_into_html(original, "")
        assert result == original


class TestFetchNhcAjaxPages:
    """Unit test for _fetch_nhc_ajax_pages with mocked page.evaluate."""

    def test_fetches_all_pages(self):
        """Should fetch page 1, then pages 2 through total_pages."""

        class FakePage:
            def __init__(self):
                self.call_count = 0

            def evaluate(self, expr: str) -> dict:
                self.call_count += 1
                # Return 40 items on page 1, 10 on page 2
                total = 50
                page_size = 20
                page_num = self.call_count
                start = (page_num - 1) * page_size
                remaining = total - start
                count = min(page_size, remaining)
                results = [
                    {"title": f"标准{i}", "url": f"/wjw/test/{i}.shtml"}
                    for i in range(start, start + count)
                ]
                return {"data": {"total": total, "results": results}}

        page = FakePage()
        results = _fetch_nhc_ajax_pages(page, "fake-channel-id", max_pages=200)
        assert len(results) == 50
        assert page.call_count == 3  # pages 1, 2, 3

    def test_respects_max_pages(self):
        """Should not exceed max_pages limit."""

        class FakePage:
            def __init__(self):
                self.call_count = 0

            def evaluate(self, expr: str) -> dict:
                self.call_count += 1
                return {
                    "data": {
                        "total": 100,
                        "results": [{"title": f"item{i}"} for i in range(20)],
                    }
                }

        page = FakePage()
        results = _fetch_nhc_ajax_pages(page, "fake-channel-id", max_pages=2)
        assert page.call_count == 2
        assert len(results) == 40

    def test_single_page(self):
        """If total <= pageSize, only one page fetched."""

        class FakePage:
            def __init__(self):
                self.call_count = 0

            def evaluate(self, expr: str) -> dict:
                self.call_count += 1
                return {
                    "data": {
                        "total": 15,
                        "results": [{"title": f"item{i}"} for i in range(15)],
                    }
                }

        page = FakePage()
        results = _fetch_nhc_ajax_pages(page, "fake-channel-id", max_pages=200)
        assert page.call_count == 1
        assert len(results) == 15
