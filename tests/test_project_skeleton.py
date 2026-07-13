from agentic_rag_template import __version__
from agentic_rag_template.app import create_server
from agentic_rag_template.api.schemas import ChatRequest, ChatResponse
from agentic_rag_template.config import Settings
import json
from pathlib import Path
import threading
from urllib import request


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


def test_local_server_exposes_health_and_chat(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    data_dir = tmp_path / "data"
    frontend_dir.mkdir()
    data_dir.mkdir()
    (frontend_dir / "index.html").write_text("<h1>Chat</h1>", encoding="utf-8")
    settings = Settings(frontend_dir=frontend_dir, data_dir=data_dir, host="127.0.0.1", port=0)
    server = create_server(settings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        health_response = request.urlopen(f"http://{host}:{port}/health", timeout=2)
        health_payload = json.loads(health_response.read().decode("utf-8"))
        collections_response = request.urlopen(f"http://{host}:{port}/collections", timeout=2)
        collections_payload = json.loads(collections_response.read().decode("utf-8"))
        search_response = request.urlopen(
            f"http://{host}:{port}/vector-store/preview?q=agentic",
            timeout=2,
        )
        search_payload = json.loads(search_response.read().decode("utf-8"))
        retrieval_response = request.urlopen(
            f"http://{host}:{port}/retrieval/search?q=agentic",
            timeout=2,
        )
        retrieval_payload = json.loads(retrieval_response.read().decode("utf-8"))

        chat_request = request.Request(
            f"http://{host}:{port}/chat",
            data=json.dumps({"message": "Hallo"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        chat_response = request.urlopen(chat_request, timeout=2)
        chat_payload = json.loads(chat_response.read().decode("utf-8"))

        assert health_payload["status"] == "ok"
        assert collections_payload == {"collections": []}
        assert search_payload["provider"] == "hash"
        assert search_payload["indexed_chunk_count"] == 0
        assert retrieval_payload["provider"] == "hash"
        assert retrieval_payload["indexed_chunk_count"] == 0
        assert retrieval_payload["trace"] == [
            "loaded_chunks",
            "embedded_chunks",
            "searched_vector_store",
            "formatted_retrieval_results",
        ]
        assert "keine passende Quelle gefunden" in chat_payload["answer"]
        assert chat_payload["trace"] == [
            "validated_message",
            "searched_knowledge_base",
            "skipped_source_read",
            "composed_answer",
        ]
        assert [tool_call["name"] for tool_call in chat_payload["tool_calls"]] == [
            "search_knowledge_base",
            "answer_with_citations",
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
