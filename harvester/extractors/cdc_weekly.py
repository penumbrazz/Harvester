"""CDC weekly influenza report discovery extractors."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin

from harvester.domain.urls import compute_canonical_url_hash, normalize_url
from harvester.extractors.base import CandidateItem, DiscoveredTarget, ExtractionOutput

_WEEKLY_ID_RE = re.compile(r"(?P<year>\d{4})年第(?P<week>\d+)周.*?第(?P<issue>\d+)期")


@dataclass
class _ListEntry:
    title: str
    href: str
    published_date: str | None = None


class _WeeklyListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[_ListEntry] = []
        self._in_li = False
        self._current_href: str | None = None
        self._current_title_parts: list[str] = []
        self._current_date_parts: list[str] = []
        self._capture_link = False
        self._capture_date = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "li":
            self._in_li = True
            self._current_href = None
            self._current_title_parts = []
            self._current_date_parts = []
        elif self._in_li and tag == "a":
            self._capture_link = True
            self._current_href = attrs_dict.get("href")
        elif self._in_li and tag == "span" and attrs_dict.get("class") == "date":
            self._capture_date = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._capture_link = False
        elif tag == "span":
            self._capture_date = False
        elif tag == "li":
            title = _clean_text(" ".join(self._current_title_parts))
            published_date = _clean_text(" ".join(self._current_date_parts)) or None
            if self._current_href and title:
                self.entries.append(
                    _ListEntry(
                        title=title,
                        href=self._current_href,
                        published_date=published_date,
                    )
                )
            self._in_li = False

    def handle_data(self, data: str) -> None:
        if self._capture_link:
            self._current_title_parts.append(data)
        elif self._capture_date:
            self._current_date_parts.append(data)


class _WeeklyDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.paragraphs: list[str] = []
        self.pdf_hrefs: list[str] = []
        self._capture_title = False
        self._capture_paragraph = False
        self._paragraph_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "h1":
            self._capture_title = True
        elif tag == "p":
            self._capture_paragraph = True
            self._paragraph_parts = []
        elif tag == "a":
            href = attrs_dict.get("href")
            if href and href.lower().split("?", 1)[0].endswith(".pdf"):
                self.pdf_hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._capture_title = False
        elif tag == "p":
            text = _clean_text(" ".join(self._paragraph_parts))
            if text:
                self.paragraphs.append(text)
            self._capture_paragraph = False

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self.title_parts.append(data)
        elif self._capture_paragraph:
            self._paragraph_parts.append(data)

    @property
    def title(self) -> str:
        return _clean_text(" ".join(self.title_parts))


class CdcWeeklyListExtractor:
    """Extract CDC weekly report item identities and detail targets."""

    def extract(
        self,
        raw_metadata: dict,
        raw_payload: str | bytes,
    ) -> ExtractionOutput:
        payload = _decode_payload(raw_payload)
        source_url = raw_metadata.get("source_url") or ""
        parser = _WeeklyListParser()
        parser.feed(payload)

        output = ExtractionOutput()
        for position, entry in enumerate(parser.entries):
            if "流感监测周报" not in entry.title:
                continue
            detail_url = urljoin(source_url, entry.href)
            external_item_id = _external_item_id_from_title(entry.title, detail_url)
            item = CandidateItem(
                external_item_id=external_item_id,
                item_type="article",
                title=entry.title,
                original_url=detail_url,
                canonical_url=normalize_url(detail_url),
                canonical_url_hash=compute_canonical_url_hash(detail_url),
                content_text=f"{entry.title} {entry.published_date or ''}".strip(),
                language="zh",
                position=position,
                observed_url=source_url,
                snippet=entry.title,
                extra={"published_date": entry.published_date},
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
                )
            )
        return output


class CdcWeeklyDetailExtractor:
    """Extract CDC weekly report detail metadata and PDF asset targets."""

    def extract(
        self,
        raw_metadata: dict,
        raw_payload: str | bytes,
    ) -> ExtractionOutput:
        payload = _decode_payload(raw_payload)
        detail_url = (
            raw_metadata.get("target_url") or raw_metadata.get("source_url") or ""
        )
        parser = _WeeklyDetailParser()
        parser.feed(payload)

        title = parser.title
        external_item_id = _external_item_id_from_title(title, detail_url)
        content_text = " ".join(parser.paragraphs)
        output = ExtractionOutput(
            items=[
                CandidateItem(
                    external_item_id=external_item_id,
                    item_type="article",
                    title=title,
                    original_url=detail_url,
                    canonical_url=normalize_url(detail_url),
                    canonical_url_hash=compute_canonical_url_hash(detail_url),
                    content_text=content_text,
                    language="zh",
                    position=0,
                    observed_url=detail_url,
                    snippet=content_text[:240] or None,
                )
            ]
        )

        for href in parser.pdf_hrefs:
            output.discovered_targets.append(
                DiscoveredTarget(
                    target_url=urljoin(detail_url, href),
                    target_role="asset",
                    media_type="pdf",
                    content_type="application/pdf",
                    external_item_id=external_item_id,
                    depth=2,
                    priority=0,
                )
            )
        return output


def _decode_payload(raw_payload: str | bytes) -> str:
    if isinstance(raw_payload, bytes):
        return raw_payload.decode("utf-8")
    return raw_payload


def _external_item_id_from_title(title: str, fallback_url: str) -> str:
    match = _WEEKLY_ID_RE.search(title)
    if match:
        year = match.group("year")
        week = int(match.group("week"))
        issue = int(match.group("issue"))
        return f"cncdc-flu-weekly:{year}:W{week}:issue-{issue}"
    return f"cncdc-flu-weekly:url:{compute_canonical_url_hash(fallback_url)[:16]}"


def _clean_text(text: str) -> str:
    return " ".join(text.split())
