"""Sina fixture extractor — processes Weibo-style JSON test data."""

from __future__ import annotations

import json

from harvester.extractors.base import CandidateItem


class SinaFixtureExtractor:
    """Extract items from a Sina/Weibo-style JSON fixture.

    Expected payload format: a JSON object with a ``statuses`` array.  Each
    status object has fields ``idstr``, ``text``, ``source``, and ``created_at``.
    """

    def extract(
        self, raw_metadata: dict, raw_payload: str | bytes
    ) -> list[CandidateItem]:
        """Extract candidate items from Sina fixture JSON.

        Parameters
        ----------
        raw_metadata : dict
            Metadata dict (may contain ``source_url`` or other context).
        raw_payload : str or bytes
            JSON string or bytes containing ``{"statuses": [...]}``.

        Returns
        -------
        list[CandidateItem]
            One candidate item per status in the JSON payload.
        """
        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode("utf-8")

        data = json.loads(raw_payload)
        statuses = data.get("statuses", [])
        items: list[CandidateItem] = []

        for idx, status in enumerate(statuses):
            text = status.get("text", "")
            snippet = text[:200] if len(text) > 200 else text

            item = CandidateItem(
                external_item_id=status.get("idstr"),
                item_type="post",
                content_text=text,
                position=idx,
                snippet=snippet,
                extra={
                    "source": status.get("source"),
                    "created_at": status.get("created_at"),
                },
            )
            items.append(item)

        return items
