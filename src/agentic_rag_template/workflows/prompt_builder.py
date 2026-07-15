"""Build prompts for configured workflow agents."""

import json
from typing import Any, Dict, List

from agentic_rag_template.workflows.models import AgentVersion


class PromptBuilder:
    def build(self, agent_version: AgentVersion, resolved_input: Dict[str, Any]) -> Dict[str, str]:
        system_parts: List[str] = [agent_version.system_prompt]
        method_packs = [pack for pack in agent_version.method_packs if pack]
        if method_packs:
            system_parts.append("Methodenwissen:")
            system_parts.append(json.dumps(method_packs, ensure_ascii=True))
        system_parts.append("Output-Schema:")
        system_parts.append(json.dumps(agent_version.output_schema, ensure_ascii=True))
        return {
            "system_prompt": "\n\n".join(part for part in system_parts if part),
            "user_prompt": _render_template(agent_version.user_prompt_template, resolved_input),
        }


def _render_template(template: str, context: Dict[str, Any]) -> str:
    rendered = template
    for key, value in context.items():
        rendered_value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)
        rendered = rendered.replace("{{ " + key + " }}", rendered_value)
        rendered = rendered.replace("{{" + key + "}}", rendered_value)
    return rendered

