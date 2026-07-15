import json
from pathlib import Path
import threading
from urllib import request

from agentic_rag_template.app import create_server
from agentic_rag_template.config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_workflow_admin_api_lists_details_and_validates_workflows() -> None:
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

        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/workflows",
            timeout=15,
        ) as response:
            listed = json.loads(response.read().decode("utf-8"))

        assert listed["app_id"] == "software-factory"
        assert listed["workflows"][0]["id"] == "architecture_sheet"
        assert listed["workflows"][0]["slug"] == "architecture-sheet"
        assert listed["workflows"][0]["step_count"] == 7
        assert listed["workflows"][0]["validation"]["valid"] is True

        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/workflows/architecture_sheet",
            timeout=15,
        ) as response:
            detail = json.loads(response.read().decode("utf-8"))

        assert detail["workflow_id"] == "architecture_sheet"
        assert detail["workflow"]["workflow"]["name"] == "Architecture Sheet"
        assert [step["step_key"] for step in detail["workflow"]["steps"]] == [
            "validate_description",
            "load_schema",
            "load_method_sources",
            "analyze_requirements",
            "synthesize_architecture",
            "review_architecture",
            "validate_contract",
        ]

        validate_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/architecture_sheet/validate",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(validate_request, timeout=15) as response:
            validation = json.loads(response.read().decode("utf-8"))

        assert validation["validation"] == {"valid": True, "errors": [], "warnings": []}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)


def test_workflow_admin_api_starts_test_run_and_exposes_run_details() -> None:
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
        create_run_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/architecture_sheet/test-runs",
            data=json.dumps(
                {
                    "description": "Eine einfache Team-Todo-Liste mit Aufgaben und Status.",
                    "responses": _workflow_fake_responses(),
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(create_run_request, timeout=15) as response:
            assert response.status == 201
            created = json.loads(response.read().decode("utf-8"))

        run = created["run"]
        run_id = run["id"]
        assert run["status"] == "succeeded"
        assert run["initial_input"]["description"] == "Eine einfache Team-Todo-Liste mit Aufgaben und Status."
        assert [artifact["artifact_key"] for artifact in run["artifacts"]] == [
            "validated_description",
            "architecture_schema",
            "method_sources",
            "requirements_analysis",
            "architecture_sheet",
            "architecture_review",
            "contract_validation",
        ]
        assert run["artifacts"][3]["content"]["artifact_name"] == "Team-Todo-Liste"
        assert run["artifacts"][4]["content"]["architecture_sheet"]["artifact_name"] == "Team-Todo-Liste"

        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/workflows/architecture_sheet/runs",
            timeout=15,
        ) as response:
            listed_runs = json.loads(response.read().decode("utf-8"))

        assert [item["id"] for item in listed_runs["runs"]] == [run_id]
        assert listed_runs["runs"][0]["status"] == "succeeded"
        assert listed_runs["runs"][0]["artifact_count"] == 7

        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/workflows/architecture_sheet/runs/{run_id}",
            timeout=15,
        ) as response:
            loaded = json.loads(response.read().decode("utf-8"))

        assert loaded["run"]["id"] == run_id
        assert loaded["run"]["step_runs"][3]["workflow_step"]["step_key"] == "analyze_requirements"
        assert loaded["run"]["step_runs"][4]["validation_result"]["valid"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)


def _workflow_fake_responses():
    return [
        {
            "parsed_output": {
                "schema_version": "2.0.0",
                "artifact_name": "Team-Todo-Liste",
                "business_goal": {
                    "description": "Teammitglieder verwalten eine gemeinsam sichtbare Aufgabenliste.",
                    "evidence": {"source": "input"},
                },
                "input_summary": "Eine einfache Team-Todo-Liste mit Aufgaben und Status.",
                "roles": [{"name": "Teammitglieder", "description": "Nutzen die gemeinsame Aufgabenliste."}],
                "domain_entities": [{"name": "Aufgabe", "description": "Aufgabenbeschreibung und Status."}],
                "enumerations": [{"name": "Aufgabenstatus", "values": ["offen", "in Bearbeitung", "fertig"]}],
                "functional_requirements": [
                    {"description": "Aufgabe erfassen."},
                    {"description": "Aufgabenliste anzeigen."},
                    {"description": "Status aendern."},
                ],
                "crud_requirements": [],
                "validation_rules": [],
                "security_rules": [],
                "ui_requirements": [],
                "technical_constraints": [],
                "delivery_requirements": [],
                "test_requirements": [],
                "quality_requirements": [],
                "in_scope": ["Aufgabe", "Aufgabe erfassen", "Status aendern", "Aufgabenliste anzeigen"],
                "explicitly_excluded": [],
                "not_requested": [],
                "not_evidenced": [],
                "future_ideas": [],
                "core_facts": ["Aufgabe", "Aufgabe erfassen", "Status aendern"],
                "risks": [],
                "assumptions": [],
                "open_questions": [],
                "readiness": "ready",
            }
        },
        {
            "parsed_output": {
                "architecture_sheet": {
                    "artifact_name": "Team-Todo-Liste",
                    "business_goal": "Teammitglieder verwalten eine gemeinsam sichtbare Aufgabenliste.",
                    "requirement_version": "2.0.0",
                    "building_blocks": [
                        {
                            "name": "Aufgabe",
                            "responsibility": "Speichert Beschreibung und Status.",
                        }
                    ],
                    "runtime_scenarios": [
                        {
                            "name": "Aufgabe erfassen",
                            "steps": ["Beschreibung eingeben.", "Aufgabe speichern."],
                        }
                    ],
                    "arc42": {
                        "building_block_view": "Der Baustein Aufgabe kapselt Beschreibung und Status.",
                        "runtime_view": "Im Szenario Aufgabe erfassen wird eine Beschreibung gespeichert.",
                    },
                }
            }
        },
        {
            "parsed_output": {
                "passes": True,
                "findings": [],
                "required_corrections": [],
            }
        },
    ]
