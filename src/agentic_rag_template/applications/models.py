"""Application instance models for configurable RAG apps."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agentic_rag_template.template_config import ApplicationProfile


@dataclass(frozen=True)
class ApplicationSummary:
    """List view metadata for one configured application."""

    id: str
    name: str
    description: str
    default_collection: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "default_collection": self.default_collection,
        }


@dataclass(frozen=True)
class ApplicationInstance:
    """Resolved runtime paths and profile for one application."""

    id: str
    profile: ApplicationProfile
    template_dir: Path
    data_dir: Path

    def summary(self) -> ApplicationSummary:
        return ApplicationSummary(
            id=self.id,
            name=self.profile.name,
            description=self.profile.description,
            default_collection=self.profile.default_collection,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.summary().to_dict(),
            "template_dir": self.template_dir.as_posix(),
            "data_dir": self.data_dir.as_posix(),
            "profile": self.profile.to_dict(),
        }
