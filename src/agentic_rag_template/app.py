"""Application entrypoint for the agentic RAG template."""

from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from agentic_rag_template.api.schemas import ChatRequest, ChatResponse
from agentic_rag_template.config import Settings
from agentic_rag_template.embeddings import create_embedding_provider
from agentic_rag_template.ingestion import discover_collections, ingest_data, load_documents
from agentic_rag_template.retrieval import InMemoryVectorStore


def create_app_settings() -> Settings:
    """Create application settings for the current runtime."""
    return Settings.from_env()


class AgenticRagRequestHandler(SimpleHTTPRequestHandler):
    """Small local HTTP API plus static frontend server."""

    settings: Settings

    def __init__(self, *args: Any, settings: Settings, **kwargs: Any) -> None:
        self.settings = settings
        super().__init__(*args, directory=str(settings.frontend_dir), **kwargs)

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/health":
            self._send_json({"status": "ok", "app": self.settings.app_name})
            return

        if parsed_url.path == "/collections":
            self._send_json(self._list_collections())
            return

        if parsed_url.path == "/ingestion/preview":
            self._send_json(self._preview_ingestion(parsed_url.query))
            return

        if parsed_url.path == "/vector-store/preview":
            self._send_json(self._preview_vector_search(parsed_url.query))
            return

        if parsed_url.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
            return

        payload = self._read_json_body()
        message = str(payload.get("message", "")).strip()

        if not message:
            self._send_json({"error": "message is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        request = ChatRequest(
            message=message,
            conversation_id=payload.get("conversation_id"),
        )
        response = self._handle_chat(request)
        self._send_json(
            {
                "answer": response.answer,
                "sources": [
                    {"title": source.title, "location": source.location}
                    for source in response.sources
                ],
                "trace": response.trace,
            }
        )

    def _handle_chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            answer=(
                "Der lokale Chat-Endpoint laeuft. "
                "Retrieval und Agentenlogik werden in den naechsten Schritten angebunden."
            ),
            trace=[
                "received_message",
                "returned_stub_response",
            ],
        )

    def _list_collections(self) -> Dict[str, Any]:
        collections = []

        for collection in discover_collections(self.settings.data_dir):
            documents = load_documents(self.settings.data_dir, collection=collection)
            collections.append(
                {
                    "name": collection,
                    "document_count": len(documents),
                }
            )

        return {"collections": collections}

    def _preview_ingestion(self, query: str) -> Dict[str, Any]:
        params = parse_qs(query)
        collection = params.get("collection", [None])[0]
        chunks = ingest_data(self.settings.data_dir, collection=collection)

        return {
            "chunk_count": len(chunks),
            "chunks": [
                {
                    "id": chunk.id,
                    "collection": chunk.collection,
                    "source_path": chunk.source_path,
                    "title": chunk.title,
                    "chunk_index": chunk.chunk_index,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks[:10]
            ],
        }

    def _preview_vector_search(self, query: str) -> Dict[str, Any]:
        params = parse_qs(query)
        search_query = params.get("q", [""])[0].strip()
        collection = params.get("collection", [None])[0]
        top_k = int(params.get("top_k", ["5"])[0])

        if not search_query:
            return {
                "error": "q is required",
                "provider": self.settings.embedding_provider,
                "model": self.settings.embedding_model,
            }

        chunks = ingest_data(self.settings.data_dir, collection=collection)
        embedding_provider = create_embedding_provider(self.settings)
        vector_store = InMemoryVectorStore(embedding_provider)
        vector_store.add_chunks(chunks)
        results = vector_store.search(search_query, top_k=top_k, collection=collection)

        return {
            "query": search_query,
            "provider": embedding_provider.name,
            "model": embedding_provider.model,
            "dimension": embedding_provider.dimension,
            "indexed_chunk_count": vector_store.size,
            "results": [
                {
                    "score": round(result.score, 6),
                    "id": result.chunk.id,
                    "collection": result.chunk.collection,
                    "source_path": result.chunk.source_path,
                    "title": result.chunk.title,
                    "chunk_index": result.chunk.chunk_index,
                    "text": result.chunk.text,
                    "metadata": result.chunk.metadata,
                }
                for result in results
            ],
        }

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

        if isinstance(payload, dict):
            return payload

        return {}

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(settings: Optional[Settings] = None) -> ThreadingHTTPServer:
    """Create a local HTTP server for API and frontend requests."""
    active_settings = settings or create_app_settings()
    frontend_dir = Path(active_settings.frontend_dir)
    frontend_dir.mkdir(parents=True, exist_ok=True)
    handler = partial(AgenticRagRequestHandler, settings=active_settings)
    return ThreadingHTTPServer((active_settings.host, active_settings.port), handler)


def main() -> None:
    settings = create_app_settings()
    server = create_server(settings)
    print(f"{settings.app_name} listening on http://{settings.host}:{settings.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
