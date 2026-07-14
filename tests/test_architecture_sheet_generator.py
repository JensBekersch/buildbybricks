import json
from pathlib import Path
import threading
from urllib import request

from agentic_rag_template.app import create_server
from agentic_rag_template.applications import FileApplicationRegistry
from agentic_rag_template.config import Settings
from agentic_rag_template.software_factory import generate_architecture_sheet


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeArchitectureLLMProvider:
    name = "fake-architecture-llm"
    model = "fake-json-v1"

    def generate_json(self, system_prompt: str, user_prompt: str):
        assert "valides JSON" in system_prompt
        assert "Deterministisches Basissheet" in user_prompt
        return {
            "artifact_name": "LLM Angebotsplattform",
            "solution_strategy": "LLM-verfeinerte Django-Strategie mit klaren Fachmodulen.",
            "architecture_decisions": [
                {
                    "id": "ADR-LLM-001",
                    "decision": "Angebote werden als eigenes Django-Modul umgesetzt.",
                    "rationale": "Der Angebotsprozess hat eigene Regeln, Tests und Freigaben.",
                    "status": "proposed",
                }
            ],
        }


def test_generate_architecture_sheet_returns_schema_shaped_django_contract() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")

    result = generate_architecture_sheet(
        "Eine Django-App zur Verwaltung von Kunden, Angeboten, Freigabeprozessen und PDF-Exporten.",
        application,
    )
    payload = result.to_dict()
    sheet = payload["architecture_sheet"]

    assert payload["validation"] == {"valid": True, "missing_fields": []}
    assert payload["schema_id"].endswith("/architecture-sheet.schema.json")
    assert payload["sources"][0]["location"] == "architecture-method/arc42_architecture_sheet.md"
    assert sheet["schema_version"] == "1.0.0"
    assert sheet["artifact_type"] == "django-application"
    assert sheet["artifact_name"] == "Verwaltung Kunden"
    assert sheet["input_summary"].startswith("Eine Django-App")
    assert sheet["architecture_drivers"]
    assert sheet["architecture_decisions"]
    assert sheet["acceptance_criteria"]
    assert sheet["readiness"]["status"] == "ready-for-review"
    assert any(block["name"] == "Approval Workflow" for block in sheet["building_blocks"])
    assert any(block["name"] == "Document Export" for block in sheet["building_blocks"])
    assert any(scenario["name"] == "Freigabe durchfuehren" for scenario in sheet["runtime_scenarios"])
    assert any(scenario["name"] == "PDF exportieren" for scenario in sheet["runtime_scenarios"])
    assert "generated_django_architecture_sheet" in payload["trace"]
    assert payload["generation"]["mode"] == "deterministic"


def test_generate_architecture_sheet_can_merge_llm_json() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")

    result = generate_architecture_sheet(
        "Eine Django-App fuer Angebote und Freigaben.",
        application,
        llm_provider=FakeArchitectureLLMProvider(),
    )
    payload = result.to_dict()
    sheet = payload["architecture_sheet"]

    assert payload["validation"]["valid"] is True
    assert payload["generation"]["mode"] == "llm-assisted"
    assert payload["generation"]["llm_provider"] == "fake-architecture-llm"
    assert sheet["artifact_name"] == "LLM Angebotsplattform"
    assert sheet["schema_version"] == "1.0.0"
    assert sheet["architecture_decisions"][0]["id"] == "ADR-LLM-001"
    assert sheet["quality_goals"]
    assert "generated_llm_architecture_sheet" in payload["trace"]


def test_architecture_sheet_endpoint_returns_generated_sheet() -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
    )
    server = create_server(settings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        architecture_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/architecture-sheet",
            data=json.dumps(
                {
                    "description": (
                        "Eine Django-Anwendung fuer Kundenverwaltung mit Rollen, "
                        "API und Freigabeprozess."
                    )
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = request.urlopen(architecture_request, timeout=2)
        payload = json.loads(response.read().decode("utf-8"))

        assert response.status == 200
        assert payload["validation"]["valid"] is True
        assert payload["architecture_sheet"]["artifact_type"] == "django-application"
        assert payload["architecture_sheet"]["schema_version"] == "1.0.0"
        assert payload["architecture_sheet"]["context"]["interfaces"][-1]["type"] == "rest-api"
        assert payload["architecture_sheet"]["architecture_decisions"]
        assert payload["architecture_sheet"]["acceptance_criteria"]
        assert payload["architecture_sheet"]["open_questions"]
        assert payload["generation"]["llm_provider"] == "none"
        assert payload["trace"] == [
            "validated_description",
            "loaded_architecture_sheet_schema",
            "loaded_architecture_method_sources",
            "generated_django_architecture_sheet",
            "validated_architecture_sheet_contract",
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
