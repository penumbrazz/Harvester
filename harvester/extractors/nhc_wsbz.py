"""NHC health standards (卫生健康标准) discovery extractors.

Handles the multi-level page structure:
- List page: table with standard entries and detail page links
- Detail page: standard metadata with PDF download link
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin

from harvester.domain.urls import compute_canonical_url_hash, normalize_url
from harvester.extractors.base import CandidateItem, DiscoveredTarget, ExtractionOutput

# Detail page URL pattern: /wjw/{section}/{YYYYMM}/{hash}.shtml
_DETAIL_URL_RE = re.compile(r"/wjw/\w+/\d{6}/[a-f0-9]+\.shtml")

# PDF link pattern in detail page content area
_PDF_LINK_RE = re.compile(r'href="([^"]*?\.pdf)"')

# Standard number pattern (WS/T 874—2025, GBZ 42—2025, etc.)
_STD_NUM_RE = re.compile(
    r"(WS\s*/?\s*T?\s*[\d.]+[\s—-]*\d+|GBZ\s*/?\s*T?\s*[\d.]+[\s—-]*\d+)"
)

# Section code from NHC URL path: /wjw/{section}/...
_SECTION_RE = re.compile(r"/wjw/(\w+)/\d{6}/")

# NHC section code -> Chinese category name
_NHC_SECTION_CATEGORIES: dict[str, str] = {
    "pyl": "职业健康",
    "fsgc": "放射卫生",
    "s9497": "卫生健康信息",
    "s9493": "临床检验",
    "s9496": "环境健康",
    "s9494": "学校卫生",
    "s9495": "传染病",
    "s9498": "消毒",
    "s9499": "寄生虫病",
    "s9500": "地方病",
    "s9501": "食品卫生",
    "s9502": "营养",
    "s9503": "精神卫生",
    "c100309": "医疗服务",
    "c100310": "老年健康",
    "c100311": "基层卫生",
    "c100312": "妇幼健康",
    "c100313": "药政管理",
    "c100314": "综合监督",
    "c100315": "疾病控制",
    "c100316": "卫生应急",
    "c100317": "政策法规",
    "c100318": "人事管理",
    "c100319": "规划信息",
    "c100320": "财务管理",
    "c100321": "国际合作",
    "c100322": "宣传",
    "c100323": "机关党建",
    "c100324": "科技教育",
}


def _category_for_url(url: str) -> str | None:
    """Extract Chinese category name from NHC URL path."""
    match = _SECTION_RE.search(url)
    if match:
        section = match.group(1)
        return _NHC_SECTION_CATEGORIES.get(section)
    return None


class _ListRowParser(HTMLParser):
    """Parse the standards table from NHC list page HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[dict] = []
        self._in_data_row = False
        self._td_index = 0
        self._current_href: str | None = None
        self._current_title: str | None = None
        self._td_texts: list[str] = []
        self._capture_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        if tag == "tr" and "xx" in cls:
            self._in_data_row = True
            self._td_index = 0
            self._current_href = None
            self._current_title = None
        elif self._in_data_row and tag == "td":
            self._td_texts = []
            self._capture_text = True
        elif self._in_data_row and tag == "a" and self._td_index == 2:
            self._current_href = attrs_dict.get("href")
            self._current_title = attrs_dict.get("title")
            self._td_texts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._capture_text:
            text = _clean_text(" ".join(self._td_texts))
            if self._in_data_row:
                if self._td_index == 1:
                    self._current_std_num = text
                elif self._td_index == 2 and not self._current_title:
                    self._current_title = text
                elif self._td_index == 3:
                    self._current_publish_date = text
                elif self._td_index == 4:
                    self._current_impl_date = text
            self._td_index += 1
            self._capture_text = False
        elif tag == "tr" and self._in_data_row:
            if self._current_href and self._td_index >= 3:
                # Initialize attributes that may not have been set
                std_num = getattr(self, "_current_std_num", "")
                publish_date = getattr(self, "_current_publish_date", "")
                impl_date = getattr(self, "_current_impl_date", "")
                self.entries.append(
                    {
                        "std_num": std_num,
                        "title": self._current_title or "",
                        "href": self._current_href or "",
                        "publish_date": publish_date,
                        "impl_date": impl_date,
                    }
                )
            self._in_data_row = False

    def handle_data(self, data: str) -> None:
        if self._capture_text:
            self._td_texts.append(data.strip())


