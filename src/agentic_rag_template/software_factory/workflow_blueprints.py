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
