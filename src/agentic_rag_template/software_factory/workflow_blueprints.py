"""Load Software Factory workflow blueprints from YAML configuration."""

from pathlib import Path
from copy import deepcopy
from typing import Any, Dict, List

import yaml

from agentic_rag_template.applications import ApplicationInstance
from agentic_rag_template.workflows.models import (
    STEP_TYPE_AGENT,
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    AgentDefinition,
    AgentVersion,
    Workflow,
    WorkflowStep,
    WorkflowVersion,
)


class WorkflowBlueprintError(RuntimeError):
    """Raised when a workflow blueprint cannot be loaded."""


def workflow_blueprint_path(application: ApplicationInstance, workflow_id: str) -> Path:
    """Return the YAML path for one configured workflow blueprint."""
    return application.template_dir / "workflows" / f"{workflow_id}.yaml"


def step_template_path(application: ApplicationInstance, template_id: str) -> Path:
    """Return the YAML path for one configured step template."""
    return application.template_dir / "step_templates" / f"{template_id}.yaml"


def llm_profiles_path(application: ApplicationInstance) -> Path:
    """Return the YAML path for configured LLM profiles."""
    return application.template_dir / "llm_profiles.yaml"


def list_llm_profiles(application: ApplicationInstance) -> List[Dict[str, Any]]:
    """Load configured LLM profiles for an application."""
    path = llm_profiles_path(application)
    if not path.is_file():
        return []

    payload = _load_yaml(path)
    profiles = payload.get("profiles", [])
    if not isinstance(profiles, list):
        raise WorkflowBlueprintError("LLM profiles must be a list")

    result = []
    for profile in profiles:
        if not isinstance(profile, dict):
            raise WorkflowBlueprintError("LLM profile must be an object")
        profile_id = str(profile.get("id", "")).strip()
        if not profile_id:
            raise WorkflowBlueprintError("LLM profile id is required")
        result.append(_llm_profile_to_dict(profile))
    return result


def load_llm_profiles_config(application: ApplicationInstance) -> Dict[str, Any]:
    """Load raw LLM profile configuration."""
    path = llm_profiles_path(application)
    if not path.is_file():
        return {"profiles": []}
    return _load_yaml(path)


