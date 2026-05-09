"""Text chunking for embedding pipeline.

Chunks derive ONLY from ``item_versions.normalized_text`` — never from raw
HTML/API payloads.  The caller is responsible for ensuring the input text has
already been extracted and normalized before chunking.
"""

from __future__ import annotations

import math


def chunk_text(
    normalized_text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """Split *normalized_text* into overlapping chunks for embedding.

    Parameters
    ----------
    normalized_text : str
        Pre-extracted, normalized plain text from an item version.
    chunk_size : int
        Maximum number of characters per chunk.
    overlap : int
        Number of characters to overlap between consecutive chunks.

    Returns
    -------
    list[dict]
        Each dict has keys ``chunk_index``, ``text``, ``token_count``.
        ``token_count`` is approximated as ``len(text) // 4``.
        Returns an empty list if the input is empty or whitespace-only.
    """
    if not normalized_text or not normalized_text.strip():
        return []

    step = max(chunk_size - overlap, 1)
    chunks: list[dict] = []
    start = 0

    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        text = normalized_text[start:end]
        chunks.append(
            {
                "chunk_index": len(chunks),
                "text": text,
                "token_count": len(text) // 4,
            }
        )
        # Advance by step; if we've reached the end, stop.
        if end >= len(normalized_text):
            break
        start += step

    return chunks
