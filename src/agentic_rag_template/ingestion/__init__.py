"""Document ingestion components."""

from agentic_rag_template.ingestion.loader import discover_collections, load_documents
from agentic_rag_template.ingestion.models import DocumentChunk, SourceDocument
from agentic_rag_template.ingestion.pipeline import ingest_data

__all__ = [
    "DocumentChunk",
    "SourceDocument",
    "discover_collections",
    "ingest_data",
    "load_documents",
]
