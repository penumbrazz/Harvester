"""Shared types for crawl adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CrawlResult:
    """Normalized result from a crawl operation."""

    original_url: str
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    payload_text: str | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None
