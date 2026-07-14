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


class GenericArchitectureLLMProvider:
    name = "generic-architecture-llm"
    model = "generic-json-v1"

    def generate_json(self, system_prompt: str, user_prompt: str):
        if "Requirement Analyst" in system_prompt:
            raise RuntimeError("pipeline unavailable")
        assert "Vermeide generische Platzhalter" in system_prompt
        return {
            "artifact_name": "Generische Fachanwendung",
            "building_blocks": [
                {
                    "name": "Core Domain",
                    "responsibility": "Generische Fachobjekte modellieren.",
                    "django_mapping": "Django app `core`.",
                }
            ],
            "runtime_scenarios": [
                {
                    "name": "Fachobjekt erfassen",
                    "steps": ["Nutzer erfasst ein Objekt."],
                }
            ],
            "context": {
                "users": [{"name": "Fachanwender", "description": "Nutzen die Anwendung."}],
                "external_systems": [],
                "interfaces": [
                    {
                        "name": "Application API",
                        "type": "rest-api",
                        "description": "API fuer Clients.",
                    }
                ],
            },
        }


class AgenticArchitectureLLMProvider:
    name = "agentic-architecture-llm"
    model = "agentic-json-v1"

    def __init__(self) -> None:
        self.calls = []

    def generate_json(self, system_prompt: str, user_prompt: str):
        self.calls.append(system_prompt.split("\n")[0])
        if "Requirement Analyst" in system_prompt:
            return {
                "artifact_name": "Arbeitszeit Cockpit",
                "business_goal": "Arbeitszeiten erfassen, pruefen, freigeben und als Monatsbericht auswerten.",
                "roles": [
                    {"name": "Mitarbeitende", "description": "Erfassen eigene Zeiteintraege."},
                    {"name": "Fuehrungskraefte", "description": "Pruefen und geben Teamzeiten frei."},
                    {"name": "Administratoren", "description": "Verwalten Stammdaten."},
                ],
                "core_entities": [
                    {"name": "Zeiteintrag", "description": "Datum, Start, Ende, Pause, Projekt und Taetigkeit."},
                    {"name": "Monatsabschluss", "description": "Gebundelte Monatsuebersicht mit Freigabestatus."},
                    {"name": "Arbeitszeitmodell", "description": "Sollzeiten, Feiertage und Pausenregeln."},
                ],
                "workflows": [
                    {"name": "Arbeitszeit loggen", "description": "Mitarbeitende erfassen und korrigieren offene Zeiten."},
                    {"name": "Monat freigeben", "description": "Fuehrungskraefte pruefen Monatsuebersichten."},
                    {"name": "CSV exportieren", "description": "Freigegebene Monatsberichte werden exportiert."},
                ],
                "current_interfaces": [
                    {"name": "Django Web UI", "type": "web-ui", "description": "Oberflaeche fuer Zeiterfassung und Freigabe."},
                    {"name": "Django Admin", "type": "admin-ui", "description": "Stammdatenpflege."},
                ],
                "future_interfaces": [
                    {"name": "Mobile REST API", "type": "rest-api", "description": "Spaetere mobile Nutzung."}
                ],
                "quality_goals": [
                    {"name": "Berechnungskorrektheit", "description": "Soll-Ist-Zeiten werden korrekt berechnet."}
                ],
                "constraints": [{"description": "Erste Version als serverseitige Django-Anwendung."}],
                "risks": [
                    {
                        "description": "Arbeitszeitregeln koennen komplex sein.",
                        "mitigation": "Regeln in Services kapseln und testen.",
                    }
                ],
                "assumptions": [{"description": "REST API ist nicht Teil des ersten Scopes."}],
                "open_questions": [{"description": "Welche Rundungsregeln gelten?"}],
            }
        if "Architecture Synthesizer" in system_prompt:
            assert "Requirement-Analyse" in user_prompt
            return {
                "artifact_name": "Arbeitszeit Cockpit",
                "business_goal": "Arbeitszeiten erfassen, pruefen, freigeben und auswerten.",
                "building_blocks": [
                    {
                        "name": "Zeiteintrag",
                        "responsibility": "Zeiteintraege erfassen und validieren.",
                        "django_mapping": "Django app `timesheets`.",
                    },
                    {
                        "name": "Monatsabschluss",
                        "responsibility": "Monatsuebersichten und Freigabestatus steuern.",
                        "django_mapping": "Django app `approvals`.",
                    },
                ],
                "runtime_scenarios": [
                    {
                        "name": "Arbeitszeit loggen",
                        "steps": ["Mitarbeitender erfasst Zeit.", "System validiert und speichert."],
                    }
                ],
                "context": {
                    "users": [{"name": "Mitarbeitende", "description": "Erfassen eigene Zeiten."}],
                    "external_systems": [
                        {
                            "name": "Zukuenftige Integrationen",
                            "description": "Mobile REST API ist spaeterer Scope.",
                        }
                    ],
                    "interfaces": [
                        {"name": "Django Web UI", "type": "web-ui", "description": "Aktueller Scope."}
                    ],
                },
                "data_view": "Zentrale Models sind Zeiteintrag, Monatsabschluss und Arbeitszeitmodell.",
                "test_strategy": "Service-Tests fuer Soll-Ist-Berechnung und Workflow-Tests fuer Freigabe.",
            }
        if "Architecture Reviewer" in system_prompt:
            return {"passes": True, "findings": [], "required_corrections": []}
        raise AssertionError(system_prompt)


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
        generation_mode="legacy_llm_enrichment",
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


