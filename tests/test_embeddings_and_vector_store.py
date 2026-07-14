from pathlib import Path
import json

import pytest

from agentic_rag_template.config import Settings
from agentic_rag_template.embeddings import (
    HashEmbeddingProvider,
    OllamaEmbeddingProvider,
    create_embedding_provider,
)
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


def test_embedding_provider_factory_creates_ollama_provider() -> None:
    settings = Settings(
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        embedding_dimension=0,
        embedding_api_base_url="http://ollama:11434",
    )

    provider = create_embedding_provider(settings)

    assert provider.name == "ollama"
    assert provider.model == "nomic-embed-text"
    assert provider.dimension == 0
    assert provider.api_base_url == "http://ollama:11434"


def test_embedding_provider_factory_rejects_unimplemented_provider() -> None:
    settings = Settings(embedding_provider="openai", embedding_model="text-embedding-3-small")

    with pytest.raises(ValueError, match="Supported providers"):
        create_embedding_provider(settings)


def test_ollama_embedding_provider_parses_and_normalizes_response(monkeypatch) -> None:
    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return json.dumps({"embedding": [3.0, 4.0]}).encode("utf-8")

    def fake_urlopen(req, timeout):
        body = json.loads(req.data.decode("utf-8"))
        assert req.full_url == "http://ollama:11434/api/embeddings"
        assert body == {"model": "nomic-embed-text", "prompt": "Agentic RAG"}
        assert timeout == 300
        return FakeHTTPResponse()

    monkeypatch.setattr("agentic_rag_template.embeddings.ollama_provider.request.urlopen", fake_urlopen)
    provider = OllamaEmbeddingProvider(model="nomic-embed-text", api_base_url="http://ollama:11434")

    assert provider.embed_text("Agentic RAG") == [0.6, 0.8]
    assert provider.dimension == 2


def test_ollama_embedding_provider_rejects_dimension_mismatch(monkeypatch) -> None:
    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return json.dumps({"embedding": [1.0, 2.0, 3.0]}).encode("utf-8")

    def fake_urlopen(req, timeout):
        return FakeHTTPResponse()

    monkeypatch.setattr("agentic_rag_template.embeddings.ollama_provider.request.urlopen", fake_urlopen)
    provider = OllamaEmbeddingProvider(model="nomic-embed-text", dimension=2)

    with pytest.raises(RuntimeError, match="dimension mismatch"):
        provider.embed_text("Agentic RAG")


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
