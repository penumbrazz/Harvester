"""Sina 7x24 real-time financial flash news Markdown extractor."""

from __future__ import annotations

import re

from harvester.extractors.base import CandidateItem

# Pattern: HH:MM:SS\n\n[title](url)\n\n<read_count_line>\n\n<digit>
_FLASH_RE = re.compile(
    r"(?P<time>\d{2}:\d{2}:\d{2})\n"
    r"\n"
    r"\[(?P<title>(?:[^\]]|\]\()[^]]*)\]\((?P<url>https?://wap\.cj\.sina\.cn/pc/7x24/\d+)\)\n"
    r"\n"
    r"(?:(?P<read_line>[^\n]*阅读[^\n]*)\n\n)?",
    re.MULTILINE,
)


def _parse_read_count(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"([\d,.]+)\s*万", text)
    if m:
        raw = m.group(1).replace(",", "")
        # String-based decimal parse to avoid float precision errors
        if "." in raw:
            int_part, frac_part = raw.split(".", 1)
            frac_part = frac_part.ljust(4, "0")[:4]
            return int(int_part) * 10000 + int(frac_part)
        return int(raw) * 10000
    m = re.search(r"([\d,]+)\s*", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _extract_item_id(url: str) -> str | None:
    m = re.search(r"/(\d+)(?:[/?#]|$)", url)
    return m.group(1) if m else None


class Sina7x24Extractor:
    """Extract flash news items from Sina 7x24 Markdown payload."""

    def extract(
        self, raw_metadata: dict, raw_payload: str | bytes
    ) -> list[CandidateItem]:
        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode("utf-8", errors="replace")
        items: list[CandidateItem] = []
        for m in _FLASH_RE.finditer(raw_payload):
            url = m.group("url")
            title = m.group("title")
            item_id = _extract_item_id(url)
            if item_id is None:
                continue
            items.append(
                CandidateItem(
                    external_item_id=item_id,
                    item_type="flash",
                    title=title,
                    original_url=url,
                    final_url=url,
                    content_text=title,
                    position=len(items),
                    extra={
                        "time": m.group("time"),
                        "read_count": _parse_read_count(m.group("read_line")),
                    },
                )
            )
        return items
