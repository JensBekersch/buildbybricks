import json
from pathlib import Path
import threading
from urllib import error, request

from agentic_rag_template.app import create_server
from agentic_rag_template.config import Settings
from agentic_rag_template.workflows.models import WorkflowRun


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeWorkflowStore:
    def __init__(self) -> None:
        self.runs = {}

    def initialize(self):
        pass

    def save_run(self, workflow_run: WorkflowRun) -> None:
        self.runs[workflow_run.id] = WorkflowRun.from_dict(workflow_run.to_dict())

    def get_run(self, run_id: str):
        run = self.runs.get(run_id)
        return WorkflowRun.from_dict(run.to_dict()) if run else None

    def list_runs(self, workflow_slug=None, limit=50):
        runs = list(self.runs.values())
        if workflow_slug:
            runs = [run for run in runs if run.workflow_version.workflow.slug == workflow_slug]
        return [WorkflowRun.from_dict(run.to_dict()) for run in runs[:limit]]

    def claim_next_run(self, workflow_slug=None):
        for run in self.list_runs(workflow_slug=workflow_slug):
            if run.status == "pending":
                run.start()
                self.save_run(run)
                return run
        return None


def test_workflow_admin_api_lists_details_and_validates_workflows() -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
    )
    server = create_server(settings, workflow_store=FakeWorkflowStore())
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
    workflow_store = FakeWorkflowStore()
    server = create_server(settings, workflow_store=workflow_store)
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
        assert workflow_store.get_run(run_id) is not None
        assert workflow_store.get_run(run_id).status == "succeeded"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)


def test_workflow_admin_api_queues_generic_workflow_run_for_worker() -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
    )
    workflow_store = FakeWorkflowStore()
    server = create_server(settings, workflow_store=workflow_store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        create_run_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/architecture_sheet/runs",
            data=json.dumps({"description": "Eine einfache Team-Todo-Liste."}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(create_run_request, timeout=15) as response:
            assert response.status == 202
            created = json.loads(response.read().decode("utf-8"))

        run_id = created["run"]["id"]
        assert created["run"]["status"] == "pending"
        assert workflow_store.get_run(run_id).initial_input == {
            "description": "Eine einfache Team-Todo-Liste."
        }

        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/workflows/architecture_sheet/runs",
            timeout=15,
        ) as response:
            listed_runs = json.loads(response.read().decode("utf-8"))

        assert [item["id"] for item in listed_runs["runs"]] == [run_id]
        assert listed_runs["runs"][0]["status"] == "pending"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)


