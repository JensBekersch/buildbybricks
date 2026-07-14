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
    template_dir: Path = Path("template")
    host: str = "0.0.0.0"
    port: int = 8000
    embedding_provider: str = "hash"
    embedding_model: str = "local-hash-v1"
    embedding_dimension: int = 64
    embedding_api_base_url: str = "http://localhost:11434"
    embedding_api_key: str = ""
    llm_provider: str = "deterministic"
    llm_model: str = "local-deterministic-v1"
    llm_api_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""
    debug: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables used by local and Docker runs."""
        return cls(
            data_dir=Path(os.getenv("AGENTIC_RAG_DATA_DIR", "data")),
            sample_data_dir=Path(os.getenv("AGENTIC_RAG_SAMPLE_DATA_DIR", "data/sample")),
            frontend_dir=Path(os.getenv("AGENTIC_RAG_FRONTEND_DIR", "frontend")),
            template_dir=Path(os.getenv("AGENTIC_RAG_TEMPLATE_DIR", "template")),
            host=os.getenv("AGENTIC_RAG_HOST", "0.0.0.0"),
            port=int(os.getenv("AGENTIC_RAG_PORT", "8000")),
            embedding_provider=os.getenv("AGENTIC_RAG_EMBEDDING_PROVIDER", "hash"),
            embedding_model=os.getenv("AGENTIC_RAG_EMBEDDING_MODEL", "local-hash-v1"),
            embedding_dimension=int(os.getenv("AGENTIC_RAG_EMBEDDING_DIMENSION", "64")),
            embedding_api_base_url=os.getenv(
                "AGENTIC_RAG_EMBEDDING_API_BASE_URL",
                "http://localhost:11434",
            ),
            embedding_api_key=os.getenv("AGENTIC_RAG_EMBEDDING_API_KEY", ""),
            llm_provider=os.getenv("AGENTIC_RAG_LLM_PROVIDER", "deterministic"),
            llm_model=os.getenv("AGENTIC_RAG_LLM_MODEL", "local-deterministic-v1"),
            llm_api_base_url=os.getenv(
                "AGENTIC_RAG_LLM_API_BASE_URL",
                "http://localhost:11434",
            ),
            llm_api_key=os.getenv("AGENTIC_RAG_LLM_API_KEY", ""),
            debug=os.getenv("AGENTIC_RAG_DEBUG", "true").lower() == "true",
        )
