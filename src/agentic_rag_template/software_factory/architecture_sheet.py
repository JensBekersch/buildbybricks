"""Generate first-pass architecture sheets for Django software artifacts."""

from dataclasses import dataclass
import json
import re
from typing import Any, Dict, List, Optional

from agentic_rag_template.applications import ApplicationInstance
from agentic_rag_template.ingestion import load_documents
from agentic_rag_template.llm.models import LLMProvider


@dataclass(frozen=True)
class ArchitectureSheetResult:
    """Generated architecture sheet plus workflow metadata."""

    sheet: Dict[str, Any]
    schema_id: str
    validation: Dict[str, Any]
    sources: List[Dict[str, Any]]
    trace: List[str]
    generation: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "architecture_sheet": self.sheet,
            "schema_id": self.schema_id,
            "validation": self.validation,
            "sources": self.sources,
            "trace": self.trace,
            "generation": self.generation,
        }


def generate_architecture_sheet(
    description: str,
    application: ApplicationInstance,
    llm_provider: Optional[LLMProvider] = None,
) -> ArchitectureSheetResult:
    """Create a schema-shaped architecture sheet from a free-form description."""
    normalized_description = " ".join(description.strip().split())
    schema = _load_schema(application)
    sources = _load_method_sources(application)
    base_sheet = _build_sheet(normalized_description)
    sheet = base_sheet
    trace = [
        "validated_description",
        "loaded_architecture_sheet_schema",
        "loaded_architecture_method_sources",
        "generated_django_architecture_sheet",
    ]
    generation = {
        "mode": "deterministic",
        "llm_provider": getattr(llm_provider, "name", "none") if llm_provider else "none",
        "llm_model": getattr(llm_provider, "model", "none") if llm_provider else "none",
        "warnings": [],
    }

    llm_sheet = _try_generate_llm_sheet(
        description=normalized_description,
        base_sheet=base_sheet,
        schema=schema,
        method_sources=sources,
        llm_provider=llm_provider,
    )

    if llm_sheet["sheet"] is not None:
        sheet = _merge_known_schema_fields(base_sheet, llm_sheet["sheet"], schema)
        generation["mode"] = "llm-assisted"
        trace.append("generated_llm_architecture_sheet")
    elif llm_sheet["warning"]:
        generation["warnings"].append(llm_sheet["warning"])
        trace.append("skipped_or_failed_llm_architecture_sheet")

    validation = _validate_required_fields(sheet, schema)
    trace.append("validated_architecture_sheet_contract")

    return ArchitectureSheetResult(
        sheet=sheet,
        schema_id=str(schema.get("$id", "")),
        validation=validation,
        sources=sources,
        trace=trace,
        generation=generation,
    )


def _load_schema(application: ApplicationInstance) -> Dict[str, Any]:
    schema_path = application.template_dir / "architecture_sheet.schema.json"

    if not schema_path.is_file():
        raise FileNotFoundError(f"Architecture sheet schema is missing: {schema_path}")

    return json.loads(schema_path.read_text(encoding="utf-8"))


def _load_method_sources(application: ApplicationInstance) -> List[Dict[str, Any]]:
    documents = load_documents(application.data_dir, collection=application.profile.default_collection)
    return [
        {
            "title": document.title,
            "location": document.relative_path.as_posix(),
            "excerpt": document.content[:280],
        }
        for document in documents
    ]


