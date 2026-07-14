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
    apps_dir = tmp_path / "apps"
    template_dir = tmp_path / "template"
    frontend_dir.mkdir()
    data_dir.mkdir()
    template_dir.mkdir()
    policy_app_dir = apps_dir / "policy-assistant"
    policy_app_dir.mkdir(parents=True)
    policy_data_dir = data_dir / "policy-assistant" / "policies"
    policy_data_dir.mkdir(parents=True)
    (frontend_dir / "index.html").write_text("<h1>Chat</h1>", encoding="utf-8")
    (policy_app_dir / "app_profile.json").write_text(
        json.dumps(
            {
                "name": "Policy Assistant",
                "description": "Answers from policy docs.",
                "default_collection": "policies",
                "default_top_k": 2,
                "answer_policy": "Use policy sources only.",
            }
        ),
        encoding="utf-8",
    )
    (policy_data_dir / "rules.md").write_text(
        "Policy documents explain approval workflows.",
        encoding="utf-8",
    )
    settings = Settings(
        frontend_dir=frontend_dir,
        data_dir=data_dir,
        template_dir=template_dir,
        apps_dir=apps_dir,
        host="127.0.0.1",
        port=0,
    )
    server = create_server(settings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        health_response = request.urlopen(f"http://{host}:{port}/health", timeout=2)
        health_payload = json.loads(health_response.read().decode("utf-8"))
        collections_response = request.urlopen(f"http://{host}:{port}/collections", timeout=2)
        collections_payload = json.loads(collections_response.read().decode("utf-8"))
        apps_response = request.urlopen(f"http://{host}:{port}/apps", timeout=2)
        apps_payload = json.loads(apps_response.read().decode("utf-8"))
        policy_app_response = request.urlopen(
            f"http://{host}:{port}/apps/policy-assistant",
            timeout=2,
        )
        policy_app_payload = json.loads(policy_app_response.read().decode("utf-8"))
        policy_collections_response = request.urlopen(
            f"http://{host}:{port}/apps/policy-assistant/collections",
            timeout=2,
        )
        policy_collections_payload = json.loads(policy_collections_response.read().decode("utf-8"))
        policy_documents_response = request.urlopen(
            f"http://{host}:{port}/apps/policy-assistant/collections/policies/documents",
            timeout=2,
        )
        policy_documents_payload = json.loads(policy_documents_response.read().decode("utf-8"))
        upload_request = request.Request(
            f"http://{host}:{port}/apps/policy-assistant/collections/policies/documents",
            data=json.dumps(
                {
                    "filename": "approval-note.md",
                    "content": "Additional policy notes require management approval.",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        upload_response = request.urlopen(upload_request, timeout=2)
        upload_payload = json.loads(upload_response.read().decode("utf-8"))
        updated_policy_documents_response = request.urlopen(
            f"http://{host}:{port}/apps/policy-assistant/collections/policies/documents",
            timeout=2,
        )
        updated_policy_documents_payload = json.loads(
            updated_policy_documents_response.read().decode("utf-8")
        )
        app_ingestion_response = request.urlopen(
            f"http://{host}:{port}/apps/policy-assistant/ingestion/preview?collection=policies",
            timeout=2,
        )
        app_ingestion_payload = json.loads(app_ingestion_response.read().decode("utf-8"))
        app_retrieval_response = request.urlopen(
            f"http://{host}:{port}/apps/policy-assistant/retrieval/search?q=approval&collection=policies",
            timeout=2,
        )
        app_retrieval_payload = json.loads(app_retrieval_response.read().decode("utf-8"))
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
        evaluation_response = request.urlopen(
            f"http://{host}:{port}/evaluation/run",
            timeout=2,
        )
        evaluation_payload = json.loads(evaluation_response.read().decode("utf-8"))
        profile_response = request.urlopen(
            f"http://{host}:{port}/template/profile",
            timeout=2,
        )
        profile_payload = json.loads(profile_response.read().decode("utf-8"))

        chat_request = request.Request(
            f"http://{host}:{port}/chat",
            data=json.dumps({"message": "Hallo"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        chat_response = request.urlopen(chat_request, timeout=2)
        chat_payload = json.loads(chat_response.read().decode("utf-8"))
        policy_chat_request = request.Request(
            f"http://{host}:{port}/apps/policy-assistant/chat",
            data=json.dumps({"message": "What do policy documents explain?"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        policy_chat_response = request.urlopen(policy_chat_request, timeout=2)
        policy_chat_payload = json.loads(policy_chat_response.read().decode("utf-8"))

        assert health_payload["status"] == "ok"
        assert collections_payload == {
            "collections": [{"name": "policy-assistant", "document_count": 1}]
        }
        assert [application["id"] for application in apps_payload["applications"]] == [
            "default",
            "policy-assistant",
        ]
        assert policy_app_payload["name"] == "Policy Assistant"
        assert policy_app_payload["profile"]["default_collection"] == "policies"
        assert policy_collections_payload == {
            "collections": [{"name": "policies", "document_count": 1}]
        }
        assert policy_documents_payload["document_count"] == 1
        assert policy_documents_payload["documents"][0]["relative_path"] == "policies/rules.md"
        assert upload_response.status == 201
        assert upload_payload["relative_path"] == "policies/approval-note.md"
        assert updated_policy_documents_payload["document_count"] == 2
        assert sorted(
            document["relative_path"] for document in updated_policy_documents_payload["documents"]
        ) == ["policies/approval-note.md", "policies/rules.md"]
        assert app_ingestion_payload["chunk_count"] == 2
        assert app_retrieval_payload["provider"] == "hash"
        assert app_retrieval_payload["indexed_chunk_count"] == 2
        assert search_payload["provider"] == "hash"
        assert search_payload["indexed_chunk_count"] == 2
        assert retrieval_payload["provider"] == "hash"
        assert retrieval_payload["indexed_chunk_count"] == 2
        assert retrieval_payload["trace"] == [
            "loaded_chunks",
            "embedded_chunks",
            "searched_vector_store",
            "formatted_retrieval_results",
        ]
        assert evaluation_payload["total_cases"] >= 2
        assert evaluation_payload["provider"] == "hash"
        assert profile_payload["default_collection"] == "sample"
        assert "keine passende Quelle gefunden" in chat_payload["answer"]
        assert chat_payload["sources"] == []
        assert "Keine lokalen Treffer" in chat_payload["uncertainty"]
        assert chat_payload["trace"] == [
            "validated_message",
            "searched_knowledge_base",
            "skipped_source_read",
            "deterministic_answer_composed",
            "composed_answer",
        ]
        assert [tool_call["name"] for tool_call in chat_payload["tool_calls"]] == [
            "search_knowledge_base",
            "answer_with_citations",
        ]
        assert policy_chat_payload["sources"][0]["location"] == "policies/rules.md"
        assert "Policy documents" in policy_chat_payload["answer"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
