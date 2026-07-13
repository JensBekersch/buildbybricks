"""Chunk loaded documents into retrieval-ready text segments."""

from typing import List

from agentic_rag_template.ingestion.models import DocumentChunk, SourceDocument


def chunk_document(
    document: SourceDocument,
    chunk_size: int = 800,
    overlap: int = 120,
) -> List[DocumentChunk]:
    """Split one document into deterministic character chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap must not be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = normalize_text(document.content)
    chunks: List[DocumentChunk] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunk_index = len(chunks)
            chunks.append(
                DocumentChunk(
                    id=build_chunk_id(document, chunk_index),
                    collection=document.collection,
                    source_path=document.relative_path.as_posix(),
                    title=document.title,
                    text=chunk_text,
                    chunk_index=chunk_index,
                    char_start=start,
                    char_end=end,
                    metadata={
                        **document.metadata,
                        "chunk_size": str(chunk_size),
                        "overlap": str(overlap),
                    },
                )
            )

        if end == len(text):
            break

        start = end - overlap

    return chunks


def normalize_text(text: str) -> str:
    """Normalize whitespace without changing the source language."""
    lines = [line.strip() for line in text.splitlines()]
    normalized_lines = [line for line in lines if line]
    return "\n".join(normalized_lines)


def build_chunk_id(document: SourceDocument, chunk_index: int) -> str:
    """Build a stable id for a document chunk."""
    return f"{document.collection}:{document.relative_path.as_posix()}:{chunk_index}"
