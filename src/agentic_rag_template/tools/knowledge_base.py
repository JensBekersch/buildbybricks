"""Knowledge-base tools used by the first deterministic agent."""

from pathlib import Path
from typing import List, Optional

from agentic_rag_template.api.schemas import SourceReference
from agentic_rag_template.embeddings.models import EmbeddingProvider
from agentic_rag_template.retrieval import RetrievedChunk, RetrievalQuery, Retriever
from agentic_rag_template.tools.answering import AnswerDraft, compose_grounded_answer


def search_knowledge_base(
    data_dir: Path,
    embedding_provider: EmbeddingProvider,
    query: str,
    collection: Optional[str] = None,
    top_k: int = 3,
) -> List[RetrievedChunk]:
    """Search local knowledge collections and return retrieval results."""
    retriever = Retriever(data_dir, embedding_provider)
    response = retriever.retrieve(RetrievalQuery(text=query, collection=collection, top_k=top_k))
    return response.results


def read_source(data_dir: Path, source_path: str) -> str:
    """Read one source file from the data directory."""
    root = data_dir.resolve()
    source = (root / source_path).resolve()

    if root not in source.parents and source != root:
        raise ValueError("source_path must stay within data_dir")

    if not source.exists() or not source.is_file():
        raise ValueError(f"source '{source_path}' was not found")

    return source.read_text(encoding="utf-8")


def answer_with_citations(query: str, results: List[RetrievedChunk]) -> AnswerDraft:
    """Build an answer draft grounded in retrieved chunks."""
    return compose_grounded_answer(query, results)


def build_source_references(results: List[RetrievedChunk]) -> List[SourceReference]:
    """Convert retrieval results to API source references."""
    seen = set()
    sources: List[SourceReference] = []

    for result in results:
        key = result.source_path
        if key in seen:
            continue

        seen.add(key)
        sources.append(
            SourceReference(
                title=result.title,
                location=result.source_path,
                excerpt=result.text,
                score=round(result.score, 6),
            )
        )

    return sources
