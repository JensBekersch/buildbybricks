"""Resolve configured application instances from the filesystem."""

from pathlib import Path
import re
from typing import List

from agentic_rag_template.applications.models import ApplicationInstance
from agentic_rag_template.config import Settings
from agentic_rag_template.template_config import load_application_profile

DEFAULT_APP_ID = "default"
APP_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


class FileApplicationRegistry:
    """File-backed registry for reusable app instances."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list(self) -> List[ApplicationInstance]:
        instances = [self.get(DEFAULT_APP_ID)]

        if not self.settings.apps_dir.exists():
            return instances

        app_ids = sorted(
            path.name
            for path in self.settings.apps_dir.iterdir()
            if path.is_dir() and path.name != DEFAULT_APP_ID and is_valid_app_id(path.name)
        )
        instances.extend(self.get(app_id) for app_id in app_ids)
        return instances

    def get(self, app_id: str) -> ApplicationInstance:
        normalized_app_id = normalize_app_id(app_id)

        if normalized_app_id == DEFAULT_APP_ID:
            return ApplicationInstance(
                id=DEFAULT_APP_ID,
                profile=load_application_profile(self.settings.template_dir),
                template_dir=self.settings.template_dir,
                data_dir=self.settings.data_dir,
            )

        template_dir = self.settings.apps_dir / normalized_app_id

        if not template_dir.is_dir():
            raise KeyError(f"Application '{normalized_app_id}' does not exist")

        return ApplicationInstance(
            id=normalized_app_id,
            profile=load_application_profile(template_dir),
            template_dir=template_dir,
            data_dir=self.settings.data_dir / normalized_app_id,
        )


def normalize_app_id(app_id: str) -> str:
    """Validate and normalize a user-facing app id."""
    normalized = app_id.strip().lower()

    if not is_valid_app_id(normalized):
        raise ValueError(
            "Application ids must start with a lowercase letter or number and contain "
            "only lowercase letters, numbers, hyphens, and underscores."
        )

    return normalized


def is_valid_app_id(app_id: str) -> bool:
    return bool(APP_ID_PATTERN.fullmatch(app_id))
