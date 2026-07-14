"""Deterministic LLM provider used for tests and offline operation."""

from agentic_rag_template.llm.models import LLMRequest, LLMResponse
from agentic_rag_template.tools.answering import compose_grounded_answer


class DeterministicLLMProvider:
    """Answer provider that uses the local deterministic answer composer."""

    name = "deterministic"

    def __init__(self, model: str = "local-deterministic-v1") -> None:
        self.model = model

    def generate_answer(self, request: LLMRequest) -> LLMResponse:
        draft = compose_grounded_answer(request.query, request.retrieved_chunks)
        return LLMResponse(
            answer=draft.answer,
            uncertainty=draft.uncertainty,
            trace=["deterministic_answer_composed"],
        )
