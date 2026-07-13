"""Evaluation data structures for repeatable agent checks."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvaluationCase:
    """One repeatable question and its expected observable properties."""

    id: str
    question: str
    collection: Optional[str] = None
    expected_source_locations: List[str] = field(default_factory=list)
    required_answer_terms: List[str] = field(default_factory=list)
    require_sources: bool = True
    require_uncertainty: bool = True
    required_tool_calls: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvaluationCheck:
    """One pass/fail check inside an evaluation case."""

    name: str
    passed: bool
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
        }


@dataclass(frozen=True)
class EvaluationResult:
    """Evaluation result for one case."""

    case_id: str
    question: str
    passed: bool
    checks: List[EvaluationCheck]
    answer: str
    sources: List[Dict[str, Any]]
    uncertainty: str
    tool_calls: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "question": self.question,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "answer": self.answer,
            "sources": self.sources,
            "uncertainty": self.uncertainty,
            "tool_calls": self.tool_calls,
        }


@dataclass(frozen=True)
class EvaluationReport:
    """Summary for a full evaluation run."""

    passed: bool
    total_cases: int
    passed_cases: int
    failed_cases: int
    results: List[EvaluationResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "results": [result.to_dict() for result in self.results],
        }
