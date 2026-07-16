"""Deterministic task registry for workflows."""

from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class TaskContext:
    input: Dict[str, Any]
    configuration: Dict[str, Any]


class WorkflowTask(Protocol):
    task_type: str

    def execute(self, context: TaskContext) -> Any:
        """Execute a deterministic workflow task."""


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: Dict[str, WorkflowTask] = {}

    def register(self, task: WorkflowTask) -> None:
        self._tasks[task.task_type] = task

    def get(self, task_type: str) -> WorkflowTask:
        if task_type not in self._tasks:
            raise KeyError(f"unknown task: {task_type}")
        return self._tasks[task_type]

    @classmethod
    def defaults(cls) -> "TaskRegistry":
        registry = cls()
        registry.register(EchoTask())
        registry.register(FieldMappingTask())
        registry.register(TextMergeTask())
        registry.register(ResultExtractionTask())
        return registry


class EchoTask:
    task_type = "echo"

    def execute(self, context: TaskContext) -> Any:
        return dict(context.input)


class FieldMappingTask:
    task_type = "field_mapping"

    def execute(self, context: TaskContext) -> Any:
        mapping = context.configuration.get("mapping", {})
        return {target: _get_path(context.input, source) for target, source in mapping.items()}


class TextMergeTask:
    task_type = "text_merge"

    def execute(self, context: TaskContext) -> Any:
        fields = context.configuration.get("fields", [])
        separator = context.configuration.get("separator", "\n")
        return separator.join(str(_get_path(context.input, field) or "") for field in fields)


class ResultExtractionTask:
    task_type = "result_extraction"

    def execute(self, context: TaskContext) -> Any:
        return _get_path(context.input, context.configuration.get("path", ""))


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

