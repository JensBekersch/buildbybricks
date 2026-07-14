"""Generate first-pass architecture sheets for Django software artifacts."""

from dataclasses import dataclass
import json
import re
from typing import Any, Callable, Dict, List, Optional

from agentic_rag_template.applications import ApplicationInstance
from agentic_rag_template.ingestion import load_documents
from agentic_rag_template.llm.models import LLMProvider
from agentic_rag_template.software_factory.jobs import (
    EVENT_STEP_COMPLETED,
    EVENT_STEP_FAILED,
    EVENT_STEP_SKIPPED,
    EVENT_STEP_STARTED,
    ArchitectureGenerationEvent,
)


ArchitectureGenerationEventHandler = Callable[[ArchitectureGenerationEvent], None]


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


class ArchitectureSheetGenerationError(RuntimeError):
    """Raised when an architecture sheet cannot be generated safely."""


def _emit_event(
    event_handler: Optional[ArchitectureGenerationEventHandler],
    event_type: str,
    step: str,
    message: str,
    level: str = "info",
) -> None:
    if event_handler is None:
        return
    event_handler(
        ArchitectureGenerationEvent(
            type=event_type,
            step=step,
            message=message,
            level=level,
        )
    )


def _emit_started(
    event_handler: Optional[ArchitectureGenerationEventHandler],
    step: str,
    message: str,
) -> None:
    _emit_event(event_handler, EVENT_STEP_STARTED, step, message)


def _emit_completed(
    event_handler: Optional[ArchitectureGenerationEventHandler],
    step: str,
    message: str,
) -> None:
    _emit_event(event_handler, EVENT_STEP_COMPLETED, step, message)


def _emit_failed(
    event_handler: Optional[ArchitectureGenerationEventHandler],
    step: str,
    message: str,
) -> None:
    _emit_event(event_handler, EVENT_STEP_FAILED, step, message, level="error")


def _emit_skipped(
    event_handler: Optional[ArchitectureGenerationEventHandler],
    step: str,
    message: str,
) -> None:
    _emit_event(event_handler, EVENT_STEP_SKIPPED, step, message)


def generate_architecture_sheet(
    description: str,
    application: ApplicationInstance,
    llm_provider: Optional[LLMProvider] = None,
    generation_mode: str = "agentic_with_review",
    event_handler: Optional[ArchitectureGenerationEventHandler] = None,
) -> ArchitectureSheetResult:
    """Create a schema-shaped architecture sheet from a free-form description."""
    _emit_started(event_handler, "validate_description", "Beschreibung wird validiert.")
    normalized_description = " ".join(description.strip().split())
    mode = _normalize_generation_mode(generation_mode)
    _emit_completed(event_handler, "validate_description", "Beschreibung ist verwendbar.")

    _emit_started(event_handler, "load_schema", "Architecture-Sheet-Schema wird geladen.")
    schema = _load_schema(application)
    _emit_completed(event_handler, "load_schema", "Architecture-Sheet-Schema wurde geladen.")

    _emit_started(event_handler, "load_method_sources", "Methodenwissen wird geladen.")
    sources = _load_method_sources(application)
    _emit_completed(event_handler, "load_method_sources", "Methodenwissen wurde geladen.")
    trace = [
        "validated_description",
        "loaded_architecture_sheet_schema",
        "loaded_architecture_method_sources",
    ]
    generation = {
        "mode": mode,
        "requested_mode": mode,
        "llm_provider": getattr(llm_provider, "name", "none") if llm_provider else "none",
        "llm_model": getattr(llm_provider, "model", "none") if llm_provider else "none",
        "warnings": [],
    }

    agentic_sheet = _try_generate_agentic_architecture_sheet(
        description=normalized_description,
        schema=schema,
        method_sources=sources,
        llm_provider=llm_provider,
        include_review=mode == "agentic_with_review",
        event_handler=event_handler,
    )

    if agentic_sheet["sheet"] is None:
        warning = agentic_sheet["warning"] or "Agentic architecture generation did not return a sheet."
        raise ArchitectureSheetGenerationError(warning)

    sheet = _merge_known_schema_fields(agentic_sheet["base_sheet"], agentic_sheet["sheet"], schema)
    generation["pipeline"] = (
        "requirement_analyst -> architecture_synthesizer -> architecture_reviewer"
        if mode == "agentic_with_review"
        else "requirement_analyst -> architecture_synthesizer"
    )
    generation["requirement_analysis"] = agentic_sheet["analysis"]
    if agentic_sheet["review"]:
        generation["architecture_review"] = agentic_sheet["review"]
    if agentic_sheet["warning"]:
        generation["warnings"].append(agentic_sheet["warning"])
    trace.extend(["analyzed_requirements", "synthesized_architecture_sheet"])
    if mode == "agentic_with_review":
        trace.append("reviewed_architecture_sheet")

    _emit_started(event_handler, "validate_contract", "Architecture Sheet wird gegen den Contract validiert.")
    validation = _validate_required_fields(sheet, schema)
    _emit_completed(event_handler, "validate_contract", "Architecture Sheet wurde gegen den Contract validiert.")
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


