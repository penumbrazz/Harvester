"""Stub model adapter for local testing and development.

Returns deterministic vectors based on a hash of the input text.
Never makes network calls — suitable for offline testing.
"""

from __future__ import annotations

import hashlib
import struct


class StubModelAdapter:
    """Deterministic stub embedding adapter.

    Produces a float vector from the SHA-256 hash of the input text,
    repeated and normalized to fill the required dimensionality.  The output is
    purely deterministic and does not depend on any external service.
    """

    def __init__(self, dimension: int | None = None) -> None:
        if dimension is not None:
            self._dimension = dimension
        else:
            from harvester.adapters.embedding_settings import EmbeddingSettings

            self._dimension = EmbeddingSettings().dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> list[float]:
        """Return a deterministic embedding vector for *text*.

        Parameters
        ----------
        text : str
            Input text to embed.

        Returns
        -------
        list[float]
            A list of floats in the range [-1.0, 1.0] with ``self._dimension``
            elements.
        """
        raw = hashlib.sha256(text.encode()).digest()
        values: list[float] = []
        for i in range(self._dimension):
            byte_offset = (i * 4) % len(raw)
            chunk = raw[byte_offset : byte_offset + 4]
            if len(chunk) < 4:
                chunk = chunk + raw[: 4 - len(chunk)]
            int_val = struct.unpack("<I", chunk)[0]
            values.append((int_val / (2**32 - 1)) * 2.0 - 1.0)
        return values
