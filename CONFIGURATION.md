# Configuration Guide

This project is designed so application-specific behavior can move into configuration instead of Python code.

## Current State

The current implementation is fully local and deterministic:

- Embeddings: `hash`
- Answer generation: `deterministic`
- Default app data: files under `data/<collection>/`
- Configurable app instances: profiles under `apps/<app-id>/`, data under `data/<app-id>/<collection>/`
- Legacy default app profile and evaluation cases: files under `template/`

Ollama is implemented as an LLM provider. OpenAI and Ollama embeddings are not implemented yet. The configuration surface is prepared so those providers can be added behind the existing interfaces.

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

The app can call Ollama for chat answers when `AGENTIC_RAG_LLM_PROVIDER=ollama` is set. Ollama embeddings are still a separate future adapter.

## Data and Template Files

The legacy `default` application uses `template/` and `data/<collection>/`.

```text
data/
├── sample/
├── policies/
└── product-docs/
```

Application behavior goes into `template/`.

- `template/app_profile.json`: app name, default collection, default top-k, answer policy, enabled tools
- `template/evaluation_cases.json`: repeatable test questions and expected sources/tool calls

Reusable application instances live under `apps/<app-id>/`:

```text
apps/
└── policy-assistant/
    ├── app_profile.json
    └── evaluation_cases.json
```

Their knowledge lives under `data/<app-id>/<collection>/`:

```text
data/
└── policy-assistant/
    └── policies/
        └── handbook.md
```

Runtime endpoints:

- `GET /apps`
- `GET /apps/{app_id}`
- `GET /apps/{app_id}/collections`
- `GET /apps/{app_id}/collections/{collection}/documents`
- `POST /apps/{app_id}/collections/{collection}/documents`
- `GET /apps/{app_id}/ingestion/preview?collection={collection}`
- `GET /apps/{app_id}/retrieval/search?q={query}&collection={collection}`
- `POST /apps/{app_id}/chat`
- `GET /apps/{app_id}/evaluation/run`
- `POST /apps/software-factory/architecture-sheet`

The document upload endpoint accepts JSON and writes supported text files into
the app data directory:

```json
{
  "filename": "handbook.md",
  "content": "Knowledge content for this app collection."
}
```

Docker Compose mounts `./data` as writable so uploaded knowledge is persisted on
the host during local experiments. `./apps` and `./template` stay read-only
because app configuration should remain an explicit file change for now.

The Software Factory architecture-sheet endpoint accepts:

```json
{
  "description": "A Django application for customers, offers, approvals, and PDF exports."
}
```

It returns a schema-shaped `architecture_sheet`, validation metadata, method
sources, and trace steps. The current generator is deterministic so local tests
remain stable.

The current architecture-sheet contract is `schema_version` `1.0.0`. It includes
architecture drivers, explicit architecture decisions, acceptance criteria, and a
readiness status so later workorder agents can consume the sheet predictably.

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

LLM configuration supports the deterministic answer composer and Ollama chat generation.

Current default:

```env
AGENTIC_RAG_LLM_PROVIDER=deterministic
AGENTIC_RAG_LLM_MODEL=local-deterministic-v1
```

Ollama chat configuration:

```env
AGENTIC_RAG_LLM_PROVIDER=ollama
AGENTIC_RAG_LLM_MODEL=llama3.1
AGENTIC_RAG_LLM_API_BASE_URL=http://ollama:11434
AGENTIC_RAG_LLM_TIMEOUT_SECONDS=300
AGENTIC_RAG_LLM_MAX_TOKENS=160
```

Large local models can need longer on the first request because Ollama has to load
the model into memory. Increase `AGENTIC_RAG_LLM_TIMEOUT_SECONDS` when first
requests time out during model startup.

On CPU-only Docker runs, generation can also be slow. Lower
`AGENTIC_RAG_LLM_MAX_TOKENS` for live tests when a large model takes too long to
finish.

Planned OpenAI-style configuration:

```env
AGENTIC_RAG_LLM_PROVIDER=openai
AGENTIC_RAG_LLM_MODEL=gpt-4.1-mini
AGENTIC_RAG_LLM_API_BASE_URL=https://api.openai.com/v1
AGENTIC_RAG_LLM_API_KEY=...
```

## What Is Still Missing For Ollama

Ollama chat is implemented. Still missing:

- optional `OllamaEmbeddingProvider`
- optional integration tests that require a live Ollama service and pulled models
- model management helpers for pulling/checking required models

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
