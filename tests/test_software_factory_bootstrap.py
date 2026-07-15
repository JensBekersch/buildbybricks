import json
from pathlib import Path

import yaml

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
        "architecture-method/arc42_sections.json",
        "architecture-method/description_to_sheet_mapping.md",
        "architecture-method/django_building_blocks.md",
        "architecture-method/quality_goals_catalog.md",
        "architecture-method/risks_and_review.md",
    ]
    all_content = "\n".join(document.content for document in documents)
    assert "Architecture Sheet" in all_content
    assert "crosscutting_concepts" in all_content
    assert "Django Building Blocks" in all_content
    assert "Qualitaetsziele" in all_content
    assert "Review-Regeln" in all_content


def test_software_factory_arc42_sections_reference_covers_all_chapters() -> None:
    reference_path = (
        PROJECT_ROOT
        / "data"
        / "software-factory"
        / "architecture-method"
        / "arc42_sections.json"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    sections = reference["sections"]

    assert reference["schema_version"] == "1.0.0"
    assert reference["language"] == "de"
    assert [section["id"] for section in sections] == [str(index) for index in range(1, 13)]
    assert [section["key"] for section in sections] == [
        "introduction_and_goals",
        "constraints",
        "context_and_scope",
        "solution_strategy",
        "building_block_view",
        "runtime_view",
        "deployment_view",
        "crosscutting_concepts",
        "architecture_decisions",
        "quality_requirements",
        "risks_and_technical_debt",
        "glossary",
    ]
    for section in sections:
        assert section["content"]
        assert section["motivation"]
        assert section["form"]
        assert section["must_include"]
        assert section["must_not_include"]
        assert section["review_checks"]
        assert section["django_guidance"]


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
        "arc42",
    }
    assert set(schema["$defs"]["arc42_document"]["required"]) == {
        "introduction_and_goals",
        "constraints",
        "context_and_scope",
        "solution_strategy",
        "building_block_view",
        "runtime_view",
        "deployment_view",
        "crosscutting_concepts",
        "architecture_decisions",
        "quality_requirements",
        "risks_and_technical_debt",
        "glossary",
    }


def test_software_factory_requirement_analyst_agent_config_is_loadable() -> None:
    config_path = (
        PROJECT_ROOT
        / "apps"
        / "software-factory"
        / "agents"
        / "requirement_analyst.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["id"] == "requirement_analyst"
    assert config["name"] == "Requirement Analyst"
    assert config["version"] == 2
    assert "domain_entities" in config["output_contract"]["required"]
    assert "test_requirements" in config["output_contract"]["required"]
    assert "quality_gate" in config
    assert "{{ user_description }}" in config["prompt"]["user_template"]
    assert "{% if method_sources %}" in config["prompt"]["user_template"]
    assert any(rule["id"] == "preserve_explicit_test_cases" for rule in config["review_rules"])


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