def _normalize_generation_mode(generation_mode: str) -> str:
    allowed_modes = {"agentic", "agentic_with_review"}
    mode = (generation_mode or "agentic_with_review").strip().lower().replace("-", "_")

    if mode not in allowed_modes:
        raise ArchitectureSheetGenerationError(
            "Architecture sheets require generation_mode 'agentic' or 'agentic_with_review'."
        )

    return mode


def _try_generate_agentic_architecture_sheet(
    description: str,
    schema: Dict[str, Any],
    method_sources: List[Dict[str, Any]],
    llm_provider: Optional[LLMProvider],
    include_review: bool,
    event_handler: Optional[ArchitectureGenerationEventHandler],
) -> Dict[str, Any]:
    if llm_provider is None or llm_provider.name == "deterministic":
        _emit_failed(event_handler, "analyze_requirements", "Architecture sheet generation requires a structured LLM provider.")
        return {
            "sheet": None,
            "base_sheet": None,
            "analysis": {},
            "review": {},
            "warning": "Architecture sheet generation requires a structured LLM provider.",
        }

    generate_json = getattr(llm_provider, "generate_json", None)

    if not callable(generate_json):
        _emit_failed(
            event_handler,
            "analyze_requirements",
            f"LLM provider '{llm_provider.name}' does not support structured JSON generation.",
        )
        return {
            "sheet": None,
            "base_sheet": None,
            "analysis": {},
            "review": {},
            "warning": f"LLM provider '{llm_provider.name}' does not support structured JSON generation.",
        }

    current_step = "analyze_requirements"

    try:
        _emit_started(event_handler, "analyze_requirements", "Requirement Analyst wird aufgerufen.")
        raw_analysis = generate_json(
            system_prompt=_build_requirements_analyst_system_prompt(),
            user_prompt=_build_requirements_analyst_user_prompt(description, method_sources),
        )
        analysis = _normalize_requirements_analysis(raw_analysis, description)
        _emit_completed(event_handler, "analyze_requirements", "Requirement-Analyse wurde erstellt.")
        base_sheet = _build_sheet_from_requirements_analysis(description, analysis)

        current_step = "synthesize_architecture"
        _emit_started(event_handler, "synthesize_architecture", "Architecture Synthesizer wird aufgerufen.")
        raw_sheet = generate_json(
            system_prompt=_build_architecture_synthesizer_system_prompt(),
            user_prompt=_build_architecture_synthesizer_user_prompt(
                description=description,
                requirement_analysis=analysis,
                base_sheet=base_sheet,
                schema=_compact_schema_contract(schema),
                method_sources=method_sources,
            ),
        )
        candidate_sheet = raw_sheet.get("architecture_sheet", raw_sheet)

        if not isinstance(candidate_sheet, dict):
            _emit_failed(event_handler, "synthesize_architecture", "Architecture synthesizer did not return a JSON object.")
            return {
                "sheet": None,
                "base_sheet": None,
                "analysis": analysis,
                "review": {},
                "warning": "Architecture synthesizer did not return a JSON object.",
            }

        reviewed_sheet = _merge_known_schema_fields(base_sheet, candidate_sheet, schema)
        _emit_completed(event_handler, "synthesize_architecture", "Architecture Sheet wurde synthetisiert.")
        review = {}
        warning = ""
        if include_review:
            current_step = "review_architecture"
            _emit_started(event_handler, "review_architecture", "Architecture Reviewer wird aufgerufen.")
            raw_review = generate_json(
                system_prompt=_build_architecture_reviewer_system_prompt(),
                user_prompt=_build_architecture_reviewer_user_prompt(
                    description=description,
                    requirement_analysis=analysis,
                    sheet=reviewed_sheet,
                ),
            )
            review = _normalize_architecture_review(raw_review)
            warning = "" if review.get("passes") else "Architecture reviewer found issues."
            if warning:
                _emit_failed(event_handler, "review_architecture", warning)
            else:
                _emit_completed(event_handler, "review_architecture", "Architecture Review wurde abgeschlossen.")
        else:
            _emit_skipped(event_handler, "review_architecture", "Architecture Review wurde fuer diesen Modus uebersprungen.")
        return {
            "sheet": reviewed_sheet,
            "base_sheet": base_sheet,
            "analysis": analysis,
            "review": review,
            "warning": warning,
        }
    except Exception as error:
        _emit_failed(event_handler, current_step, f"Agentic architecture pipeline failed: {error}")
        return {
            "sheet": None,
            "base_sheet": None,
            "analysis": {},
            "review": {},
            "warning": f"Agentic architecture pipeline failed: {error}",
        }


