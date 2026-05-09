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


class Extractor(Protocol):
    """Protocol for raw object extractors."""

    def extract(
        self, raw_metadata: dict, raw_payload: str | bytes
    ) -> list[CandidateItem]:
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
