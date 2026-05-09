"""Stub model adapter for local testing and development.

Returns deterministic 1536-dimensional vectors based on a hash of the input
text.  Never makes network calls — suitable for offline testing.
"""

from __future__ import annotations

import hashlib
import struct


class StubModelAdapter:
    """Deterministic stub embedding adapter.

    Produces a 1536-dim float vector from the SHA-256 hash of the input text,
    repeated and normalized to fill the required dimensionality.  The output is
    purely deterministic and does not depend on any external service.
    """

    DIMENSION = 1536

    def embed(self, text: str) -> list[float]:
        """Return a deterministic 1536-dim embedding vector for *text*.

        Parameters
        ----------
        text : str
            Input text to embed.

        Returns
        -------
        list[float]
            A 1536-element list of floats in the range [-1.0, 1.0].
        """
        raw = hashlib.sha256(text.encode()).digest()
        # Each float is derived from 4 bytes of the hash.
        # We cycle through the 32-byte hash to fill 1536 floats.
        values: list[float] = []
        for i in range(self.DIMENSION):
            byte_offset = (i * 4) % len(raw)
            # Pick 4 bytes, wrapping around the hash if needed.
            chunk = raw[byte_offset : byte_offset + 4]
            if len(chunk) < 4:
                chunk = chunk + raw[: 4 - len(chunk)]
            int_val = struct.unpack("<I", chunk)[0]
            # Map uint32 to [-1.0, 1.0].
            values.append((int_val / (2**32 - 1)) * 2.0 - 1.0)
        return values
