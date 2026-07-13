from pathlib import Path

import pytest

from agentic_rag_template.config import Settings
from agentic_rag_template.embeddings import HashEmbeddingProvider, create_embedding_provider
from agentic_rag_template.ingestion import ingest_data
from agentic_rag_template.retrieval import InMemoryVectorStore


def test_hash_embedding_provider_is_deterministic_and_configurable() -> None:
    provider = HashEmbeddingProvider(model="test-hash", dimension=16)

    first = provider.embed_text("Agentic RAG retrieval")
    second = provider.embed_text("Agentic RAG retrieval")

    assert first == second
    assert provider.model == "test-hash"
    assert len(first) == 16


def test_embedding_provider_factory_uses_settings() -> None:
    settings = Settings(
        embedding_provider="hash",
        embedding_model="local-test",
        embedding_dimension=8,
    )

    provider = create_embedding_provider(settings)

    assert provider.name == "hash"
    assert provider.model == "local-test"
    assert provider.dimension == 8


def test_embedding_provider_factory_rejects_unimplemented_provider() -> None:
    settings = Settings(embedding_provider="ollama", embedding_model="nomic-embed-text")

    with pytest.raises(ValueError, match="not implemented yet"):
        create_embedding_provider(settings)


def test_vector_store_searches_chunks_and_filters_by_collection(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample"
    policies_dir = tmp_path / "policies"
    sample_dir.mkdir()
    policies_dir.mkdir()
    (sample_dir / "rag.md").write_text("Agentic retrieval uses chunks and tools.", encoding="utf-8")
    (policies_dir / "security.md").write_text("Security policy requires access review.", encoding="utf-8")

    chunks = ingest_data(tmp_path, chunk_size=200, overlap=20)
    provider = HashEmbeddingProvider(dimension=32)
    vector_store = InMemoryVectorStore(provider)
    vector_store.add_chunks(chunks)

    all_results = vector_store.search("agentic retrieval", top_k=2)
    filtered_results = vector_store.search("security policy", top_k=2, collection="policies")

    assert vector_store.size == 2
    assert all_results[0].chunk.collection == "sample"
    assert filtered_results
    assert {result.chunk.collection for result in filtered_results} == {"policies"}
