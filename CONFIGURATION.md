# Configuration Guide

This project is designed so application-specific behavior can move into configuration instead of Python code.

## Current State

The current implementation is fully local and deterministic:

- Embeddings: `hash`
- Answer generation: `deterministic`
- Data: files under `data/<collection>/`
- App profile and evaluation cases: files under `template/`

Ollama, OpenAI, and other LLM providers are not implemented yet. The configuration surface is prepared so those providers can be added behind the existing interfaces.

## Using `.env`

Copy the example file and edit it:

```bash
cp .env.example .env
```

Docker Compose reads `.env` automatically and passes the values into the container.

```bash
docker compose up --build
```

## Optional Ollama Container

Ollama can run as a second Docker Compose service. It is behind the optional `ollama` profile so the default local development path stays lightweight.

Start the app plus Ollama:

```bash
docker compose --profile ollama up --build
```

Ollama is then reachable inside the Compose network at:

```text
http://ollama:11434
```

It is also exposed on the host at:

```text
http://localhost:11434
```

Pulling models is still a separate action. For example, after the service is running:

```bash
docker compose --profile ollama exec ollama ollama pull llama3.1
docker compose --profile ollama exec ollama ollama pull nomic-embed-text
```

The app does not yet call Ollama directly. The service is available so the next implementation step can add `OllamaLLMProvider` and `OllamaEmbeddingProvider` behind the existing provider settings.

## Data and Template Files

Knowledge goes into `data/<collection>/`.

```text
data/
├── sample/
├── policies/
└── product-docs/
```

Application behavior goes into `template/`.

- `template/app_profile.json`: app name, default collection, default top-k, answer policy, enabled tools
- `template/evaluation_cases.json`: repeatable test questions and expected sources/tool calls

## Embedding Providers

Embeddings convert chunks into vectors for retrieval.

Current default:

```env
AGENTIC_RAG_EMBEDDING_PROVIDER=hash
AGENTIC_RAG_EMBEDDING_MODEL=local-hash-v1
AGENTIC_RAG_EMBEDDING_DIMENSION=64
```

Planned Ollama embedding configuration:

```env
AGENTIC_RAG_EMBEDDING_PROVIDER=ollama
AGENTIC_RAG_EMBEDDING_MODEL=nomic-embed-text
AGENTIC_RAG_EMBEDDING_API_BASE_URL=http://ollama:11434
```

Use `http://ollama:11434` when Ollama runs as the second Compose service. Use `http://host.docker.internal:11434` when Ollama runs directly on the host machine and only the app runs in Docker.

## LLM Providers

LLM configuration is prepared, but only the deterministic answer composer exists today.

Current default:

```env
AGENTIC_RAG_LLM_PROVIDER=deterministic
AGENTIC_RAG_LLM_MODEL=local-deterministic-v1
```

Planned Ollama chat configuration:

```env
AGENTIC_RAG_LLM_PROVIDER=ollama
AGENTIC_RAG_LLM_MODEL=llama3.1
AGENTIC_RAG_LLM_API_BASE_URL=http://ollama:11434
```

Planned OpenAI-style configuration:

```env
AGENTIC_RAG_LLM_PROVIDER=openai
AGENTIC_RAG_LLM_MODEL=gpt-4.1-mini
AGENTIC_RAG_LLM_API_BASE_URL=https://api.openai.com/v1
AGENTIC_RAG_LLM_API_KEY=...
```

## What Is Still Missing For Ollama

To actually use Ollama as the LLM, we still need to implement:

- an `LLMProvider` interface
- an `OllamaLLMProvider`
- optional `OllamaEmbeddingProvider`
- agent wiring that calls the configured LLM provider instead of the deterministic answer composer
- tests that can run without requiring Ollama, plus optional integration tests when Ollama is available

The ingestion, retrieval, sources, evaluation, Docker runtime, and `.env` configuration surface are already in place.

## MCP Experiments

MCP servers are separate tool services, not part of Ollama itself. The same Compose pattern can be used later:

- add one MCP server as another Compose service
- expose it through environment variables
- add an agent tool adapter in `src/agentic_rag_template/tools/`
- include it in `template/app_profile.json`

For now, the project has explicit local tools: `search_knowledge_base`, `read_source`, and `answer_with_citations`.

## Quick Local Knowledge Test

1. Put files into a collection, for example `data/my-topic/notes.md`.
2. Set `template/app_profile.json`:

```json
{
  "name": "My Topic Assistant",
  "description": "Answers from my-topic documents.",
  "default_collection": "my-topic",
  "default_top_k": 3,
  "answer_policy": "Answer only from retrieved local sources.",
  "enabled_tools": [
    "search_knowledge_base",
    "read_source",
    "answer_with_citations"
  ]
}
```

3. Start locally:

```bash
docker compose up --build
```

4. Test:

- `http://localhost:8000/collections`
- `http://localhost:8000/evaluation/run`
- `http://localhost:8000`
