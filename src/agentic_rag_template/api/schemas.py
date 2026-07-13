"""Shared request and response shapes for the future chat API."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ChatRequest:
    """A user message submitted through the chat frontend."""

    message: str
    conversation_id: Optional[str] = None


@dataclass(frozen=True)
class SourceReference:
    """A source that supports a generated answer."""

    title: str
    location: str


@dataclass(frozen=True)
class ChatResponse:
    """The structured response returned by the future chat endpoint."""

    answer: str
    sources: List[SourceReference] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)
