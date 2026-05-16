"""Tests for QwenEmbeddingAdapter — harvester.adapters.qwen_embedding.

Uses mocked HTTP transport to verify request format, success parsing,
timeout, HTTP errors, missing embedding, dimension mismatch, and non-finite
values.  No real network calls are made.
"""

import json
import math

import httpx
import pytest

from harvester.adapters.qwen_embedding import (
    EmbeddingAdapterError,
    QwenEmbeddingAdapter,
)


def _make_1536_embedding(seed: float = 0.1) -> list[float]:
    """Produce a deterministic 1536-dim embedding for test assertions."""
    return [seed] * 1536


def _success_response(embedding: list[float] | None = None) -> httpx.Response:
    """Build a mock successful OpenAI-compatible embeddings response."""
    emb = embedding or _make_1536_embedding()
    body = {
        "object": "list",
        "data": [{"object": "embedding", "index": 0, "embedding": emb}],
        "model": "text-embedding-v3",
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }
    return httpx.Response(200, json=body)


def _make_adapter(
    transport: httpx.BaseTransport,
    base_url: str = "http://localhost:8080",
    model: str = "text-embedding-v3",
    dimension: int = 1536,
    timeout: float = 30.0,
) -> QwenEmbeddingAdapter:
    """Create an adapter with a mocked transport layer."""
    client = httpx.Client(transport=transport)
    return QwenEmbeddingAdapter(
        base_url=base_url,
        model=model,
        timeout=timeout,
        dimension=dimension,
        client=client,
    )


class TestQwenAdapterSuccess:
    """Successful embedding request."""

    def test_returns_1536_dim_embedding(self):
        transport = httpx.MockTransport(
            lambda req: _success_response(_make_1536_embedding(0.42))
        )
        adapter = _make_adapter(transport)
        result = adapter.embed("hello world")
        assert len(result) == 1536
        assert all(isinstance(v, float) for v in result)
        assert result[0] == pytest.approx(0.42)

    def test_request_url_contains_v1_embeddings(self):
        captured_url = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured_url.append(str(req.url))
            return _success_response()

        transport = httpx.MockTransport(handler)
        adapter = _make_adapter(transport, base_url="http://localhost:8080")
        adapter.embed("test")
        assert "/v1/embeddings" in captured_url[0]

    def test_request_body_contains_model_and_input(self):
        captured_body = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(req.content))
            return _success_response()

        transport = httpx.MockTransport(handler)
        adapter = _make_adapter(transport, model="text-embedding-v3")
        adapter.embed("test input")
        assert captured_body["model"] == "text-embedding-v3"
        assert captured_body["input"] == "test input"


class TestQwenAdapterTimeout:
    """Timeout error handling."""

    def test_timeout_raises_embedding_error(self):
        transport = httpx.MockTransport(
            lambda req: (_ for _ in ()).throw(httpx.TimeoutException("timed out"))
        )
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="timed out"):
            adapter.embed("test")


class TestQwenAdapterHTTPError:
    """Non-2xx HTTP response handling."""

    def test_http_500_raises_embedding_error(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(500, text="Internal Server Error")
        )
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="HTTP 500"):
            adapter.embed("test")

    def test_http_422_raises_embedding_error(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(422, text="Unprocessable Entity")
        )
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="HTTP 422"):
            adapter.embed("test")


class TestQwenAdapterMissingEmbedding:
    """Response with missing embedding data."""

    def test_empty_data_array_raises_error(self):
        body = {"object": "list", "data": [], "model": "test"}
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=body))
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="Empty data array"):
            adapter.embed("test")

    def test_missing_data_key_raises_error(self):
        body = {"object": "list", "model": "test"}
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=body))
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="Missing embedding"):
            adapter.embed("test")

    def test_missing_embedding_field_raises_error(self):
        body = {"data": [{"object": "embedding", "index": 0}]}
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=body))
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="Missing embedding"):
            adapter.embed("test")


class TestQwenAdapterDimensionMismatch:
    """Dimension validation."""

    def test_wrong_dimension_raises_error(self):
        wrong_embedding = [0.1] * 768
        transport = httpx.MockTransport(lambda req: _success_response(wrong_embedding))
        adapter = _make_adapter(transport, dimension=1536)
        with pytest.raises(EmbeddingAdapterError, match="dimension mismatch"):
            adapter.embed("test")


class TestQwenAdapterNonFiniteValues:
    """Non-finite value detection."""

    def _make_nonfinite_response(self, embedding: list) -> httpx.Response:
        """Build a response with potentially non-JSON-compliant embedding values.

        Uses content= to bypass JSON serialization that would reject NaN/Inf.
        """
        body = {
            "object": "list",
            "data": [{"object": "embedding", "index": 0, "embedding": embedding}],
            "model": "text-embedding-v3",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }
        # Use json.dumps with allow_nan=True to serialize non-finite values
        content = json.dumps(body, allow_nan=True).encode("utf-8")
        return httpx.Response(
            200,
            content=content,
            headers={"content-type": "application/json"},
        )

    def test_nan_in_embedding_raises_error(self):
        bad_embedding = [0.1] * 1536
        bad_embedding[100] = float("nan")
        transport = httpx.MockTransport(
            lambda req: self._make_nonfinite_response(bad_embedding)
        )
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="Non-finite"):
            adapter.embed("test")

    def test_inf_in_embedding_raises_error(self):
        bad_embedding = [0.1] * 1536
        bad_embedding[50] = float("inf")
        transport = httpx.MockTransport(
            lambda req: self._make_nonfinite_response(bad_embedding)
        )
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="Non-finite"):
            adapter.embed("test")


class TestQwenAdapterNetworkError:
    """Generic HTTP transport error."""

    def test_connection_error_raises_embedding_error(self):
        transport = httpx.MockTransport(
            lambda req: (_ for _ in ()).throw(httpx.ConnectError("Connection refused"))
        )
        adapter = _make_adapter(transport)
        with pytest.raises(EmbeddingAdapterError, match="HTTP error"):
            adapter.embed("test")