def _try_generate_llm_sheet(
    description: str,
    base_sheet: Dict[str, Any],
    schema: Dict[str, Any],
    method_sources: List[Dict[str, Any]],
    llm_provider: Optional[LLMProvider],
) -> Dict[str, Any]:
    if llm_provider is None or llm_provider.name == "deterministic":
        return {"sheet": None, "warning": ""}

    generate_json = getattr(llm_provider, "generate_json", None)

    if not callable(generate_json):
        return {
            "sheet": None,
            "warning": f"LLM provider '{llm_provider.name}' does not support structured JSON generation.",
        }

    try:
        candidate = generate_json(
            system_prompt=_build_architecture_sheet_system_prompt(),
            user_prompt=_build_architecture_sheet_user_prompt(
                description=description,
                base_sheet=base_sheet,
                schema=schema,
                method_sources=method_sources,
            ),
        )
    except Exception as error:
        return {"sheet": None, "warning": f"LLM generation failed: {error}"}

    if not isinstance(candidate, dict):
        return {"sheet": None, "warning": "LLM generation did not return a JSON object."}

    sheet = candidate.get("architecture_sheet", candidate)

    if not isinstance(sheet, dict):
        return {"sheet": None, "warning": "LLM architecture sheet payload is not an object."}

    return {"sheet": sheet, "warning": ""}


def _build_architecture_sheet_system_prompt() -> str:
    return "\n".join(
        [
            "Du bist ein Software-Architektur-Agent fuer Django-Applikationen.",
            "Erzeuge ausschliesslich valides JSON.",
            "Halte dich an das bereitgestellte Architecture-Sheet-Schema.",
            "Erfinde keine unbekannten Fakten. Nutze assumptions und open_questions fuer Unsicherheit.",
            "Behalte schema_version 1.0.0 bei.",
        ]
    )


def _build_architecture_sheet_user_prompt(
    description: str,
    base_sheet: Dict[str, Any],
    schema: Dict[str, Any],
    method_sources: List[Dict[str, Any]],
) -> str:
    return "\n\n".join(
        [
            f"Beschreibung:\n{description}",
            f"Schema:\n{json.dumps(schema, ensure_ascii=True)}",
            f"Methodenquellen:\n{json.dumps(method_sources, ensure_ascii=True)}",
            f"Deterministisches Basissheet zum Verbessern:\n{json.dumps(base_sheet, ensure_ascii=True)}",
            (
                "Aufgabe: Gib ein vollstaendiges JSON-Objekt fuer das Architecture Sheet zurueck. "
                "Keine Markdown-Zaunbloecke, keine Erklaerung ausserhalb von JSON."
            ),
        ]
    )


def _merge_known_schema_fields(
    base_sheet: Dict[str, Any],
    candidate_sheet: Dict[str, Any],
    schema: Dict[str, Any],
) -> Dict[str, Any]:
    known_fields = set(schema.get("properties", {}).keys())
    merged = dict(base_sheet)

    for field in known_fields:
        value = candidate_sheet.get(field)

        if value not in (None, "", [], {}):
            merged[field] = value

    merged["schema_version"] = "1.0.0"
    return merged


