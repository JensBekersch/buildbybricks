from agentic_rag_template.retrieval import RetrievedChunk
from agentic_rag_template.tools import compose_grounded_answer


def test_compose_grounded_answer_includes_citations_and_uncertainty() -> None:
    result = RetrievedChunk(
        id="sample:guide.md:0",
        score=0.5,
        collection="sample",
        source_path="sample/guide.md",
        title="guide",
        text="Agentic RAG answers with local sources and explicit uncertainty.",
        chunk_index=0,
        metadata={"filename": "guide.md"},
    )

    draft = compose_grounded_answer("What is agentic RAG?", [result])

    assert "Kurzantwort:" in draft.answer
    assert "Quellen:" in draft.answer
    assert draft.citations[0].location == "sample/guide.md"
    assert draft.sources[0].excerpt == "Agentic RAG answers with local sources and explicit uncertainty."
    assert "lokal belegt" in draft.uncertainty


def test_compose_grounded_answer_handles_missing_sources() -> None:
    draft = compose_grounded_answer("Unknown?", [])

    assert "keine passende Quelle gefunden" in draft.answer
    assert draft.citations == []
    assert "Keine lokalen Treffer" in draft.uncertainty
