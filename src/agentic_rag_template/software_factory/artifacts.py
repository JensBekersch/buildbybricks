"""Filesystem artifacts produced by Software Factory workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any, Dict, List, Optional

from agentic_rag_template.applications import ApplicationInstance
from agentic_rag_template.software_factory.jobs import ArchitectureGenerationJob, timestamp, utc_now


ARCHITECTURE_SHEETS_DIR = "architecture-sheets"


@dataclass(frozen=True)
class ArchitectureSheetArtifact:
    """Persisted Architecture Sheet metadata."""

    id: str
    app_id: str
    job_id: str
    title: str
    json_path: str
    markdown_path: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "app_id": self.app_id,
            "job_id": self.job_id,
            "title": self.title,
            "json_path": self.json_path,
            "markdown_path": self.markdown_path,
            "created_at": self.created_at,
        }


class FileArchitectureArtifactStore:
    """Store generated Architecture Sheets as JSON and Markdown files."""

    def __init__(self, application: ApplicationInstance) -> None:
        self.application = application
        self.artifact_dir = application.data_dir / ARCHITECTURE_SHEETS_DIR

    def save_architecture_sheet(
        self,
        job: ArchitectureGenerationJob,
        result: Dict[str, Any],
    ) -> ArchitectureSheetArtifact:
        sheet = result.get("architecture_sheet") if isinstance(result, dict) else {}
        sheet = sheet if isinstance(sheet, dict) else {}
        title = str(sheet.get("artifact_name") or sheet.get("title") or job.id)
        stem = f"{_slugify(title)}-{job.id}"
        json_path = self.artifact_dir / f"{stem}.json"
        markdown_path = self.artifact_dir / f"{stem}.md"
        created_at = timestamp(utc_now()) or ""

        artifact = ArchitectureSheetArtifact(
            id=job.id,
            app_id=job.app_id,
            job_id=job.id,
            title=title,
            json_path=json_path.relative_to(self.application.data_dir).as_posix(),
            markdown_path=markdown_path.relative_to(self.application.data_dir).as_posix(),
            created_at=created_at,
        )
        payload = {
            "artifact": artifact.to_dict(),
            "job": {
                "id": job.id,
                "description": job.description,
                "generation_mode": job.generation_mode,
                "llm_provider": job.llm_provider,
                "llm_model": job.llm_model,
            },
            "result": result,
        }

        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        markdown_path.write_text(_render_markdown(title, result, artifact), encoding="utf-8")
        return artifact

    def list_architecture_sheets(self) -> List[ArchitectureSheetArtifact]:
        if not self.artifact_dir.is_dir():
            return []

        artifacts: List[ArchitectureSheetArtifact] = []
        for path in sorted(self.artifact_dir.glob("*.json"), reverse=True):
            artifact = self.get_architecture_sheet(path.stem)
            if artifact is not None:
                artifacts.append(artifact)
        return artifacts

    def get_architecture_sheet(self, artifact_id: str) -> Optional[ArchitectureSheetArtifact]:
        if not self.artifact_dir.is_dir():
            return None

        for path in self.artifact_dir.glob("*.json"):
            if artifact_id not in {path.stem, _read_artifact_id(path)}:
                continue

            payload = json.loads(path.read_text(encoding="utf-8"))
            artifact_payload = payload.get("artifact", {})
            return ArchitectureSheetArtifact(
                id=str(artifact_payload.get("id", artifact_id)),
                app_id=str(artifact_payload.get("app_id", self.application.id)),
                job_id=str(artifact_payload.get("job_id", artifact_id)),
                title=str(artifact_payload.get("title", artifact_id)),
                json_path=str(artifact_payload.get("json_path", "")),
                markdown_path=str(artifact_payload.get("markdown_path", "")),
                created_at=str(artifact_payload.get("created_at", "")),
            )

        return None

    def load_architecture_sheet_payload(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        if not self.artifact_dir.is_dir():
            return None

        for path in self.artifact_dir.glob("*.json"):
            if artifact_id not in {path.stem, _read_artifact_id(path)}:
                continue
            return json.loads(path.read_text(encoding="utf-8"))

        return None


def _read_artifact_id(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    artifact = payload.get("artifact", {})
    return str(artifact.get("id", ""))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "architecture-sheet"


def _render_markdown(
    title: str,
    result: Dict[str, Any],
    artifact: ArchitectureSheetArtifact,
) -> str:
    sheet = result.get("architecture_sheet", {}) if isinstance(result, dict) else {}
    validation = result.get("validation", {}) if isinstance(result, dict) else {}
    generation = result.get("generation", {}) if isinstance(result, dict) else {}
    lines = [
        f"# {title}",
        "",
        f"- Artifact ID: `{artifact.id}`",
        f"- Schema: `{result.get('schema_id', '-')}`",
        f"- Validation: `{validation.get('valid', False)}`",
        f"- Generator: `{generation.get('llm_provider', generation.get('mode', '-'))}`",
        "",
        "## Business Goal",
        "",
        _value_text(sheet.get("business_goal") or sheet.get("goal") or ""),
        "",
    ]

    if isinstance(sheet.get("arc42"), dict):
        lines.extend(_render_arc42_markdown(sheet["arc42"]))
        return "\n".join(lines).rstrip() + "\n"

    sections = [
        ("Architecture Drivers", sheet.get("architecture_drivers") or sheet.get("drivers") or []),
        ("Qualitaetsziele", sheet.get("quality_goals") or []),
        ("Kontext und Schnittstellen", sheet.get("context") or sheet.get("external_interfaces") or []),
        ("Bausteine", sheet.get("building_blocks") or []),
        ("Laufzeitszenarien", sheet.get("runtime_scenarios") or []),
        ("Architekturentscheidungen", sheet.get("architecture_decisions") or sheet.get("decisions") or []),
        ("Risiken", sheet.get("risks") or []),
        ("Annahmen", sheet.get("assumptions") or []),
        ("Offene Fragen", sheet.get("open_questions") or []),
        ("Akzeptanzkriterien", sheet.get("acceptance_criteria") or []),
        ("Teststrategie", sheet.get("test_strategy") or []),
    ]

    for heading, value in sections:
        lines.extend([f"## {heading}", ""])
        lines.extend(_markdown_lines(value))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_arc42_markdown(arc42: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    sections = [
        ("1. Einfuehrung & Ziele", arc42.get("introduction_and_goals")),
        ("2. Randbedingungen", arc42.get("constraints")),
        ("3. Kontext & Abgrenzung", arc42.get("context_and_scope")),
        ("4. Loesungsstrategie", arc42.get("solution_strategy")),
        ("5. Bausteinsicht", arc42.get("building_block_view")),
        ("6. Laufzeitsicht", arc42.get("runtime_view")),
        ("7. Verteilungssicht", arc42.get("deployment_view")),
        ("8. Querschnittliche Konzepte", arc42.get("crosscutting_concepts")),
        ("9. Architekturentscheidungen", arc42.get("architecture_decisions")),
        ("10. Qualitaetsanforderungen", arc42.get("quality_requirements")),
        ("11. Risiken & Technische Schulden", arc42.get("risks_and_technical_debt")),
        ("12. Glossar", arc42.get("glossary")),
    ]

    for heading, value in sections:
        lines.extend([f"## {heading}", ""])
        lines.extend(_markdown_lines(value))
        lines.append("")

    return lines


def _markdown_lines(value: Any) -> List[str]:
    if value in (None, "", []):
        return ["Noch offen."]
    if isinstance(value, list):
        return [f"- {_value_text(item)}" for item in value] or ["Noch offen."]
    return [_value_text(value)]


def _value_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return "; ".join(_value_text(item) for item in value if _value_text(item))
    if isinstance(value, dict):
        parts = []
        for key, entry in value.items():
            text = _value_text(entry)
            if text:
                parts.append(f"{key.replace('_', ' ')}: {text}")
        return "; ".join(parts)
    return str(value)
