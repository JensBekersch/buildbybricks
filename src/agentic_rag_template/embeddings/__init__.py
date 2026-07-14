"""Embedding provider abstractions and local implementations."""

from agentic_rag_template.embeddings.factory import create_embedding_provider
from agentic_rag_template.embeddings.hash_provider import HashEmbeddingProvider
from agentic_rag_template.embeddings.models import EmbeddingProvider, EmbeddingProviderConfig
from agentic_rag_template.embeddings.ollama_provider import OllamaEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingProviderConfig",
    "HashEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "create_embedding_provider",
]
