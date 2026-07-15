"""Load Software Factory workflow blueprints from YAML configuration."""

from pathlib import Path
from typing import Any, Dict

import yaml

from agentic_rag_template.applications import ApplicationInstance
from agentic_rag_template.workflows.models import (
    STEP_TYPE_AGENT,
    VERSION_STATUS_PUBLISHED,
    AgentDefinition,
    AgentVersion,
    Workflow,
    WorkflowStep,
    WorkflowVersion,
)


class WorkflowBlueprintError(RuntimeError):
    """Raised when a workflow blueprint cannot be loaded."""


def load_software_factory_workflow(
    application: ApplicationInstance,
    workflow_id: str = "architecture_sheet",
) -> WorkflowVersion:
    """Load one configured Software Factory workflow as a WorkflowVersion."""
    workflow_config = _load_yaml(application.template_dir / "workflows" / f"{workflow_id}.yaml")
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
