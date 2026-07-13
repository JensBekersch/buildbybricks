"""Runtime configuration for the study template."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Small configuration object that can later be backed by environment variables."""

    app_name: str = "Agentic RAG Study Template"
    data_dir: Path = Path("data")
    sample_data_dir: Path = Path("data/sample")
    frontend_dir: Path = Path("frontend")
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables used by local and Docker runs."""
        return cls(
            data_dir=Path(os.getenv("AGENTIC_RAG_DATA_DIR", "data")),
            sample_data_dir=Path(os.getenv("AGENTIC_RAG_SAMPLE_DATA_DIR", "data/sample")),
            frontend_dir=Path(os.getenv("AGENTIC_RAG_FRONTEND_DIR", "frontend")),
            host=os.getenv("AGENTIC_RAG_HOST", "0.0.0.0"),
            port=int(os.getenv("AGENTIC_RAG_PORT", "8000")),
            debug=os.getenv("AGENTIC_RAG_DEBUG", "true").lower() == "true",
        )