def _compact_schema_contract(schema: Dict[str, Any]) -> Dict[str, Any]:
    properties = schema.get("properties", {})
    compact_properties: Dict[str, Dict[str, Any]] = {}

    for field_name, field_schema in properties.items():
        compact_field = {
            key: field_schema[key]
            for key in ("type", "enum", "const", "description")
            if key in field_schema
        }
        compact_properties[field_name] = compact_field

    return {
        "required": schema.get("required", []),
        "properties": compact_properties,
        "object_shapes": {
            "stakeholders": "Array of {name, description}",
            "architecture_drivers": "Array of {name, description, impact}",
            "quality_goals": "Array of {name, scenario, priority}",
            "constraints": "Array of {description}",
            "context": "{users: [{name, description}], external_systems: [{name, description}], interfaces: [{name, type, description}]}",
            "architecture_decisions": "Array of {id, decision, rationale, status}",
            "building_blocks": "Array of {name, responsibility, django_mapping}",
            "runtime_scenarios": "Array of {name, steps}",
            "acceptance_criteria": "Array of {description, verification}",
            "risks": "Array of {description, mitigation}",
            "open_questions": "Array of {description}",
            "assumptions": "Array of {description}",
            "readiness": "{status, summary}",
        },
    }


def _compact_method_sources(method_sources: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {
            "title": _string_value(source.get("title")),
            "location": _string_value(source.get("location")),
        }
        for source in method_sources[:5]
    ]


def _build_requirements_analyst_system_prompt() -> str:
    return "\n".join(
        [
            "Du bist der Requirement Analyst einer agentischen Django-Softwarefabrik.",
            "Erzeuge ausschliesslich valides JSON.",
            "Analysiere die Beschreibung, ohne Architektur zu erfinden.",
            "Trenne aktuellen Scope strikt von spaeteren, optionalen oder unklaren Erweiterungen.",
            "Extrahiere konkrete Rollen, Kernobjekte, Workflows, Schnittstellen, Qualitaetsziele, Risiken, Annahmen und offene Fragen.",
            "Verwende die Begriffe aus der Nutzerbeschreibung, keine generischen Platzhalter.",
        ]
    )


def _build_requirements_analyst_user_prompt(
    description: str,
    method_sources: List[Dict[str, Any]],
) -> str:
    return "\n\n".join(
        [
            f"Beschreibung:\n{description}",
            f"Methodenhinweise:\n{json.dumps(_compact_method_sources(method_sources), ensure_ascii=True)}",
            (
                "Gib JSON mit diesen Feldern zurueck: artifact_name, business_goal, roles, "
                "core_entities, workflows, current_interfaces, future_interfaces, quality_goals, "
                "constraints, explicitly_not_needed, risks, assumptions, open_questions. "
                "Array-Eintraege sollen konkrete Strings oder Objekte mit name/description sein."
            ),
        ]
    )


