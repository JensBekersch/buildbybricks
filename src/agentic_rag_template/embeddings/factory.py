"""Factory for selecting the configured embedding provider."""

from agentic_rag_template.config import Settings
from agentic_rag_template.embeddings.hash_provider import HashEmbeddingProvider
from agentic_rag_template.embeddings.models import EmbeddingProvider, EmbeddingProviderConfig


def config_from_settings(settings: Settings) -> EmbeddingProviderConfig:
    """Extract embedding settings from the application settings object."""
    return EmbeddingProviderConfig(
        provider=settings.embedding_provider,
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
        api_base_url=settings.embedding_api_base_url,
        api_key=settings.embedding_api_key,
    )


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Create the configured embedding provider.

    Only the local hash provider is implemented now. Other providers are
    represented in configuration so they can be added without changing callers.
    """
    config = config_from_settings(settings)
    provider = config.provider.lower().strip()

    if provider == "hash":
        return HashEmbeddingProvider(model=config.model, dimension=config.dimension)

    supported_later = ", ".join(["ollama", "openai", "sentence-transformers"])
    raise ValueError(
        f"Embedding provider '{config.provider}' is not implemented yet. "
        f"Use 'hash' for now; planned providers include {supported_later}."
    )
