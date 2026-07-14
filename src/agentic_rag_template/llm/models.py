"""Shared LLM provider contracts."""

from dataclasses import dataclass, field
from typing import List, Protocol

from agentic_rag_template.retrieval import RetrievedChunk


@dataclass(frozen=True)
class LLMRequest:
    """Input for answer generation."""

    query: str
    retrieved_chunks: List[RetrievedChunk]
    answer_policy: str


@dataclass(frozen=True)
class LLMResponse:
    """Output from an answer generation provider."""

    answer: str
    uncertainty: str
    trace: List[str] = field(default_factory=list)


class LLMProvider(Protocol):
    """Provider interface for answer generation."""

    name: str
    model: str

    def generate_answer(self, request: LLMRequest) -> LLMResponse:
        """Generate one grounded answer."""


@dataclass(frozen=True)
class LLMProviderConfig:
    """Configuration for current and future LLM providers."""

    provider: str = "deterministic"
    model: str = "local-deterministic-v1"
    api_base_url: str = "http://localhost:11434"
    api_key: str = ""