def _build_architecture_synthesizer_system_prompt() -> str:
    return "\n".join(
        [
            "Du bist der Architecture Synthesizer einer agentischen Django-Softwarefabrik.",
            "Erzeuge ausschliesslich valides JSON.",
            "Erzeuge ein vollstaendiges Architecture Sheet nach Schema.",
            "Nutze die Requirement-Analyse als fuehrende Quelle.",
            "Alle Bausteine, Szenarien, Datenmodelle und Tests muessen zur beschriebenen Anwendung passen.",
            "Zukuenftige oder optionale Schnittstellen gehoeren nur in assumptions/open_questions oder external_systems, nicht in current_interfaces.",
        ]
    )


def _build_architecture_synthesizer_user_prompt(
    description: str,
    requirement_analysis: Dict[str, Any],
    base_sheet: Dict[str, Any],
    schema: Dict[str, Any],
    method_sources: List[Dict[str, Any]],
) -> str:
    return "\n\n".join(
        [
            f"Beschreibung:\n{description}",
            f"Requirement-Analyse:\n{json.dumps(requirement_analysis, ensure_ascii=True)}",
            f"Schema-Vertrag:\n{json.dumps(schema, ensure_ascii=True)}",
            f"Methodenhinweise:\n{json.dumps(_compact_method_sources(method_sources), ensure_ascii=True)}",
            f"Schema-kompatible Baseline:\n{json.dumps(base_sheet, ensure_ascii=True)}",
            "Gib nur das vollstaendige Architecture-Sheet-JSON zurueck.",
        ]
    )


def _build_architecture_reviewer_system_prompt() -> str:
    return "\n".join(
        [
            "Du bist der Architecture Reviewer einer agentischen Django-Softwarefabrik.",
            "Erzeuge ausschliesslich valides JSON.",
            "Pruefe, ob das Architecture Sheet fachlich zur Beschreibung und Requirement-Analyse passt.",
            "Markiere generische Platzhalter, erfundene Features, Scope-Verletzungen und fehlende Kernobjekte.",
            "Gib passes, findings und required_corrections zurueck.",
        ]
    )


def _build_architecture_reviewer_user_prompt(
    description: str,
    requirement_analysis: Dict[str, Any],
    sheet: Dict[str, Any],
) -> str:
    return "\n\n".join(
        [
            f"Beschreibung:\n{description}",
            f"Requirement-Analyse:\n{json.dumps(requirement_analysis, ensure_ascii=True)}",
            f"Architecture Sheet:\n{json.dumps(sheet, ensure_ascii=True)}",
            (
                "Bewerte streng als JSON: "
                "{\"passes\": boolean, \"findings\": [string], \"required_corrections\": [string]}"
            ),
        ]
    )


