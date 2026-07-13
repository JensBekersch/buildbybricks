"""Default evaluation cases for the sample collection."""

import json
from pathlib import Path
from typing import Any, Dict, List

from agentic_rag_template.evaluation.models import EvaluationCase


def default_evaluation_cases(template_dir: Path = Path("template")) -> List[EvaluationCase]:
    """Return evaluation cases from template config or bundled defaults."""
    configured_cases = load_evaluation_cases(template_dir)

    if configured_cases:
        return configured_cases

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


def load_evaluation_cases(template_dir: Path) -> List[EvaluationCase]:
    """Load evaluation cases from template/evaluation_cases.json when present."""
    cases_path = template_dir / "evaluation_cases.json"

    if not cases_path.exists():
        return []

    payload = json.loads(cases_path.read_text(encoding="utf-8"))

    if not isinstance(payload, list):
        raise ValueError(f"{cases_path} must contain a JSON array")

    return [case_from_dict(item) for item in payload]


def case_from_dict(payload: Dict[str, Any]) -> EvaluationCase:
    """Convert a JSON object into an evaluation case."""
    return EvaluationCase(
        id=str(payload["id"]),
        question=str(payload["question"]),
        collection=payload.get("collection"),
        expected_source_locations=list(payload.get("expected_source_locations", [])),
        required_answer_terms=list(payload.get("required_answer_terms", [])),
        require_sources=bool(payload.get("require_sources", True)),
        require_uncertainty=bool(payload.get("require_uncertainty", True)),
        required_tool_calls=list(payload.get("required_tool_calls", [])),
    )
