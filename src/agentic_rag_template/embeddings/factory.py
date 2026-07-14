"""Factory for selecting the configured embedding provider."""

from agentic_rag_template.config import Settings
from agentic_rag_template.embeddings.hash_provider import HashEmbeddingProvider
from agentic_rag_template.embeddings.models import EmbeddingProvider, EmbeddingProviderConfig
from agentic_rag_template.embeddings.ollama_provider import OllamaEmbeddingProvider


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

    Hash is the deterministic offline default. Ollama can be selected for local
    semantic embeddings when an Ollama service and embedding model are available.
    """
    config = config_from_settings(settings)
    provider = config.provider.lower().strip()

    if provider == "hash":
        return HashEmbeddingProvider(model=config.model, dimension=config.dimension)

    if provider == "ollama":
        return OllamaEmbeddingProvider(
            model=config.model,
            api_base_url=config.api_base_url,
            api_key=config.api_key,
            dimension=config.dimension if config.dimension > 0 else 0,
        )

    supported_later = ", ".join(["openai", "sentence-transformers"])
    raise ValueError(
        f"Embedding provider '{config.provider}' is not implemented yet. "
        f"Supported providers: hash, ollama. Planned providers include {supported_later}."
    )
