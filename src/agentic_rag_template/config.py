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
    apps_dir: Path = Path("apps")
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
    llm_timeout_seconds: int = 3600
    llm_max_tokens: int = 4096
    architecture_generation_mode: str = "agentic_with_review"
    database_url: str = "postgresql://agentic_rag:agentic_rag@localhost:5432/agentic_rag"
    worker_poll_seconds: float = 2.0
    job_stream_poll_seconds: float = 1.0
    debug: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables used by local and Docker runs."""
        return cls(
            data_dir=Path(os.getenv("AGENTIC_RAG_DATA_DIR", "data")),
            sample_data_dir=Path(os.getenv("AGENTIC_RAG_SAMPLE_DATA_DIR", "data/sample")),
            frontend_dir=Path(os.getenv("AGENTIC_RAG_FRONTEND_DIR", "frontend")),
            template_dir=Path(os.getenv("AGENTIC_RAG_TEMPLATE_DIR", "template")),
            apps_dir=Path(os.getenv("AGENTIC_RAG_APPS_DIR", "apps")),
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
            llm_timeout_seconds=int(os.getenv("AGENTIC_RAG_LLM_TIMEOUT_SECONDS", "3600")),
            llm_max_tokens=int(os.getenv("AGENTIC_RAG_LLM_MAX_TOKENS", "4096")),
            architecture_generation_mode=os.getenv(
                "AGENTIC_RAG_ARCHITECTURE_GENERATION_MODE",
                "agentic_with_review",
            ).strip().lower().replace("-", "_"),
            database_url=os.getenv(
                "AGENTIC_RAG_DATABASE_URL",
                "postgresql://agentic_rag:agentic_rag@localhost:5432/agentic_rag",
            ),
            worker_poll_seconds=float(os.getenv("AGENTIC_RAG_WORKER_POLL_SECONDS", "2")),
            job_stream_poll_seconds=float(os.getenv("AGENTIC_RAG_JOB_STREAM_POLL_SECONDS", "1")),
            debug=os.getenv("AGENTIC_RAG_DEBUG", "true").lower() == "true",
        )

    def runtime_config(self) -> dict:
        """Return non-secret runtime configuration for API and UI inspection."""
        return {
            "app_name": self.app_name,
            "llm": {
                "provider": self.llm_provider,
                "model": self.llm_model,
                "api_base_url": self.llm_api_base_url,
                "api_key_configured": bool(self.llm_api_key),
                "timeout_seconds": self.llm_timeout_seconds,
                "max_tokens": self.llm_max_tokens,
                "scope": "global",
            },
            "pipelines": {
                "architecture_sheet": {
                    "mode": self.architecture_generation_mode,
                    "supported_modes": ["agentic_with_review", "agentic"],
                    "llm_provider": self.llm_provider,
                    "llm_model": self.llm_model,
                    "timeout_seconds": self.llm_timeout_seconds,
                    "max_tokens": self.llm_max_tokens,
                    "scope": "global-default",
                }
            },
            "future_overrides": {
                "per_app": False,
                "per_pipeline": False,
            },
        }
