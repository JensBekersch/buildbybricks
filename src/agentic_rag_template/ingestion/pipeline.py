"""High-level ingestion pipeline for local collection folders."""

from pathlib import Path
from typing import List, Optional

from agentic_rag_template.ingestion.chunker import chunk_document
from agentic_rag_template.ingestion.loader import load_documents
from agentic_rag_template.ingestion.models import DocumentChunk


def ingest_data(
    data_dir: Path,
    collection: Optional[str] = None,
    chunk_size: int = 800,
    overlap: int = 120,
) -> List[DocumentChunk]:
    """Load and chunk all supported documents from data/<collection>/ folders."""
    chunks: List[DocumentChunk] = []

    for document in load_documents(data_dir=data_dir, collection=collection):
        chunks.extend(
            chunk_document(
                document=document,
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    return chunks