class _DetailParser(HTMLParser):
    """Parse standard metadata and PDF link from NHC detail page HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.publish_date = ""
        self.impl_date = ""
        self.std_num = ""
        self.pdf_href: str | None = None

        self._in_title = False
        self._in_con = False
        self._title_parts: list[str] = []

        # Label/value tracking for the metadata table
        self._in_label_cell = False
        self._expecting_value = False
        self._current_label = ""
        self._label_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        if tag == "div" and cls == "tit":
            self._in_title = True
            self._title_parts = []
        elif tag == "div" and cls == "con":
            self._in_con = True
        elif tag == "td":
            td_cls = attrs_dict.get("class", "")
            if "xxgk_td_bgcolor" in td_cls:
                # This is a label cell (标准号, 标准名, etc.)
                self._in_label_cell = True
                self._label_parts = []
            elif self._expecting_value:
                # This is the value cell after a label
                pass
        elif tag == "a" and self._in_con:
            href = attrs_dict.get("href", "")
            if href.lower().endswith(".pdf") and not self.pdf_href:
                self.pdf_href = href

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._in_title:
            self.title = _clean_text(" ".join(self._title_parts))
            self._in_title = False
        elif tag == "div" and self._in_con:
            self._in_con = False
        elif tag == "td" and self._in_label_cell:
            # Label cell closed, next td will be the value
            self._in_label_cell = False
            self._current_label = _clean_text(" ".join(self._label_parts))
            if self._current_label in ("标准号", "标准名", "发布时间", "实施时间"):
                self._expecting_value = True
        elif tag == "td" and self._expecting_value:
            self._expecting_value = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
            return

        stripped = data.strip()
        if not stripped:
            return

        if self._in_label_cell:
            self._label_parts.append(stripped)
            return

        if self._expecting_value:
            if self._current_label == "标准号":
                self.std_num = stripped
            elif self._current_label == "标准名":
                if not self.title:
                    self.title = stripped
            elif self._current_label == "发布时间":
                self.publish_date = stripped
            elif self._current_label == "实施时间":
                self.impl_date = stripped
            self._current_label = ""


def _parse_list_html(payload: str) -> list[dict]:
    """Parse list page HTML and return standard entries."""
    parser = _ListRowParser()
    parser.feed(payload)
    return parser.entries


def _parse_detail_html(payload: str) -> dict:
    """Parse detail page HTML and return standard metadata with PDF link."""
    parser = _DetailParser()
    parser.feed(payload)

    # Also extract PDF link via regex as fallback
    pdf_href = parser.pdf_href
    if not pdf_href:
        match = _PDF_LINK_RE.search(payload)
        if match:
            pdf_href = match.group(1)

    return {
        "title": parser.title,
        "std_num": parser.std_num,
        "publish_date": parser.publish_date,
        "impl_date": parser.impl_date,
        "pdf_href": pdf_href,
    }


def _make_external_item_id(std_num: str, fallback_url: str) -> str:
    """Generate external_item_id from standard number or URL hash."""
    cleaned = std_num.replace(" ", "").strip()
    if cleaned:
        return f"nhc-wsbz:{cleaned}"
    return f"nhc-wsbz:url:{compute_canonical_url_hash(fallback_url)[:16]}"


def _clean_text(text: str) -> str:
    return " ".join(text.split())


class NhcWsbzListExtractor:
    """Extract NHC health standard entries and discover detail page targets."""

    def extract(
        self,
        raw_metadata: dict,
        raw_payload: str | bytes,
    ) -> ExtractionOutput:
        payload = _decode_payload(raw_payload)
        source_url = raw_metadata.get("source_url") or ""

        entries = _parse_list_html(payload)
        output = ExtractionOutput()

        for position, entry in enumerate(entries):
            href = entry.get("href", "")
            title = entry.get("title", "")
            std_num = entry.get("std_num", "")

            if not href or not title:
                continue

            detail_url = urljoin(source_url, href)
            external_item_id = _make_external_item_id(std_num, detail_url)

            item = CandidateItem(
                external_item_id=external_item_id,
                item_type="standard",
                title=title,
                original_url=detail_url,
                canonical_url=normalize_url(detail_url),
                canonical_url_hash=compute_canonical_url_hash(detail_url),
                content_text=f"{std_num} {title}",
                language="zh",
                position=position,
                observed_url=source_url,
                snippet=title,
                extra={
                    "std_num": std_num,
                    "publish_date": entry.get("publish_date", ""),
                    "impl_date": entry.get("impl_date", ""),
                },
            )
            output.items.append(item)
            output.discovered_targets.append(
                DiscoveredTarget(
                    target_url=detail_url,
                    target_role="detail",
                    media_type="html",
                    content_type="text/html",
                    external_item_id=external_item_id,
                    depth=1,
                    priority=0,
                    category=_category_for_url(detail_url),
                )
            )
        return output


class NhcWsbzDetailExtractor:
    """Extract NHC standard detail metadata and discover PDF asset targets."""

    def extract(
        self,
        raw_metadata: dict,
        raw_payload: str | bytes,
    ) -> ExtractionOutput:
        payload = _decode_payload(raw_payload)
        detail_url = (
            raw_metadata.get("target_url") or raw_metadata.get("source_url") or ""
        )

        parsed = _parse_detail_html(payload)
        std_num = parsed.get("std_num", "")
        title = parsed.get("title", "")
        pdf_href = parsed.get("pdf_href")

        external_item_id = _make_external_item_id(std_num, detail_url)

        extra = {}
        if parsed.get("publish_date"):
            extra["publish_date"] = parsed["publish_date"]
        if parsed.get("impl_date"):
            extra["impl_date"] = parsed["impl_date"]

        output = ExtractionOutput(
            items=[
                CandidateItem(
                    external_item_id=external_item_id,
                    item_type="standard",
                    title=title,
                    original_url=detail_url,
                    canonical_url=normalize_url(detail_url),
                    canonical_url_hash=compute_canonical_url_hash(detail_url),
                    content_text=f"{std_num} {title}",
                    language="zh",
                    position=0,
                    observed_url=detail_url,
                    snippet=title,
                    extra=extra,
                )
            ]
        )

        if pdf_href:
            pdf_url = urljoin(detail_url, pdf_href)
            output.discovered_targets.append(
                DiscoveredTarget(
                    target_url=pdf_url,
                    target_role="asset",
                    media_type="pdf",
                    content_type="application/pdf",
                    external_item_id=external_item_id,
                    depth=2,
                    priority=0,
                    category=_category_for_url(detail_url),
                )
            )
        return output


def _decode_payload(raw_payload: str | bytes) -> str:
    if isinstance(raw_payload, bytes):
        return raw_payload.decode("utf-8")
    return raw_payload
