"""Agent input and output structures."""

from dataclasses import dataclass, field
from typing import List, Optional

from agentic_rag_template.api.schemas import SourceReference
from agentic_rag_template.tools import ToolCall


@dataclass(frozen=True)
class AgentRequest:
    """A user request handled by the first deterministic agent."""

    message: str
    collection: Optional[str] = None
    top_k: int = 3


@dataclass(frozen=True)
class AgentResponse:
    """The agent answer plus sources and trace details."""

    answer: str
    sources: List[SourceReference] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
