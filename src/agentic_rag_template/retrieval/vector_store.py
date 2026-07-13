"""In-memory vector store for the study template."""

import math
from typing import Iterable, List, Optional, Tuple

from agentic_rag_template.embeddings.models import EmbeddingProvider, Vector
from agentic_rag_template.ingestion.models import DocumentChunk
from agentic_rag_template.retrieval.models import SearchResult


class InMemoryVectorStore:
    """Store embedded chunks and search them by cosine similarity."""

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider
        self._entries: List[Tuple[DocumentChunk, Vector]] = []

    @property
    def size(self) -> int:
        return len(self._entries)

    def add_chunks(self, chunks: Iterable[DocumentChunk]) -> None:
        chunk_list = list(chunks)
        vectors = self.embedding_provider.embed_texts([chunk.text for chunk in chunk_list])
        self._entries.extend(zip(chunk_list, vectors))

    def search(
        self,
        query: str,
        top_k: int = 5,
        collection: Optional[str] = None,
    ) -> List[SearchResult]:
        if top_k <= 0:
            return []

        query_vector = self.embedding_provider.embed_text(query)
        results: List[SearchResult] = []

        for chunk, vector in self._entries:
            if collection and chunk.collection != collection:
                continue

            results.append(SearchResult(chunk=chunk, score=cosine_similarity(query_vector, vector)))

        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]


def cosine_similarity(left: Vector, right: Vector) -> float:
    """Calculate cosine similarity for two vectors."""
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimension")

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    return dot_product / (left_norm * right_norm)
