"""Runtime configuration for the study template."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Small configuration object that can later be backed by environment variables."""

    app_name: str = "Agentic RAG Study Template"
    data_dir: Path = Path("data")
    sample_data_dir: Path = Path("data/sample")
    frontend_dir: Path = Path("frontend")
    debug: bool = True
