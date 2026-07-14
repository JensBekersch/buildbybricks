"""Prometheus metrics derived from persisted runtime state."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import math
import re
from typing import Dict, Iterable, List, Optional, Tuple

from agentic_rag_template.config import Settings
from agentic_rag_template.software_factory.jobs import ArchitectureGenerationJob


def render_prometheus_metrics(settings: Settings, jobs: Iterable[ArchitectureGenerationJob]) -> str:
    """Render Software Factory metrics in Prometheus text exposition format."""
    job_list = list(jobs)
    lines: List[str] = [
        "# HELP buildbybricks_runtime_info Active non-secret runtime configuration.",
        "# TYPE buildbybricks_runtime_info gauge",
        _metric(
            "buildbybricks_runtime_info",
            1,
            {
                "llm_provider": settings.llm_provider,
                "llm_model": settings.llm_model,
                "architecture_mode": settings.architecture_generation_mode,
            },
        ),
        "# HELP buildbybricks_llm_timeout_seconds Configured LLM timeout.",
        "# TYPE buildbybricks_llm_timeout_seconds gauge",
        f"buildbybricks_llm_timeout_seconds {settings.llm_timeout_seconds}",
        "# HELP buildbybricks_llm_token_budget Configured LLM max token budget.",
        "# TYPE buildbybricks_llm_token_budget gauge",
        f"buildbybricks_llm_token_budget {settings.llm_max_tokens}",
    ]

    lines.extend(_job_status_metrics(job_list))
    lines.extend(_job_duration_metrics(job_list))
    lines.extend(_step_duration_metrics(job_list))
    lines.extend(_llm_call_metrics(job_list))
    lines.extend(_error_metrics(job_list))
    return "\n".join(lines) + "\n"


def _job_status_metrics(jobs: List[ArchitectureGenerationJob]) -> List[str]:
    counts = Counter(job.status for job in jobs)
    lines = [
        "# HELP buildbybricks_architecture_jobs Number of Architecture Sheet jobs by status.",
        "# TYPE buildbybricks_architecture_jobs gauge",
    ]
    for status, count in sorted(counts.items()):
        lines.append(_metric("buildbybricks_architecture_jobs", count, {"status": status}))
    return lines


def _job_duration_metrics(jobs: List[ArchitectureGenerationJob]) -> List[str]:
    grouped: Dict[str, List[float]] = defaultdict(list)
    now = datetime.now(timezone.utc)
    for job in jobs:
        started_at = job.started_at or job.created_at
        finished_at = job.finished_at or now
        duration = (finished_at - started_at).total_seconds()
        if duration >= 0:
            grouped[job.status].append(duration)

    lines = [
        "# HELP buildbybricks_architecture_job_duration_seconds Architecture job runtime by final/current status.",
        "# TYPE buildbybricks_architecture_job_duration_seconds summary",
    ]
    for status, durations in sorted(grouped.items()):
        labels = {"status": status}
        lines.append(_metric("buildbybricks_architecture_job_duration_seconds_count", len(durations), labels))
        lines.append(_metric("buildbybricks_architecture_job_duration_seconds_sum", sum(durations), labels))
    return lines


def _step_duration_metrics(jobs: List[ArchitectureGenerationJob]) -> List[str]:
    grouped: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    for job in jobs:
        for step in job.steps:
            if step.started_at is None or step.finished_at is None:
                continue
            duration = (step.finished_at - step.started_at).total_seconds()
            if duration >= 0:
                grouped[(step.key, step.status)].append(duration)

    lines = [
        "# HELP buildbybricks_architecture_step_duration_seconds Architecture pipeline step runtime.",
        "# TYPE buildbybricks_architecture_step_duration_seconds summary",
    ]
    for (step, status), durations in sorted(grouped.items()):
        labels = {"step": step, "status": status}
        lines.append(_metric("buildbybricks_architecture_step_duration_seconds_count", len(durations), labels))
        lines.append(_metric("buildbybricks_architecture_step_duration_seconds_sum", sum(durations), labels))
    return lines


def _llm_call_metrics(jobs: List[ArchitectureGenerationJob]) -> List[str]:
    grouped: Dict[Tuple[str, str, str, str], List[float]] = defaultdict(list)
    for job in jobs:
        for log in job.logs:
            metadata = log.metadata or {}
            if metadata.get("kind") != "llm_call":
                continue
            duration = _float(metadata.get("duration_seconds"))
            if duration is None:
                continue
            key = (
                str(metadata.get("llm_step", log.step or "unknown")),
                str(metadata.get("provider", job.llm_provider)),
                str(metadata.get("model", job.llm_model)),
                str(metadata.get("status", log.level)),
            )
            grouped[key].append(duration)

    lines = [
        "# HELP buildbybricks_llm_call_duration_seconds LLM call runtime from structured job logs.",
        "# TYPE buildbybricks_llm_call_duration_seconds summary",
    ]
    for (llm_step, provider, model, status), durations in sorted(grouped.items()):
        labels = {
            "llm_step": llm_step,
            "provider": provider,
            "model": model,
            "status": status,
        }
        lines.append(_metric("buildbybricks_llm_call_duration_seconds_count", len(durations), labels))
        lines.append(_metric("buildbybricks_llm_call_duration_seconds_sum", sum(durations), labels))
    return lines


def _error_metrics(jobs: List[ArchitectureGenerationJob]) -> List[str]:
    counts = Counter()
    for job in jobs:
        if not job.error:
            continue
        counts[(_sanitize_error(job.error), job.status)] += 1

    lines = [
        "# HELP buildbybricks_architecture_job_errors Architecture job error causes.",
        "# TYPE buildbybricks_architecture_job_errors gauge",
    ]
    for (reason, status), count in sorted(counts.items()):
        lines.append(_metric("buildbybricks_architecture_job_errors", count, {"reason": reason, "status": status}))
    return lines


def _metric(name: str, value: float, labels: Dict[str, str]) -> str:
    label_text = ",".join(f'{key}="{_escape_label(value)}"' for key, value in sorted(labels.items()))
    rendered_value = _render_number(value)
    return f"{name}{{{label_text}}} {rendered_value}" if label_text else f"{name} {rendered_value}"


def _render_number(value: float) -> str:
    if isinstance(value, int):
        return str(value)
    if math.isfinite(value):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return "0"


def _escape_label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _sanitize_error(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized[:120] if normalized else "unknown"


def _float(value: object) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
