"""Configurable application profile structures."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ApplicationProfile:
    """Application-specific text and defaults loaded from template files."""

    name: str = "Agentic RAG Study Template"
    description: str = "Reusable local agentic RAG study template."
    default_collection: str = "sample"
    default_top_k: int = 3
    answer_policy: str = "Answer only from local sources and state uncertainty."
    enabled_tools: List[str] = field(
        default_factory=lambda: [
            "search_knowledge_base",
            "read_source",
            "answer_with_citations",
        ]
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "default_collection": self.default_collection,
            "default_top_k": self.default_top_k,
            "answer_policy": self.answer_policy,
            "enabled_tools": self.enabled_tools,
        }
