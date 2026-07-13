"""Shared embedding provider contracts."""

from dataclasses import dataclass
from typing import List, Protocol


Vector = List[float]


class EmbeddingProvider(Protocol):
    """Provider interface for turning text into numeric vectors."""

    name: str
    model: str
    dimension: int

    def embed_text(self, text: str) -> Vector:
        """Embed one text string."""

    def embed_texts(self, texts: List[str]) -> List[Vector]:
        """Embed multiple text strings."""


@dataclass(frozen=True)
class EmbeddingProviderConfig:
    """Configuration shared by current and future embedding providers."""

    provider: str = "hash"
    model: str = "local-hash-v1"
    dimension: int = 64
    api_base_url: str = "http://localhost:11434"
    api_key: str = ""
