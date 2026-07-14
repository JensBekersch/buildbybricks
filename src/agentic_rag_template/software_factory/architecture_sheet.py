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


@dataclass(frozen=True)
class DomainAnalysis:
    """Small deterministic domain analysis for the architecture baseline."""

    kind: str
    name: str
    entities: List[str]
    roles: List[str]
    workflows: List[str]
    current_interfaces: List[Dict[str, str]]
    future_interfaces: List[Dict[str, str]]


def generate_architecture_sheet(
    description: str,
    application: ApplicationInstance,
    llm_provider: Optional[LLMProvider] = None,
    generation_mode: str = "fast",
) -> ArchitectureSheetResult:
    """Create a schema-shaped architecture sheet from a free-form description."""
    normalized_description = " ".join(description.strip().split())
    mode = _normalize_generation_mode(generation_mode, llm_provider)
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
        "mode": "deterministic" if mode == "fast" else mode,
        "requested_mode": mode,
        "llm_provider": getattr(llm_provider, "name", "none") if llm_provider else "none",
        "llm_model": getattr(llm_provider, "model", "none") if llm_provider else "none",
        "warnings": [],
    }

    agentic_sheet = _try_generate_agentic_architecture_sheet(
        description=normalized_description,
        schema=schema,
        method_sources=sources,
        llm_provider=llm_provider if mode in ("agentic", "agentic_with_review") else None,
        include_review=mode == "agentic_with_review",
    )

    if agentic_sheet["sheet"] is not None:
        sheet = _merge_known_schema_fields(agentic_sheet["base_sheet"], agentic_sheet["sheet"], schema)
        generation["mode"] = mode
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
    elif agentic_sheet["warning"]:
        generation["warnings"].append(agentic_sheet["warning"])
        trace.append("skipped_or_failed_agentic_architecture_pipeline")

    llm_sheet = _try_generate_llm_sheet(
        description=normalized_description,
        base_sheet=base_sheet,
        schema=schema,
        method_sources=sources,
        llm_provider=(
            llm_provider
            if agentic_sheet["sheet"] is None and mode == "legacy_llm_enrichment"
            else None
        ),
    )

    if llm_sheet["sheet"] is not None:
        sheet = _merge_known_schema_fields(base_sheet, llm_sheet["sheet"], schema)
        sheet = _preserve_domain_focus(base_sheet, sheet, normalized_description)
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


def _normalize_generation_mode(generation_mode: str, llm_provider: Optional[LLMProvider]) -> str:
    allowed_modes = {"fast", "agentic", "agentic_with_review", "legacy_llm_enrichment"}
    mode = (generation_mode or "fast").strip().lower().replace("-", "_")

    if mode in ("deterministic", "offline"):
        mode = "fast"

    if mode not in allowed_modes:
        mode = "agentic_with_review" if llm_provider else "fast"

    if llm_provider is None and mode != "fast":
        return "fast"

    return mode


def _try_generate_agentic_architecture_sheet(
    description: str,
    schema: Dict[str, Any],
    method_sources: List[Dict[str, Any]],
    llm_provider: Optional[LLMProvider],
    include_review: bool,
) -> Dict[str, Any]:
    if llm_provider is None or llm_provider.name == "deterministic":
        return {"sheet": None, "base_sheet": None, "analysis": {}, "review": {}, "warning": ""}

    generate_json = getattr(llm_provider, "generate_json", None)

    if not callable(generate_json):
        return {
            "sheet": None,
            "base_sheet": None,
            "analysis": {},
            "review": {},
            "warning": f"LLM provider '{llm_provider.name}' does not support structured JSON generation.",
        }

    try:
        raw_analysis = generate_json(
            system_prompt=_build_requirements_analyst_system_prompt(),
            user_prompt=_build_requirements_analyst_user_prompt(description, method_sources),
        )
        analysis = _normalize_requirements_analysis(raw_analysis, description)
        base_sheet = _build_sheet_from_requirements_analysis(description, analysis)
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
            return {
                "sheet": None,
                "base_sheet": None,
                "analysis": analysis,
                "review": {},
                "warning": "Architecture synthesizer did not return a JSON object.",
            }

        reviewed_sheet = _merge_known_schema_fields(base_sheet, candidate_sheet, schema)
        review = {}
        warning = ""
        if include_review:
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
        return {
            "sheet": reviewed_sheet,
            "base_sheet": base_sheet,
            "analysis": analysis,
            "review": review,
            "warning": warning,
        }
    except Exception as error:
        return {
            "sheet": None,
            "base_sheet": None,
            "analysis": {},
            "review": {},
            "warning": f"Agentic architecture pipeline failed: {error}",
        }


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
            "Jedes fachliche Feld muss konkrete Begriffe aus der Beschreibung verwenden.",
            "Vermeide generische Platzhalter wie Core Domain, Fachobjekt oder Fachanwender, wenn konkrete Begriffe vorhanden sind.",
            "Nimm zukuenftige oder optionale Schnittstellen nicht in den ersten Scope auf.",
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
                "constraints, risks, assumptions, open_questions. "
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
        "security_view": (
            f"Authentifizierung basiert auf Django Auth. Berechtigungen werden entlang der Rollen "
            f"{', '.join(role_names)} und der fachlichen Workflows objektbezogen geprueft."
        ),
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


