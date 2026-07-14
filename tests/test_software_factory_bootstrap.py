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
    document_paths = [document.relative_path.as_posix() for document in documents]

    assert collections == ["architecture-method"]
    assert document_paths == [
        "architecture-method/arc42_architecture_sheet.md",
        "architecture-method/description_to_sheet_mapping.md",
        "architecture-method/django_building_blocks.md",
        "architecture-method/quality_goals_catalog.md",
        "architecture-method/risks_and_review.md",
    ]
    all_content = "\n".join(document.content for document in documents)
    assert "Architecture Sheet" in all_content
    assert "Django Building Blocks" in all_content
    assert "Qualitaetsziele" in all_content
    assert "Review-Regeln" in all_content


def test_software_factory_architecture_sheet_schema_has_required_contract() -> None:
    schema_path = PROJECT_ROOT / "apps" / "software-factory" / "architecture_sheet.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["title"] == "Software Factory Architecture Sheet"
    assert schema["properties"]["schema_version"]["const"] == "1.0.0"
    assert "additionalProperties" in schema
    assert schema["additionalProperties"] is False
    assert schema["properties"]["artifact_type"]["enum"] == [
        "django-application",
        "django-service",
        "django-app-module",
        "unknown",
    ]
    assert set(schema["required"]) >= {
        "schema_version",
        "artifact_name",
        "artifact_type",
        "input_summary",
        "business_goal",
        "architecture_drivers",
        "quality_goals",
        "context",
        "architecture_decisions",
        "building_blocks",
        "runtime_scenarios",
        "acceptance_criteria",
        "risks",
        "open_questions",
        "assumptions",
        "readiness",
    }


def test_software_factory_examples_document_good_and_bad_outputs() -> None:
    examples_dir = PROJECT_ROOT / "apps" / "software-factory" / "examples"
    good_example = json.loads(
        (examples_dir / "good_architecture_sheet.json").read_text(encoding="utf-8")
    )
    bad_example = (examples_dir / "bad_architecture_sheet.md").read_text(encoding="utf-8")

    assert good_example["schema_version"] == "1.0.0"
    assert good_example["architecture_decisions"]
    assert good_example["acceptance_criteria"]
    assert good_example["readiness"]["status"] == "ready-for-review"
    assert "kein maschinenlesbares JSON" in bad_example
