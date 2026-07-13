"""Evaluation runner for the deterministic study agent."""

from pathlib import Path
from typing import Iterable, List

from agentic_rag_template.agent import AgentRequest, StudyAgent
from agentic_rag_template.evaluation.fixtures import default_evaluation_cases
from agentic_rag_template.evaluation.models import (
    EvaluationCase,
    EvaluationCheck,
    EvaluationReport,
    EvaluationResult,
)


class EvaluationRunner:
    """Run evaluation cases against the current agent behavior."""

    def __init__(self, agent: StudyAgent) -> None:
        self.agent = agent

    def run(self, cases: Iterable[EvaluationCase]) -> EvaluationReport:
        results = [self.run_case(case) for case in cases]
        passed_cases = sum(1 for result in results if result.passed)

        return EvaluationReport(
            passed=passed_cases == len(results),
            total_cases=len(results),
            passed_cases=passed_cases,
            failed_cases=len(results) - passed_cases,
            results=results,
        )

    def run_default(self) -> EvaluationReport:
        return self.run(default_evaluation_cases())

    def run_template(self, template_dir: Path) -> EvaluationReport:
        return self.run(default_evaluation_cases(template_dir))

    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        response = self.agent.answer(
            AgentRequest(
                message=case.question,
                collection=case.collection,
                top_k=3,
            )
        )
        source_locations = [source.location for source in response.sources]
        tool_call_names = [tool_call.name for tool_call in response.tool_calls]
        checks = build_checks(case, response.answer, source_locations, response.uncertainty, tool_call_names)

        return EvaluationResult(
            case_id=case.id,
            question=case.question,
            passed=all(check.passed for check in checks),
            checks=checks,
            answer=response.answer,
            sources=[
                {
                    "title": source.title,
                    "location": source.location,
                    "excerpt": source.excerpt,
                    "score": source.score,
                }
                for source in response.sources
            ],
            uncertainty=response.uncertainty,
            tool_calls=tool_call_names,
        )


def build_checks(
    case: EvaluationCase,
    answer: str,
    source_locations: List[str],
    uncertainty: str,
    tool_call_names: List[str],
) -> List[EvaluationCheck]:
    """Build pass/fail checks from observable agent output."""
    checks = [
        EvaluationCheck(
            name="answer_not_empty",
            passed=bool(answer.strip()),
            details="answer has content",
        ),
        EvaluationCheck(
            name="required_answer_terms",
            passed=all(term.lower() in answer.lower() for term in case.required_answer_terms),
            details=", ".join(case.required_answer_terms) or "no required terms",
        ),
        EvaluationCheck(
            name="expected_sources",
            passed=all(location in source_locations for location in case.expected_source_locations),
            details=", ".join(source_locations) or "no sources",
        ),
        EvaluationCheck(
            name="sources_required",
            passed=(not case.require_sources) or bool(source_locations),
            details=f"{len(source_locations)} source(s)",
        ),
        EvaluationCheck(
            name="uncertainty_required",
            passed=(not case.require_uncertainty) or bool(uncertainty.strip()),
            details=uncertainty or "no uncertainty",
        ),
        EvaluationCheck(
            name="required_tool_calls",
            passed=all(tool_call in tool_call_names for tool_call in case.required_tool_calls),
            details=", ".join(tool_call_names) or "no tool calls",
        ),
    ]
    return checks
