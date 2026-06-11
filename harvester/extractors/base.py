"""Extractor interface for Harvester."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class CandidateItem:
    """A normalized candidate content item extracted from a raw object."""

    external_item_id: str | None = None
    item_type: str = "post"
    title: str | None = None
    original_url: str | None = None
    final_url: str | None = None
    canonical_url: str | None = None
    canonical_url_hash: str | None = None
    content_text: str = ""
    language: str | None = None
    position: int | None = None
    observed_url: str | None = None
    payload_hash: str | None = None
    snippet: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredTarget:
    """A crawl target candidate discovered while extracting a raw object."""

    target_url: str
    target_role: str
    media_type: str = "unknown"
    content_type: str | None = None
    external_item_id: str | None = None
    parent_target_id: str | None = None
    depth: int = 0
    priority: int = 0
    category: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionOutput:
    """Combined extractor output for content items and discovered targets."""

    items: list[CandidateItem] = field(default_factory=list)
    discovered_targets: list[DiscoveredTarget] = field(default_factory=list)


def normalize_extraction_output(
    output: list[CandidateItem] | ExtractionOutput,
) -> ExtractionOutput:
    """Normalize legacy and new extractor return values."""
    if isinstance(output, ExtractionOutput):
        return output
    return ExtractionOutput(items=output, discovered_targets=[])


class Extractor(Protocol):
    """Protocol for raw object extractors."""

    def extract(
        self, raw_metadata: dict, raw_payload: str | bytes
    ) -> list[CandidateItem] | ExtractionOutput:
        """Extract candidate items from a raw object.

        Parameters
        ----------
        raw_metadata : dict
            Metadata associated with the raw object (e.g. source info, headers).
        raw_payload : str or bytes
            The raw content to extract items from.

        Returns
        -------
        list[CandidateItem]
            Extracted candidate items.
        """
        ...
