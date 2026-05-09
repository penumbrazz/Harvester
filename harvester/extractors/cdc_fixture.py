"""CDC fixture extractor — processes JSON list test data."""

from __future__ import annotations

import json

from harvester.extractors.base import CandidateItem


class CdcFixtureExtractor:
    """Extract items from a CDC-style JSON fixture.

    Expected payload format: a JSON list of objects, each with fields
    ``id``, ``title``, ``url``, and ``content``.
    """

    def extract(
        self, raw_metadata: dict, raw_payload: str | bytes
    ) -> list[CandidateItem]:
        """Extract candidate items from CDC fixture JSON.

        Parameters
        ----------
        raw_metadata : dict
            Metadata dict (may contain ``source_url`` or other context).
        raw_payload : str or bytes
            JSON string or bytes containing a list of item objects.

        Returns
        -------
        list[CandidateItem]
            One candidate item per entry in the JSON array.
        """
        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode("utf-8")

        data = json.loads(raw_payload)
        items: list[CandidateItem] = []

        for idx, entry in enumerate(data):
            item = CandidateItem(
                external_item_id=str(entry.get("id")),
                item_type="article",
                title=entry.get("title"),
                original_url=entry.get("url"),
                final_url=entry.get("url"),
                content_text=entry.get("content", ""),
                position=idx,
            )
            items.append(item)

        return items
