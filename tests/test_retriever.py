from pathlib import Path

import pytest

from agentic_rag_template.embeddings import HashEmbeddingProvider
from agentic_rag_template.retrieval import RetrievalQuery, Retriever
from agentic_rag_template.retrieval.retriever import normalize_retrieval_query


def test_retriever_returns_agent_friendly_results_with_trace(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "rag.md").write_text(
        "Agentic RAG retrieves chunks before answering with sources.",
        encoding="utf-8",
    )

    retriever = Retriever(tmp_path, HashEmbeddingProvider(dimension=32))
    response = retriever.retrieve(RetrievalQuery(text="agentic sources", collection="sample", top_k=3))

    assert response.query.collection == "sample"
    assert response.indexed_chunk_count == 1
    assert response.results[0].collection == "sample"
    assert response.results[0].source_path == "sample/rag.md"
    assert response.trace == [
        "loaded_chunks",
        "embedded_chunks",
        "searched_vector_store",
        "formatted_retrieval_results",
    ]


def test_retriever_filters_to_requested_collection(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample"
    policy_dir = tmp_path / "policies"
    sample_dir.mkdir()
    policy_dir.mkdir()
    (sample_dir / "rag.md").write_text("Agentic retrieval and tools.", encoding="utf-8")
    (policy_dir / "policy.md").write_text("Policy review and approvals.", encoding="utf-8")

    retriever = Retriever(tmp_path, HashEmbeddingProvider(dimension=32))
    response = retriever.retrieve(RetrievalQuery(text="policy", collection="policies", top_k=5))

    assert response.indexed_chunk_count == 1
    assert [result.collection for result in response.results] == ["policies"]


def test_retrieval_query_normalization_rejects_empty_query_and_caps_top_k() -> None:
    normalized = normalize_retrieval_query(RetrievalQuery(text="  agentic  ", top_k=999))

    assert normalized.text == "agentic"
    assert normalized.top_k == 20

    with pytest.raises(ValueError, match="query text is required"):
        normalize_retrieval_query(RetrievalQuery(text="   "))
