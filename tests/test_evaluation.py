from pathlib import Path

from agentic_rag_template.agent import StudyAgent
from agentic_rag_template.embeddings import HashEmbeddingProvider
from agentic_rag_template.evaluation import EvaluationCase, EvaluationRunner, default_evaluation_cases
from agentic_rag_template.evaluation.runner import build_checks


def test_default_evaluation_cases_are_defined() -> None:
    cases = default_evaluation_cases()

    assert len(cases) >= 2
    assert cases[0].expected_source_locations == ["sample/agentic_rag_basics.md"]
    assert "search_knowledge_base" in cases[0].required_tool_calls


def test_evaluation_runner_passes_sample_case(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "agentic_rag_basics.md").write_text(
        "Agentic RAG verbindet Retrieval mit einem kontrollierten Agentenablauf.",
        encoding="utf-8",
    )
    agent = StudyAgent(tmp_path, HashEmbeddingProvider(dimension=32))
    runner = EvaluationRunner(agent)
    case = EvaluationCase(
        id="sample",
        question="Was ist Agentic RAG?",
        collection="sample",
        expected_source_locations=["sample/agentic_rag_basics.md"],
        required_answer_terms=["Kurzantwort", "Quellen"],
        required_tool_calls=[
            "search_knowledge_base",
            "read_source",
            "answer_with_citations",
        ],
    )

    report = runner.run([case])

    assert report.passed
    assert report.total_cases == 1
    assert report.results[0].passed
    assert report.results[0].sources[0]["location"] == "sample/agentic_rag_basics.md"


def test_evaluation_checks_fail_when_required_source_is_missing() -> None:
    case = EvaluationCase(
        id="missing-source",
        question="Question",
        expected_source_locations=["sample/missing.md"],
        required_answer_terms=["Kurzantwort"],
        required_tool_calls=["search_knowledge_base"],
    )

    checks = build_checks(
        case=case,
        answer="Kurzantwort",
        source_locations=[],
        uncertainty="Keine lokalen Treffer.",
        tool_call_names=["search_knowledge_base"],
    )

    failed_checks = [check.name for check in checks if not check.passed]

    assert "expected_sources" in failed_checks
    assert "sources_required" in failed_checks
