"""Generate first-pass architecture sheets for Django software artifacts."""

from dataclasses import dataclass
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional

from agentic_rag_template.applications import ApplicationInstance
from agentic_rag_template.ingestion import load_documents
from agentic_rag_template.llm.models import LLMProvider
from agentic_rag_template.software_factory.configured_agent import ConfiguredAgent
from agentic_rag_template.software_factory.jobs import (
    EVENT_STEP_COMPLETED,
    EVENT_STEP_FAILED,
    EVENT_LOG,
    EVENT_STEP_SKIPPED,
    EVENT_STEP_STARTED,
    ArchitectureGenerationEvent,
)
from agentic_rag_template.software_factory.workflow_blueprints import load_software_factory_workflow


ArchitectureGenerationEventHandler = Callable[[ArchitectureGenerationEvent], None]
MAX_REVIEW_CORRECTION_ATTEMPTS = 2
SCOPE_SENSITIVE_TERMS = (
    "projektmanagement",
    "cloud",
    "team-zuordnung",
    "teamzuordnung",
    "team zuordnung",
    "loeschen",
    "löschen",
    "ersteller",
    "erstellt hat",
    "zustaendig",
    "zuständig",
    "zustaendiger",
    "zuständiger",
    "zugewiesen",
    "zuweisung",
    "periodisierung",
)


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
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if event_handler is None:
        return
    event_handler(
        ArchitectureGenerationEvent(
            type=event_type,
            step=step,
            message=message,
            level=level,
            metadata=metadata or {},
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


def _emit_log(
    event_handler: Optional[ArchitectureGenerationEventHandler],
    step: str,
    message: str,
    level: str = "info",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    _emit_event(event_handler, EVENT_LOG, step, message, level=level, metadata=metadata)


def _emit_step_output(
    event_handler: Optional[ArchitectureGenerationEventHandler],
    step: str,
    output: Any,
    message: str = "Schritt-Ergebnis wurde gespeichert.",
) -> None:
    _emit_log(
        event_handler,
        step,
        message,
        metadata={
            "kind": "step_output",
            "output": output,
        },
    )


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
    _emit_step_output(
        event_handler,
        "validate_description",
        {
            "description": normalized_description,
            "generation_mode": mode,
        },
    )
    _emit_completed(event_handler, "validate_description", "Beschreibung ist verwendbar.")

    _emit_started(event_handler, "load_schema", "Architecture-Sheet-Schema wird geladen.")
    schema = _load_schema(application)
    _emit_step_output(
        event_handler,
        "load_schema",
        {
            "schema_id": str(schema.get("$id", "")),
            "schema_version": schema.get("properties", {}).get("schema_version", {}).get("const"),
            "required": schema.get("required", []),
        },
    )
    _emit_completed(event_handler, "load_schema", "Architecture-Sheet-Schema wurde geladen.")

    _emit_started(event_handler, "load_method_sources", "Methodenwissen wird geladen.")
    sources = _load_method_sources(application)
    _emit_step_output(event_handler, "load_method_sources", sources)
    _emit_completed(event_handler, "load_method_sources", "Methodenwissen wurde geladen.")
    workflow_version = load_software_factory_workflow(application, "architecture_sheet")
    configured_agents = _load_configured_workflow_agents(application, workflow_version)
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
        "workflow": _workflow_summary(workflow_version, include_review=mode == "agentic_with_review"),
    }

    agentic_sheet = _try_generate_agentic_architecture_sheet(
        description=normalized_description,
        schema=schema,
        method_sources=sources,
        llm_provider=llm_provider,
        include_review=mode == "agentic_with_review",
        event_handler=event_handler,
        requirement_analyst_agent=configured_agents["requirement_analyst"],
        architecture_synthesizer_agent=configured_agents["architecture_synthesizer"],
        architecture_reviewer_agent=configured_agents["architecture_reviewer"],
    )

    if agentic_sheet["sheet"] is None:
        warning = agentic_sheet["warning"] or "Agentic architecture generation did not return a sheet."
        raise ArchitectureSheetGenerationError(warning)

    sheet = _merge_known_schema_fields(
        agentic_sheet["base_sheet"],
        agentic_sheet["sheet"],
        schema,
        analysis=agentic_sheet["analysis"],
    )
    generation["pipeline"] = (
        "requirement_analyst -> architecture_synthesizer -> architecture_reviewer"
        if mode == "agentic_with_review"
        else "requirement_analyst -> architecture_synthesizer"
    )
    generation["agent_configs"] = {
        agent_id: agent.summary()
        for agent_id, agent in configured_agents.items()
        if include_review_agent(agent_id, mode)
    }
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
    _emit_step_output(event_handler, "validate_contract", validation)
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


def _load_configured_workflow_agents(
    application: ApplicationInstance,
    workflow_version: Any,
) -> Dict[str, ConfiguredAgent]:
    agents: Dict[str, ConfiguredAgent] = {}
    for step in workflow_version.steps:
        if step.agent_version is None:
            continue
        agent_id = step.agent_version.agent.slug.replace("-", "_")
        agents[agent_id] = ConfiguredAgent.load(application, agent_id)
    return agents


def _workflow_summary(workflow_version: Any, include_review: bool) -> Dict[str, Any]:
    steps = [
        step.step_key
        for step in sorted(workflow_version.steps, key=lambda item: item.position)
        if include_review or step.step_key != "review_architecture"
    ]
    return {
        "id": workflow_version.workflow.slug,
        "name": workflow_version.workflow.name,
        "version": workflow_version.version_number,
        "status": workflow_version.status,
        "steps": steps,
    }


def include_review_agent(agent_id: str, mode: str) -> bool:
    return mode == "agentic_with_review" or agent_id != "architecture_reviewer"


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
    requirement_analyst_agent: ConfiguredAgent,
    architecture_synthesizer_agent: ConfiguredAgent,
    architecture_reviewer_agent: ConfiguredAgent,
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
        raw_analysis = requirement_analyst_agent.run_json(
            llm_provider=llm_provider,
            context={
                "user_description": description,
                "method_sources": _compact_method_sources(method_sources),
            },
            event_handler=event_handler,
            step="analyze_requirements",
            llm_step="requirement_analyst",
        )
        analysis = _normalize_requirements_analysis(raw_analysis, description)
        _emit_step_output(event_handler, "analyze_requirements", analysis)
        _emit_completed(event_handler, "analyze_requirements", "Requirement-Analyse wurde erstellt.")
        base_sheet = _build_sheet_from_requirements_analysis(description, analysis)

        current_step = "synthesize_architecture"
        _emit_started(event_handler, "synthesize_architecture", "Architecture Synthesizer wird aufgerufen.")
        raw_sheet = architecture_synthesizer_agent.run_json(
            llm_provider=llm_provider,
            context={
                "description": description,
                "requirement_analysis": analysis,
                "base_sheet": base_sheet,
                "schema": _compact_schema_contract(schema),
                "method_sources": method_sources,
            },
            event_handler=event_handler,
            step="synthesize_architecture",
            llm_step="architecture_synthesizer",
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

        reviewed_sheet = _merge_known_schema_fields(base_sheet, candidate_sheet, schema, analysis=analysis)
        _emit_step_output(event_handler, "synthesize_architecture", reviewed_sheet)
        _emit_completed(event_handler, "synthesize_architecture", "Architecture Sheet wurde synthetisiert.")
        review = {}
        warning = ""
        if include_review:
            current_step = "review_architecture"
            _emit_started(event_handler, "review_architecture", "Architecture Reviewer wird aufgerufen.")
            review = _review_and_correct_architecture_sheet(
                generate_json=generate_json,
                llm_provider=llm_provider,
                event_handler=event_handler,
                description=description,
                requirement_analysis=analysis,
                base_sheet=base_sheet,
                schema=schema,
                method_sources=method_sources,
                initial_sheet=reviewed_sheet,
                architecture_reviewer_agent=architecture_reviewer_agent,
            )
            reviewed_sheet = review["sheet"]
            _emit_step_output(
                event_handler,
                "review_architecture",
                {
                    key: value
                    for key, value in review.items()
                    if key != "sheet"
                },
            )
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


def _review_and_correct_architecture_sheet(
    generate_json: Callable[..., Dict[str, Any]],
    llm_provider: LLMProvider,
    event_handler: Optional[ArchitectureGenerationEventHandler],
    description: str,
    requirement_analysis: Dict[str, Any],
    base_sheet: Dict[str, Any],
    schema: Dict[str, Any],
    method_sources: List[Dict[str, Any]],
    initial_sheet: Dict[str, Any],
    architecture_reviewer_agent: ConfiguredAgent,
) -> Dict[str, Any]:
    sheet = initial_sheet
    reviews: List[Dict[str, Any]] = []

    for attempt in range(MAX_REVIEW_CORRECTION_ATTEMPTS + 1):
        raw_review = architecture_reviewer_agent.run_json(
            llm_provider=llm_provider,
            context={
                "description": description,
                "requirement_analysis": requirement_analysis,
                "architecture_sheet": sheet,
            },
            event_handler=event_handler,
            step="review_architecture",
            llm_step="architecture_reviewer",
        )
        review = _normalize_architecture_review(raw_review)
        review["attempt"] = attempt + 1
        reviews.append(review)
        _emit_step_output(
            event_handler,
            "review_architecture",
            {
                "latest_review": review,
                "reviews": reviews,
            },
            message=f"Review-Ergebnis fuer Versuch {attempt + 1} wurde gespeichert.",
        )

        if review["passes"]:
            review["sheet"] = sheet
            review["correction_attempts"] = reviews[:-1]
            return review

        if attempt >= MAX_REVIEW_CORRECTION_ATTEMPTS:
            review["sheet"] = sheet
            review["correction_attempts"] = reviews[:-1]
            return review

        _emit_log(
            event_handler,
            "review_architecture",
            f"Architecture Review fordert Korrekturlauf {attempt + 1}.",
            level="warning",
            metadata={
                "kind": "architecture_correction",
                "attempt": attempt + 1,
                "findings": review["findings"],
                "required_corrections": review["required_corrections"],
            },
        )
        raw_correction = _call_generate_json_with_metrics(
            generate_json=generate_json,
            llm_provider=llm_provider,
            event_handler=event_handler,
            step="synthesize_architecture",
            llm_step="architecture_correction",
            system_prompt=_build_architecture_correction_system_prompt(),
            user_prompt=_build_architecture_correction_user_prompt(
                description=description,
                requirement_analysis=requirement_analysis,
                base_sheet=base_sheet,
                current_sheet=sheet,
                review=review,
                schema=_compact_schema_contract(schema),
                method_sources=method_sources,
            ),
        )
        candidate_sheet = raw_correction.get("architecture_sheet", raw_correction)
        if not isinstance(candidate_sheet, dict):
            raise ArchitectureSheetGenerationError("Architecture correction did not return a JSON object.")
        sheet = _merge_known_schema_fields(
            base_sheet,
            candidate_sheet,
            schema,
            analysis=requirement_analysis,
        )
        _emit_step_output(
            event_handler,
            "synthesize_architecture",
            {
                "correction_attempt": attempt + 1,
                "sheet": sheet,
            },
            message=f"Korrigiertes Architecture Sheet fuer Versuch {attempt + 1} wurde gespeichert.",
        )

    return {
        "passes": False,
        "findings": ["Architecture Review konnte nicht abgeschlossen werden."],
        "required_corrections": ["Sheet manuell pruefen."],
        "sheet": sheet,
        "correction_attempts": reviews,
    }


def _call_generate_json_with_metrics(
    generate_json: Callable[..., Dict[str, Any]],
    llm_provider: LLMProvider,
    event_handler: Optional[ArchitectureGenerationEventHandler],
    step: str,
    llm_step: str,
    system_prompt: str,
    user_prompt: str,
) -> Dict[str, Any]:
    started_at = time.perf_counter()
    metadata = {
        "kind": "llm_call",
        "llm_step": llm_step,
        "provider": getattr(llm_provider, "name", "none"),
        "model": getattr(llm_provider, "model", "none"),
    }

    try:
        result = generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
    except Exception as error:
        duration_seconds = time.perf_counter() - started_at
        _emit_log(
            event_handler,
            step,
            f"LLM call failed: {error}",
            level="error",
            metadata={
                **metadata,
                "status": "failed",
                "duration_seconds": round(duration_seconds, 6),
                "error": str(error),
            },
        )
        raise

    duration_seconds = time.perf_counter() - started_at
    _emit_log(
        event_handler,
        step,
        "LLM call completed.",
        metadata={
            **metadata,
            "status": "completed",
            "duration_seconds": round(duration_seconds, 6),
        },
    )
    return result


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


def _build_architecture_correction_system_prompt() -> str:
    return "\n".join(
        [
            "Du bist der Architecture Corrector einer agentischen Django-Softwarefabrik.",
            "Erzeuge ausschliesslich valides JSON.",
            "Korrigiere ein Architecture Sheet anhand der Review-Hinweise.",
            "Schreibe alle beschreibenden Texte konsequent auf Deutsch.",
            "Erhalte fachlich richtige Inhalte, entferne Scope-fremde Features und ergaenze fehlende oder zu duenne Abschnitte.",
            "Entferne alle Inhalte, die in out_of_scope, explicitly_excluded_terms oder not_evidenced enthalten sind.",
            "Stelle sicher, dass das arc42-Objekt alle 12 Kapitel enthaelt.",
            "Gib ein vollstaendiges Architecture-Sheet-JSON nach Schema zurueck.",
        ]
    )


def _build_architecture_correction_user_prompt(
    description: str,
    requirement_analysis: Dict[str, Any],
    base_sheet: Dict[str, Any],
    current_sheet: Dict[str, Any],
    review: Dict[str, Any],
    schema: Dict[str, Any],
    method_sources: List[Dict[str, Any]],
) -> str:
    return "\n\n".join(
        [
            f"Beschreibung:\n{description}",
            f"Requirement-Analyse:\n{json.dumps(requirement_analysis, ensure_ascii=True)}",
            f"Aktuelles Architecture Sheet:\n{json.dumps(current_sheet, ensure_ascii=True)}",
            f"Review-Befunde:\n{json.dumps(review, ensure_ascii=True)}",
            f"Schema-Vertrag:\n{json.dumps(schema, ensure_ascii=True)}",
            f"Methodenhinweise:\n{json.dumps(_compact_method_sources(method_sources), ensure_ascii=True)}",
            f"Schema-kompatible Baseline:\n{json.dumps(base_sheet, ensure_ascii=True)}",
            (
                "Korrigiere alle required_corrections. "
                "Gib nur das vollstaendige korrigierte Architecture-Sheet-JSON zurueck."
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
        "in_scope": _list_of_text_items(raw_analysis.get("in_scope")),
        "out_of_scope": _list_of_text_items(raw_analysis.get("out_of_scope")),
        "not_evidenced": _list_of_text_items(raw_analysis.get("not_evidenced")),
        "explicitly_excluded": _list_of_structured_items(raw_analysis.get("explicitly_excluded")),
        "not_requested": _list_of_structured_items(raw_analysis.get("not_requested")),
        "future_ideas": _list_of_structured_items(raw_analysis.get("future_ideas")),
        "explicitly_excluded_terms": [
            item["description"] for item in _list_of_text_items(raw_analysis.get("explicitly_excluded_terms"))
        ],
        "core_facts": _list_of_text_items(raw_analysis.get("core_facts")),
        "domain_entities": _list_of_domain_entities(raw_analysis.get("domain_entities")),
        "enumerations": _list_of_structured_items(raw_analysis.get("enumerations")),
        "functional_requirements": _list_of_structured_items(raw_analysis.get("functional_requirements")),
        "crud_requirements": _list_of_structured_items(raw_analysis.get("crud_requirements")),
        "validation_rules": _list_of_structured_items(raw_analysis.get("validation_rules")),
        "security_rules": _list_of_structured_items(raw_analysis.get("security_rules")),
        "ui_requirements": _list_of_structured_items(raw_analysis.get("ui_requirements")),
        "technical_constraints": _list_of_structured_items(raw_analysis.get("technical_constraints")),
        "delivery_requirements": _list_of_structured_items(raw_analysis.get("delivery_requirements")),
        "test_requirements": _list_of_structured_items(raw_analysis.get("test_requirements")),
        "quality_requirements": _list_of_structured_items(raw_analysis.get("quality_requirements")),
        "risks": _list_of_risk_items(raw_analysis.get("risks")),
        "assumptions": _list_of_text_items(raw_analysis.get("assumptions")),
        "open_questions": _list_of_text_items(raw_analysis.get("open_questions")),
    }

    if not analysis["core_entities"] and analysis["domain_entities"]:
        analysis["core_entities"] = _derive_core_entities_from_domain_entities(analysis)
    if not analysis["workflows"] and analysis["functional_requirements"]:
        analysis["workflows"] = _derive_workflows_from_functional_requirements(analysis)
    if not analysis["quality_goals"] and analysis["quality_requirements"]:
        analysis["quality_goals"] = _derive_quality_goals_from_quality_requirements(analysis)
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
    analysis["explicitly_excluded_terms"] = _dedupe_strings(
        analysis["explicitly_excluded_terms"] + _derive_excluded_terms(description)
    )
    if analysis["explicitly_not_needed"]:
        analysis["out_of_scope"].extend(analysis["explicitly_not_needed"])
    if not analysis["in_scope"]:
        analysis["in_scope"] = _derive_in_scope_items(analysis)
    if not analysis["core_facts"]:
        analysis["core_facts"] = _derive_core_facts(description, analysis)
    if not analysis["domain_entities"]:
        analysis["domain_entities"] = _derive_domain_entities(analysis)
    if not analysis["functional_requirements"]:
        analysis["functional_requirements"] = _derive_functional_requirements(analysis)
    if not analysis["technical_constraints"]:
        analysis["technical_constraints"] = _list_of_structured_items(analysis["constraints"])
    if not analysis["explicitly_excluded"] and analysis["out_of_scope"]:
        analysis["explicitly_excluded"] = _list_of_structured_items(analysis["out_of_scope"])
    if not analysis["not_evidenced"]:
        analysis["not_evidenced"] = [
            {"description": term}
            for term in SCOPE_SENSITIVE_TERMS
            if term not in _scope_text(analysis)
        ]
    analysis["out_of_scope"] = _dedupe_text_items(analysis["out_of_scope"])
    analysis["not_evidenced"] = _dedupe_text_items(analysis["not_evidenced"])
    analysis["in_scope"] = _dedupe_text_items(analysis["in_scope"])
    analysis["core_facts"] = _dedupe_text_items(analysis["core_facts"])

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


def _derive_excluded_terms(description: str) -> List[str]:
    lowered = description.lower()
    terms: List[str] = []
    patterns = [
        ("login", ("kein login", "keinen login", "ohne login", "braucht also keinen login")),
        ("authentifizierung", ("keine authentifizierung", "ohne authentifizierung")),
        ("team-zuordnung", ("keinen teams zugeordnet", "keine team-zuordnung", "keinen teams")),
        ("periodisierung", ("keine periodisierung", "periodisierung findet nicht statt")),
        ("ersteller", ("nicht gespeichert, wer eine aufgabe erstellt", "wer eine aufgabe erstellt hat")),
        ("zuständiger", ("wer fuer die ausfuehrung zustaendig ist", "wer für die ausführung zuständig ist")),
        ("löschen", ("nicht geloescht", "nicht gelöscht")),
    ]

    for term, needles in patterns:
        if any(needle in lowered for needle in needles):
            terms.append(term)

    return terms


def _derive_in_scope_items(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for collection in ("roles", "core_entities", "workflows", "current_interfaces", "quality_goals"):
        for entry in analysis.get(collection, []):
            description = entry.get("description") or entry.get("name")
            if description:
                items.append({"description": description})
    return items


def _derive_core_facts(description: str, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    facts = [{"description": description}]
    for entity in analysis.get("core_entities", []):
        facts.append({"description": f"Kernobjekt: {entity['name']} - {entity['description']}"})
    for workflow in analysis.get("workflows", []):
        facts.append({"description": f"Workflow: {workflow['name']} - {workflow['description']}"})
    return facts


def _derive_domain_entities(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "name": entity["name"],
            "description": entity["description"],
            "attributes": [],
        }
        for entity in analysis.get("core_entities", [])
    ]


def _derive_core_entities_from_domain_entities(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        {
            "name": _string_value(entity.get("name")),
            "description": _string_value(entity.get("description")) or _string_value(entity.get("name")),
        }
        for entity in analysis.get("domain_entities", [])
        if _string_value(entity.get("name"))
    ]


def _derive_workflows_from_functional_requirements(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    workflows = []
    for requirement in analysis.get("functional_requirements", []):
        name = _string_value(
            requirement.get("name")
            or requirement.get("action")
            or requirement.get("id")
        )
        description = _string_value(requirement.get("description")) or name
        if name:
            workflows.append({"name": name, "description": description})
    return workflows


def _derive_quality_goals_from_quality_requirements(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    goals = []
    for requirement in analysis.get("quality_requirements", []):
        name = _string_value(
            requirement.get("name")
            or requirement.get("category")
            or requirement.get("id")
        )
        scenario = _string_value(requirement.get("description")) or name
        if name:
            goals.append({"name": name, "description": scenario})
    return goals


def _derive_functional_requirements(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "name": workflow["name"],
            "description": workflow["description"],
            "evidence": workflow["description"],
        }
        for workflow in analysis.get("workflows", [])
    ]


def _dedupe_text_items(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    result = []
    for item in items:
        description = _string_value(item.get("description"))
        key = description.lower()
        if description and key not in seen:
            seen.add(key)
            result.append({"description": description})
    return result


def _dedupe_strings(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        normalized = _string_value(item)
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _scope_text(analysis: Dict[str, Any]) -> str:
    values = []
    for key in ("in_scope", "core_facts", "roles", "core_entities", "workflows", "current_interfaces"):
        values.append(json.dumps(analysis.get(key, []), ensure_ascii=False).lower())
    return " ".join(values)


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
            "Die Anwendung wird als modulare Django-Applikation aufgebaut. Die fachlichen Kernobjekte "
            "werden als Django-Models mit klaren Validierungsregeln modelliert und durch Services oder "
            "Forms von der Darstellung getrennt. Die zentralen Workflows werden ueber serverseitige Views "
            "und Templates abgebildet, damit die erste Ausbaustufe einfach betreibbar und gut testbar bleibt."
        ),
        "architecture_decisions": [
            {
                "id": "ADR-001",
                "decision": "Das Artefakt wird als Django-Applikation umgesetzt.",
                "rationale": "Django liefert ORM, Admin, Templates, Migrationen und Testunterstuetzung als produktive Basis.",
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
            "Startpunkt ist ein containerisierbares Django-Deployment mit einem Webprozess und einer "
            "relationalen Datenbank. Lokale Entwicklung, Test und Produktion verwenden getrennte "
            "Konfigurationen, aber denselben fachlichen Codepfad. Statische Dateien und Migrationslaeufe "
            "werden im Deployment explizit beruecksichtigt."
        ),
        "data_view": (
            f"Zentrale Django-Models werden aus den Kernobjekten abgeleitet: {', '.join(entity_names)}. "
            "Fachliche Statuswerte und Pflichtfelder werden direkt am Modell oder in dedizierten "
            "Validierungsfunktionen abgesichert. Beziehungen werden nur eingefuehrt, wenn sie aus der "
            "Requirement-Analyse ableitbar sind."
        ),
        "security_view": _analysis_security_view(analysis, role_names),
        "test_strategy": (
            "Automatisierte Tests umfassen Model- und Service-Tests fuer Kernobjekte sowie Medium-Tests "
            "fuer die zentralen Workflows. Rollen- oder Berechtigungstests werden nur erzeugt, wenn die "
            "Requirement-Analyse Rollen mit unterschiedlichen Rechten vorgibt. Export- oder API-Tests "
            "werden nur fuer Schnittstellen im aktuellen Scope erstellt."
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
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    known_fields = set(schema.get("properties", {}).keys())
    merged = dict(base_sheet)
    normalized_candidate = _normalize_candidate_sheet(candidate_sheet)
    normalized_analysis = analysis or {}

    for field in known_fields:
        value = normalized_candidate.get(field)

        if value not in (None, "", [], {}):
            merged[field] = value

    merged["schema_version"] = "1.0.0"
    merged = _filter_sheet_against_scope(merged, normalized_analysis)
    for field in (
        "architecture_drivers",
        "quality_goals",
        "architecture_decisions",
        "building_blocks",
        "runtime_scenarios",
        "acceptance_criteria",
        "risks",
    ):
        if merged.get(field) in (None, "", [], {}):
            merged[field] = base_sheet.get(field)
    merged["arc42"] = _build_arc42_document(merged, normalized_analysis)
    return merged


def _normalize_candidate_sheet(candidate_sheet: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "artifact_name": _string_value(candidate_sheet.get("artifact_name")),
        "artifact_type": _normalize_artifact_type(candidate_sheet.get("artifact_type")),
        "input_summary": _string_value(candidate_sheet.get("input_summary")),
        "business_goal": _string_value(candidate_sheet.get("business_goal")),
        "stakeholders": _list_of_named_items(candidate_sheet.get("stakeholders")),
        "architecture_drivers": _list_of_architecture_drivers(candidate_sheet.get("architecture_drivers")),
        "quality_goals": _list_of_quality_goals(candidate_sheet.get("quality_goals")),
        "constraints": _list_of_text_items(candidate_sheet.get("constraints")),
        "context": _normalize_context(candidate_sheet.get("context")),
        "solution_strategy": _string_value(candidate_sheet.get("solution_strategy")),
        "architecture_decisions": _list_of_architecture_decisions(candidate_sheet.get("architecture_decisions")),
        "building_blocks": _list_of_building_blocks(candidate_sheet.get("building_blocks")),
        "runtime_scenarios": _list_of_runtime_scenarios(candidate_sheet.get("runtime_scenarios")),
        "deployment_view": _string_value(candidate_sheet.get("deployment_view")),
        "data_view": _string_value(candidate_sheet.get("data_view")),
        "security_view": _string_value(candidate_sheet.get("security_view")),
        "test_strategy": _string_value(candidate_sheet.get("test_strategy")),
        "acceptance_criteria": _list_of_acceptance_criteria(candidate_sheet.get("acceptance_criteria")),
        "risks": _list_of_risk_items(candidate_sheet.get("risks")),
        "open_questions": _list_of_text_items(candidate_sheet.get("open_questions")),
        "assumptions": _list_of_text_items(candidate_sheet.get("assumptions")),
        "readiness": _normalize_readiness(candidate_sheet.get("readiness")),
    }


def _filter_sheet_against_scope(sheet: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    forbidden_terms = _scope_forbidden_terms(analysis)
    if not forbidden_terms:
        return sheet

    filtered = dict(sheet)
    for field in (
        "architecture_drivers",
        "quality_goals",
        "architecture_decisions",
        "building_blocks",
        "runtime_scenarios",
        "acceptance_criteria",
        "risks",
        "open_questions",
        "assumptions",
    ):
        value = filtered.get(field)
        if isinstance(value, list):
            kept = [
                item
                for item in value
                if not _contains_scope_forbidden_term(item, forbidden_terms)
            ]
            filtered[field] = kept

    context = filtered.get("context")
    if isinstance(context, dict):
        filtered["context"] = {
            key: [
                item
                for item in value
                if not _contains_scope_forbidden_term(item, forbidden_terms)
            ]
            if isinstance(value, list)
            else value
            for key, value in context.items()
        }

    for field in ("solution_strategy", "deployment_view", "data_view", "test_strategy"):
        if _contains_scope_forbidden_term(filtered.get(field), forbidden_terms):
            filtered[field] = (
                "Dieser Abschnitt wurde auf den belegten Scope reduziert. "
                "Nicht belegte oder ausgeschlossene Funktionen werden nicht als Architekturinhalt verwendet."
            )

    return filtered


def _scope_forbidden_terms(analysis: Dict[str, Any]) -> List[str]:
    scope_text = _scope_text(analysis)
    explicit_terms = list(analysis.get("explicitly_excluded_terms", []))
    not_evidenced_terms = [
        item["description"]
        for item in _list_of_text_items(analysis.get("not_evidenced"))
    ]
    out_of_scope_terms = [
        item["description"]
        for item in _list_of_text_items(analysis.get("out_of_scope"))
    ]
    terms = []

    for term in explicit_terms + not_evidenced_terms + out_of_scope_terms:
        normalized = _string_value(term).lower()
        if not normalized:
            continue
        if normalized in {"login", "authentifizierung"}:
            continue
        if normalized in scope_text and normalized not in json.dumps(
            analysis.get("out_of_scope", []), ensure_ascii=False
        ).lower():
            continue
        terms.append(normalized)

    return _dedupe_strings(terms)


def _contains_scope_forbidden_term(value: Any, forbidden_terms: List[str]) -> bool:
    text = json.dumps(value, ensure_ascii=False).lower() if isinstance(value, (dict, list)) else _string_value(value).lower()
    if not text:
        return False
    return any(term and term in text for term in forbidden_terms)


def _build_arc42_document(sheet: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    non_goals = _list_of_text_items(analysis.get("out_of_scope")) + [
        {"description": f"Nicht belegt und daher nicht Teil der Architektur: {item['description']}"}
        for item in _list_of_text_items(analysis.get("not_evidenced"))
    ]
    if not non_goals:
        non_goals = [{"description": "Nicht explizit beschriebene Funktionen bleiben ausserhalb des aktuellen Scopes."}]

    crosscutting_concepts = [
        {
            "name": "Validierung und fachliche Regeln",
            "description": (
                "Eingaben und Statuswechsel werden an den Django-Formularen, Models oder Services validiert. "
                "Nicht belegte Funktionen werden nicht als implizite Erweiterung modelliert."
            ),
        },
        {
            "name": "Testbarkeit",
            "description": (
                "Kernlogik, Validierung und zentrale Workflows werden in Unit- und Medium-Tests abgesichert. "
                "Die Teststrategie folgt den explizit genannten Qualitaetszielen."
            ),
        },
    ]
    if sheet.get("security_view"):
        crosscutting_concepts.append(
            {
                "name": "Sicherheit und Betrieb",
                "description": sheet["security_view"],
            }
        )

    return {
        "introduction_and_goals": {
            "summary": sheet.get("business_goal") or sheet.get("input_summary") or "Ziel der Anwendung ist noch zu konkretisieren.",
            "goals": _list_of_text_items(sheet.get("business_goal")) or _list_of_text_items(analysis.get("core_facts")),
            "stakeholders": sheet.get("stakeholders") or [{"name": "Stakeholder", "description": "Noch zu konkretisieren."}],
            "quality_goals": sheet.get("quality_goals") or _analysis_quality_goals(analysis),
            "non_goals": non_goals,
        },
        "constraints": {
            "constraints": sheet.get("constraints") or [{"description": "Erster Fokus ist eine Django-Applikation."}],
            "assumptions": sheet.get("assumptions") or [],
            "open_questions": sheet.get("open_questions") or [],
        },
        "context_and_scope": {
            "business_context": sheet.get("context") or {
                "users": sheet.get("stakeholders") or [],
                "external_systems": [],
                "interfaces": [],
            },
            "technical_context": (sheet.get("context") or {}).get("interfaces", []),
            "in_scope": _list_of_text_items(analysis.get("in_scope")) or _list_of_text_items(sheet.get("business_goal")),
            "out_of_scope": _list_of_text_items(analysis.get("out_of_scope")),
            "not_evidenced": _list_of_text_items(analysis.get("not_evidenced")),
        },
        "solution_strategy": {
            "summary": sheet.get("solution_strategy") or "Die Loesungsstrategie wird aus den fachlichen Kernobjekten abgeleitet.",
            "key_ideas": _list_of_text_items(sheet.get("solution_strategy"))
            + [
                {"description": f"{block['name']}: {block['responsibility']}"}
                for block in sheet.get("building_blocks", [])
            ],
        },
        "building_block_view": {
            "summary": "Die Bausteinsicht beschreibt die fachlichen Django-Komponenten und ihre Verantwortlichkeiten.",
            "building_blocks": sheet.get("building_blocks") or _analysis_building_blocks(analysis),
        },
        "runtime_view": {
            "summary": (
                "Die Laufzeitsicht dokumentiert nur architekturrelevante Szenarien aus den beschriebenen "
                "Kernworkflows, nicht jeden moeglichen Bedienpfad."
            ),
            "scenarios": sheet.get("runtime_scenarios") or _analysis_runtime_scenarios(analysis),
        },
        "deployment_view": {
            "summary": sheet.get("deployment_view") or "Deployment wird fuer lokale Tests und spaetere Produktion containerisierbar gehalten.",
            "nodes": [
                {
                    "name": "Django Webprozess",
                    "description": "Fuehrt Views, Templates, Forms, Services und ORM-Zugriffe aus.",
                },
                {
                    "name": "Relationale Datenbank",
                    "description": "Persistiert die fachlichen Kernobjekte der Anwendung.",
                },
            ],
            "assumptions": sheet.get("assumptions") or [],
        },
        "crosscutting_concepts": {
            "concepts": crosscutting_concepts,
        },
        "architecture_decisions": sheet.get("architecture_decisions") or [],
        "quality_requirements": {
            "quality_goals": sheet.get("quality_goals") or _analysis_quality_goals(analysis),
            "quality_scenarios": sheet.get("acceptance_criteria") or _analysis_acceptance_criteria(analysis),
        },
        "risks_and_technical_debt": {
            "risks": sheet.get("risks") or _list_of_risk_items(analysis.get("risks")),
            "technical_debt": [
                {"description": "Offene Fragen muessen vor Workorder-Erzeugung geklaert oder explizit als Annahme akzeptiert werden."}
            ]
            if sheet.get("open_questions")
            else [],
        },
        "glossary": _build_arc42_glossary(sheet, analysis),
    }


def _build_arc42_glossary(sheet: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    glossary = []
    for entity in _list_of_named_items(analysis.get("core_entities")):
        glossary.append({"term": entity["name"], "definition": entity["description"]})
    for block in sheet.get("building_blocks", []):
        if not any(item["term"].lower() == block["name"].lower() for item in glossary):
            glossary.append({"term": block["name"], "definition": block["responsibility"]})
    return glossary or [{"term": sheet.get("artifact_name", "Anwendung"), "definition": sheet.get("business_goal", "Django-Anwendung im aktuellen Scope.")}]


def _normalize_artifact_type(value: Any) -> str:
    artifact_type = _string_value(value).lower()
    if artifact_type in {"django-application", "django-service", "django-app-module", "unknown"}:
        return artifact_type
    if "service" in artifact_type:
        return "django-service"
    if "module" in artifact_type or "modul" in artifact_type:
        return "django-app-module"
    if artifact_type:
        return "django-application"
    return ""


def _normalize_context(value: Any) -> Dict[str, List[Dict[str, str]]]:
    if not isinstance(value, dict):
        return {}

    external_systems = value.get("external_systems")
    if isinstance(external_systems, dict):
        external_systems = (
            _list_value(external_systems.get("systems"))
            + _list_value(external_systems.get("current_interfaces"))
            + _list_value(external_systems.get("future_interfaces"))
        )

    interfaces = value.get("interfaces")
    if not interfaces:
        interfaces = value.get("current_interfaces")

    context = {
        "users": _list_of_named_items(value.get("users") or value.get("actors")),
        "external_systems": _list_of_named_items(external_systems),
        "interfaces": _list_of_interface_items(interfaces),
    }
    if not any(context.values()):
        return {}
    return context


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
            name = _string_value(
                entry.get("name")
                or entry.get("title")
                or entry.get("role")
                or entry.get("goal")
                or entry.get("driver")
                or entry.get("type")
            )
            description = _string_value(
                entry.get("description")
                or entry.get("scenario")
                or entry.get("responsibility")
                or entry.get("target")
                or entry.get("impact")
            )
        else:
            name = _string_value(entry)
            description = ""

        if name:
            items.append({"name": name, "description": description or name})

    return items


def _list_of_architecture_drivers(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            name = _string_value(entry.get("name") or entry.get("driver") or entry.get("title"))
            description = _string_value(entry.get("description") or entry.get("scenario") or entry.get("reason"))
            impact = _string_value(entry.get("impact") or entry.get("consequence") or entry.get("target"))
        else:
            name = _string_value(entry)
            description = name
            impact = "Dieser Treiber muss bei Bausteinschnitt, Datenmodell und Tests beruecksichtigt werden."

        if name:
            items.append(
                {
                    "name": name,
                    "description": description or impact or name,
                    "impact": impact
                    or "Dieser Treiber muss bei Bausteinschnitt, Datenmodell und Tests beruecksichtigt werden.",
                }
            )

    return items


def _list_of_quality_goals(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            name = _string_value(entry.get("name") or entry.get("goal") or entry.get("title"))
            scenario = _string_value(entry.get("scenario") or entry.get("description") or entry.get("target"))
            priority = _normalize_priority(entry.get("priority"))
        else:
            name = _string_value(entry)
            scenario = name
            priority = "high"

        if name:
            items.append({"name": name, "scenario": scenario or name, "priority": priority})

    return items


def _normalize_priority(value: Any) -> str:
    priority = _string_value(value).lower()
    if priority in {"high", "hoch"}:
        return "high"
    if priority in {"medium", "mittel"}:
        return "medium"
    if priority in {"low", "niedrig"}:
        return "low"
    return "high"


def _list_of_text_items(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        description = _string_value(entry)
        if description:
            items.append({"description": description})

    return items


def _list_of_structured_items(value: Any) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            normalized = {
                str(key): _json_compatible(item_value)
                for key, item_value in entry.items()
                if _json_compatible(item_value) not in (None, "", [], {})
            }
            if normalized:
                items.append(normalized)
        else:
            description = _string_value(entry)
            if description:
                items.append({"description": description})

    return items


def _list_of_domain_entities(value: Any) -> List[Dict[str, Any]]:
    entities = []
    for item in _list_of_structured_items(value):
        name = _string_value(item.get("name") or item.get("entity") or item.get("title"))
        description = _string_value(item.get("description")) or name
        if name:
            entity = dict(item)
            entity["name"] = name
            entity["description"] = description
            entity["attributes"] = _list_of_structured_items(entity.get("attributes"))
            entities.append(entity)
    return entities


def _json_compatible(value: Any) -> Any:
    if value in (None, ""):
        return value
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_compatible(item) for item in value if _json_compatible(item) not in (None, "")]
    if isinstance(value, dict):
        return {
            str(key): _json_compatible(item_value)
            for key, item_value in value.items()
            if _json_compatible(item_value) not in (None, "")
        }
    return str(value)


def _list_of_architecture_decisions(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for index, entry in enumerate(_list_value(value), start=1):
        if isinstance(entry, dict):
            decision = _string_value(entry.get("decision") or entry.get("name") or entry.get("description"))
            rationale = _string_value(entry.get("rationale") or entry.get("reason") or entry.get("impact"))
            status = _string_value(entry.get("status")).lower()
        else:
            decision = _string_value(entry)
            rationale = ""
            status = "proposed"

        if status not in {"proposed", "accepted", "rejected", "superseded"}:
            status = "proposed"
        if decision:
            items.append(
                {
                    "id": (_string_value(entry.get("id")) if isinstance(entry, dict) else "") or f"ADR-{index:03d}",
                    "decision": decision,
                    "rationale": rationale or "Die Entscheidung ist aus der Requirement-Analyse abzuleiten.",
                    "status": status,
                }
            )

    return items


def _list_of_building_blocks(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            name = _string_value(entry.get("name") or entry.get("title"))
            responsibility = _string_value(entry.get("responsibility") or entry.get("description"))
            django_mapping = _string_value(entry.get("django_mapping") or entry.get("mapping"))
        else:
            name = _string_value(entry)
            responsibility = name
            django_mapping = ""

        if name:
            items.append(
                {
                    "name": name,
                    "responsibility": responsibility or name,
                    "django_mapping": django_mapping or "Django-App, Service oder Modul mit passenden Tests.",
                }
            )

    return items


def _list_of_runtime_scenarios(value: Any) -> List[Dict[str, List[str]]]:
    items: List[Dict[str, List[str]]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            name = _string_value(entry.get("name") or entry.get("title"))
            steps = [_string_value(step) for step in _list_value(entry.get("steps")) if _string_value(step)]
            description = _string_value(entry.get("description"))
        else:
            name = _string_value(entry)
            steps = []
            description = ""

        if name:
            if description and description not in steps:
                steps.insert(0, description)
            items.append({"name": name, "steps": steps or [name]})

    return items


def _list_of_acceptance_criteria(value: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    for entry in _list_value(value):
        if isinstance(entry, dict):
            description = _string_value(entry.get("description") or entry.get("criterion") or entry.get("name"))
            verification = _string_value(entry.get("verification") or entry.get("test") or entry.get("target"))
        else:
            description = _string_value(entry)
            verification = ""

        if description:
            items.append(
                {
                    "description": description,
                    "verification": verification or "Automatisiert oder im Review pruefen.",
                }
            )

    return items


def _normalize_readiness(value: Any) -> Dict[str, str]:
    if isinstance(value, dict):
        status = _string_value(value.get("status"))
        summary = _string_value(value.get("summary") or value.get("description"))
    else:
        status = _string_value(value)
        summary = ""

    if status not in {"draft", "needs-clarification", "ready-for-review", "approved"}:
        status = "ready-for-review" if status else ""
    if not status:
        return {}
    return {"status": status, "summary": summary or "Das Sheet wurde fuer den naechsten Review-Schritt vorbereitet."}


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
            "name": "Django-Projektgrundlage",
            "responsibility": "Settings, URL-Routing, ASGI/WSGI, Deployment-Konfiguration und Umgebungsprofile.",
            "django_mapping": "Django-Projektpaket mit Settings-Modulen, zentraler urls.py und Deployment-Einstiegspunkten.",
        }
    ]

    for entity in analysis["core_entities"]:
        slug = _slug_from_name(entity["name"])
        blocks.append(
            {
                "name": entity["name"],
                "responsibility": entity["description"],
                "django_mapping": f"Django-App oder Modul `{slug}` mit Models, Services, Forms/Views und Tests.",
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
                    "Ein Nutzer startet den Workflow in der Django-Weboberflaeche.",
                    workflow["description"],
                    "Das System validiert Eingaben und fachliche Regeln.",
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
