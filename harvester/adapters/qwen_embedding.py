"""Qwen embedding adapter — OpenAI-compatible HTTP embeddings protocol.

Calls ``POST {base_url}/v1/embeddings`` with ``{model, input}`` and parses
the OpenAI-compatible response.  Validates dimension and finiteness of the
returned embedding vector.
"""

from __future__ import annotations

import logging
import math

import httpx

logger = logging.getLogger(__name__)


class EmbeddingAdapterError(Exception):
    """Base error for embedding adapter failures.

    Distinguishes configuration errors from runtime errors.
    """

    def __init__(self, message: str, *, is_config_error: bool = False) -> None:
        super().__init__(message)
        self.is_config_error = is_config_error


class QwenEmbeddingAdapter:
    """Embedding adapter using an OpenAI-compatible HTTP endpoint.

    Parameters
    ----------
    base_url : str
        Base URL of the embedding service (e.g. ``http://localhost:8080``).
    model : str
        Model name to pass in the request body.
    timeout : float
        Request timeout in seconds.
    dimension : int
        Expected embedding dimension (validated after each call).
    """

    def __init__(
        self,
        base_url: str,
        *,
        model: str = "text-embedding-v3",
        timeout: float = 30.0,
        dimension: int = 1536,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._dimension = dimension
        self._client = client or httpx.Client(timeout=timeout)

    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for *text* via the Qwen HTTP API.

        Parameters
        ----------
        text : str
            Input text to embed.

        Returns
        -------
        list[float]
            A 1536-element list of floats.

        Raises
        ------
        EmbeddingAdapterError
            On timeout, HTTP error, missing embedding, dimension mismatch,
            or non-finite values.
        """
        endpoint = f"{self._base_url}/v1/embeddings"
        body = {"model": self._model, "input": text}

        try:
            response = self._client.post(endpoint, json=body, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            raise EmbeddingAdapterError(
                f"Embedding request timed out: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise EmbeddingAdapterError(
                f"Embedding HTTP error: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise EmbeddingAdapterError(
                f"Embedding service returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            data = response.json()
        except (ValueError, KeyError) as exc:
            raise EmbeddingAdapterError(
                f"Failed to parse embedding response JSON: {exc}"
            ) from exc

        # Extract embedding from OpenAI-compatible response
        try:
            embedding_data = data["data"]
            if not embedding_data:
                raise EmbeddingAdapterError(
                    "Empty data array in embedding response"
                )
            embedding = embedding_data[0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise EmbeddingAdapterError(
                f"Missing embedding in response: {exc}"
            ) from exc

        # Validate dimension
        if len(embedding) != self._dimension:
            raise EmbeddingAdapterError(
                f"Embedding dimension mismatch: expected {self._dimension}, "
                f"got {len(embedding)}"
            )

        # Validate all values are finite
        for i, v in enumerate(embedding):
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                raise EmbeddingAdapterError(
                    f"Non-finite value at index {i}: {v!r}"
                )

        return list(embedding)
