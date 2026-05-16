"""Extractor registry — maps source URLs and content types to extractors."""

from __future__ import annotations

import logging
import re

from harvester.extractors.base import Extractor
from harvester.extractors.cdc_weekly import (
    CdcWeeklyDetailExtractor,
    CdcWeeklyListExtractor,
)
from harvester.extractors.pdf_text import PdfTextExtractor
from harvester.extractors.sina_7x24 import Sina7x24Extractor

logger = logging.getLogger(__name__)

ExtractorClass = type[Extractor]

_REGISTRY: list[tuple[re.Pattern[str], ExtractorClass]] = [
    # CDC weekly — detail page (must precede list pattern)
    (
        re.compile(r"chinacdc\.cn/jksj/jksj04_14249/\d{6}/t\d+_\d+\.html"),
        CdcWeeklyDetailExtractor,
    ),
    # CDC weekly — list page
    (
        re.compile(r"chinacdc\.cn/jksj/jksj04_14249/?$"),
        CdcWeeklyListExtractor,
    ),
    (re.compile(r"sina\.com\.cn/7x24"), Sina7x24Extractor),
]

_CONTENT_TYPE_EXTRACTORS: dict[str, ExtractorClass] = {
    "application/pdf": PdfTextExtractor,
}


def get_extractor_for_url(url: str) -> Extractor | None:
    """Return an extractor instance matching the source URL, or None."""
    for pattern, cls in _REGISTRY:
        if pattern.search(url):
            logger.debug("Matched extractor %s for URL %s", cls.__name__, url)
            return cls()
    return None


def get_extractor(url: str, content_type: str | None = None) -> Extractor | None:
    """Return an extractor matching URL pattern or content type fallback."""
    extractor = get_extractor_for_url(url)
    if extractor is not None:
        return extractor
    if content_type and content_type in _CONTENT_TYPE_EXTRACTORS:
        cls = _CONTENT_TYPE_EXTRACTORS[content_type]
        logger.debug(
            "Matched extractor %s for content_type %s", cls.__name__, content_type
        )
        return cls()
    return None
