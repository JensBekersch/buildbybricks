import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib import request

from agentic_rag_template.app import create_server
from agentic_rag_template.applications import FileApplicationRegistry
from agentic_rag_template.config import Settings
from agentic_rag_template.software_factory import (
    ArchitectureGenerationJob,
    EVENT_LOG,
    EVENT_STEP_COMPLETED,
    EVENT_STEP_FAILED,
    EVENT_STEP_SKIPPED,
    EVENT_STEP_STARTED,
    ArchitectureSheetGenerationError,
    FileArchitectureArtifactStore,
    apply_architecture_generation_event,
    generate_architecture_sheet,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


class TodoArchitectureLLMProvider:
    name = "todo-architecture-llm"
    model = "todo-json-v1"

    def generate_json(self, system_prompt: str, user_prompt: str):
        if "Requirement Analyst" in system_prompt:
            return {
                "artifact_name": "Team-Todo-Liste",
                "business_goal": "Teammitglieder verwalten eine gemeinsam sichtbare Liste einfacher Aufgaben.",
                "roles": [{"name": "Teammitglieder", "description": "Sehen und bearbeiten die gemeinsame Aufgabenliste."}],
                "core_entities": [
                    {"name": "Aufgabe", "description": "Ein Satz Beschreibung plus Status."},
                    {"name": "Aufgabenstatus", "description": "offen, in Bearbeitung oder fertig."},
                ],
                "workflows": [
                    {"name": "Aufgabe erfassen", "description": "Ein Teammitglied gibt eine Aufgabenbeschreibung in einem Satz ein."},
                    {"name": "Aufgabenliste anzeigen", "description": "Alle Teammitglieder sehen die gespeicherten Aufgaben."},
                    {"name": "Status aendern", "description": "Ein Teammitglied setzt offen, in Bearbeitung oder fertig."},
                ],
                "current_interfaces": [
                    {"name": "Gemeinsame Aufgabenliste", "type": "web-ui", "description": "Oeffentliche Teamansicht ohne Login."}
                ],
                "future_interfaces": [],
                "quality_goals": [
                    {
                        "name": "Testabdeckung",
                        "description": "Unit- und Medium-Tests erreichen mindestens 98 Prozent Coverage.",
                    }
                ],
                "constraints": [{"description": "Kein Login-Bereich."}],
                "explicitly_not_needed": [{"description": "Login und Authentifizierung sind nicht erforderlich."}],
                "risks": [
                    {
                        "description": "Statuswerte koennen inkonsistent gespeichert werden.",
                        "mitigation": "Status als feste Enumeration modellieren und testen.",
                    }
                ],
                "assumptions": [{"description": "Die Liste ist fuer das Team innerhalb der Laufzeitumgebung sichtbar."}],
                "open_questions": [{"description": "Muessen Aufgaben geloescht oder nur erledigt markiert werden?"}],
            }
        if "Architecture Synthesizer" in system_prompt:
            return {
                "artifact_name": "Team-Todo-Liste",
                "business_goal": "Eine einfache gemeinsame Aufgabenliste fuer Teammitglieder.",
                "stakeholders": [{"name": "Teammitglieder", "description": "Nutzen die Aufgabenliste gemeinsam."}],
                "context": {
                    "users": [{"name": "Teammitglieder", "description": "Greifen ohne Login auf die Liste zu."}],
                    "external_systems": [],
                    "interfaces": [
                        {"name": "Gemeinsame Aufgabenliste", "type": "web-ui", "description": "Web UI ohne Login."}
                    ],
                },
                "building_blocks": [
                    {
                        "name": "Aufgabenliste",
                        "responsibility": "Aufgaben speichern und fuer alle Teammitglieder anzeigen.",
                        "django_mapping": "Django app `tasks` with Task model, list/create/update views.",
                    },
                    {
                        "name": "Statusverwaltung",
                        "responsibility": "Statuswerte offen, in Bearbeitung und fertig validieren.",
                        "django_mapping": "Task.status as TextChoices enum with unit tests.",
                    },
                ],
                "runtime_scenarios": [
                    {
                        "name": "Aufgabe erstellen",
                        "steps": ["Beschreibung eingeben.", "System speichert Aufgabe mit Status offen."],
                    },
                    {
                        "name": "Status aendern",
                        "steps": ["Aufgabe auswaehlen.", "Status auf offen, in Bearbeitung oder fertig setzen."],
                    },
                ],
                "security_view": "Kein Login-Bereich. Eingaben werden validiert; es gibt keine Accounts-App.",
                "test_strategy": "Unit- und Medium-Tests mit mindestens 98 Prozent Coverage.",
            }
        if "Architecture Reviewer" in system_prompt:
            return {"passes": True, "findings": [], "required_corrections": []}
        raise AssertionError(system_prompt)


class HallucinatingScopeLLMProvider(TodoArchitectureLLMProvider):
    name = "hallucinating-scope-llm"
    model = "hallucinating-json-v1"

    def generate_json(self, system_prompt: str, user_prompt: str):
        if "Architecture Synthesizer" in system_prompt:
            return {
                "artifact_name": "Team-Todo-Liste",
                "business_goal": "Eine einfache gemeinsame Aufgabenliste fuer Teammitglieder.",
                "building_blocks": [
                    {
                        "name": "Projektmanagement-Integration",
                        "responsibility": "Synchronisiert Aufgaben in Cloud-Projektmanagement-Tools.",
                        "django_mapping": "Nicht belegt.",
                    }
                ],
                "runtime_scenarios": [
                    {
                        "name": "Ersteller zuweisen",
                        "steps": ["Ersteller und Zustaendiger werden gespeichert."],
                    }
                ],
                "architecture_decisions": [
                    {
                        "id": "ADR-999",
                        "decision": "Cloud-Synchronisation einbauen.",
                        "rationale": "Nicht belegt.",
                        "status": "proposed",
                    }
                ],
            }
        return super().generate_json(system_prompt, user_prompt)


class FailingRequirementsLLMProvider:
    name = "failing-requirements-llm"
    model = "failing-json-v1"

    def generate_json(self, system_prompt: str, user_prompt: str):
        if "Requirement Analyst" in system_prompt:
            raise RuntimeError("requirements failed")
        raise AssertionError(system_prompt)


class CorrectableReviewLLMProvider:
    name = "correctable-review-llm"
    model = "correctable-json-v1"

    def __init__(self) -> None:
        self.review_calls = 0
        self.correction_calls = 0

    def generate_json(self, system_prompt: str, user_prompt: str):
        if "Requirement Analyst" in system_prompt:
            return {
                "artifact_name": "Team-Todo-Liste",
                "business_goal": "Teammitglieder verwalten gemeinsam einfache Aufgaben mit Status.",
                "roles": [{"name": "Teammitglieder", "description": "Sehen und bearbeiten die gemeinsame Liste."}],
                "core_entities": [{"name": "Aufgabe", "description": "Aufgabenbeschreibung und Bearbeitungsstatus."}],
                "workflows": [{"name": "Aufgabe pflegen", "description": "Aufgabe erfassen, anzeigen und Status setzen."}],
                "current_interfaces": [{"name": "Aufgabenliste", "type": "web-ui", "description": "Gemeinsame Weboberflaeche."}],
                "quality_goals": [{"name": "Testabdeckung", "description": "Mindestens 98 Prozent Coverage."}],
                "constraints": [{"description": "Kein Login-Bereich."}],
                "risks": [{"description": "Statuswerte koennen falsch gesetzt werden.", "mitigation": "Enum validieren."}],
                "assumptions": [],
                "open_questions": [],
            }
        if "Architecture Synthesizer" in system_prompt:
            return {
                "artifact_name": "Team Todo List Architecture Sheet",
                "business_goal": "Enable teams to manage shared task lists.",
                "quality_goals": [{"goal": "Test Coverage", "target": "98%", "priority": "High"}],
            }
        if "Architecture Reviewer" in system_prompt:
            self.review_calls += 1
            if self.review_calls == 1:
                return {
                    "passes": False,
                    "findings": ["Das Sheet enthaelt englische fachliche Inhalte."],
                    "required_corrections": ["Alle fachlichen Texte auf Deutsch umformulieren."],
                }
            return {"passes": True, "findings": [], "required_corrections": []}
        if "Architecture Corrector" in system_prompt:
            self.correction_calls += 1
            assert "Alle fachlichen Texte auf Deutsch umformulieren." in user_prompt
            return {
                "artifact_name": "Team-Todo-Liste",
                "business_goal": "Teammitglieder koennen eine gemeinsame Aufgabenliste pflegen und den Status jeder Aufgabe nachvollziehen.",
                "quality_goals": [
                    {
                        "name": "Testabdeckung",
                        "scenario": "Unit- und Medium-Tests erreichen mindestens 98 Prozent Coverage.",
                        "priority": "high",
                    }
                ],
            }
        raise AssertionError(system_prompt)


class MalformedArchitectureLLMProvider:
    name = "malformed-architecture-llm"
    model = "malformed-json-v1"

    def generate_json(self, system_prompt: str, user_prompt: str):
        if "Requirement Analyst" in system_prompt:
            return {
                "artifact_name": "Team-Todo-Liste",
                "business_goal": "Teammitglieder verwalten gemeinsam einfache Aufgaben.",
                "roles": ["Teammitglieder"],
                "core_entities": ["Aufgabe"],
                "workflows": ["Aufgabe erfassen"],
                "current_interfaces": ["Aufgabenliste"],
                "quality_goals": ["Testabdeckung"],
                "constraints": ["Kein Login"],
                "risks": [{"risk": "Unzureichende Testabdeckung", "mitigation": "Coverage pruefen."}],
            }
        if "Architecture Synthesizer" in system_prompt:
            return {
                "artifact_type": "Architecture Decision Record",
                "architecture_drivers": [{"driver": "Testbarkeit", "impact": "98 Prozent Coverage."}],
                "quality_goals": [{"goal": "Testabdeckung", "target": "98 Prozent", "priority": "High"}],
                "risks": [{"risk": "Statusfehler", "mitigation": "Status als Enum modellieren."}],
                "acceptance_criteria": [{"criterion": "Status offen ist verfuegbar", "testable": True}],
                "readiness": "ready-for-review",
            }
        if "Architecture Reviewer" in system_prompt:
            return {"passes": True, "findings": [], "required_corrections": []}
        raise AssertionError(system_prompt)


class FakeArchitectureJobStore:
    def __init__(self) -> None:
        self.jobs = {}

    def save(self, job: ArchitectureGenerationJob) -> None:
        self.jobs[job.id] = job

    def get(self, job_id: str):
        return self.jobs.get(job_id)

    def list(self, limit=50):
        return list(self.jobs.values())


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
    assert payload["generation"]["requirement_analysis"]["in_scope"]
    assert payload["generation"]["requirement_analysis"]["not_evidenced"]
    assert provider.calls == [
        "Du bist der Requirement Analyst einer agentischen Django-Softwarefabrik.",
        "Du bist der Architecture Synthesizer einer agentischen Django-Softwarefabrik.",
        "Du bist der Architecture Reviewer einer agentischen Django-Softwarefabrik.",
    ]
    assert sheet["artifact_name"] == "Arbeitszeit Cockpit"
    assert "Zeiteintrag" in block_names
    assert "Monatsabschluss" in block_names
    assert "rest-api" not in interface_types
    assert set(sheet["arc42"]) == {
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
    assert sheet["arc42"]["runtime_view"]["scenarios"]
    assert sheet["arc42"]["crosscutting_concepts"]["concepts"]
    assert sheet["arc42"]["quality_requirements"]["quality_scenarios"]
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


def test_generate_architecture_sheet_emits_real_pipeline_events() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")
    events = []

    result = generate_architecture_sheet(
        "Django-Webanwendung zur Erfassung und Auswertung von Arbeitszeiten.",
        application,
        llm_provider=AgenticArchitectureLLMProvider(),
        generation_mode="agentic",
        event_handler=events.append,
    )

    assert result.validation["valid"] is True
    assert [(event.type, event.step) for event in events] == [
        (EVENT_STEP_STARTED, "validate_description"),
        (EVENT_STEP_COMPLETED, "validate_description"),
        (EVENT_STEP_STARTED, "load_schema"),
        (EVENT_STEP_COMPLETED, "load_schema"),
        (EVENT_STEP_STARTED, "load_method_sources"),
        (EVENT_STEP_COMPLETED, "load_method_sources"),
        (EVENT_STEP_STARTED, "analyze_requirements"),
        (EVENT_LOG, "analyze_requirements"),
        (EVENT_STEP_COMPLETED, "analyze_requirements"),
        (EVENT_STEP_STARTED, "synthesize_architecture"),
        (EVENT_LOG, "synthesize_architecture"),
        (EVENT_STEP_COMPLETED, "synthesize_architecture"),
        (EVENT_STEP_SKIPPED, "review_architecture"),
        (EVENT_STEP_STARTED, "validate_contract"),
        (EVENT_STEP_COMPLETED, "validate_contract"),
    ]
    llm_events = [event for event in events if event.type == EVENT_LOG]
    assert [event.metadata["llm_step"] for event in llm_events] == [
        "requirement_analyst",
        "architecture_synthesizer",
    ]
    assert all(event.metadata["duration_seconds"] >= 0 for event in llm_events)


def test_architecture_generation_events_update_job_state() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")
    job = ArchitectureGenerationJob.create(
        "Django-Webanwendung zur Erfassung und Auswertung von Arbeitszeiten.",
        generation_mode="agentic",
        job_id="event-job",
    )

    result = generate_architecture_sheet(
        job.description,
        application,
        llm_provider=AgenticArchitectureLLMProvider(),
        generation_mode=job.generation_mode,
        event_handler=lambda event: apply_architecture_generation_event(job, event),
    )
    job.complete(result.to_dict())
    payload = job.to_dict()
    steps = {step["key"]: step for step in payload["steps"]}

    assert payload["status"] == "completed"
    assert steps["validate_description"]["status"] == "completed"
    assert steps["analyze_requirements"]["status"] == "completed"
    assert steps["synthesize_architecture"]["status"] == "completed"
    assert steps["review_architecture"]["status"] == "skipped"
    assert steps["validate_contract"]["status"] == "completed"
    assert payload["result"]["architecture_sheet"]["artifact_name"] == "Arbeitszeit Cockpit"


def test_generate_architecture_sheet_requires_structured_llm_provider() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")

    try:
        generate_architecture_sheet("Eine einfache Todo Liste.", application)
    except ArchitectureSheetGenerationError as error:
        assert "requires a structured LLM provider" in str(error)
    else:
        raise AssertionError("Architecture sheet generation must not fall back to a generic sheet.")


def test_generate_architecture_sheet_emits_failed_event_without_structured_llm() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")
    events = []

    try:
        generate_architecture_sheet(
            "Eine einfache Todo Liste.",
            application,
            event_handler=events.append,
        )
    except ArchitectureSheetGenerationError:
        pass
    else:
        raise AssertionError("Architecture sheet generation must fail without a structured LLM provider.")

    assert (EVENT_STEP_FAILED, "analyze_requirements") in [
        (event.type, event.step) for event in events
    ]


def test_generate_architecture_sheet_attaches_exception_to_current_step() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")
    events = []

    try:
        generate_architecture_sheet(
            "Eine einfache Todo Liste.",
            application,
            llm_provider=FailingRequirementsLLMProvider(),
            event_handler=events.append,
        )
    except ArchitectureSheetGenerationError:
        pass
    else:
        raise AssertionError("Architecture sheet generation must fail when the analyst fails.")

    failed_events = [
        event for event in events if event.type == EVENT_STEP_FAILED
    ]
    assert [(event.step, event.message) for event in failed_events] == [
        ("analyze_requirements", "Agentic architecture pipeline failed: requirements failed")
    ]


def test_generate_architecture_sheet_preserves_explicit_no_login_requirement() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")

    result = generate_architecture_sheet(
        "Einfache Todo Liste fuer Teammitglieder ohne Login.",
        application,
        llm_provider=TodoArchitectureLLMProvider(),
        generation_mode="agentic_with_review",
    )
    payload = result.to_dict()
    sheet = payload["architecture_sheet"]
    block_names = {block["name"] for block in sheet["building_blocks"]}
    all_text = json.dumps(sheet, ensure_ascii=False).lower()

    assert payload["validation"]["valid"] is True
    assert sheet["artifact_name"] == "Team-Todo-Liste"
    assert "Aufgabenliste" in block_names
    assert "Statusverwaltung" in block_names
    assert "Accounts and Permissions" not in block_names
    assert "core domain" not in all_text
    assert "kein login" in all_text
    assert "accounts-app" in all_text
    assert "98 Prozent Coverage".lower() in all_text
    architecture_payload = json.dumps(
        {
            "drivers": sheet["architecture_drivers"],
            "quality_goals": sheet["quality_goals"],
            "decisions": sheet["architecture_decisions"],
            "blocks": sheet["building_blocks"],
            "runtime": sheet["runtime_scenarios"],
            "open_questions": sheet["open_questions"],
            "assumptions": sheet["assumptions"],
        },
        ensure_ascii=False,
    ).lower()
    assert "projektmanagement" not in architecture_payload
    assert "cloud" not in architecture_payload
    assert "team-zuordnung" not in architecture_payload
    assert "zuständiger" not in architecture_payload
    assert "loeschen" not in architecture_payload
    assert "löschen" not in architecture_payload


def test_generate_architecture_sheet_removes_not_evidenced_features_from_architecture() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")

    result = generate_architecture_sheet(
        "Einfache Todo Liste fuer Teammitglieder ohne Login.",
        application,
        llm_provider=HallucinatingScopeLLMProvider(),
        generation_mode="agentic_with_review",
    )
    sheet = result.to_dict()["architecture_sheet"]
    architecture_payload = json.dumps(
        {
            "decisions": sheet["architecture_decisions"],
            "blocks": sheet["building_blocks"],
            "runtime": sheet["runtime_scenarios"],
            "arc42_blocks": sheet["arc42"]["building_block_view"],
            "arc42_runtime": sheet["arc42"]["runtime_view"],
        },
        ensure_ascii=False,
    ).lower()

    assert "projektmanagement" not in architecture_payload
    assert "cloud" not in architecture_payload
    assert "ersteller" not in architecture_payload
    assert "zustaendiger" not in architecture_payload
    assert "zuständiger" not in architecture_payload
    assert "Aufgabe" in {block["name"] for block in sheet["building_blocks"]}


def test_generate_architecture_sheet_corrects_failed_review_once() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")
    provider = CorrectableReviewLLMProvider()

    result = generate_architecture_sheet(
        "Eine einfache Todo Liste fuer Teammitglieder ohne Login.",
        application,
        llm_provider=provider,
        generation_mode="agentic_with_review",
    )
    payload = result.to_dict()
    review = payload["generation"]["architecture_review"]

    assert provider.review_calls == 2
    assert provider.correction_calls == 1
    assert review["passes"] is True
    assert review["correction_attempts"][0]["passes"] is False
    assert payload["architecture_sheet"]["artifact_name"] == "Team-Todo-Liste"
    assert "gemeinsame Aufgabenliste" in payload["architecture_sheet"]["business_goal"]


def test_generate_architecture_sheet_normalizes_malformed_llm_contract_shapes() -> None:
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    application = FileApplicationRegistry(settings).get("software-factory")

    result = generate_architecture_sheet(
        "Eine einfache Todo Liste fuer Teammitglieder ohne Login.",
        application,
        llm_provider=MalformedArchitectureLLMProvider(),
        generation_mode="agentic_with_review",
    )
    sheet = result.to_dict()["architecture_sheet"]

    assert sheet["artifact_type"] == "django-application"
    assert sheet["architecture_drivers"][0] == {
        "name": "Testbarkeit",
        "description": "98 Prozent Coverage.",
        "impact": "98 Prozent Coverage.",
    }
    assert sheet["quality_goals"][0] == {
        "name": "Testabdeckung",
        "scenario": "98 Prozent",
        "priority": "high",
    }
    assert sheet["risks"][0] == {
        "description": "Statusfehler",
        "mitigation": "Status als Enum modellieren.",
    }
    assert sheet["acceptance_criteria"][0]["description"] == "Status offen ist verfuegbar"
    assert sheet["readiness"]["status"] == "ready-for-review"


def test_architecture_sheet_endpoint_is_removed() -> None:
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
        old_request = request.Request(
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
        try:
            request.urlopen(old_request, timeout=2)
        except HTTPError as error:
            assert error.status == 404
        else:
            raise AssertionError("Old synchronous architecture sheet endpoint must be removed.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_architecture_sheet_job_endpoints_create_list_and_get_job() -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
        llm_provider="ollama",
        llm_model="qwen3:14b",
    )
    store = FakeArchitectureJobStore()
    server = create_server(settings, architecture_job_store=store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        create_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/architecture-sheet/jobs",
            data=json.dumps(
                {
                    "description": "Eine Django-Anwendung fuer Kundenverwaltung.",
                    "generation_mode": "agentic",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(create_request, timeout=2) as response:
            assert response.status == 202
            created = json.loads(response.read().decode("utf-8"))

        job_id = created["job"]["id"]
        assert created["job"]["status"] == "queued"
        assert created["job"]["description"] == "Eine Django-Anwendung fuer Kundenverwaltung."
        assert created["job"]["generation_mode"] == "agentic"
        assert created["job"]["llm_provider"] == "ollama"
        assert created["job"]["llm_model"] == "qwen3:14b"

        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/architecture-sheet/jobs",
            timeout=2,
        ) as response:
            listed = json.loads(response.read().decode("utf-8"))

        assert [job["id"] for job in listed["jobs"]] == [job_id]
        assert "result" not in listed["jobs"][0]

        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/architecture-sheet/jobs/{job_id}",
            timeout=2,
        ) as response:
            loaded = json.loads(response.read().decode("utf-8"))

        assert loaded["job"]["id"] == job_id
        assert loaded["job"]["result"] is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_architecture_sheet_job_uses_configured_default_generation_mode() -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
        llm_provider="ollama",
        llm_model="qwen3:14b",
        architecture_generation_mode="agentic",
    )
    store = FakeArchitectureJobStore()
    server = create_server(settings, architecture_job_store=store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        create_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/architecture-sheet/jobs",
            data=json.dumps({"description": "Eine Django-Anwendung fuer Kundenverwaltung."}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(create_request, timeout=2) as response:
            created = json.loads(response.read().decode("utf-8"))

        assert response.status == 202
        assert created["job"]["generation_mode"] == "agentic"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_metrics_endpoint_exposes_architecture_job_metrics() -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
        llm_provider="ollama",
        llm_model="qwen3:14b",
    )
    store = FakeArchitectureJobStore()
    job = ArchitectureGenerationJob.create(
        "Eine Django-Anwendung fuer Kundenverwaltung.",
        generation_mode="agentic",
        llm_provider="ollama",
        llm_model="qwen3:14b",
        job_id="metrics-job",
    )
    job.add_log(
        "LLM call completed.",
        step="analyze_requirements",
        metadata={
            "kind": "llm_call",
            "llm_step": "requirement_analyst",
            "provider": "ollama",
            "model": "qwen3:14b",
            "status": "completed",
            "duration_seconds": 0.42,
        },
    )
    job.complete({"architecture_sheet": {"artifact_name": "Kundenverwaltung"}})
    store.save(job)
    server = create_server(settings, architecture_job_store=store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        with request.urlopen(f"http://{host}:{port}/metrics", timeout=2) as response:
            payload = response.read().decode("utf-8")

        assert response.status == 200
        assert response.headers["Content-Type"].startswith("text/plain")
        assert "buildbybricks_runtime_info" in payload
        assert "buildbybricks_architecture_jobs" in payload
        assert "buildbybricks_llm_call_duration_seconds_sum" in payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_architecture_sheet_job_events_streams_current_job_snapshot() -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
        job_stream_poll_seconds=0.01,
    )
    store = FakeArchitectureJobStore()
    job = ArchitectureGenerationJob.create(
        "Eine Django-Anwendung fuer Kundenverwaltung.",
        generation_mode="agentic",
        job_id="stream-job",
    )
    job.complete({"architecture_sheet": {"artifact_name": "Kundenverwaltung"}})
    store.save(job)
    server = create_server(settings, architecture_job_store=store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/architecture-sheet/jobs/stream-job/events",
            timeout=2,
        ) as response:
            body = response.read().decode("utf-8")

        assert response.status == 200
        assert response.headers["Content-Type"] == "text/event-stream; charset=utf-8"
        assert "event: job" in body
        assert '"id": "stream-job"' in body
        assert '"status": "completed"' in body
        assert '"artifact_name": "Kundenverwaltung"' in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_architecture_sheet_job_cancel_and_retry_actions() -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
        llm_provider="ollama",
        llm_model="qwen3:14b",
    )
    store = FakeArchitectureJobStore()
    job = ArchitectureGenerationJob.create(
        "Eine Django-Anwendung fuer Kundenverwaltung.",
        generation_mode="agentic",
        job_id="cancel-job",
    )
    store.save(job)
    server = create_server(settings, architecture_job_store=store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        cancel_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/architecture-sheet/jobs/cancel-job/cancel",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(cancel_request, timeout=2) as response:
            canceled = json.loads(response.read().decode("utf-8"))

        assert response.status == 200
        assert canceled["job"]["id"] == "cancel-job"
        assert canceled["job"]["status"] == "canceled"
        assert "Benutzer" in canceled["job"]["error"]

        retry_request = request.Request(
            f"http://{host}:{port}/apps/software-factory/architecture-sheet/jobs/cancel-job/retry",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(retry_request, timeout=2) as response:
            retried = json.loads(response.read().decode("utf-8"))

        assert response.status == 202
        assert retried["source_job_id"] == "cancel-job"
        assert retried["job"]["id"] != "cancel-job"
        assert retried["job"]["status"] == "queued"
        assert retried["job"]["description"] == "Eine Django-Anwendung fuer Kundenverwaltung."
        assert retried["job"]["generation_mode"] == "agentic"
        assert retried["job"]["llm_provider"] == "ollama"
        assert retried["job"]["llm_model"] == "qwen3:14b"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_architecture_sheet_artifact_endpoints_list_and_load_payload(tmp_path: Path) -> None:
    settings = Settings(
        frontend_dir=PROJECT_ROOT / "frontend",
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=tmp_path / "data",
        template_dir=PROJECT_ROOT / "template",
        host="127.0.0.1",
        port=0,
    )
    application = FileApplicationRegistry(settings).get("software-factory")
    job = ArchitectureGenerationJob.create(
        "Eine Django-Anwendung fuer Kundenverwaltung.",
        generation_mode="agentic",
        job_id="artifact-job",
    )
    FileArchitectureArtifactStore(application).save_architecture_sheet(
        job,
        {
            "architecture_sheet": {"artifact_name": "Kundenverwaltung"},
            "schema_id": "schema",
            "validation": {"valid": True},
            "generation": {},
        },
    )
    server = create_server(settings, architecture_job_store=FakeArchitectureJobStore())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/architecture-sheets",
            timeout=2,
        ) as response:
            listed = json.loads(response.read().decode("utf-8"))

        assert response.status == 200
        assert listed["artifacts"][0]["id"] == "artifact-job"
        assert listed["artifacts"][0]["title"] == "Kundenverwaltung"

        with request.urlopen(
            f"http://{host}:{port}/apps/software-factory/architecture-sheets/artifact-job",
            timeout=2,
        ) as response:
            loaded = json.loads(response.read().decode("utf-8"))

        assert loaded["artifact"]["id"] == "artifact-job"
        assert loaded["result"]["architecture_sheet"]["artifact_name"] == "Kundenverwaltung"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
