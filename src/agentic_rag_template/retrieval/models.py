"""Retrieval data structures."""

from dataclasses import dataclass

from agentic_rag_template.ingestion.models import DocumentChunk


@dataclass(frozen=True)
class SearchResult:
    """A chunk returned by vector search."""

    chunk: DocumentChunk
    score: float
