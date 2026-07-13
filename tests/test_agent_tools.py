from pathlib import Path

import pytest

from agentic_rag_template.agent import AgentRequest, StudyAgent
from agentic_rag_template.embeddings import HashEmbeddingProvider
from agentic_rag_template.tools import read_source, search_knowledge_base


def test_search_knowledge_base_returns_retrieved_chunks(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "agent.md").write_text("Agentic RAG uses retrieval tools.", encoding="utf-8")

    results = search_knowledge_base(
        data_dir=tmp_path,
        embedding_provider=HashEmbeddingProvider(dimension=32),
        query="agentic retrieval",
        collection="sample",
        top_k=2,
    )

    assert len(results) == 1
    assert results[0].source_path == "sample/agent.md"


def test_read_source_rejects_paths_outside_data_dir(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must stay within data_dir"):
        read_source(tmp_path, "../secret.txt")


def test_study_agent_uses_tools_and_returns_sources(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "agent.md").write_text(
        "Agentic RAG searches local knowledge before answering.",
        encoding="utf-8",
    )

    agent = StudyAgent(tmp_path, HashEmbeddingProvider(dimension=32))
    response = agent.answer(AgentRequest(message="How does agentic RAG answer?", collection="sample"))

    assert "Kurzantwort:" in response.answer
    assert "Quellen:" in response.answer
    assert response.uncertainty
    assert response.sources[0].location == "sample/agent.md"
    assert response.sources[0].excerpt
    assert [tool_call.name for tool_call in response.tool_calls] == [
        "search_knowledge_base",
        "read_source",
        "answer_with_citations",
    ]
    assert response.trace == [
        "validated_message",
        "searched_knowledge_base",
        "read_top_source",
        "composed_answer",
    ]
