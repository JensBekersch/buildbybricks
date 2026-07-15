"""Structural validation for workflow versions."""

from dataclasses import dataclass, field
from typing import List

from agentic_rag_template.workflows.models import (
    STEP_TYPE_AGENT,
    STEP_TYPE_TASK,
    VERSION_STATUS_PUBLISHED,
    WorkflowVersion,
)


@dataclass(frozen=True)
class WorkflowValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class WorkflowVersionValidator:
    def validate(self, workflow_version: WorkflowVersion) -> WorkflowValidationResult:
        errors: List[str] = []
        enabled_steps = [step for step in workflow_version.steps if step.is_enabled]
        if not enabled_steps:
            errors.append("workflow version must contain at least one enabled step")

        step_keys = [step.step_key for step in workflow_version.steps]
        if len(step_keys) != len(set(step_keys)):
            errors.append("step_key must be unique within a workflow version")

        positions = [step.position for step in workflow_version.steps]
        if len(positions) != len(set(positions)):
            errors.append("position must be unique within a workflow version")

        known_steps = {step.step_key: step for step in workflow_version.steps}
        for step in workflow_version.steps:
            if step.step_type == STEP_TYPE_AGENT:
                if step.agent_version is None:
                    errors.append(f"{step.step_key}: agent_version is required")
                elif step.agent_version.status != VERSION_STATUS_PUBLISHED:
                    errors.append(f"{step.step_key}: agent_version must be published")
            if step.step_type == STEP_TYPE_TASK and not step.task_definition.get("task_type"):
                errors.append(f"{step.step_key}: task_type is required")
            for source in step.input_mapping.values():
                if not isinstance(source, dict) or source.get("source") != "step_output":
                    continue
                referenced_key = source.get("step_key")
                referenced_step = known_steps.get(referenced_key)
                if referenced_step is None:
                    errors.append(f"{step.step_key}: referenced step does not exist: {referenced_key}")
                elif referenced_step.position >= step.position:
                    errors.append(f"{step.step_key}: input can only reference previous steps")

        output_keys = [step.output_key for step in workflow_version.steps if step.output_key]
        if len(output_keys) != len(set(output_keys)):
            errors.append("output_key must be unique within a workflow version")

        return WorkflowValidationResult(valid=not errors, errors=errors)

    def publish(self, workflow_version: WorkflowVersion) -> WorkflowValidationResult:
        result = self.validate(workflow_version)
        if result.valid:
            workflow_version.status = VERSION_STATUS_PUBLISHED
        return result

