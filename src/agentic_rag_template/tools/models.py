"""Shared structures for agent tool execution."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ToolCall:
    """One executed tool call for agent tracing."""

    name: str
    arguments: Dict[str, Any]
    result_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
            "result_summary": self.result_summary,
        }