def save_llm_profiles_config(application: ApplicationInstance, config: Dict[str, Any]) -> None:
    """Persist raw LLM profile configuration."""
    try:
        llm_profiles_path(application).write_text(
            yaml.safe_dump(config, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
    except OSError as error:
        raise WorkflowBlueprintError(f"LLM profiles cannot be saved: {error}") from error


def upsert_llm_profile(application: ApplicationInstance, profile_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update one LLM profile."""
    config = load_llm_profiles_config(application)
    profiles = config.get("profiles", [])
    if not isinstance(profiles, list):
        raise WorkflowBlueprintError("LLM profiles must be a list")

    existing_index = next(
        (index for index, profile in enumerate(profiles) if isinstance(profile, dict) and profile.get("id") == profile_id),
        -1,
    )
    existing = dict(profiles[existing_index]) if existing_index >= 0 else {"id": profile_id}
    updated = _llm_profile_from_payload(existing, profile_id, payload)

    if existing_index >= 0:
        profiles[existing_index] = updated
    else:
        profiles.append(updated)
    config["profiles"] = profiles
    save_llm_profiles_config(application, config)
    return _llm_profile_to_dict(updated)


def delete_llm_profile(application: ApplicationInstance, profile_id: str) -> None:
    """Delete one LLM profile."""
    config = load_llm_profiles_config(application)
    profiles = config.get("profiles", [])
    if not isinstance(profiles, list):
        raise WorkflowBlueprintError("LLM profiles must be a list")

    remaining = [
        profile for profile in profiles if not (isinstance(profile, dict) and str(profile.get("id", "")) == profile_id)
    ]
    if len(remaining) == len(profiles):
        raise WorkflowBlueprintError(f"LLM profile is missing: {profile_id}")
    config["profiles"] = remaining
    save_llm_profiles_config(application, config)


def find_llm_profile(application: ApplicationInstance, profile_id: str) -> Dict[str, Any]:
    """Find one configured LLM profile."""
    for profile in list_llm_profiles(application):
        if profile["id"] == profile_id:
            return profile
    raise WorkflowBlueprintError(f"LLM profile is missing: {profile_id}")


def list_step_templates(application: ApplicationInstance) -> List[Dict[str, Any]]:
    """Load all configured step templates for an application."""
    template_dir = application.template_dir / "step_templates"
    templates = []

    if not template_dir.is_dir():
        return templates

    for path in sorted(template_dir.glob("*.yaml")):
        template = _load_yaml(path)
        template_id = str(template.get("id", path.stem)).strip()
        if not template_id:
            raise WorkflowBlueprintError(f"Step template id is missing: {path}")
        templates.append(
            {
                "id": template_id,
                "name": str(template.get("name", template_id)),
                "category": str(template.get("category", template.get("step_type", "TASK"))),
                "description": str(template.get("description", "")),
                "step_type": str(template.get("step_type", "TASK")),
                "defaults": dict(template.get("defaults", {})),
            }
        )

    return templates


def load_step_template(application: ApplicationInstance, template_id: str) -> Dict[str, Any]:
    """Load one configured step template."""
    template = _load_yaml(step_template_path(application, template_id))
    template["id"] = str(template.get("id", template_id))
    return template


def load_software_factory_workflow_config(
    application: ApplicationInstance,
    workflow_id: str,
) -> Dict[str, Any]:
    """Load the raw YAML config for one workflow blueprint."""
    return _load_yaml(workflow_blueprint_path(application, workflow_id))


def save_software_factory_workflow_config(
    application: ApplicationInstance,
    workflow_id: str,
    workflow_config: Dict[str, Any],
) -> None:
    """Persist a raw workflow blueprint config."""
    workflow_dir = application.template_dir / "workflows"
    try:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_blueprint_path(application, workflow_id).write_text(
            yaml.safe_dump(workflow_config, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
    except OSError as error:
        raise WorkflowBlueprintError(f"Workflow blueprint cannot be saved: {error}") from error


def delete_software_factory_workflow_config(
    application: ApplicationInstance,
    workflow_id: str,
) -> None:
    """Delete one workflow blueprint config."""
    try:
        workflow_blueprint_path(application, workflow_id).unlink()
    except OSError as error:
        raise WorkflowBlueprintError(f"Workflow blueprint cannot be deleted: {error}") from error


def new_workflow_config(workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a draft workflow config from an admin API payload."""
    return _workflow_config_from_payload(
        {
            "name": workflow_id.replace("_", " ").replace("-", " ").title(),
            "slug": workflow_id.replace("_", "-"),
            "description": "",
            "workflow_status": "active",
            "status": VERSION_STATUS_DRAFT,
            "version": 1,
            "change_summary": "Initial draft workflow.",
            "created_by": "workflow-admin-ui",
            "final_output_key": "",
            "steps": [],
        },
        payload,
    )


def update_workflow_config(existing: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing draft workflow config from an admin API payload."""
    return _workflow_config_from_payload(dict(existing), payload)


def add_step_from_template(
    workflow_config: Dict[str, Any],
    template: Dict[str, Any],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Append a configured workflow step based on a step template."""
    workflow = dict(workflow_config)
    existing_steps = list(workflow.get("steps", []))
    if not all(isinstance(step, dict) for step in existing_steps):
        raise WorkflowBlueprintError("Workflow steps must be objects")

    defaults = dict(template.get("defaults", {}))
    step = _step_config_from_template(defaults, template, payload, existing_steps)
    existing_steps.append(step)
    workflow["steps"] = _normalize_step_positions(existing_steps)
    return workflow


def delete_step_from_workflow(workflow_config: Dict[str, Any], step_key: str) -> Dict[str, Any]:
    """Remove one workflow step if no other step references it."""
    workflow = dict(workflow_config)
    existing_steps = list(workflow.get("steps", []))
    if not all(isinstance(step, dict) for step in existing_steps):
        raise WorkflowBlueprintError("Workflow steps must be objects")

    if not any(str(step.get("step_key", "")) == step_key for step in existing_steps):
        raise WorkflowBlueprintError(f"Workflow step is missing: {step_key}")

    referencing_steps = _steps_referencing_step(existing_steps, step_key)
    if referencing_steps:
        joined = ", ".join(referencing_steps)
        raise WorkflowBlueprintError(f"Workflow step is still referenced by: {joined}")

    workflow["steps"] = _normalize_step_positions(
        [step for step in existing_steps if str(step.get("step_key", "")) != step_key]
    )
    return workflow


def update_step_in_workflow(
    workflow_config: Dict[str, Any],
    step_key: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Update one workflow step in a draft workflow config."""
    workflow = dict(workflow_config)
    existing_steps = list(workflow.get("steps", []))
    if not all(isinstance(step, dict) for step in existing_steps):
        raise WorkflowBlueprintError("Workflow steps must be objects")

    target_index = next(
        (index for index, step in enumerate(existing_steps) if str(step.get("step_key", "")) == step_key),
        -1,
    )
    if target_index < 0:
        raise WorkflowBlueprintError(f"Workflow step is missing: {step_key}")

    updated_step = _updated_step_config(existing_steps[target_index], payload)
    updated_step_key = str(updated_step.get("step_key", ""))
    if updated_step_key != step_key:
        if any(str(step.get("step_key", "")) == updated_step_key for step in existing_steps):
            raise WorkflowBlueprintError(f"Workflow step already exists: {updated_step_key}")
        referencing_steps = _steps_referencing_step(existing_steps, step_key)
        if referencing_steps:
            joined = ", ".join(referencing_steps)
            raise WorkflowBlueprintError(f"Workflow step key is still referenced by: {joined}")

    existing_steps[target_index] = updated_step
    workflow["steps"] = _normalize_step_positions(existing_steps)
    return workflow


def load_software_factory_workflow(
    application: ApplicationInstance,
    workflow_id: str = "architecture_sheet",
) -> WorkflowVersion:
    """Load one configured Software Factory workflow as a WorkflowVersion."""
    workflow_config = load_software_factory_workflow_config(application, workflow_id)
    workflow = Workflow(
        name=str(workflow_config.get("name", workflow_id)),
        slug=str(workflow_config.get("slug", workflow_id.replace("_", "-"))),
        description=str(workflow_config.get("description", "")),
        status=str(workflow_config.get("workflow_status", "active")),
        created_by=str(workflow_config.get("created_by", "system")),
    )
    workflow_version = WorkflowVersion(
        workflow=workflow,
        version_number=int(workflow_config.get("version", 1)),
        status=str(workflow_config.get("status", VERSION_STATUS_PUBLISHED)),
        change_summary=str(workflow_config.get("change_summary", "Configured workflow blueprint.")),
        created_by=str(workflow_config.get("created_by", "system")),
        final_output_key=str(workflow_config.get("final_output_key", "")),
    )

    for step_config in workflow_config.get("steps", []):
        if not isinstance(step_config, dict):
            raise WorkflowBlueprintError("Workflow step config must be an object.")
        workflow_version.steps.append(_workflow_step_from_config(application, workflow_version, step_config))

    return workflow_version


def _workflow_step_from_config(
    application: ApplicationInstance,
    workflow_version: WorkflowVersion,
    config: Dict[str, Any],
) -> WorkflowStep:
    step_type = str(config.get("step_type", "TASK"))
    agent_version = None
    agent_id = ""
    if step_type == STEP_TYPE_AGENT:
        agent_id = str(config.get("agent", ""))
        if not agent_id:
            raise WorkflowBlueprintError(f"{config.get('step_key', '<unknown>')}: agent is required")
        agent_version = _agent_version_from_yaml(application.template_dir / "agents" / f"{agent_id}.yaml")

    return WorkflowStep(
        workflow_version=workflow_version,
        name=str(config.get("name", "")),
        step_key=str(config.get("step_key", "")),
        step_type=step_type,
        position=int(config.get("position", 0)),
        description=str(config.get("description", "")),
        is_enabled=bool(config.get("is_enabled", True)),
        agent_id=agent_id,
        agent_version=agent_version,
        task_definition=dict(config.get("task", {})),
        input_mapping=dict(config.get("input_mapping", {})),
        output_key=str(config.get("output_key", "")),
        condition_expression=dict(config.get("condition_expression", {})),
        timeout_seconds=int(config.get("timeout_seconds", 300) or 300),
        retry_policy=dict(config.get("retry_policy", {})),
        failure_strategy=str(config.get("failure_strategy", "STOP_WORKFLOW")),
        configuration=dict(config.get("configuration", {})),
    )


def _agent_version_from_yaml(path: Path) -> AgentVersion:
    config = _load_yaml(path)
    agent_id = str(config.get("id", path.stem))
    prompt = config.get("prompt", {}) if isinstance(config.get("prompt"), dict) else {}
    output_schema = config.get("json_schema") if isinstance(config.get("json_schema"), dict) else {}
    output_schema = output_schema or config.get("output_schema", {})
    if not isinstance(output_schema, dict):
        output_schema = {}
    return AgentVersion(
        agent=AgentDefinition(
            name=str(config.get("name", agent_id)),
            slug=agent_id.replace("_", "-"),
            description=str(config.get("description", "")),
            status="active",
            created_by="system",
        ),
        version_number=int(config.get("version", 1)),
        status=str(config.get("status", VERSION_STATUS_PUBLISHED)),
        system_prompt=str(prompt.get("system", "")),
        user_prompt_template=str(prompt.get("user_template", "")),
        input_contract=dict(config.get("input_contract", {})),
        output_schema=output_schema,
        model_configuration=dict(config.get("model_configuration", {})),
        retry_configuration=dict(config.get("retry_configuration", {})),
        timeout_seconds=int(config.get("timeout_seconds", 300) or 300),
        created_by="system",
        validators=list(config.get("validators", [])),
        method_packs=list(config.get("method_packs", [])),
    )


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise WorkflowBlueprintError(f"Workflow blueprint file is missing: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise WorkflowBlueprintError(f"YAML blueprint must be an object: {path}")
    return payload


def _step_config_from_template(
    defaults: Dict[str, Any],
    template: Dict[str, Any],
    payload: Dict[str, Any],
    existing_steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    step_type = str(payload.get("step_type") or template.get("step_type") or "TASK")
    step_key = str(payload.get("step_key") or "").strip()
    if not step_key:
        step_key = _next_step_key(str(defaults.get("step_key_prefix") or template.get("id") or "step"), existing_steps)

    if any(str(step.get("step_key", "")) == step_key for step in existing_steps):
        raise WorkflowBlueprintError(f"Workflow step already exists: {step_key}")

    step: Dict[str, Any] = {
        "step_key": step_key,
        "name": str(payload.get("name") or defaults.get("name") or template.get("name") or step_key),
        "step_type": step_type,
        "position": int(payload.get("position") or len(existing_steps) + 1),
        "output_key": str(payload.get("output_key") or defaults.get("output_key") or step_key),
    }

    for field in ("description", "failure_strategy"):
        if field in payload or field in defaults:
            step[field] = str(payload.get(field) or defaults.get(field) or "")

    for field in ("task", "input_mapping", "condition_expression", "retry_policy", "configuration"):
        if field in payload:
            value = payload.get(field)
        else:
            value = deepcopy(defaults.get(field, {}))
        if value:
            if not isinstance(value, dict):
                raise WorkflowBlueprintError(f"{field} must be an object")
            step[field] = value

    if "timeout_seconds" in payload or "timeout_seconds" in defaults:
        step["timeout_seconds"] = int(payload.get("timeout_seconds") or defaults.get("timeout_seconds") or 300)

    if step_type == STEP_TYPE_AGENT:
        agent = str(payload.get("agent") or defaults.get("agent") or "").strip()
        if not agent:
            raise WorkflowBlueprintError("agent is required for AGENT steps")
        step["agent"] = agent

    return step


def _next_step_key(prefix: str, existing_steps: List[Dict[str, Any]]) -> str:
    existing_keys = {str(step.get("step_key", "")) for step in existing_steps}
    normalized_prefix = prefix.strip().replace("-", "_") or "step"
    if normalized_prefix not in existing_keys:
        return normalized_prefix

    index = 2
    while f"{normalized_prefix}_{index}" in existing_keys:
        index += 1
    return f"{normalized_prefix}_{index}"


def _normalize_step_positions(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered = sorted(steps, key=lambda step: int(step.get("position", 0) or 0))
    normalized = []
    for index, step in enumerate(ordered, start=1):
        updated = dict(step)
        updated["position"] = index
        normalized.append(updated)
    return normalized


def _steps_referencing_step(steps: List[Dict[str, Any]], step_key: str) -> List[str]:
    referencing_steps = []
    for step in steps:
        current_step_key = str(step.get("step_key", ""))
        if current_step_key == step_key:
            continue
        input_mapping = step.get("input_mapping", {})
        if isinstance(input_mapping, dict) and _mapping_references_step(input_mapping, step_key):
            referencing_steps.append(current_step_key or "<unknown>")
    return referencing_steps


def _mapping_references_step(mapping: Dict[str, Any], step_key: str) -> bool:
    for value in mapping.values():
        if not isinstance(value, dict):
            continue
        if value.get("source") == "step_output" and value.get("step_key") == step_key:
            return True
    return False


def _updated_step_config(existing: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(existing)

    for field in ("step_key", "name", "step_type", "output_key", "description", "failure_strategy", "agent"):
        if field in payload:
            value = str(payload.get(field, "")).strip()
            if value:
                updated[field] = value
            elif field in {"description", "failure_strategy", "agent"}:
                updated.pop(field, None)

    if "position" in payload:
        updated["position"] = int(payload.get("position") or existing.get("position") or 0)

    if "timeout_seconds" in payload:
        updated["timeout_seconds"] = int(payload.get("timeout_seconds") or 300)

    for field in ("task", "input_mapping", "condition_expression", "retry_policy", "configuration"):
        if field not in payload:
            continue
        value = payload.get(field)
        if value in (None, ""):
            updated.pop(field, None)
            continue
        if not isinstance(value, dict):
            raise WorkflowBlueprintError(f"{field} must be an object")
        updated[field] = value

    if "llm_profile" in payload:
        configuration = dict(updated.get("configuration", {}))
        llm_profile = str(payload.get("llm_profile", "")).strip()
        if llm_profile:
            configuration["llm_profile"] = llm_profile
        else:
            configuration.pop("llm_profile", None)
        updated["configuration"] = configuration

    if "model_configuration" in payload:
        value = payload.get("model_configuration")
        if value in (None, ""):
            configuration = dict(updated.get("configuration", {}))
            configuration.pop("model_configuration", None)
            updated["configuration"] = configuration
        elif isinstance(value, dict):
            configuration = dict(updated.get("configuration", {}))
            configuration["model_configuration"] = value
            updated["configuration"] = configuration
        else:
            raise WorkflowBlueprintError("model_configuration must be an object")

    if str(updated.get("step_type", "")) == STEP_TYPE_AGENT and not str(updated.get("agent", "")).strip():
        raise WorkflowBlueprintError("agent is required for AGENT steps")

    return updated


def _llm_profile_to_dict(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(profile.get("id", "")).strip(),
        "name": str(profile.get("name", profile.get("id", ""))),
        "provider": str(profile.get("provider", "deterministic")),
        "model": str(profile.get("model", "")),
        "api_base_url": str(profile.get("api_base_url", "")),
        "api_key_configured": bool(profile.get("api_key", "")),
        "timeout_seconds": int(profile.get("timeout_seconds", 0) or 0),
        "max_tokens": int(profile.get("max_tokens", 0) or 0),
        "response_format": str(profile.get("response_format", "json")),
        "parameters": dict(profile.get("parameters", {})),
        "description": str(profile.get("description", "")),
    }


def _llm_profile_from_payload(existing: Dict[str, Any], profile_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(existing)
    updated["id"] = profile_id
    for field in (
        "name",
        "provider",
        "model",
        "api_base_url",
        "description",
        "response_format",
    ):
        if field in payload:
            updated[field] = str(payload.get(field, "")).strip()

    if "api_key" in payload and str(payload.get("api_key", "")).strip():
        updated["api_key"] = str(payload.get("api_key", "")).strip()

    if "timeout_seconds" in payload:
        updated["timeout_seconds"] = int(payload.get("timeout_seconds") or 0)
    if "max_tokens" in payload:
        updated["max_tokens"] = int(payload.get("max_tokens") or 0)
    if "parameters" in payload:
        parameters = payload.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise WorkflowBlueprintError("parameters must be an object")
        updated["parameters"] = parameters

    if not updated.get("provider"):
        raise WorkflowBlueprintError("provider is required")
    if not updated.get("model"):
        raise WorkflowBlueprintError("model is required")
    return updated


def _workflow_config_from_payload(existing: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    scalar_fields = {
        "name",
        "slug",
        "description",
        "workflow_status",
        "status",
        "change_summary",
        "created_by",
        "final_output_key",
    }

    for field in scalar_fields:
        if field in payload:
            existing[field] = str(payload.get(field, "")).strip()

    if "version" in payload:
        existing["version"] = int(payload.get("version") or 1)

    if "steps" in payload:
        steps = payload.get("steps")
        if not isinstance(steps, list):
            raise WorkflowBlueprintError("steps must be a list")
        existing["steps"] = steps

    return existing
