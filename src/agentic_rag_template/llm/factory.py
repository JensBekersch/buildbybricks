"""Factory for selecting the configured LLM provider."""

from agentic_rag_template.config import Settings
from agentic_rag_template.llm.deterministic_provider import DeterministicLLMProvider
from agentic_rag_template.llm.models import LLMProvider, LLMProviderConfig
from agentic_rag_template.llm.ollama_provider import OllamaLLMProvider


def config_from_settings(settings: Settings) -> LLMProviderConfig:
    """Extract LLM settings from application settings."""
    return LLMProviderConfig(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
    )


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Create the configured LLM provider."""
    config = config_from_settings(settings)
    provider = config.provider.lower().strip()

    if provider == "deterministic":
        return DeterministicLLMProvider(model=config.model)

    if provider == "ollama":
        return OllamaLLMProvider(
            model=config.model,
            api_base_url=config.api_base_url,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
        )

    raise ValueError(
        f"LLM provider '{config.provider}' is not implemented. "
        "Supported providers: deterministic, ollama."
    )
