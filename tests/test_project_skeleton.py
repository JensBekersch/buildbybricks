from agentic_rag_template import __version__
from agentic_rag_template.api.schemas import ChatRequest, ChatResponse
from agentic_rag_template.config import Settings


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"


def test_default_settings_point_to_project_folders() -> None:
    settings = Settings()

    assert settings.data_dir.as_posix() == "data"
    assert settings.frontend_dir.as_posix() == "frontend"


def test_chat_schema_defaults_are_empty_collections() -> None:
    request = ChatRequest(message="Was ist im Repo geplant?")
    response = ChatResponse(answer="Noch kein Agent angebunden.")

    assert request.conversation_id is None
    assert response.sources == []
    assert response.trace == []