def _build_sheet(description: str) -> Dict[str, Any]:
    artifact_name = _infer_artifact_name(description)
    lower_description = description.lower()
    has_pdf = "pdf" in lower_description
    has_approval = any(term in lower_description for term in ["freigabe", "approval", "genehmigung"])
    has_api = "api" in lower_description or "schnittstelle" in lower_description

    building_blocks = [
        {
            "name": "Django Project Shell",
            "responsibility": "Globale Settings, URL-Routing, ASGI/WSGI-Einstieg und Deployment-Konfiguration.",
            "django_mapping": "Django project package with settings modules, root urls.py and deployment entrypoints.",
        },
        {
            "name": "Accounts and Permissions",
            "responsibility": "Benutzer, Rollen, Berechtigungen und Zugriffsschutz fuer fachliche Workflows.",
            "django_mapping": "Django app `accounts` using auth groups, permissions and policy checks.",
        },
        {
            "name": "Core Domain",
            "responsibility": "Fachliche Kernobjekte aus der Artefaktbeschreibung modellieren und validieren.",
            "django_mapping": "One or more Django domain apps with models, services, forms or serializers.",
        },
    ]

    if has_approval:
        building_blocks.append(
            {
                "name": "Approval Workflow",
                "responsibility": "Freigabeschritte, Statusuebergaenge, Verantwortlichkeiten und Audit-Trail abbilden.",
                "django_mapping": "Django app `approvals` with workflow models, services and integration tests.",
            }
        )

    if has_pdf:
        building_blocks.append(
            {
                "name": "Document Export",
                "responsibility": "PDF- oder Dateiexporte aus fachlichen Daten erzeugen und nachvollziehbar speichern.",
                "django_mapping": "Django service module or background job for PDF rendering and file storage.",
            }
        )

    interfaces = [
        {
            "name": "Web UI",
            "type": "web-ui",
            "description": "Browserbasierte Oberflaeche fuer die wichtigsten fachlichen Workflows.",
        },
        {
            "name": "Django Admin",
            "type": "admin-ui",
            "description": "Interne Pflege- und Diagnoseoberflaeche fuer Stammdaten und Betrieb.",
        },
    ]

    if has_api:
        interfaces.append(
            {
                "name": "Application API",
                "type": "rest-api",
                "description": "Programmierbare Schnittstelle fuer externe Systeme oder spaetere Automatisierung.",
            }
        )

    runtime_scenarios = [
        {
            "name": "Fachobjekt erfassen",
            "steps": [
                "Ein berechtigter Nutzer oeffnet die Django-Weboberflaeche.",
                "Der Nutzer erfasst oder aktualisiert ein fachliches Objekt.",
                "Die Anwendung validiert Eingaben und speichert Daten transaktional.",
                "Das System zeigt den aktualisierten Zustand nachvollziehbar an.",
            ],
        }
    ]

    if has_approval:
        runtime_scenarios.append(
            {
                "name": "Freigabe durchfuehren",
                "steps": [
                    "Ein Nutzer reicht ein Objekt zur Freigabe ein.",
                    "Das System ermittelt die naechste freigabeberechtigte Rolle.",
                    "Ein Entscheider genehmigt oder lehnt ab.",
                    "Die Entscheidung wird mit Zeitstempel und Nutzer im Audit-Trail gespeichert.",
                ],
            }
        )

    if has_pdf:
        runtime_scenarios.append(
            {
                "name": "PDF exportieren",
                "steps": [
                    "Ein Nutzer waehlt ein freigegebenes Objekt aus.",
                    "Das System rendert ein PDF aus den gespeicherten Daten.",
                    "Das PDF wird bereitgestellt und optional im Dateispeicher abgelegt.",
                ],
            }
        )

    return {
        "schema_version": "1.0.0",
        "artifact_name": artifact_name,
        "artifact_type": "django-application",
        "input_summary": description,
        "business_goal": (
            f"Das Softwareartefakt soll den beschriebenen fachlichen Prozess als Django-Applikation "
            f"unterstuetzen: {description}"
        ),
        "stakeholders": [
            {
                "name": "Fachanwender",
                "description": "Nutzen die Anwendung fuer die taeglichen fachlichen Workflows.",
            },
            {
                "name": "Fachverantwortliche",
                "description": "Definieren Regeln, Qualitaetsziele und Abnahmekriterien.",
            },
            {
                "name": "Entwicklungsteam",
                "description": "Implementiert Django-Code, Tests, Migrationen und Deployment-Artefakte.",
            },
            {
                "name": "Betrieb",
                "description": "Betreibt Anwendung, Datenbank, Backups, Monitoring und Releases.",
            },
        ],
        "architecture_drivers": [
            {
                "name": "Django-first Umsetzung",
                "description": "Die erste produktive Softwarefabrik spezialisiert sich auf Django-Applikationen.",
                "impact": "Architekturschnitte, Teststrategie und spaetere Workorders werden in Django-Begriffen formuliert.",
            },
            {
                "name": "Folgeagenten-Faehigkeit",
                "description": "Das Sheet muss spaeter von Workorder-, Implementierungs- und Testagenten verarbeitet werden.",
                "impact": "Alle zentralen Architekturentscheidungen, Risiken und offenen Fragen werden strukturiert abgelegt.",
            },
        ],
        "quality_goals": [
            {
                "name": "Nachvollziehbarkeit",
                "scenario": "Wichtige fachliche Entscheidungen und Datenveraenderungen koennen spaeter rekonstruiert werden.",
                "priority": "high",
            },
            {
                "name": "Aenderbarkeit",
                "scenario": "Fachliche Regeln koennen in klar abgegrenzten Django-Apps angepasst werden.",
                "priority": "high",
            },
            {
                "name": "Testbarkeit",
                "scenario": "Kernlogik, Berechtigungen und wichtige Workflows sind automatisiert testbar.",
                "priority": "high",
            },
        ],
        "constraints": [
            {
                "description": "Der erste Implementierungsfokus liegt auf Django-Applikationen."
            },
            {
                "description": "Architekturentscheidungen muessen spaeter in Workorders und Tests ueberfuehrbar sein."
            },
        ],
        "context": {
            "users": [
                {
                    "name": "Authentifizierte Nutzer",
                    "description": "Interagieren rollenbasiert mit der Django-Weboberflaeche.",
                }
            ],
            "external_systems": [
                {
                    "name": "Noch zu klaerende externe Systeme",
                    "description": "Integrationen wurden aus der Beschreibung noch nicht eindeutig abgeleitet.",
                }
            ],
            "interfaces": interfaces,
        },
        "solution_strategy": (
            "Die Anwendung wird als modular geschnittene Django-Applikation aufgebaut. "
            "Fachliche Module werden als Django Apps gekapselt, zentrale Regeln liegen in Services, "
            "Persistenz erfolgt ueber Django Models und kritische Workflows werden automatisiert getestet."
        ),
        "architecture_decisions": [
            {
                "id": "ADR-001",
                "decision": "Das Artefakt wird als Django-Applikation modelliert.",
                "rationale": "Django liefert Auth, ORM, Admin, Migrations und Testunterstuetzung als produktive Basis.",
                "status": "proposed",
            },
            {
                "id": "ADR-002",
                "decision": "Fachliche Verantwortlichkeiten werden in getrennte Django Apps geschnitten.",
                "rationale": "Modulare Django Apps erleichtern Workorder-Schnitt, Tests und spaetere Erweiterungen.",
                "status": "proposed",
            },
            {
                "id": "ADR-003",
                "decision": "Fachlogik wird nicht direkt in Views versteckt, sondern in Services oder klar testbaren Modulen gebuendelt.",
                "rationale": "Das verbessert Testbarkeit und macht Folgeagenten-Aufgaben kleinteiliger und pruefbarer.",
                "status": "proposed",
            },
        ],
        "building_blocks": building_blocks,
        "runtime_scenarios": runtime_scenarios,
        "deployment_view": (
            "Startpunkt ist ein containerisierbares Django-Deployment mit Webprozess, relationaler Datenbank "
            "und getrennten Konfigurationen fuer lokale Entwicklung, Test und Produktion."
        ),
        "data_view": (
            "Die fachlichen Kernobjekte werden als Django Models modelliert. Beziehungen, Statusfelder, "
            "Zeitstempel und Audit-relevante Informationen werden frueh festgelegt und durch Migrationen versioniert."
        ),
        "security_view": (
            "Authentifizierung basiert auf Django Auth. Autorisierung erfolgt rollen- und objektbezogen. "
            "Kritische Aktionen benoetigen explizite Berechtigungen und sollten auditierbar sein."
        ),
        "test_strategy": (
            "Automatisierte Tests umfassen Model- und Service-Tests, Permission-Tests, Workflow-Tests "
            "und bei API-Anteilen API-Tests. Kritische Pfade werden als Integrationstests abgebildet."
        ),
        "acceptance_criteria": [
            {
                "description": "Alle Pflichtfelder des Architecture-Sheet-Schemas sind gefuellt.",
                "verification": "Schema- und Contract-Validierung meldet keine fehlenden Felder.",
            },
            {
                "description": "Django-spezifische Building Blocks und Teststrategie sind vorhanden.",
                "verification": "Das Sheet enthaelt Django Project/App-Zuordnungen und konkrete Testarten.",
            },
            {
                "description": "Offene Fragen, Annahmen und Risiken sind fuer eine menschliche Review sichtbar.",
                "verification": "Die Listen `open_questions`, `assumptions` und `risks` sind nicht leer.",
            },
        ],
        "risks": [
            {
                "description": "Fachliche Regeln und Rollen koennen in der Beschreibung noch unvollstaendig sein.",
                "mitigation": "Offene Fragen vor der Workorder-Erzeugung klaeren und Annahmen versioniert dokumentieren.",
            },
            {
                "description": "Zu grobe Django-App-Schnitte koennen spaeter Aenderbarkeit und Testbarkeit erschweren.",
                "mitigation": "Fachliche Grenzen frueh pruefen und Module entlang stabiler Verantwortlichkeiten schneiden.",
            },
        ],
        "open_questions": _build_open_questions(has_approval, has_pdf, has_api),
        "assumptions": [
            {
                "description": "Die Anwendung wird primaer als serverseitige Django-Webapplikation umgesetzt."
            },
            {
                "description": "Eine relationale Datenbank ist fuer die erste produktive Ausbaustufe ausreichend."
            },
        ],
        "readiness": {
            "status": "ready-for-review",
            "summary": "Das Sheet ist strukturell vollstaendig, benoetigt aber menschliche Review vor Workorder-Erzeugung.",
        },
    }


