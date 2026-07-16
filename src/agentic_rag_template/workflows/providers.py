"""Provider adapter contracts for workflow agents."""

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Protocol

from agentic_rag_template.llm.models import LLMProvider


@dataclass(frozen=True)
class WorkflowLLMRequest:
    system_prompt: str
    user_prompt: str
    provider: str
    model: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    response_format: str = "json"


@dataclass(frozen=True)
class WorkflowLLMResponse:
    raw_output: str
    parsed_output: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMProviderAdapter(Protocol):
    def invoke(self, request: WorkflowLLMRequest) -> WorkflowLLMResponse:
        """Invoke one model behind a provider-neutral interface."""


class LLMProviderWorkflowAdapter:
    """Adapter from the configured application LLM provider to workflow agents."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def invoke(self, request: WorkflowLLMRequest) -> WorkflowLLMResponse:
        if request.response_format != "json":
            raise RuntimeError(f"unsupported workflow response format: {request.response_format}")

        generate_json = getattr(self.llm_provider, "generate_json", None)
        if not callable(generate_json):
            raise RuntimeError(
                f"LLM provider '{getattr(self.llm_provider, 'name', 'none')}' does not support structured JSON generation."
            )

        parsed_output = generate_json(
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
        )
        return WorkflowLLMResponse(
            raw_output=json.dumps(parsed_output, ensure_ascii=True),
            parsed_output=parsed_output,
            metadata={
                "provider": getattr(self.llm_provider, "name", request.provider),
                "model": getattr(self.llm_provider, "model", request.model),
                "requested_provider": request.provider,
                "requested_model": request.model,
            },
        )


class FakeLLMProviderAdapter:
    """Deterministic adapter used by workflow tests."""

    def __init__(self, responses: List[Any]) -> None:
        self.responses = list(responses)
        self.requests: List[WorkflowLLMRequest] = []

    def invoke(self, request: WorkflowLLMRequest) -> WorkflowLLMResponse:
        self.requests.append(request)
        if not self.responses:
            raise RuntimeError("fake provider has no response left")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, str):
            return WorkflowLLMResponse(raw_output=response, metadata={"provider": request.provider, "model": request.model})
        return WorkflowLLMResponse(
            raw_output=response.get("raw_output", ""),
            parsed_output=response.get("parsed_output"),
            metadata=response.get("metadata", {"provider": request.provider, "model": request.model}),
        )
