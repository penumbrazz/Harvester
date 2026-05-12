"""Extractor registry — maps source URLs to the appropriate extractor."""

from __future__ import annotations

import logging
import re

from harvester.extractors.base import CandidateItem, Extractor
from harvester.extractors.sina_7x24 import Sina7x24Extractor

logger = logging.getLogger(__name__)

ExtractorClass = type[Extractor]

_REGISTRY: list[tuple[re.Pattern[str], ExtractorClass]] = [
    (re.compile(r"sina\.com\.cn/7x24"), Sina7x24Extractor),
]


def get_extractor_for_url(url: str) -> Extractor | None:
    """Return an extractor instance matching the source URL, or None."""
    for pattern, cls in _REGISTRY:
        if pattern.search(url):
            logger.debug("Matched extractor %s for URL %s", cls.__name__, url)
            return cls()
    return None