def test_workflow_admin_api_creates_updates_and_deletes_draft_workflows(tmp_path) -> None:
    settings = _isolated_settings(tmp_path)
    server = create_server(settings, workflow_store=FakeWorkflowStore())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        create_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows",
            data=json.dumps(
                {
                    "id": "demo_workflow",
                    "name": "Demo Workflow",
                    "slug": "demo-workflow",
                    "description": "Ein editierbarer Draft Workflow.",
                    "final_output_key": "demo_output",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(create_request, timeout=15) as response:
            assert response.status == 201
            created = json.loads(response.read().decode("utf-8"))

        assert created["workflow_id"] == "demo_workflow"
        assert created["workflow"]["status"] == "draft"
        assert created["workflow"]["workflow"]["name"] == "Demo Workflow"
        assert (tmp_path / "apps" / "software-factory" / "workflows" / "demo_workflow.yaml").is_file()

        update_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/demo_workflow",
            data=json.dumps(
                {
                    "name": "Demo Workflow aktualisiert",
                    "description": "Draft wurde angepasst.",
                    "final_output_key": "updated_output",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with request.urlopen(update_request, timeout=15) as response:
            assert response.status == 200
            updated = json.loads(response.read().decode("utf-8"))

        assert updated["workflow"]["workflow"]["name"] == "Demo Workflow aktualisiert"
        assert updated["workflow"]["final_output_key"] == "updated_output"

        delete_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/demo_workflow",
            method="DELETE",
        )
        with request.urlopen(delete_request, timeout=15) as response:
            assert response.status == 200
            deleted = json.loads(response.read().decode("utf-8"))

        assert deleted["deleted"] is True
        assert not (tmp_path / "apps" / "software-factory" / "workflows" / "demo_workflow.yaml").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)


def test_workflow_admin_api_rejects_published_workflow_mutation(tmp_path) -> None:
    settings = _isolated_settings(tmp_path, published_workflow=True)
    server = create_server(settings, workflow_store=FakeWorkflowStore())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        update_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/published_workflow",
            data=json.dumps({"name": "Soll nicht geaendert werden"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )

        try:
            request.urlopen(update_request, timeout=15)
        except error.HTTPError as http_error:
            assert http_error.code == 409
        else:
            raise AssertionError("Published workflow update must fail")

        delete_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/published_workflow",
            method="DELETE",
        )
        try:
            request.urlopen(delete_request, timeout=15)
        except error.HTTPError as http_error:
            assert http_error.code == 409
        else:
            raise AssertionError("Published workflow delete must fail")

        add_step_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/published_workflow/steps",
            data=json.dumps({"template_id": "input_guard"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            request.urlopen(add_step_request, timeout=15)
        except error.HTTPError as http_error:
            assert http_error.code == 409
        else:
            raise AssertionError("Published workflow step mutation must fail")

        update_step_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/published_workflow/steps/any_step",
            data=json.dumps({"name": "Soll nicht geaendert werden"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        try:
            request.urlopen(update_step_request, timeout=15)
        except error.HTTPError as http_error:
            assert http_error.code == 409
        else:
            raise AssertionError("Published workflow step update must fail")

        delete_step_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/published_workflow/steps/any_step",
            method="DELETE",
        )
        try:
            request.urlopen(delete_step_request, timeout=15)
        except error.HTTPError as http_error:
            assert http_error.code == 409
        else:
            raise AssertionError("Published workflow step delete must fail")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)


def test_workflow_admin_api_lists_templates_and_adds_step_to_draft(tmp_path) -> None:
    settings = _isolated_settings(tmp_path)
    server = create_server(settings, workflow_store=FakeWorkflowStore())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/step-templates",
            timeout=15,
        ) as response:
            templates = json.loads(response.read().decode("utf-8"))

        assert [template["id"] for template in templates["templates"]] == ["input_guard"]

        create_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows",
            data=json.dumps(
                {
                    "id": "step_demo",
                    "name": "Step Demo",
                    "slug": "step-demo",
                    "description": "Draft fuer Step Tests.",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(create_request, timeout=15) as response:
            assert response.status == 201

        add_step_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/step_demo/steps",
            data=json.dumps(
                {
                    "template_id": "input_guard",
                    "step_key": "validate_description",
                    "name": "Beschreibung pruefen",
                    "output_key": "validated_description",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(add_step_request, timeout=15) as response:
            assert response.status == 201
            updated = json.loads(response.read().decode("utf-8"))

        assert updated["workflow"]["steps"][0]["step_key"] == "validate_description"
        assert updated["workflow"]["steps"][0]["step_type"] == "TASK"
        assert updated["workflow"]["steps"][0]["output_key"] == "validated_description"
        assert updated["workflow"]["steps"][0]["task_definition"] == {"task_type": "echo"}

        add_referencing_step_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/step_demo/steps",
            data=json.dumps(
                {
                    "template_id": "input_guard",
                    "step_key": "consume_description",
                    "name": "Beschreibung nutzen",
                    "output_key": "consumed_description",
                    "input_mapping": {
                        "description": {
                            "source": "step_output",
                            "step_key": "validate_description",
                            "path": "validated_output.description",
                        }
                    },
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(add_referencing_step_request, timeout=15) as response:
            assert response.status == 201

        update_step_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/step_demo/steps/consume_description",
            data=json.dumps(
                {
                    "step_key": "consume_description",
                    "name": "Beschreibung verarbeiten",
                    "step_type": "TASK",
                    "output_key": "processed_description",
                    "timeout_seconds": 600,
                    "failure_strategy": "STOP_WORKFLOW",
                    "task": {"task_type": "echo"},
                    "input_mapping": {
                        "description": {
                            "source": "step_output",
                            "step_key": "validate_description",
                            "path": "validated_output.description",
                        }
                    },
                    "configuration": {"required_inputs": ["description"]},
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with request.urlopen(update_step_request, timeout=15) as response:
            assert response.status == 200
            edited = json.loads(response.read().decode("utf-8"))

        edited_step = edited["workflow"]["steps"][1]
        assert edited_step["step_key"] == "consume_description"
        assert edited_step["name"] == "Beschreibung verarbeiten"
        assert edited_step["output_key"] == "processed_description"
        assert edited_step["timeout_seconds"] == 600
        assert edited_step["configuration"] == {"required_inputs": ["description"]}

        blocked_rename_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/step_demo/steps/validate_description",
            data=json.dumps({"step_key": "validate_input"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        try:
            request.urlopen(blocked_rename_request, timeout=15)
        except error.HTTPError as http_error:
            assert http_error.code == 409
            payload = json.loads(http_error.read().decode("utf-8"))
            assert payload["error"] == "Workflow step key is still referenced by: consume_description"
        else:
            raise AssertionError("Referenced workflow step rename must fail")

        blocked_delete_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/step_demo/steps/validate_description",
            method="DELETE",
        )
        try:
            request.urlopen(blocked_delete_request, timeout=15)
        except error.HTTPError as http_error:
            assert http_error.code == 409
            payload = json.loads(http_error.read().decode("utf-8"))
            assert payload["error"] == "Workflow step is still referenced by: consume_description"
        else:
            raise AssertionError("Referenced workflow step delete must fail")

        delete_step_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/workflows/step_demo/steps/consume_description",
            method="DELETE",
        )
        with request.urlopen(delete_step_request, timeout=15) as response:
            assert response.status == 200
            deleted = json.loads(response.read().decode("utf-8"))

        assert deleted["deleted"] is True
        assert deleted["step_key"] == "consume_description"
        assert [step["step_key"] for step in deleted["workflow"]["steps"]] == ["validate_description"]
        assert deleted["workflow"]["steps"][0]["position"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)


def _isolated_settings(tmp_path, published_workflow=False):
    apps_dir = tmp_path / "apps"
    app_dir = apps_dir / "software-factory"
    workflow_dir = app_dir / "workflows"
    step_template_dir = app_dir / "step_templates"
    workflow_dir.mkdir(parents=True)
    step_template_dir.mkdir(parents=True)
    (tmp_path / "frontend").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "template").mkdir()
    (app_dir / "app_profile.json").write_text(
        json.dumps(
            {
                "name": "Software Factory",
                "description": "Workflow Factory Tests",
                "default_collection": "software-factory",
                "default_top_k": 3,
                "answer_policy": "Only local sources.",
            }
        ),
        encoding="utf-8",
    )

    if published_workflow:
        (workflow_dir / "published_workflow.yaml").write_text(
            "\n".join(
                [
                    "name: Published Workflow",
                    "slug: published-workflow",
                    "description: Immutable workflow.",
                    "workflow_status: active",
                    "status: published",
                    "version: 1",
                    "final_output_key: result",
                    "steps: []",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    (step_template_dir / "input_guard.yaml").write_text(
        "\n".join(
            [
                "id: input_guard",
                "name: Input Guard",
                "category: TASK",
                "description: Prueft Eingaben.",
                "step_type: TASK",
                "defaults:",
                "  name: Eingabe pruefen",
                "  step_key_prefix: input_guard",
                "  output_key: validated_input",
                "  task:",
                "    task_type: echo",
                "  input_mapping:",
                "    description:",
                "      source: workflow_input",
                "      path: description",
                "  configuration:",
                "    required_inputs:",
                "      - description",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return Settings(
        frontend_dir=tmp_path / "frontend",
        apps_dir=apps_dir,
        data_dir=tmp_path / "data",
        template_dir=tmp_path / "template",
        host="127.0.0.1",
        port=0,
    )


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
