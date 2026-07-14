from agentic_rag_template.config import Settings


def test_settings_reads_llm_configuration_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_RAG_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("AGENTIC_RAG_LLM_MODEL", "llama3.1")
    monkeypatch.setenv("AGENTIC_RAG_LLM_API_BASE_URL", "http://host.docker.internal:11434")
    monkeypatch.setenv("AGENTIC_RAG_LLM_API_KEY", "secret")

    settings = Settings.from_env()

    assert settings.llm_provider == "ollama"
    assert settings.llm_model == "llama3.1"
    assert settings.llm_api_base_url == "http://host.docker.internal:11434"
    assert settings.llm_api_key == "secret"
