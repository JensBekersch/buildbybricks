import json
from pathlib import Path

from agentic_rag_template.config import Settings
from agentic_rag_template.ingestion import discover_collections, load_documents
from agentic_rag_template.applications import FileApplicationRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_software_factory_app_is_registered() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )

    application = FileApplicationRegistry(settings).get("software-factory")

    assert application.profile.name == "Software Factory"
    assert application.profile.default_collection == "architecture-method"
    assert application.data_dir == PROJECT_ROOT / "data" / "software-factory"


def test_software_factory_architecture_method_collection_is_loadable() -> None:
    data_dir = PROJECT_ROOT / "data" / "software-factory"

    collections = discover_collections(data_dir)
    documents = load_documents(data_dir, collection="architecture-method")

    assert collections == ["architecture-method"]
    assert [document.relative_path.as_posix() for document in documents] == [
        "architecture-method/arc42_architecture_sheet.md"
    ]
    assert "Architecture Sheet" in documents[0].content
    assert "Django" in documents[0].content


def test_software_factory_architecture_sheet_schema_has_required_contract() -> None:
    schema_path = PROJECT_ROOT / "apps" / "software-factory" / "architecture_sheet.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["title"] == "Software Factory Architecture Sheet"
    assert "additionalProperties" in schema
    assert schema["additionalProperties"] is False
    assert schema["properties"]["artifact_type"]["enum"] == [
        "django-application",
        "django-service",
        "django-app-module",
        "unknown",
    ]
    assert set(schema["required"]) >= {
        "artifact_name",
        "artifact_type",
        "business_goal",
        "quality_goals",
        "context",
        "building_blocks",
        "runtime_scenarios",
        "risks",
        "open_questions",
        "assumptions",
    }
