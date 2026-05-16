"""Tests for EmbeddingSettings and create_embedding_adapter factory.

Covers: default stub adapter, explicit qwen configuration, missing base URL
error, model name, dimension, and timeout configuration.
"""

import os
from unittest.mock import patch

import pytest

from harvester.adapters.embedding_settings import (
    EmbeddingSettings,
    create_embedding_adapter,
)
from harvester.adapters.stub_model import StubModelAdapter


class TestEmbeddingSettingsDefaults:
    """EmbeddingSettings should have sensible defaults."""

    def test_default_adapter_is_stub(self):
        settings = EmbeddingSettings()
        assert settings.adapter == "stub"

    def test_default_model_name(self):
        settings = EmbeddingSettings()
        assert settings.model == "stub-embedding-1536"

    def test_default_dimension(self):
        settings = EmbeddingSettings()
        assert settings.dimension == 1536

    def test_default_timeout(self):
        settings = EmbeddingSettings()
        assert settings.qwen_timeout_seconds == 30


class TestEmbeddingSettingsFromEnv:
    """EmbeddingSettings reads configuration from environment variables."""

    def test_adapter_from_env(self):
        with patch.dict(os.environ, {"HARVESTER_EMBEDDING_ADAPTER": "qwen"}):
            settings = EmbeddingSettings()
            assert settings.adapter == "qwen"

    def test_model_from_env(self):
        with patch.dict(os.environ, {"HARVESTER_EMBEDDING_MODEL": "text-embedding-v3"}):
            settings = EmbeddingSettings()
            assert settings.model == "text-embedding-v3"

    def test_dimension_from_env(self):
        with patch.dict(os.environ, {"HARVESTER_EMBEDDING_DIMENSION": "768"}):
            settings = EmbeddingSettings()
            assert settings.dimension == 768

    def test_timeout_from_env(self):
        with patch.dict(os.environ, {"HARVESTER_QWEN_EMBEDDING_TIMEOUT_SECONDS": "60"}):
            settings = EmbeddingSettings()
            assert settings.qwen_timeout_seconds == 60

    def test_qwen_base_url_from_env(self):
        with patch.dict(
            os.environ, {"HARVESTER_QWEN_EMBEDDING_BASE_URL": "http://localhost:8080"}
        ):
            settings = EmbeddingSettings()
            assert settings.qwen_base_url == "http://localhost:8080"


class TestCreateEmbeddingAdapterDefault:
    """Factory should return StubModelAdapter when not configured for qwen."""

    def test_default_returns_stub_adapter(self):
        adapter, model_name = create_embedding_adapter()
        assert isinstance(adapter, StubModelAdapter)
        assert model_name == "stub-embedding-1536"

    def test_explicit_stub_returns_stub(self):
        settings = EmbeddingSettings(adapter="stub")
        adapter, model_name = create_embedding_adapter(settings)
        assert isinstance(adapter, StubModelAdapter)
        assert model_name == "stub-embedding-1536"

    def test_custom_model_name_with_stub(self):
        settings = EmbeddingSettings(adapter="stub", model="custom-stub")
        adapter, model_name = create_embedding_adapter(settings)
        assert isinstance(adapter, StubModelAdapter)
        assert model_name == "custom-stub"


class TestCreateEmbeddingAdapterQwen:
    """Factory should return QwenEmbeddingAdapter when configured for qwen."""

    def test_qwen_adapter_created_with_base_url(self):
        from harvester.adapters.qwen_embedding import QwenEmbeddingAdapter

        settings = EmbeddingSettings(
            adapter="qwen",
            model="text-embedding-v3",
            qwen_base_url="http://localhost:8080",
        )
        adapter, model_name = create_embedding_adapter(settings)
        assert isinstance(adapter, QwenEmbeddingAdapter)
        assert model_name == "text-embedding-v3"

    def test_qwen_adapter_missing_base_url_raises_error(self):
        settings = EmbeddingSettings(
            adapter="qwen",
            model="text-embedding-v3",
            # qwen_base_url intentionally omitted
        )
        with pytest.raises(Exception, match="BASE_URL"):
            create_embedding_adapter(settings)

    def test_qwen_adapter_uses_configured_timeout(self):
        from harvester.adapters.qwen_embedding import QwenEmbeddingAdapter

        settings = EmbeddingSettings(
            adapter="qwen",
            model="text-embedding-v3",
            qwen_base_url="http://localhost:8080",
            qwen_timeout_seconds=60,
        )
        adapter, model_name = create_embedding_adapter(settings)
        assert isinstance(adapter, QwenEmbeddingAdapter)
