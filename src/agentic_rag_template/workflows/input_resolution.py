"""Resolve workflow step inputs from configured mappings."""

from typing import Any, Dict

from agentic_rag_template.workflows.models import WorkflowRun


class InputResolutionError(RuntimeError):
    """Raised when a step input mapping cannot be resolved."""


class InputResolver:
    def resolve(self, mapping: Dict[str, Any], workflow_run: WorkflowRun) -> Dict[str, Any]:
        return {
            target_key: self._resolve_source(source, workflow_run)
            for target_key, source in mapping.items()
        }

    def _resolve_source(self, source: Any, workflow_run: WorkflowRun) -> Any:
        if not isinstance(source, dict):
            return source
        source_type = source.get("source")
        if source_type == "workflow_input":
            return _get_path(workflow_run.initial_input, source.get("path", ""))
        if source_type == "step_output":
            step_key = source.get("step_key", "")
            step_run = next((item for item in workflow_run.step_runs if item.workflow_step.step_key == step_key), None)
            if step_run is None:
                raise InputResolutionError(f"step output not found: {step_key}")
            return _get_path(_step_run_payload(step_run), source.get("path", "validated_output"))
        if source_type == "artifact":
            artifact_key = source.get("artifact_key", "")
            artifact = next((item for item in workflow_run.artifacts if item.artifact_key == artifact_key), None)
            if artifact is None:
                raise InputResolutionError(f"artifact not found: {artifact_key}")
            return _get_path({"content": artifact.content, "artifact": artifact}, source.get("path", "content"))
        if source_type == "static":
            return source.get("value")
        if source_type == "run_metadata":
            return _get_path({"id": workflow_run.id, "status": workflow_run.status}, source.get("path", ""))
        raise InputResolutionError(f"unsupported input source: {source_type}")


def _step_run_payload(step_run: Any) -> Dict[str, Any]:
    return {
        "resolved_input": step_run.resolved_input,
        "raw_output": step_run.raw_output,
        "parsed_output": step_run.parsed_output,
        "validated_output": step_run.validated_output,
        "validation_result": step_run.validation_result,
    }


def _get_path(value: Any, path: str) -> Any:
    current = value
    for part in str(path).split("."):
        if not part:
            continue
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current