def _normalize_requirements_analysis(
    raw_analysis: Dict[str, Any],
    description: str,
) -> Dict[str, Any]:
    if not isinstance(raw_analysis, dict):
        raw_analysis = {}

    analysis = {
        "artifact_name": _string_value(raw_analysis.get("artifact_name")) or _infer_artifact_name(description),
        "business_goal": _string_value(raw_analysis.get("business_goal")),
        "roles": _list_of_named_items(raw_analysis.get("roles")),
        "core_entities": _list_of_named_items(raw_analysis.get("core_entities")),
        "workflows": _list_of_named_items(raw_analysis.get("workflows")),
        "current_interfaces": _list_of_interface_items(raw_analysis.get("current_interfaces")),
        "future_interfaces": _list_of_interface_items(raw_analysis.get("future_interfaces")),
        "quality_goals": _list_of_named_items(raw_analysis.get("quality_goals")),
        "constraints": _list_of_text_items(raw_analysis.get("constraints")),
        "explicitly_not_needed": _list_of_text_items(raw_analysis.get("explicitly_not_needed")),
        "risks": _list_of_risk_items(raw_analysis.get("risks")),
        "assumptions": _list_of_text_items(raw_analysis.get("assumptions")),
        "open_questions": _list_of_text_items(raw_analysis.get("open_questions")),
    }

    if not analysis["roles"]:
        analysis["roles"] = [{"name": "Nutzer", "description": "Nutzen die Django-Anwendung."}]
    if not analysis["core_entities"]:
        analysis["core_entities"] = [{"name": "Fachobjekt", "description": "Aus der Beschreibung abzuleitendes Kernobjekt."}]
    if not analysis["workflows"]:
        analysis["workflows"] = [{"name": "Fachlichen Workflow ausfuehren", "description": "Zentraler Workflow der beschriebenen Anwendung."}]
    if not analysis["current_interfaces"]:
        analysis["current_interfaces"] = [
            {
                "name": "Web UI",
                "type": "web-ui",
                "description": "Serverseitige Django-Oberflaeche fuer die beschriebenen Workflows.",
            },
            {
                "name": "Django Admin",
                "type": "admin-ui",
                "description": "Admin-Oberflaeche fuer Stammdaten und Betrieb.",
            },
        ]

    return analysis


def _normalize_architecture_review(raw_review: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw_review, dict):
        raw_review = {}

    return {
        "passes": bool(raw_review.get("passes", False)),
        "findings": [item["description"] for item in _list_of_text_items(raw_review.get("findings"))],
        "required_corrections": [
            item["description"] for item in _list_of_text_items(raw_review.get("required_corrections"))
        ],
    }


