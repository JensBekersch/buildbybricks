"""Retriever facade over ingestion, embeddings, and vector search."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentic_rag_template.embeddings.models import EmbeddingProvider
from agentic_rag_template.ingestion import ingest_data
from agentic_rag_template.retrieval.models import SearchResult
from agentic_rag_template.retrieval.vector_store import InMemoryVectorStore


@dataclass(frozen=True)
class RetrievalQuery:
    """A normalized query for knowledge-base retrieval."""

    text: str
    collection: Optional[str] = None
    top_k: int = 5


@dataclass(frozen=True)
class RetrievedChunk:
    """A retrieval result shaped for API responses and future agent tools."""

    id: str
    score: float
    collection: str
    source_path: str
    title: str
    text: str
    chunk_index: int
    metadata: Dict[str, str]

    @classmethod
    def from_search_result(cls, result: SearchResult) -> "RetrievedChunk":
        chunk = result.chunk
        return cls(
            id=chunk.id,
            score=result.score,
            collection=chunk.collection,
            source_path=chunk.source_path,
            title=chunk.title,
            text=chunk.text,
            chunk_index=chunk.chunk_index,
            metadata=chunk.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "score": round(self.score, 6),
            "collection": self.collection,
            "source_path": self.source_path,
            "title": self.title,
            "text": self.text,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class RetrievalResponse:
    """A retrieval response with trace information for observability."""

    query: RetrievalQuery
    indexed_chunk_count: int
    results: List[RetrievedChunk]
    trace: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query.text,
            "collection": self.query.collection,
            "top_k": self.query.top_k,
            "indexed_chunk_count": self.indexed_chunk_count,
            "results": [result.to_dict() for result in self.results],
            "trace": self.trace,
        }


class Retriever:
    """Build a local index and retrieve chunks for one query."""

    def __init__(self, data_dir: Path, embedding_provider: EmbeddingProvider) -> None:
        self.data_dir = data_dir
        self.embedding_provider = embedding_provider

    def retrieve(self, query: RetrievalQuery) -> RetrievalResponse:
        normalized_query = normalize_retrieval_query(query)
        chunks = ingest_data(self.data_dir, collection=normalized_query.collection)
        vector_store = InMemoryVectorStore(self.embedding_provider)
        vector_store.add_chunks(chunks)
        search_results = vector_store.search(
            normalized_query.text,
            top_k=normalized_query.top_k,
            collection=normalized_query.collection,
        )

        return RetrievalResponse(
            query=normalized_query,
            indexed_chunk_count=vector_store.size,
            results=[RetrievedChunk.from_search_result(result) for result in search_results],
            trace=[
                "loaded_chunks",
                "embedded_chunks",
                "searched_vector_store",
                "formatted_retrieval_results",
            ],
        )


def normalize_retrieval_query(query: RetrievalQuery) -> RetrievalQuery:
    """Validate and normalize retrieval parameters."""
    text = query.text.strip()

    if not text:
        raise ValueError("query text is required")

    top_k = max(1, min(query.top_k, 20))
    collection = query.collection.strip() if query.collection else None

    return RetrievalQuery(text=text, collection=collection or None, top_k=top_k)
