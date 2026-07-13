"""Application entrypoint for the agentic RAG template."""

from agentic_rag_template.config import Settings


def create_app_settings() -> Settings:
    """Create application settings for the current runtime."""
    return Settings()
