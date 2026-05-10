"""Embedding adapter configuration and factory.

Reads adapter type, model name, dimension, and Qwen-specific settings from
environment variables.  Provides ``create_embedding_adapter()`` factory that
returns the correct adapter and model name tuple.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class EmbeddingSettings(BaseSettings):
    """Embedding adapter configuration from environment variables.

    Environment variables
    ---------------------
    HARVESTER_EMBEDDING_ADAPTER
        Adapter type: ``stub`` or ``qwen`` (default: ``stub``).
    HARVESTER_EMBEDDING_MODEL
        Model identifier (default: ``stub-embedding-1536``).
    HARVESTER_EMBEDDING_DIMENSION
        Expected embedding dimension (default: 1536).
    HARVESTER_QWEN_EMBEDDING_BASE_URL
        Base URL for Qwen embedding service (required when adapter=qwen).
    HARVESTER_QWEN_EMBEDDING_TIMEOUT_SECONDS
        Request timeout in seconds (default: 30).
    """

    adapter: str = "stub"
    model: str = "stub-embedding-1536"
    dimension: int = 1536
    qwen_base_url: str = Field(
        default="",
        alias="HARVESTER_QWEN_EMBEDDING_BASE_URL",
    )
    qwen_timeout_seconds: float = Field(
        default=30.0,
        alias="HARVESTER_QWEN_EMBEDDING_TIMEOUT_SECONDS",
    )

    model_config = {
        "env_prefix": "HARVESTER_EMBEDDING_",
        "populate_by_name": True,
    }


def create_embedding_adapter(
    settings: EmbeddingSettings | None = None,
) -> tuple:
    """Create an embedding adapter and model name from configuration.

    Returns
    -------
    tuple[adapter, str]
        A (adapter_instance, model_name) tuple.

    Raises
    ------
    EmbeddingAdapterError
        If adapter type is ``qwen`` but ``qwen_base_url`` is not set.
    """
    from harvester.adapters.qwen_embedding import EmbeddingAdapterError

    if settings is None:
        settings = EmbeddingSettings()

    if settings.adapter == "qwen":
        if not settings.qwen_base_url:
            raise EmbeddingAdapterError(
                "HARVESTER_QWEN_EMBEDDING_BASE_URL is required when "
                "HARVESTER_EMBEDDING_ADAPTER=qwen",
                is_config_error=True,
            )

        from harvester.adapters.qwen_embedding import QwenEmbeddingAdapter

        adapter = QwenEmbeddingAdapter(
            base_url=settings.qwen_base_url,
            model=settings.model,
            timeout=settings.qwen_timeout_seconds,
            dimension=settings.dimension,
        )
        return adapter, settings.model

    if settings.adapter == "stub":
        from harvester.adapters.stub_model import StubModelAdapter

        return StubModelAdapter(), settings.model

    raise EmbeddingAdapterError(
        f"Unknown HARVESTER_EMBEDDING_ADAPTER '{settings.adapter}'. "
        "Allowed values: stub, qwen",
        is_config_error=True,
    )
