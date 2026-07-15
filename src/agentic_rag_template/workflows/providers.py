"""Provider adapter contracts for workflow agents."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


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