def _build_sheet_from_requirements_analysis(
    description: str,
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    entity_names = [item["name"] for item in analysis["core_entities"]]
    workflow_names = [item["name"] for item in analysis["workflows"]]
    role_names = [item["name"] for item in analysis["roles"]]

    return {
        "schema_version": "1.0.0",
        "artifact_name": analysis["artifact_name"],
        "artifact_type": "django-application",
        "input_summary": description,
        "business_goal": analysis["business_goal"]
        or f"Die Django-Anwendung unterstuetzt {', '.join(workflow_names[:3])}.",
        "stakeholders": analysis["roles"],
        "architecture_drivers": [
            {
                "name": "Fachlicher Scope aus Requirement-Analyse",
                "description": f"Kernobjekte: {', '.join(entity_names)}.",
                "impact": "Django Apps, Models, Services und Tests werden aus diesen Kernobjekten abgeleitet.",
            },
            {
                "name": "Folgeagenten-Faehigkeit",
                "description": "Das Sheet muss spaeter in Workorders, Implementierung und Tests zerlegbar sein.",
                "impact": "Bausteine, Szenarien und Entscheidungen werden strukturiert und pruefbar formuliert.",
            },
        ],
        "quality_goals": _analysis_quality_goals(analysis),
        "constraints": analysis["constraints"]
        or [{"description": "Der erste Implementierungsfokus liegt auf Django-Applikationen."}],
        "context": {
            "users": analysis["roles"],
            "external_systems": _analysis_external_systems(analysis),
            "interfaces": analysis["current_interfaces"],
        },
        "solution_strategy": (
            "Die Anwendung wird als modulare Django-Applikation aufgebaut. Kernobjekte werden als "
            "Django Models und Services geschnitten; Workflows werden ueber Views, Forms, Berechtigungen "
            "und Integrationstests abgesichert."
        ),
        "architecture_decisions": [
            {
                "id": "ADR-001",
                "decision": "Das Artefakt wird als Django-Applikation umgesetzt.",
                "rationale": "Django liefert Auth, ORM, Admin, Templates, Migrationen und Testunterstuetzung als produktive Basis.",
                "status": "proposed",
            },
            {
                "id": "ADR-002",
                "decision": "Fachliche Kernobjekte werden in eigene Django Apps und Services ueberfuehrt.",
                "rationale": f"Die Requirement-Analyse nennt {', '.join(entity_names[:5])} als zentrale Objekte.",
                "status": "proposed",
            },
        ],
        "building_blocks": _analysis_building_blocks(analysis),
        "runtime_scenarios": _analysis_runtime_scenarios(analysis),
        "deployment_view": (
            "Startpunkt ist ein containerisierbares Django-Deployment mit Webprozess, relationaler Datenbank "
            "und getrennten Konfigurationen fuer lokale Entwicklung, Test und Produktion."
        ),
        "data_view": f"Zentrale Django Models werden aus den Kernobjekten abgeleitet: {', '.join(entity_names)}.",
        "security_view": _analysis_security_view(analysis, role_names),
        "test_strategy": (
            "Automatisierte Tests umfassen Model- und Service-Tests fuer Kernobjekte, Permission-Tests fuer Rollen, "
            "Workflow-Tests fuer zentrale Szenarien und Export/API-Tests nur fuer Schnittstellen im aktuellen Scope."
        ),
        "acceptance_criteria": _analysis_acceptance_criteria(analysis),
        "risks": analysis["risks"]
        or [
            {
                "description": "Fachliche Regeln koennen noch unvollstaendig sein.",
                "mitigation": "Offene Fragen vor Workorder-Erzeugung klaeren und Annahmen versioniert dokumentieren.",
            }
        ],
        "open_questions": analysis["open_questions"],
        "assumptions": analysis["assumptions"],
        "readiness": {
            "status": "ready-for-review",
            "summary": "Das Sheet ist strukturell vollstaendig und wurde aus einer Requirement-Analyse abgeleitet.",
        },
    }


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


def _string_value(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return _string_value(value.get("description") or value.get("name") or value.get("value"))
    return str(value).strip()


def _list_value(value: Any) -> List[Any]:
    if value in (None, "", {}, []):
        return []
    if isinstance(value, list):
        return value
    return [value]


def _list_of_named_items(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            name = _string_value(entry.get("name") or entry.get("title") or entry.get("role"))
            description = _string_value(entry.get("description") or entry.get("scenario") or entry.get("responsibility"))
        else:
            name = _string_value(entry)
            description = ""

        if name:
            items.append({"name": name, "description": description or name})

    return items


def _list_of_text_items(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        description = _string_value(entry)
        if description:
            items.append({"description": description})

    return items


def _list_of_risk_items(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            description = _string_value(entry.get("description") or entry.get("risk") or entry.get("name"))
            mitigation = _string_value(entry.get("mitigation") or entry.get("countermeasure"))
        else:
            description = _string_value(entry)
            mitigation = ""

        if description:
            items.append(
                {
                    "description": description,
                    "mitigation": mitigation or "Im Review klaeren und vor Workorder-Erzeugung absichern.",
                }
            )

    return items


def _list_of_interface_items(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            name = _string_value(entry.get("name") or entry.get("title"))
            interface_type = _string_value(entry.get("type") or entry.get("interface_type"))
            description = _string_value(entry.get("description"))
        else:
            name = _string_value(entry)
            interface_type = ""
            description = ""

        if name:
            items.append(
                {
                    "name": name,
                    "type": interface_type or _infer_interface_type(name),
                    "description": description or name,
                }
            )

    return items


def _infer_interface_type(name: str) -> str:
    lowered = name.lower()
    if "admin" in lowered:
        return "admin-ui"
    if "api" in lowered or "rest" in lowered or "schnittstelle" in lowered:
        return "rest-api"
    if "csv" in lowered or "export" in lowered or "pdf" in lowered:
        return "file-export"
    return "web-ui"


def _analysis_quality_goals(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    goals = []
    for item in analysis["quality_goals"]:
        goals.append(
            {
                "name": item["name"],
                "scenario": item["description"],
                "priority": "high",
            }
        )

    return goals or [
        {
            "name": "Nachvollziehbarkeit",
            "scenario": "Wichtige fachliche Aenderungen und Entscheidungen koennen rekonstruiert werden.",
            "priority": "high",
        },
        {
            "name": "Testbarkeit",
            "scenario": "Kernlogik, Berechtigungen und zentrale Workflows sind automatisiert testbar.",
            "priority": "high",
        },
    ]


def _analysis_external_systems(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    systems = [
        {
            "name": "Noch zu klaerende externe Systeme",
            "description": "Integrationen wurden aus der Beschreibung noch nicht eindeutig abgeleitet.",
        }
    ]

    if analysis["future_interfaces"]:
        systems.append(
            {
                "name": "Zukuenftige Integrationen",
                "description": "Nicht im ersten Scope: "
                + ", ".join(interface["name"] for interface in analysis["future_interfaces"]),
            }
        )

    return systems


def _analysis_building_blocks(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    blocks = [
        {
            "name": "Django Project Shell",
            "responsibility": "Settings, URL-Routing, ASGI/WSGI, Deployment-Konfiguration und Umgebungsprofile.",
            "django_mapping": "Django project package with settings modules, root urls.py and deployment entrypoints.",
        }
    ]

    for entity in analysis["core_entities"]:
        slug = _slug_from_name(entity["name"])
        blocks.append(
            {
                "name": entity["name"],
                "responsibility": entity["description"],
                "django_mapping": f"Django app or module `{slug}` with models, services, forms/views and tests.",
            }
        )

    return blocks


def _analysis_security_view(analysis: Dict[str, Any], role_names: List[str]) -> str:
    excluded = " ".join(item["description"].lower() for item in analysis["explicitly_not_needed"])

    if "login" in excluded or "auth" in excluded or "authentifizierung" in excluded:
        return (
            "Die Requirement-Analyse schliesst einen Login- oder Authentifizierungsbereich aus. "
            "Die erste Architektur modelliert daher keine Accounts-App und keine Rollenberechtigungen. "
            "Schutzmassnahmen beschraenken sich auf sichere Defaults, Eingabevalidierung und Betriebskonfiguration."
        )

    return (
        f"Security-Anforderungen werden aus der Requirement-Analyse abgeleitet. Relevante Nutzergruppen sind "
        f"{', '.join(role_names)}. Authentifizierung oder Berechtigungen werden nur modelliert, wenn sie "
        "explizit gefordert oder als Annahme markiert sind."
    )


def _analysis_runtime_scenarios(analysis: Dict[str, Any]) -> List[Dict[str, List[str]]]:
    scenarios = []

    for workflow in analysis["workflows"]:
        scenarios.append(
            {
                "name": workflow["name"],
                "steps": [
                    "Ein berechtigter Nutzer startet den Workflow in der Django-Weboberflaeche.",
                    workflow["description"],
                    "Das System validiert Eingaben, Berechtigungen und fachliche Regeln.",
                    "Die Anwendung speichert den neuen Zustand und zeigt das Ergebnis nachvollziehbar an.",
                ],
            }
        )

    return scenarios


def _analysis_acceptance_criteria(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    entity_names = ", ".join(item["name"] for item in analysis["core_entities"])
    workflow_names = ", ".join(item["name"] for item in analysis["workflows"])

    return [
        {
            "description": f"Kernobjekte sind im Sheet als Bausteine und Datenmodell erkennbar: {entity_names}.",
            "verification": "Building Blocks und Data View enthalten die extrahierten Kernobjekte.",
        },
        {
            "description": f"Zentrale Workflows sind als Runtime-Szenarien beschrieben: {workflow_names}.",
            "verification": "Runtime-Szenarien decken die Workflows der Requirement-Analyse ab.",
        },
        {
            "description": "Optionale oder spaetere Features sind nicht als aktueller Scope modelliert.",
            "verification": "Future Interfaces erscheinen nicht in context.interfaces.",
        },
    ]


def _slug_from_name(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name.lower())
    return "_".join(words[:4]) or "domain"


def _title_from_phrase(phrase: str) -> str:
    cleaned = phrase.strip(" .,:;")
    stop_words = {"eine", "einen", "ein", "der", "die", "das", "von"}
    words = [word for word in cleaned.split() if word.lower() not in stop_words]
    title = " ".join(words[:6]).strip()
    return title[:1].upper() + title[1:] if title else "Django Softwareartefakt"

def _validate_required_fields(sheet: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = schema.get("required", [])
    missing_fields = [
        field for field in required_fields if field not in sheet or sheet[field] in ("", [], {})
    ]
    return {
        "valid": not missing_fields,
        "missing_fields": missing_fields,
    }
