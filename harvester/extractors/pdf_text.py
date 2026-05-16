"""PDF text extractor — reads raw PDF bytes and produces candidate items."""

from __future__ import annotations

import logging
from io import BytesIO

from pypdf import PdfReader

from harvester.extractors.base import CandidateItem, ExtractionOutput

logger = logging.getLogger(__name__)


class PdfTextExtractor:
    """Extract normalized text from PDF bytes."""

    def extract(
        self,
        raw_metadata: dict,
        raw_payload: str | bytes,
    ) -> ExtractionOutput:
        payload = _to_bytes(raw_payload)
        text = _extract_text(payload)
        if not text.strip():
            return ExtractionOutput()

        target_url = raw_metadata.get("target_url") or raw_metadata.get("source_url")
        external_item_id = raw_metadata.get("external_item_id")

        return ExtractionOutput(
            items=[
                CandidateItem(
                    external_item_id=external_item_id,
                    item_type="article",
                    title=raw_metadata.get("title"),
                    original_url=target_url,
                    content_text=text,
                    language="zh",
                    position=0,
                    observed_url=raw_metadata.get("source_url"),
                )
            ]
        )


def _to_bytes(payload: str | bytes) -> bytes:
    if isinstance(payload, bytes):
        return payload
    return payload.encode("latin-1")


def _extract_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes, returning empty string on any failure."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception:
        logger.debug("pdf.unreadable bytes=%d", len(pdf_bytes))
        return ""

    if reader.is_encrypted:
        logger.debug("pdf.encrypted")
        return ""

    pages = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            continue
        pages.append(page_text)

    return "\n".join(pages)
