"""Default evaluation cases for the sample collection."""

from typing import List

from agentic_rag_template.evaluation.models import EvaluationCase


def default_evaluation_cases() -> List[EvaluationCase]:
    """Return a small baseline evaluation set for the bundled sample data."""
    return [
        EvaluationCase(
            id="sample-agentic-rag-source",
            question="Was ist Agentic RAG?",
            collection="sample",
            expected_source_locations=["sample/agentic_rag_basics.md"],
            required_answer_terms=["Kurzantwort", "Quellen"],
            required_tool_calls=[
                "search_knowledge_base",
                "read_source",
                "answer_with_citations",
            ],
        ),
        EvaluationCase(
            id="sample-collection-structure",
            question="Wie werden lokale Collections organisiert?",
            collection="sample",
            expected_source_locations=["sample/agentic_rag_basics.md"],
            required_answer_terms=["Quellen"],
            required_tool_calls=[
                "search_knowledge_base",
                "read_source",
                "answer_with_citations",
            ],
        ),
    ]