def _preserve_domain_focus(
    base_sheet: Dict[str, Any],
    candidate_sheet: Dict[str, Any],
    description: str,
) -> Dict[str, Any]:
    analysis = _analyze_domain(description)

    if analysis.kind != "time_tracking":
        return candidate_sheet

    focused = dict(candidate_sheet)
    required_terms = ["arbeitszeit", "zeiteintrag", "timeentry", "monat", "pause"]
    protected_fields = [
        "artifact_name",
        "stakeholders",
        "architecture_drivers",
        "quality_goals",
        "context",
        "building_blocks",
        "runtime_scenarios",
        "data_view",
        "security_view",
        "test_strategy",
        "acceptance_criteria",
        "risks",
        "open_questions",
    ]

    for field in protected_fields:
        value = json.dumps(focused.get(field), ensure_ascii=True).lower()
        if not any(term in value for term in required_terms):
            focused[field] = base_sheet[field]

    if analysis.future_interfaces:
        interfaces = focused.get("context", {}).get("interfaces", [])
        if any(interface.get("type") == "rest-api" for interface in interfaces):
            focused["context"] = base_sheet["context"]

    focused["schema_version"] = "1.0.0"
    return focused


def _build_sheet(description: str) -> Dict[str, Any]:
    analysis = _analyze_domain(description)
    artifact_name = analysis.name or _infer_artifact_name(description)
    lower_description = description.lower()
    has_pdf = "pdf" in lower_description
    has_approval = any(term in lower_description for term in ["freigabe", "approval", "genehmigung"])
    has_export = any(term in lower_description for term in ["export", "csv", "excel", "pdf"])
    has_api = _has_current_api_requirement(lower_description)

    building_blocks = [
        {
            "name": "Django Project Shell",
            "responsibility": "Globale Settings, URL-Routing, ASGI/WSGI-Einstieg und Deployment-Konfiguration.",
            "django_mapping": "Django project package with settings modules, root urls.py and deployment entrypoints.",
        },
        {
            "name": "Accounts and Permissions",
            "responsibility": _accounts_responsibility(analysis),
            "django_mapping": "Django app `accounts` using auth groups, permissions and policy checks.",
        },
    ]
    building_blocks.extend(_domain_building_blocks(analysis))

    if has_approval and analysis.kind != "time_tracking":
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
    elif has_export:
        building_blocks.append(
            {
                "name": "Reporting and Export",
                "responsibility": "Fachliche Berichte und CSV-Exporte aus validierten Daten erzeugen.",
                "django_mapping": "Django app or service module `reports` for CSV generation and export tests.",
            }
        )

    interfaces = analysis.current_interfaces or [
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

    external_systems = [
        {
            "name": "Noch zu klaerende externe Systeme",
            "description": "Integrationen wurden aus der Beschreibung noch nicht eindeutig abgeleitet.",
        }
    ]
    if analysis.future_interfaces:
        external_systems.append(
            {
                "name": "Zukuenftige Integrationen",
                "description": "Erwaehnte, aber nicht fuer den ersten Scope verbindliche Schnittstellen: "
                + ", ".join(interface["name"] for interface in analysis.future_interfaces),
            }
        )

    runtime_scenarios = [
        *_domain_runtime_scenarios(analysis),
    ]

    if has_approval and analysis.kind != "time_tracking":
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

    if has_export and not has_pdf:
        runtime_scenarios.append(
            {
                "name": "Monatsbericht exportieren",
                "steps": [
                    "Ein berechtigter Nutzer waehlt Zeitraum, Team oder Projekt aus.",
                    "Das System ermittelt freigegebene Eintraege und berechnet Summen.",
                    "Die Anwendung erzeugt einen CSV-Export mit nachvollziehbaren Spalten.",
                    "Der Export wird bereitgestellt und die Aktion optional protokolliert.",
                ],
            }
        )

    return {
        "schema_version": "1.0.0",
        "artifact_name": artifact_name,
        "artifact_type": "django-application",
        "input_summary": description,
        "business_goal": _business_goal(description, analysis),
        "stakeholders": _stakeholders(analysis),
        "architecture_drivers": [
            *_domain_architecture_drivers(analysis),
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
        "quality_goals": _quality_goals(analysis),
        "constraints": [
            {
                "description": "Der erste Implementierungsfokus liegt auf Django-Applikationen."
            },
            {
                "description": "Architekturentscheidungen muessen spaeter in Workorders und Tests ueberfuehrbar sein."
            },
        ],
        "context": {
            "users": _context_users(analysis),
            "external_systems": external_systems,
            "interfaces": interfaces,
        },
        "solution_strategy": _solution_strategy(analysis),
        "architecture_decisions": [
            {
                "id": "ADR-001",
                "decision": "Das Artefakt wird als Django-Applikation modelliert.",
                "rationale": "Django liefert Auth, ORM, Admin, Migrations und Testunterstuetzung als produktive Basis.",
                "status": "proposed",
            },
            {
                "id": "ADR-002",
                "decision": _modular_decision(analysis),
                "rationale": _modular_decision_rationale(analysis),
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
        "data_view": _data_view(analysis),
        "security_view": _security_view(analysis),
        "test_strategy": _test_strategy(analysis, has_api),
        "acceptance_criteria": [
            *_domain_acceptance_criteria(analysis),
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
            *_domain_risks(analysis),
            {
                "description": "Fachliche Regeln und Rollen koennen in der Beschreibung noch unvollstaendig sein.",
                "mitigation": "Offene Fragen vor der Workorder-Erzeugung klaeren und Annahmen versioniert dokumentieren.",
            },
            {
                "description": "Zu grobe Django-App-Schnitte koennen spaeter Aenderbarkeit und Testbarkeit erschweren.",
                "mitigation": "Fachliche Grenzen frueh pruefen und Module entlang stabiler Verantwortlichkeiten schneiden.",
            },
        ],
        "open_questions": _build_open_questions(has_approval, has_pdf, has_api, analysis),
        "assumptions": [
            {
                "description": "Die Anwendung wird primaer als serverseitige Django-Webapplikation umgesetzt."
            },
            {
                "description": "Eine relationale Datenbank ist fuer die erste produktive Ausbaustufe ausreichend."
            },
            *_domain_assumptions(analysis),
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
        },
        {
            "name": "Accounts and Permissions",
            "responsibility": "Login, Rollen, Berechtigungen und Zugriffsschutz fuer die extrahierten Nutzerrollen.",
            "django_mapping": "Django app `accounts` using auth groups, permissions and object-level policy checks.",
        },
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


def _analyze_domain(description: str) -> DomainAnalysis:
    lower_description = description.lower()
    has_time_tracking = any(
        term in lower_description
        for term in [
            "arbeitszeit",
            "arbeitszeiten",
            "zeiteintrag",
            "startzeit",
            "endzeit",
            "pause",
            "soll-ist",
        ]
    )

    if has_time_tracking:
        current_interfaces = [
            {
                "name": "Web UI fuer Arbeitszeiterfassung",
                "type": "web-ui",
                "description": "Serverseitige Django-Oberflaeche fuer Zeiteintraege, Monatsuebersichten und Freigaben.",
            },
            {
                "name": "Django Admin fuer Stammdaten",
                "type": "admin-ui",
                "description": "Administration von Nutzern, Teams, Projekten, Feiertagen und Arbeitszeitmodellen.",
            },
        ]
        future_interfaces = []
        if "api" in lower_description:
            future_interfaces.append(
                {
                    "name": "Mobile REST API",
                    "type": "rest-api",
                    "description": "Spaetere API fuer mobile Apps; nicht Bestandteil des ersten serverseitigen Scopes.",
                }
            )

        return DomainAnalysis(
            kind="time_tracking",
            name="Arbeitszeiterfassung",
            entities=[
                "Zeiteintrag",
                "Projekt",
                "Team",
                "Monatsabschluss",
                "Freigabeentscheidung",
                "Feiertag",
                "Arbeitszeitmodell",
            ],
            roles=["Mitarbeitende", "Fuehrungskraefte", "Administratoren"],
            workflows=[
                "taegliche Arbeitszeit erfassen",
                "Monatsuebersicht pruefen",
                "Arbeitszeiten freigeben oder zur Korrektur zurueckgeben",
                "Monatsbericht exportieren",
            ],
            current_interfaces=current_interfaces,
            future_interfaces=future_interfaces,
        )

    return DomainAnalysis(
        kind="generic",
        name=_infer_artifact_name(description),
        entities=[],
        roles=[],
        workflows=[],
        current_interfaces=[],
        future_interfaces=[],
    )


def _has_current_api_requirement(lower_description: str) -> bool:
    if "api" not in lower_description and "schnittstelle" not in lower_description:
        return False

    future_markers = ["spaeter", "später", "koennte", "könnte", "optional", "zukuenftig", "zukünftig"]
    if any(marker in lower_description for marker in future_markers):
        return False

    return True


def _business_goal(description: str, analysis: DomainAnalysis) -> str:
    if analysis.kind == "time_tracking":
        return (
            "Die Anwendung soll Mitarbeitenden, Fuehrungskraeften und Administratoren eine "
            "nachvollziehbare Erfassung, Pruefung, Freigabe und Auswertung von Arbeitszeiten "
            "ermoeglichen. Im Mittelpunkt stehen korrekte Zeiteintraege, Monatsabschluesse, "
            "Soll-Ist-Berechnungen und exportierbare Monatsberichte."
        )

    return (
        f"Das Softwareartefakt soll den beschriebenen fachlichen Prozess als Django-Applikation "
        f"unterstuetzen: {description}"
    )


def _stakeholders(analysis: DomainAnalysis) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        return [
            {
                "name": "Mitarbeitende",
                "description": "Erfassen und korrigieren eigene taegliche Arbeitszeiten bis zum Monatsabschluss.",
            },
            {
                "name": "Fuehrungskraefte",
                "description": "Pruefen Monatsuebersichten ihrer Teams und geben Eintraege frei oder zur Korrektur zurueck.",
            },
            {
                "name": "Administratoren",
                "description": "Verwalten Nutzer, Teams, Projekte, Feiertage und Arbeitszeitmodelle.",
            },
            {
                "name": "Betrieb und Datenschutz",
                "description": "Stellen sicheren Betrieb, Backups, Zugriffsschutz und datenschutzkonforme Protokollierung sicher.",
            },
        ]

    return [
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
    ]


def _context_users(analysis: DomainAnalysis) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        return [
            {
                "name": "Mitarbeitende",
                "description": "Sehen und bearbeiten eigene Zeiteintraege, solange der jeweilige Monat offen ist.",
            },
            {
                "name": "Fuehrungskraefte",
                "description": "Sehen Teamzeiten, pruefen Monatsuebersichten und treffen Freigabeentscheidungen.",
            },
            {
                "name": "Administratoren",
                "description": "Pflegen Stammdaten und organisatorische Regeln ueber Admin-Oberflaechen.",
            },
        ]

    return [
        {
            "name": "Authentifizierte Nutzer",
            "description": "Interagieren rollenbasiert mit der Django-Weboberflaeche.",
        }
    ]


def _accounts_responsibility(analysis: DomainAnalysis) -> str:
    if analysis.kind == "time_tracking":
        return (
            "Login, Rollen und Berechtigungen fuer Mitarbeitende, Fuehrungskraefte und Administratoren "
            "abbilden, inklusive teambezogener Sichtbarkeit."
        )
    return "Benutzer, Rollen, Berechtigungen und Zugriffsschutz fuer fachliche Workflows."


def _domain_building_blocks(analysis: DomainAnalysis) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        return [
            {
                "name": "Time Entries",
                "responsibility": "Zeiteintraege mit Datum, Startzeit, Endzeit, Pause, Projekt, Taetigkeitsbeschreibung und Notizen erfassen, validieren und versioniert speichern.",
                "django_mapping": "Django app `timesheets` with TimeEntry model, forms, validators and service functions for duration calculation.",
            },
            {
                "name": "Projects and Teams",
                "responsibility": "Projekte, Teams und Zuordnung von Mitarbeitenden zu Fuehrungskraeften verwalten.",
                "django_mapping": "Django app `organization` with Project, Team and membership models.",
            },
            {
                "name": "Working Time Rules",
                "responsibility": "Arbeitszeitmodelle, Feiertage, Pausenregeln sowie Soll-Ist-Berechnung kapseln.",
                "django_mapping": "Django app `working_time` with calendar models and pure service layer for calculations.",
            },
            {
                "name": "Month Closing and Approval",
                "responsibility": "Monatsabschluss, Freigabe, Rueckgabe zur Korrektur und Sperrung abgeschlossener Monate steuern.",
                "django_mapping": "Django app `approvals` with MonthSummary, approval state machine and permission tests.",
            },
        ]

    return [
        {
            "name": "Core Domain",
            "responsibility": "Fachliche Kernobjekte aus der Artefaktbeschreibung modellieren und validieren.",
            "django_mapping": "One or more Django domain apps with models, services, forms or serializers.",
        }
    ]


def _domain_runtime_scenarios(analysis: DomainAnalysis) -> List[Dict[str, List[str]]]:
    if analysis.kind == "time_tracking":
        return [
            {
                "name": "Arbeitszeit erfassen",
                "steps": [
                    "Ein Mitarbeitender oeffnet die eigene Tages- oder Wochenansicht.",
                    "Der Mitarbeitende erfasst Datum, Startzeit, Endzeit, Pause, Projekt und Taetigkeitsbeschreibung.",
                    "Das System validiert Zeitlogik, Monatsstatus und Pflichtfelder.",
                    "Die Anwendung berechnet Nettoarbeitszeit und speichert den Zeiteintrag nachvollziehbar.",
                ],
            },
            {
                "name": "Monat abschliessen",
                "steps": [
                    "Ein Mitarbeitender prueft die Monatsuebersicht mit Soll-Ist-Zeiten.",
                    "Das System weist auf fehlende oder unplausible Eintraege hin.",
                    "Der Mitarbeitende reicht den Monat zur Pruefung ein.",
                    "Die Anwendung sperrt weitere Aenderungen bis zur Freigabe oder Rueckgabe.",
                ],
            },
            {
                "name": "Teamzeiten freigeben",
                "steps": [
                    "Eine Fuehrungskraft oeffnet die Monatsuebersicht eines Teammitglieds.",
                    "Das System zeigt Zeiteintraege, Summen, Abweichungen und Pruefhinweise.",
                    "Die Fuehrungskraft gibt den Monat frei oder sendet ihn mit Kommentar zur Korrektur zurueck.",
                    "Die Entscheidung wird mit Nutzer, Zeitstempel und Statuswechsel protokolliert.",
                ],
            },
        ]

    return [
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


def _domain_architecture_drivers(analysis: DomainAnalysis) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        return [
            {
                "name": "Korrekte Arbeitszeitberechnung",
                "description": "Pausen, Soll-Ist-Zeiten, Feiertage und Monatsgrenzen muessen fachlich korrekt berechnet werden.",
                "impact": "Berechnungslogik wird in testbare Services ausgelagert und nicht in Views oder Templates versteckt.",
            },
            {
                "name": "Rollen- und Team-Sichtbarkeit",
                "description": "Mitarbeitende sehen eigene Daten, Fuehrungskraefte sehen Teamdaten, Administratoren verwalten Stammdaten.",
                "impact": "Berechtigungen werden frueh modelliert und in Permission-Tests abgesichert.",
            },
        ]
    return []


def _quality_goals(analysis: DomainAnalysis) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        return [
            {
                "name": "Berechnungskorrektheit",
                "scenario": "Pausen, Nettoarbeitszeit, Monatsstunden und Soll-Ist-Abweichungen werden fuer relevante Arbeitszeitmodelle korrekt berechnet.",
                "priority": "high",
            },
            {
                "name": "Nachvollziehbarkeit",
                "scenario": "Freigaben, Rueckgaben und Aenderungen an Zeiteintraegen koennen mit Nutzer, Zeitpunkt und Status rekonstruiert werden.",
                "priority": "high",
            },
            {
                "name": "Datenschutz",
                "scenario": "Nutzer sehen nur die Arbeitszeitdaten, die ihrer Rolle und Teamzuordnung entsprechen.",
                "priority": "high",
            },
            {
                "name": "Testbarkeit",
                "scenario": "Berechnungsregeln, Berechtigungen und Monatsabschluss-Workflows sind automatisiert testbar.",
                "priority": "high",
            },
        ]

    return [
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
    ]


def _solution_strategy(analysis: DomainAnalysis) -> str:
    if analysis.kind == "time_tracking":
        return (
            "Die erste Version wird als serverseitige Django-Anwendung mit Templates, Django Auth, "
            "Django Admin und relationaler Datenbank umgesetzt. Die Fachlogik wird in klar getrennte "
            "Apps fuer Zeiteintraege, Organisation, Arbeitszeitregeln, Monatsabschluss/Freigabe und "
            "Reporting geschnitten. Berechnungen und Statuswechsel liegen in Services, damit Folgeagenten "
            "gezielt Models, Views, Tests und Workorders ableiten koennen."
        )

    return (
        "Die Anwendung wird als modular geschnittene Django-Applikation aufgebaut. "
        "Fachliche Module werden als Django Apps gekapselt, zentrale Regeln liegen in Services, "
        "Persistenz erfolgt ueber Django Models und kritische Workflows werden automatisiert getestet."
    )


def _modular_decision(analysis: DomainAnalysis) -> str:
    if analysis.kind == "time_tracking":
        return "Arbeitszeiterfassung wird in fachliche Django Apps fuer Zeiten, Organisation, Regeln, Freigabe und Reporting geschnitten."
    return "Fachliche Verantwortlichkeiten werden in getrennte Django Apps geschnitten."


def _modular_decision_rationale(analysis: DomainAnalysis) -> str:
    if analysis.kind == "time_tracking":
        return "Zeiterfassung, Stammdaten, Berechnungsregeln und Freigabe haben unterschiedliche Aenderungsgruende und Testprofile."
    return "Modulare Django Apps erleichtern Workorder-Schnitt, Tests und spaetere Erweiterungen."


def _data_view(analysis: DomainAnalysis) -> str:
    if analysis.kind == "time_tracking":
        return (
            "Zentrale Django Models sind TimeEntry, Project, Team, TeamMembership, WorkingTimeModel, "
            "Holiday, MonthSummary und ApprovalDecision. TimeEntry enthaelt Datum, Startzeit, Endzeit, "
            "Pause, Projekt, Taetigkeitsbeschreibung, Notizen, Besitzer und Statusbezug zum Monatsabschluss. "
            "MonthSummary buendelt Soll-Ist-Werte und Freigabestatus je Nutzer und Monat."
        )

    return (
        "Die fachlichen Kernobjekte werden als Django Models modelliert. Beziehungen, Statusfelder, "
        "Zeitstempel und Audit-relevante Informationen werden frueh festgelegt und durch Migrationen versioniert."
    )


def _security_view(analysis: DomainAnalysis) -> str:
    if analysis.kind == "time_tracking":
        return (
            "Authentifizierung basiert auf Django Auth. Mitarbeitende duerfen nur eigene Zeiten sehen und "
            "nur offene Monate bearbeiten. Fuehrungskraefte duerfen Teamzeiten pruefen und freigeben. "
            "Administratoren verwalten Stammdaten ueber Django Admin. Freigabeentscheidungen und Korrekturrueckgaben "
            "werden auditierbar protokolliert."
        )

    return (
        "Authentifizierung basiert auf Django Auth. Autorisierung erfolgt rollen- und objektbezogen. "
        "Kritische Aktionen benoetigen explizite Berechtigungen und sollten auditierbar sein."
    )


def _test_strategy(analysis: DomainAnalysis, has_api: bool) -> str:
    if analysis.kind == "time_tracking":
        return (
            "Automatisierte Tests umfassen Model- und Service-Tests fuer Pausen-, Nettozeit- und Soll-Ist-Berechnung, "
            "Permission-Tests fuer Mitarbeitende, Fuehrungskraefte und Administratoren, Workflow-Tests fuer Monatsabschluss, "
            "Freigabe und Rueckgabe sowie Export-Tests fuer CSV-Berichte. API-Tests werden erst relevant, wenn die spaetere "
            "mobile API in den Scope aufgenommen wird."
        )

    api_part = " und bei API-Anteilen API-Tests" if has_api else ""
    return (
        f"Automatisierte Tests umfassen Model- und Service-Tests, Permission-Tests, Workflow-Tests{api_part}. "
        "Kritische Pfade werden als Integrationstests abgebildet."
    )


def _domain_acceptance_criteria(analysis: DomainAnalysis) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        return [
            {
                "description": "Zeiteintraege koennen mit Datum, Startzeit, Endzeit, Pause, Projekt und Beschreibung modelliert werden.",
                "verification": "Das Sheet enthaelt dedizierte TimeEntry-Modelle und Validierungsregeln.",
            },
            {
                "description": "Monatsabschluss, Freigabe und Rueckgabe zur Korrektur sind als Workflow beschrieben.",
                "verification": "Runtime-Szenarien und Building Blocks enthalten Month Closing and Approval.",
            },
            {
                "description": "Soll-Ist-Berechnung, Feiertage und Arbeitszeitmodelle sind architektonisch beruecksichtigt.",
                "verification": "Data View und Teststrategie nennen WorkingTimeModel, Holiday und Berechnungstests.",
            },
        ]
    return []


def _domain_risks(analysis: DomainAnalysis) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        return [
            {
                "description": "Arbeitszeitmodelle, Feiertagsregeln und Pausenregeln koennen je Organisation komplexer sein als im MVP beschrieben.",
                "mitigation": "Berechnungsregeln in Services kapseln und mit parametrisierten Tests absichern.",
            },
            {
                "description": "Team- und Rollenberechtigungen koennen zu Datenschutzfehlern fuehren.",
                "mitigation": "Objektberechtigungen und Querysets fuer jede Rolle automatisiert testen.",
            },
        ]
    return []


def _domain_assumptions(analysis: DomainAnalysis) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        assumptions = [
            {
                "description": "Der erste Scope nutzt Django Templates und keine separate Single-Page-App."
            },
            {
                "description": "Die erwaehnte mobile REST API ist eine spaetere Erweiterung und nicht Bestandteil der ersten Architektur."
            },
        ]
        return assumptions if analysis.future_interfaces else assumptions[:1]
    return []


def _title_from_phrase(phrase: str) -> str:
    cleaned = phrase.strip(" .,:;")
    stop_words = {"eine", "einen", "ein", "der", "die", "das", "von"}
    words = [word for word in cleaned.split() if word.lower() not in stop_words]
    title = " ".join(words[:6]).strip()
    return title[:1].upper() + title[1:] if title else "Django Softwareartefakt"


def _build_open_questions(
    has_approval: bool,
    has_pdf: bool,
    has_api: bool,
    analysis: DomainAnalysis,
) -> List[Dict[str, str]]:
    if analysis.kind == "time_tracking":
        questions = [
            {
                "description": "Welche konkreten Arbeitszeitmodelle, Pausenregeln und Rundungsregeln gelten im ersten Release?"
            },
            {
                "description": "Wann gilt ein Monat als abgeschlossen und wer darf ihn in welchen Faellen wieder oeffnen?"
            },
            {
                "description": "Welche CSV-Spalten und Filter benoetigen Monatsberichte fuer Mitarbeitende, Teams und Projekte?"
            },
            {
                "description": "Welche Datenschutz- und Aufbewahrungsregeln gelten fuer Arbeitszeitdaten und Audit-Logs?"
            },
        ]
    else:
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
    elif analysis.future_interfaces:
        questions.append(
            {
                "description": "Wann soll die spaeter erwaehnte API in den Scope aufgenommen werden und welche Clients muessen sie nutzen?"
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
