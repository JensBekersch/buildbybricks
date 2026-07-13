"""Application template loading helpers."""

from agentic_rag_template.template_config.loader import load_application_profile
from agentic_rag_template.template_config.models import ApplicationProfile

__all__ = [
    "ApplicationProfile",
    "load_application_profile",
]
