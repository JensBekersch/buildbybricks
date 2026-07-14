import json

from agentic_rag_template.config import Settings
from agentic_rag_template.llm import DeterministicLLMProvider, OllamaLLMProvider, create_llm_provider
from agentic_rag_template.llm.models import LLMRequest
from agentic_rag_template.llm.ollama_provider import build_payload
from agentic_rag_template.retrieval import RetrievedChunk


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="sample:guide.md:0",
        score=0.75,
        collection="sample",
        source_path="sample/guide.md",
        title="guide",
        text="Agentic RAG uses retrieved local context.",
        chunk_index=0,
        metadata={},
    )


def test_llm_factory_creates_deterministic_provider() -> None:
    provider = create_llm_provider(Settings(llm_provider="deterministic", llm_model="local-test"))

    assert provider.name == "deterministic"
    assert provider.model == "local-test"


def test_llm_factory_creates_ollama_provider() -> None:
    provider = create_llm_provider(
        Settings(
            llm_provider="ollama",
            llm_model="llama3.1",
            llm_api_base_url="http://ollama:11434",
        )
    )

    assert provider.name == "ollama"
    assert provider.model == "llama3.1"


def test_deterministic_llm_provider_keeps_existing_grounded_answer_shape() -> None:
    response = DeterministicLLMProvider().generate_answer(
        LLMRequest(
            query="What is agentic RAG?",
            retrieved_chunks=[make_chunk()],
            answer_policy="Use sources.",
        )
    )

    assert "Kurzantwort:" in response.answer
    assert response.uncertainty
    assert response.trace == ["deterministic_answer_composed"]


def test_ollama_payload_contains_context_and_citation_instructions() -> None:
    payload = build_payload(
        LLMRequest(
            query="What is agentic RAG?",
            retrieved_chunks=[make_chunk()],
            answer_policy="Use only local sources.",
        ),
        model="llama3.1",
    )

    assert payload["model"] == "llama3.1"
    assert payload["stream"] is False
    assert "Use only local sources." in payload["messages"][0]["content"]
    assert "sample/guide.md" in payload["messages"][1]["content"]


def test_ollama_provider_parses_chat_response(monkeypatch) -> None:
    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return json.dumps({"message": {"content": "Antwort mit Quelle [1]."}}).encode("utf-8")

    def fake_urlopen(req, timeout):
        assert req.full_url == "http://ollama:11434/api/chat"
        assert timeout == 120
        return FakeHTTPResponse()

    monkeypatch.setattr("agentic_rag_template.llm.ollama_provider.request.urlopen", fake_urlopen)
    provider = OllamaLLMProvider(model="llama3.1", api_base_url="http://ollama:11434")
    response = provider.generate_answer(
        LLMRequest(
            query="What is agentic RAG?",
            retrieved_chunks=[make_chunk()],
            answer_policy="Use sources.",
        )
    )

    assert response.answer == "Antwort mit Quelle [1]."
    assert response.trace == ["ollama_chat_completed"]