def _infer_artifact_name(description: str) -> str:
    candidates = [
        r"(?:django-app|django-applikation|app|anwendung)\s+(?:fuer|für|zur|zum)\s+([^.,;]+)",
        r"(?:softwareartefakt|system)\s+(?:fuer|für|zur|zum)\s+([^.,;]+)",
    ]

    for pattern in candidates:
        match = re.search(pattern, description, flags=re.IGNORECASE)
        if match:
            return _title_from_phrase(match.group(1))

    words = re.findall(r"[A-Za-zÄÖÜäöüß0-9-]+", description)
    if words:
        return _title_from_phrase(" ".join(words[:5]))

    return "Django Softwareartefakt"


def _title_from_phrase(phrase: str) -> str:
    cleaned = phrase.strip(" .,:;")
    stop_words = {"eine", "einen", "ein", "der", "die", "das", "von"}
    words = [word for word in cleaned.split() if word.lower() not in stop_words]
    title = " ".join(words[:6]).strip()
    return title[:1].upper() + title[1:] if title else "Django Softwareartefakt"


def _build_open_questions(has_approval: bool, has_pdf: bool, has_api: bool) -> List[Dict[str, str]]:
    questions = [
        {
            "description": "Welche Rollen und Berechtigungen muessen im ersten Release verbindlich abgebildet werden?"
        },
        {
            "description": "Welche fachlichen Kernobjekte und Statusuebergaenge sind fuer den MVP zwingend?"
        },
        {
            "description": "Welche nichtfunktionalen Anforderungen gelten fuer Betrieb, Datenschutz und Performance?"
        },
    ]

    if has_approval:
        questions.append(
            {
                "description": "Wie viele Freigabestufen gibt es und welche Eskalationsregeln gelten?"
            }
        )

    if has_pdf:
        questions.append(
            {
                "description": "Welche Layout-, Archivierungs- und Versionsregeln gelten fuer PDF-Exporte?"
            }
        )

    if has_api:
        questions.append(
            {
                "description": "Welche externen Systeme konsumieren die API und welche Authentifizierung wird benoetigt?"
            }
        )

    return questions


def _validate_required_fields(sheet: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = schema.get("required", [])
    missing_fields = [
        field for field in required_fields if field not in sheet or sheet[field] in ("", [], {})
    ]
    return {
        "valid": not missing_fields,
        "missing_fields": missing_fields,
    }
