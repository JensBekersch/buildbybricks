"""Provider adapter contracts for workflow agents."""

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Protocol

from agentic_rag_template.llm.deterministic_provider import DeterministicLLMProvider
from agentic_rag_template.llm.models import LLMProvider
from agentic_rag_template.llm.ollama_provider import OllamaLLMProvider


@dataclass(frozen=True)
class WorkflowLLMRequest:
    system_prompt: str
    user_prompt: str
    provider: str
    model: str
    api_base_url: str = ""
    api_key: str = ""
    timeout_seconds: int = 0
    max_tokens: int = 0
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

        llm_provider = self._provider_for_request(request)
        generate_json = getattr(llm_provider, "generate_json", None)
        if not callable(generate_json):
            raise RuntimeError(
                f"LLM provider '{getattr(llm_provider, 'name', 'none')}' does not support structured JSON generation."
            )

        parsed_output = generate_json(
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
        )
        return WorkflowLLMResponse(
            raw_output=json.dumps(parsed_output, ensure_ascii=True),
            parsed_output=parsed_output,
            metadata={
                "provider": getattr(llm_provider, "name", request.provider),
                "model": getattr(llm_provider, "model", request.model),
                "requested_provider": request.provider,
                "requested_model": request.model,
            },
        )

    def _provider_for_request(self, request: WorkflowLLMRequest) -> LLMProvider:
        provider = request.provider.lower().strip()
        model = request.model.strip()
        if not provider:
            return self.llm_provider
        if provider not in {"deterministic", "ollama"}:
            return self.llm_provider

        current_provider = getattr(self.llm_provider, "name", "").lower()
        current_model = getattr(self.llm_provider, "model", "")
        if provider == current_provider and (not model or model == current_model) and not request.api_base_url:
            return self.llm_provider

        if provider == "deterministic":
            return DeterministicLLMProvider(model=model or "local-deterministic-v1")

        if provider == "ollama":
            return OllamaLLMProvider(
                model=model,
                api_base_url=request.api_base_url or "http://localhost:11434",
                api_key=request.api_key,
                timeout_seconds=request.timeout_seconds or 300,
                max_tokens=request.max_tokens or 2048,
            )

        raise RuntimeError(f"LLM provider '{request.provider}' is not implemented for workflow agents.")


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
