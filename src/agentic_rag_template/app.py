"""Application entrypoint for the agentic RAG template."""

from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from agentic_rag_template.agent import AgentRequest, StudyAgent
from agentic_rag_template.api.schemas import ChatRequest, ChatResponse
from agentic_rag_template.applications import ApplicationInstance, FileApplicationRegistry
from agentic_rag_template.config import Settings
from agentic_rag_template.embeddings import create_embedding_provider
from agentic_rag_template.evaluation import EvaluationRunner
from agentic_rag_template.ingestion import discover_collections, ingest_data, load_documents
from agentic_rag_template.ingestion.loader import SUPPORTED_EXTENSIONS
from agentic_rag_template.llm import create_llm_provider
from agentic_rag_template.retrieval import InMemoryVectorStore, RetrievalQuery, Retriever
from agentic_rag_template.software_factory import generate_architecture_sheet
from agentic_rag_template.template_config import load_application_profile


SAFE_COLLECTION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]*$")


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
            self._send_json(self._list_collections(self._default_application()))
            return

        app_route = self._parse_app_route(parsed_url.path)

        if app_route:
            application = self._find_application(app_route["app_id"])

            if application is None:
                return

            if app_route["remainder"] == "":
                self._send_json(application.to_dict())
                return

            if app_route["remainder"] == "/collections":
                self._send_json(self._list_collections(application))
                return

            documents_collection = self._parse_collection_documents_route(app_route["remainder"])
            if documents_collection is not None:
                self._send_json(self._list_documents(application, documents_collection))
                return

            if app_route["remainder"] == "/ingestion/preview":
                self._send_json(self._preview_ingestion(parsed_url.query, application))
                return

            if app_route["remainder"] == "/vector-store/preview":
                self._send_json(self._preview_vector_search(parsed_url.query, application))
                return

            if app_route["remainder"] == "/retrieval/search":
                self._send_json(self._search_retriever(parsed_url.query, application))
                return

            if app_route["remainder"] == "/evaluation/run":
                self._send_json(self._run_evaluation(application))
                return

        if parsed_url.path == "/apps":
            self._send_json(self._list_applications())
            return

        if parsed_url.path == "/ingestion/preview":
            self._send_json(self._preview_ingestion(parsed_url.query, self._default_application()))
            return

        if parsed_url.path == "/vector-store/preview":
            self._send_json(self._preview_vector_search(parsed_url.query, self._default_application()))
            return

        if parsed_url.path == "/retrieval/search":
            self._send_json(self._search_retriever(parsed_url.query, self._default_application()))
            return

        if parsed_url.path == "/evaluation/run":
            self._send_json(self._run_evaluation(self._default_application()))
            return

        if parsed_url.path == "/template/profile":
            self._send_json(load_application_profile(self.settings.template_dir).to_dict())
            return

        if parsed_url.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        app_route = self._parse_app_route(parsed_url.path)

        if app_route and app_route["remainder"] == "/chat":
            application = self._find_application(app_route["app_id"])

            if application is None:
                return

            self._send_chat_response(application)
            return

        if app_route and app_route["remainder"] == "/architecture-sheet":
            application = self._find_application(app_route["app_id"])

            if application is None:
                return

            self._send_architecture_sheet_response(application)
            return

        if app_route:
            documents_collection = self._parse_collection_documents_route(app_route["remainder"])
            if documents_collection is not None:
                application = self._find_application(app_route["app_id"])

                if application is None:
                    return

                upload_response = self._upload_document(application, documents_collection)

                if upload_response is not None:
                    self._send_json(upload_response, status=HTTPStatus.CREATED)

                return

        if parsed_url.path != "/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
            return

        self._send_chat_response(self._default_application())

    def _send_architecture_sheet_response(self, application: ApplicationInstance) -> None:
        if application.id != "software-factory":
            self._send_json(
                {"error": "architecture-sheet is only available for the software-factory app"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        payload = self._read_json_body()
        description = str(payload.get("description", "")).strip()

        if not description:
            self._send_json({"error": "description is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        use_llm = _payload_bool(payload.get("use_llm"), self.settings.architecture_llm_enabled)
        llm_provider = create_llm_provider(self.settings) if use_llm else None

        try:
            result = generate_architecture_sheet(
                description,
                application,
                llm_provider=llm_provider,
            )
        except FileNotFoundError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json(result.to_dict())

    def _send_chat_response(self, application: ApplicationInstance) -> None:
        payload = self._read_json_body()
        message = str(payload.get("message", "")).strip()
        profile = application.profile

        if not message:
            self._send_json({"error": "message is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        request = ChatRequest(
            message=message,
            conversation_id=payload.get("conversation_id"),
            collection=payload.get("collection") or profile.default_collection,
            top_k=int(payload.get("top_k", profile.default_top_k)),
        )
        response = self._handle_chat(request, application)
        self._send_json(
            {
                "answer": response.answer,
                "sources": [
                    {
                        "title": source.title,
                        "location": source.location,
                        "excerpt": source.excerpt,
                        "score": source.score,
                    }
                    for source in response.sources
                ],
                "uncertainty": response.uncertainty,
                "trace": response.trace,
                "tool_calls": getattr(response, "tool_calls", []),
            }
        )

    def _handle_chat(self, request: ChatRequest, application: Optional[ApplicationInstance] = None) -> ChatResponse:
        active_application = application or self._default_application()
        embedding_provider = create_embedding_provider(self.settings)
        llm_provider = create_llm_provider(self.settings)
        agent = StudyAgent(
            active_application.data_dir,
            embedding_provider,
            llm_provider=llm_provider,
            answer_policy=active_application.profile.answer_policy,
        )
        response = agent.answer(
            AgentRequest(
                message=request.message,
                collection=request.collection,
                top_k=request.top_k,
            )
        )
        chat_response = ChatResponse(
            answer=response.answer,
            sources=response.sources,
            uncertainty=response.uncertainty,
            trace=response.trace,
            tool_calls=[tool_call.to_dict() for tool_call in response.tool_calls],
        )
        return chat_response

    def _list_applications(self) -> Dict[str, Any]:
        return {
            "applications": [
                application.summary().to_dict()
                for application in FileApplicationRegistry(self.settings).list()
            ]
        }

    def _find_application(self, app_id: str) -> Optional[ApplicationInstance]:
        try:
            return FileApplicationRegistry(self.settings).get(app_id)
        except ValueError as error:
            self.send_error(HTTPStatus.BAD_REQUEST, str(error))
            return None
        except KeyError as error:
            self.send_error(HTTPStatus.NOT_FOUND, str(error))
            return None

    def _default_application(self) -> ApplicationInstance:
        return FileApplicationRegistry(self.settings).get("default")

    def _list_collections(self, application: ApplicationInstance) -> Dict[str, Any]:
        collections = []

        for collection in discover_collections(application.data_dir):
            documents = load_documents(application.data_dir, collection=collection)
            collections.append(
                {
                    "name": collection,
                    "document_count": len(documents),
                }
            )

        return {"collections": collections}

    def _list_documents(self, application: ApplicationInstance, collection: str) -> Dict[str, Any]:
        if not self._is_safe_collection_name(collection):
            return {"error": "collection contains unsupported characters"}

        documents = load_documents(application.data_dir, collection=collection)
        return {
            "app_id": application.id,
            "collection": collection,
            "document_count": len(documents),
            "documents": [
                {
                    "title": document.title,
                    "filename": document.path.name,
                    "relative_path": document.relative_path.as_posix(),
                    "extension": document.path.suffix.lower(),
                    "char_count": len(document.content),
                }
                for document in documents
            ],
        }

    def _upload_document(
        self, application: ApplicationInstance, collection: str
    ) -> Optional[Dict[str, Any]]:
        if not self._is_safe_collection_name(collection):
            self.send_error(HTTPStatus.BAD_REQUEST, "collection contains unsupported characters")
            return None

        payload = self._read_json_body()
        filename = str(payload.get("filename", "")).strip()
        content = str(payload.get("content", "")).strip()

        if not filename:
            self.send_error(HTTPStatus.BAD_REQUEST, "filename is required")
            return None

        if not content:
            self.send_error(HTTPStatus.BAD_REQUEST, "content is required")
            return None

        if not self._is_safe_filename(filename):
            self.send_error(HTTPStatus.BAD_REQUEST, "filename contains unsupported characters")
            return None

        target_dir = application.data_dir / collection
        target_path = target_dir / filename
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path.write_text(f"{content}\n", encoding="utf-8")

        return {
            "app_id": application.id,
            "collection": collection,
            "filename": filename,
            "relative_path": target_path.relative_to(application.data_dir).as_posix(),
            "char_count": len(content),
        }

    def _preview_ingestion(self, query: str, application: ApplicationInstance) -> Dict[str, Any]:
        params = parse_qs(query)
        collection = params.get("collection", [None])[0]
        chunks = ingest_data(application.data_dir, collection=collection)

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

    def _preview_vector_search(self, query: str, application: ApplicationInstance) -> Dict[str, Any]:
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

        chunks = ingest_data(application.data_dir, collection=collection)
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

    def _search_retriever(self, query: str, application: ApplicationInstance) -> Dict[str, Any]:
        params = parse_qs(query)
        search_query = params.get("q", [""])[0].strip()
        collection = params.get("collection", [None])[0]
        top_k = int(params.get("top_k", ["5"])[0])

        try:
            embedding_provider = create_embedding_provider(self.settings)
            retriever = Retriever(application.data_dir, embedding_provider)
            response = retriever.retrieve(
                RetrievalQuery(
                    text=search_query,
                    collection=collection,
                    top_k=top_k,
                )
            )
        except ValueError as error:
            return {"error": str(error)}

        payload = response.to_dict()
        payload["provider"] = embedding_provider.name
        payload["model"] = embedding_provider.model
        payload["dimension"] = embedding_provider.dimension
        return payload

    def _run_evaluation(self, application: ApplicationInstance) -> Dict[str, Any]:
        embedding_provider = create_embedding_provider(self.settings)
        llm_provider = create_llm_provider(self.settings)
        agent = StudyAgent(
            application.data_dir,
            embedding_provider,
            llm_provider=llm_provider,
            answer_policy=application.profile.answer_policy,
        )
        report = EvaluationRunner(agent).run_template(application.template_dir)
        payload = report.to_dict()
        payload["app_id"] = application.id
        payload["provider"] = embedding_provider.name
        payload["model"] = embedding_provider.model
        payload["llm_provider"] = llm_provider.name
        payload["llm_model"] = llm_provider.model
        return payload

    def _parse_app_route(self, path: str) -> Optional[Dict[str, str]]:
        if not path.startswith("/apps/"):
            return None

        parts = path.split("/", 3)

        if len(parts) < 3 or not parts[2]:
            return None

        remainder = "" if len(parts) == 3 else f"/{parts[3]}"
        return {"app_id": parts[2], "remainder": remainder}

    def _parse_collection_documents_route(self, remainder: str) -> Optional[str]:
        parts = remainder.strip("/").split("/")

        if len(parts) == 3 and parts[0] == "collections" and parts[2] == "documents":
            return parts[1]

        return None

    def _is_safe_collection_name(self, collection: str) -> bool:
        return bool(SAFE_COLLECTION_PATTERN.fullmatch(collection))

    def _is_safe_filename(self, filename: str) -> bool:
        path = Path(filename)
        return (
            path.name == filename
            and ".." not in path.parts
            and bool(SAFE_FILENAME_PATTERN.fullmatch(filename))
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

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


def _payload_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}

    return bool(value)


def main() -> None:
    settings = create_app_settings()
    server = create_server(settings)
    print(f"{settings.app_name} listening on http://{settings.host}:{settings.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