def test_generate_architecture_sheet_uses_agentic_llm_pipeline() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")
    provider = AgenticArchitectureLLMProvider()

    result = generate_architecture_sheet(
        "Django-Webanwendung zur Erfassung und Auswertung von Arbeitszeiten mit spaeterer REST API.",
        application,
        llm_provider=provider,
        generation_mode="agentic_with_review",
    )
    payload = result.to_dict()
    sheet = payload["architecture_sheet"]
    block_names = {block["name"] for block in sheet["building_blocks"]}
    interface_types = {interface["type"] for interface in sheet["context"]["interfaces"]}

    assert payload["generation"]["mode"] == "agentic_with_review"
    assert payload["generation"]["architecture_review"]["passes"] is True
    assert payload["generation"]["requirement_analysis"]["artifact_name"] == "Arbeitszeit Cockpit"
    assert provider.calls == [
        "Du bist der Requirement Analyst einer agentischen Django-Softwarefabrik.",
        "Du bist der Architecture Synthesizer einer agentischen Django-Softwarefabrik.",
        "Du bist der Architecture Reviewer einer agentischen Django-Softwarefabrik.",
    ]
    assert sheet["artifact_name"] == "Arbeitszeit Cockpit"
    assert "Zeiteintrag" in block_names
    assert "Monatsabschluss" in block_names
    assert "rest-api" not in interface_types
    assert payload["trace"][-4:] == [
        "analyzed_requirements",
        "synthesized_architecture_sheet",
        "reviewed_architecture_sheet",
        "validated_architecture_sheet_contract",
    ]


def test_generate_architecture_sheet_can_skip_agentic_review() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")
    provider = AgenticArchitectureLLMProvider()

    result = generate_architecture_sheet(
        "Django-Webanwendung zur Erfassung und Auswertung von Arbeitszeiten.",
        application,
        llm_provider=provider,
        generation_mode="agentic",
    )
    payload = result.to_dict()

    assert payload["generation"]["mode"] == "agentic"
    assert payload["generation"]["pipeline"] == "requirement_analyst -> architecture_synthesizer"
    assert "architecture_review" not in payload["generation"]
    assert provider.calls == [
        "Du bist der Requirement Analyst einer agentischen Django-Softwarefabrik.",
        "Du bist der Architecture Synthesizer einer agentischen Django-Softwarefabrik.",
    ]
    assert "reviewed_architecture_sheet" not in payload["trace"]


def test_generate_architecture_sheet_focuses_on_work_time_domain() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")

    result = generate_architecture_sheet(
        (
            "Erstelle ein Architecture Sheet fuer eine Django-Webanwendung zur Erfassung "
            "und Auswertung von Arbeitszeiten. Mitarbeitende loggen Datum, Startzeit, "
            "Endzeit, Pause, Projekt, Taetigkeitsbeschreibung und Notizen. Fuehrungskraefte "
            "pruefen Monatsuebersichten und geben Eintraege frei oder zur Korrektur zurueck. "
            "Administratoren verwalten Nutzer, Teams, Projekte, Feiertage und Arbeitszeitmodelle. "
            "Monatsberichte sollen als CSV exportiert werden. Spaeter koennte eine REST API "
            "fuer mobile Apps ergaenzt werden."
        ),
        application,
    )
    payload = result.to_dict()
    sheet = payload["architecture_sheet"]
    block_names = {block["name"] for block in sheet["building_blocks"]}
    scenario_names = {scenario["name"] for scenario in sheet["runtime_scenarios"]}
    interface_types = {interface["type"] for interface in sheet["context"]["interfaces"]}

    assert payload["validation"]["valid"] is True
    assert sheet["artifact_name"] == "Arbeitszeiterfassung"
    assert "Time Entries" in block_names
    assert "Working Time Rules" in block_names
    assert "Month Closing and Approval" in block_names
    assert "Core Domain" not in block_names
    assert "Arbeitszeit erfassen" in scenario_names
    assert "Monat abschliessen" in scenario_names
    assert "Teamzeiten freigeben" in scenario_names
    assert "rest-api" not in interface_types
    assert "TimeEntry" in sheet["data_view"]
    assert "Soll-Ist" in sheet["test_strategy"]


def test_llm_generation_keeps_work_time_domain_focus() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")

    result = generate_architecture_sheet(
        (
            "Django-Webanwendung zur Erfassung von Arbeitszeiten mit Zeiteintraegen, "
            "Pausen, Projekten, Monatsabschluss und spaeterer REST API."
        ),
        application,
        llm_provider=GenericArchitectureLLMProvider(),
        generation_mode="legacy_llm_enrichment",
    )
    payload = result.to_dict()
    sheet = payload["architecture_sheet"]
    block_names = {block["name"] for block in sheet["building_blocks"]}
    interface_types = {interface["type"] for interface in sheet["context"]["interfaces"]}

    assert payload["generation"]["mode"] == "llm-assisted"
    assert sheet["artifact_name"] == "Arbeitszeiterfassung"
    assert "Time Entries" in block_names
    assert "Core Domain" not in block_names
    assert "rest-api" not in interface_types


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
