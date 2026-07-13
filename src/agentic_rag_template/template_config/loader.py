"""Load application-specific template configuration from JSON files."""

import json
from pathlib import Path
from typing import Any, Dict

from agentic_rag_template.template_config.models import ApplicationProfile


def load_application_profile(template_dir: Path) -> ApplicationProfile:
    """Load application profile from template/app_profile.json when present."""
    profile_path = template_dir / "app_profile.json"
    defaults = ApplicationProfile()

    if not profile_path.exists():
        return defaults

    payload = read_json_object(profile_path)
    return ApplicationProfile(
        name=str(payload.get("name", defaults.name)),
        description=str(payload.get("description", defaults.description)),
        default_collection=str(payload.get("default_collection", defaults.default_collection)),
        default_top_k=int(payload.get("default_top_k", defaults.default_top_k)),
        answer_policy=str(payload.get("answer_policy", defaults.answer_policy)),
        enabled_tools=list(payload.get("enabled_tools", defaults.enabled_tools)),
    )


def read_json_object(path: Path) -> Dict[str, Any]:
    """Read a JSON file and ensure it contains an object."""
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return payload
