"""Application entrypoint for the agentic RAG template."""

from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import time
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
from agentic_rag_template.observability import render_prometheus_metrics
from agentic_rag_template.retrieval import InMemoryVectorStore, RetrievalQuery, Retriever
from agentic_rag_template.software_factory.workflow_blueprints import (
    WorkflowBlueprintError,
    load_software_factory_workflow,
)
from agentic_rag_template.software_factory import (
    ArchitectureGenerationJob,
    ArchitectureGenerationJobStoreError,
    FileArchitectureArtifactStore,
    JOB_STATUS_CANCELED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    TERMINAL_JOB_STATUSES,
    PostgresArchitectureGenerationJobStore,
)
from agentic_rag_template.template_config import load_application_profile
from agentic_rag_template.workflows.models import WorkflowRun, WorkflowVersion
from agentic_rag_template.workflows.providers import FakeLLMProviderAdapter
from agentic_rag_template.workflows.store import PostgresWorkflowStore, WorkflowStoreError
from agentic_rag_template.workflows.workflow_execution import LinearWorkflowEngine
from agentic_rag_template.workflows.workflow_validation import WorkflowVersionValidator


SAFE_COLLECTION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]*$")
SAFE_WORKFLOW_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def create_app_settings() -> Settings:
    """Create application settings for the current runtime."""
    return Settings.from_env()


class AgenticRagRequestHandler(SimpleHTTPRequestHandler):
    """Small local HTTP API plus static frontend server."""

    settings: Settings

    def __init__(
        self,
        *args: Any,
        settings: Settings,
        architecture_job_store: Any = None,
        workflow_store: Any = None,
        **kwargs: Any,
    ) -> None:
        self.settings = settings
        self.architecture_job_store = architecture_job_store
        self.workflow_store = workflow_store
        super().__init__(*args, directory=str(settings.frontend_dir), **kwargs)

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/health":
            self._send_json({"status": "ok", "app": self.settings.app_name})
            return

        if parsed_url.path == "/runtime/config":
            self._send_json(self.settings.runtime_config())
            return

        if parsed_url.path == "/metrics":
            self._send_metrics_response()
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

            if app_route["remainder"] == "/workflows":
                self._send_json(self._list_workflows(application))
                return

            workflow_run_route = self._parse_workflow_run_route(app_route["remainder"])
            if workflow_run_route is not None:
                self._send_workflow_run_response(
                    application,
                    workflow_run_route["workflow_id"],
                    workflow_run_route.get("run_id", ""),
                )
                return

            workflow_id = self._parse_workflow_detail_route(app_route["remainder"])
            if workflow_id is not None:
                self._send_workflow_detail_response(application, workflow_id)
                return

            if app_route["remainder"] == "/architecture-sheet/jobs":
                self._send_json(self._list_architecture_jobs(application))
                return

            if app_route["remainder"] == "/architecture-sheets":
                self._send_json(self._list_architecture_sheet_artifacts(application))
                return

            architecture_artifact_id = self._parse_architecture_sheet_artifact_route(app_route["remainder"])
            if architecture_artifact_id is not None:
                self._send_architecture_sheet_artifact_response(application, architecture_artifact_id)
                return

            architecture_events_job_id = self._parse_architecture_job_events_route(app_route["remainder"])
            if architecture_events_job_id is not None:
                self._send_architecture_job_events_response(application, architecture_events_job_id)
                return

            architecture_job_id = self._parse_architecture_job_route(app_route["remainder"])
            if architecture_job_id is not None:
                self._send_architecture_job_response(application, architecture_job_id)
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

        if app_route and app_route["remainder"] == "/architecture-sheet/jobs":
            application = self._find_application(app_route["app_id"])

            if application is None:
                return

            self._send_architecture_job_created_response(application)
            return

        workflow_action = self._parse_workflow_action_route(app_route["remainder"] if app_route else "")
        if workflow_action is not None:
            application = self._find_application(app_route["app_id"])

            if application is None:
                return

            self._send_workflow_action_response(
                application,
                workflow_action["workflow_id"],
                workflow_action["action"],
            )
            return

        architecture_job_action = self._parse_architecture_job_action_route(
            app_route["remainder"] if app_route else ""
        )
        if architecture_job_action is not None:
            application = self._find_application(app_route["app_id"])

            if application is None:
                return

            self._send_architecture_job_action_response(
                application,
                architecture_job_action["job_id"],
                architecture_job_action["action"],
            )
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

    def _send_architecture_job_created_response(self, application: ApplicationInstance) -> None:
        if application.id != "software-factory":
            self._send_json(
                {"error": "architecture-sheet jobs are only available for the software-factory app"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        payload = self._read_json_body()
        description = str(payload.get("description", "")).strip()

        if not description:
            self._send_json({"error": "description is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        generation_mode = str(payload.get("generation_mode") or "").strip()
        if not generation_mode:
            generation_mode = self.settings.architecture_generation_mode
        llm_provider = create_llm_provider(self.settings)

        try:
            job = ArchitectureGenerationJob.create(
                description=description,
                generation_mode=generation_mode,
                app_id=application.id,
                llm_provider=getattr(llm_provider, "name", "none"),
                llm_model=getattr(llm_provider, "model", "none"),
            )
            self._architecture_job_store().save(job)
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
            return
        except ArchitectureGenerationJobStoreError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json({"job": job.to_dict()}, status=HTTPStatus.ACCEPTED)

    def _list_architecture_jobs(self, application: ApplicationInstance) -> Dict[str, Any]:
        if application.id != "software-factory":
            return {"error": "architecture-sheet jobs are only available for the software-factory app"}

        try:
            jobs = self._architecture_job_store().list()
        except ArchitectureGenerationJobStoreError as error:
            return {"error": str(error)}

        return {
            "jobs": [
                job.to_dict(include_result=False)
                for job in jobs
                if job.app_id == application.id
            ]
        }

    def _list_architecture_sheet_artifacts(self, application: ApplicationInstance) -> Dict[str, Any]:
        if application.id != "software-factory":
            return {"error": "architecture sheets are only available for the software-factory app"}

        artifacts = FileArchitectureArtifactStore(application).list_architecture_sheets()
        return {"artifacts": [artifact.to_dict() for artifact in artifacts]}

    def _send_architecture_sheet_artifact_response(
        self,
        application: ApplicationInstance,
        artifact_id: str,
    ) -> None:
        if application.id != "software-factory":
            self._send_json(
                {"error": "architecture sheets are only available for the software-factory app"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        payload = FileArchitectureArtifactStore(application).load_architecture_sheet_payload(artifact_id)
        if payload is None:
            self._send_json({"error": "architecture sheet artifact not found"}, status=HTTPStatus.NOT_FOUND)
            return

        self._send_json(payload)

    def _send_architecture_job_response(self, application: ApplicationInstance, job_id: str) -> None:
        if application.id != "software-factory":
            self._send_json(
                {"error": "architecture-sheet jobs are only available for the software-factory app"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            job = self._architecture_job_store().get(job_id)
        except ArchitectureGenerationJobStoreError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if job is None or job.app_id != application.id:
            self._send_json({"error": "architecture generation job not found"}, status=HTTPStatus.NOT_FOUND)
            return

        self._send_json({"job": job.to_dict()})

    def _send_architecture_job_action_response(
        self,
        application: ApplicationInstance,
        job_id: str,
        action: str,
    ) -> None:
        if application.id != "software-factory":
            self._send_json(
                {"error": "architecture-sheet jobs are only available for the software-factory app"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            job = self._architecture_job_store().get(job_id)
        except ArchitectureGenerationJobStoreError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if job is None or job.app_id != application.id:
            self._send_json({"error": "architecture generation job not found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            if action == "cancel":
                if not job.can_cancel():
                    self._send_json(
                        {"error": "architecture generation job is already finished"},
                        status=HTTPStatus.CONFLICT,
                    )
                    return
                job.cancel("Job wurde durch den Benutzer abgebrochen.")
                self._architecture_job_store().save(job)
                self._send_json({"job": job.to_dict()})
                return

            if action == "retry":
                if not job.can_retry():
                    self._send_json(
                        {"error": "only failed or canceled jobs can be retried"},
                        status=HTTPStatus.CONFLICT,
                    )
                    return
                llm_provider = create_llm_provider(self.settings)
                retry_job = ArchitectureGenerationJob.create(
                    description=job.description,
                    generation_mode=job.generation_mode,
                    app_id=application.id,
                    llm_provider=getattr(llm_provider, "name", "none"),
                    llm_model=getattr(llm_provider, "model", "none"),
                )
                retry_job.add_log(f"Retry von Job {job.id}.")
                self._architecture_job_store().save(retry_job)
                self._send_json({"job": retry_job.to_dict(), "source_job_id": job.id}, status=HTTPStatus.ACCEPTED)
                return
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.CONFLICT)
            return
        except ArchitectureGenerationJobStoreError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json({"error": "unsupported architecture job action"}, status=HTTPStatus.NOT_FOUND)

    def _send_architecture_job_events_response(self, application: ApplicationInstance, job_id: str) -> None:
        if application.id != "software-factory":
            self._send_json(
                {"error": "architecture-sheet jobs are only available for the software-factory app"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            initial_job = self._architecture_job_store().get(job_id)
        except ArchitectureGenerationJobStoreError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if initial_job is None or initial_job.app_id != application.id:
            self._send_json({"error": "architecture generation job not found"}, status=HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_updated_at = ""
        job = initial_job

        while True:
            if job.updated_at.isoformat() != last_updated_at:
                last_updated_at = job.updated_at.isoformat()
                if not self._write_sse_event("job", {"job": job.to_dict()}):
                    self.close_connection = True
                    return

            if job.status in TERMINAL_JOB_STATUSES:
                self.close_connection = True
                return

            time.sleep(self.settings.job_stream_poll_seconds)

            try:
                next_job = self._architecture_job_store().get(job_id)
            except ArchitectureGenerationJobStoreError as error:
                self._write_sse_event("error", {"error": str(error)})
                self.close_connection = True
                return

            if next_job is None or next_job.app_id != application.id:
                self._write_sse_event("error", {"error": "architecture generation job not found"})
                self.close_connection = True
                return

            job = next_job

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

    def _list_workflows(self, application: ApplicationInstance) -> Dict[str, Any]:
        workflow_dir = application.template_dir / "workflows"
        workflows = []
        for path in sorted(workflow_dir.glob("*.yaml")):
            workflow_id = path.stem
            if not self._is_safe_workflow_id(workflow_id):
                continue
            try:
                workflow_version = load_software_factory_workflow(application, workflow_id=workflow_id)
            except WorkflowBlueprintError as error:
                workflows.append(
                    {
                        "id": workflow_id,
                        "status": "invalid",
                        "error": str(error),
                        "path": path.relative_to(application.template_dir).as_posix(),
                    }
                )
                continue
            workflows.append(self._workflow_summary(application, workflow_id, workflow_version))
        return {"app_id": application.id, "workflows": workflows}

    def _send_workflow_detail_response(self, application: ApplicationInstance, workflow_id: str) -> None:
        workflow_version = self._load_workflow_or_404(application, workflow_id)
        if workflow_version is None:
            return
        self._send_json(
            {
                "app_id": application.id,
                "workflow_id": workflow_id,
                "workflow": workflow_version.to_dict(),
                "validation": self._validate_workflow_version(workflow_version),
            }
        )

    def _send_workflow_action_response(
        self,
        application: ApplicationInstance,
        workflow_id: str,
        action: str,
    ) -> None:
        workflow_version = self._load_workflow_or_404(application, workflow_id)
        if workflow_version is None:
            return

        if action == "validate":
            self._send_json(
                {
                    "app_id": application.id,
                    "workflow_id": workflow_id,
                    "validation": self._validate_workflow_version(workflow_version),
                }
            )
            return

        if action == "test-runs":
            payload = self._read_json_body()
            responses = payload.get("responses", [])
            if not isinstance(responses, list):
                self._send_json({"error": "responses must be a list"}, status=HTTPStatus.BAD_REQUEST)
                return

            initial_input = payload.get("input", {})
            if not isinstance(initial_input, dict):
                self._send_json({"error": "input must be an object"}, status=HTTPStatus.BAD_REQUEST)
                return
            description = str(payload.get("description", "")).strip()
            if description and "description" not in initial_input:
                initial_input = {**initial_input, "description": description}
            if "description" not in initial_input:
                initial_input = {**initial_input, "description": "Admin API Testlauf."}

            engine = LinearWorkflowEngine(provider_adapter=FakeLLMProviderAdapter(responses))
            run = engine.run(workflow_version, initial_input)
            run.started_by = str(payload.get("started_by", "workflow-admin-api"))
            try:
                self._workflow_store().save_run(run)
            except WorkflowStoreError as error:
                self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json(
                {
                    "app_id": application.id,
                    "workflow_id": workflow_id,
                    "run": run.to_dict(),
                },
                status=HTTPStatus.CREATED,
            )
            return

        if action == "runs":
            payload = self._read_json_body()
            initial_input = payload.get("input", {})
            if not isinstance(initial_input, dict):
                self._send_json({"error": "input must be an object"}, status=HTTPStatus.BAD_REQUEST)
                return
            description = str(payload.get("description", "")).strip()
            if description and "description" not in initial_input:
                initial_input = {**initial_input, "description": description}
            if "description" not in initial_input:
                self._send_json({"error": "description is required"}, status=HTTPStatus.BAD_REQUEST)
                return

            run = WorkflowRun(
                workflow_version=workflow_version,
                initial_input=initial_input,
                started_by=str(payload.get("started_by", "workflow-admin-api")),
            )
            try:
                self._workflow_store().save_run(run)
            except WorkflowStoreError as error:
                self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            self._send_json(
                {
                    "app_id": application.id,
                    "workflow_id": workflow_id,
                    "run": run.to_dict(),
                },
                status=HTTPStatus.ACCEPTED,
            )
            return

        self._send_json({"error": "unsupported workflow action"}, status=HTTPStatus.NOT_FOUND)

    def _send_workflow_run_response(
        self,
        application: ApplicationInstance,
        workflow_id: str,
        run_id: str = "",
    ) -> None:
        if not self._is_safe_workflow_id(workflow_id):
            self._send_json({"error": "workflow_id contains unsupported characters"}, status=HTTPStatus.BAD_REQUEST)
            return
        workflow_version = self._load_workflow_or_404(application, workflow_id)
        if workflow_version is None:
            return

        if run_id:
            try:
                run = self._workflow_store().get_run(run_id)
            except WorkflowStoreError as error:
                self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            if run is None:
                self._send_json({"error": "workflow run not found"}, status=HTTPStatus.NOT_FOUND)
                return
            if run.workflow_version.workflow.slug != workflow_version.workflow.slug:
                self._send_json({"error": "workflow run not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(
                {
                    "app_id": application.id,
                    "workflow_id": workflow_id,
                    "run": run.to_dict(),
                }
            )
            return

        try:
            runs = self._workflow_store().list_runs(workflow_slug=workflow_version.workflow.slug)
        except WorkflowStoreError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_json(
            {
                "app_id": application.id,
                "workflow_id": workflow_id,
                "runs": [self._workflow_run_summary(run) for run in runs],
            }
        )

    def _load_workflow_or_404(
        self,
        application: ApplicationInstance,
        workflow_id: str,
    ) -> Optional[WorkflowVersion]:
        if not self._is_safe_workflow_id(workflow_id):
            self._send_json({"error": "workflow_id contains unsupported characters"}, status=HTTPStatus.BAD_REQUEST)
            return None
        try:
            return load_software_factory_workflow(application, workflow_id=workflow_id)
        except WorkflowBlueprintError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.NOT_FOUND)
            return None

    def _workflow_summary(
        self,
        application: ApplicationInstance,
        workflow_id: str,
        workflow_version: WorkflowVersion,
    ) -> Dict[str, Any]:
        validation = self._validate_workflow_version(workflow_version)
        return {
            "id": workflow_id,
            "name": workflow_version.workflow.name,
            "slug": workflow_version.workflow.slug,
            "description": workflow_version.workflow.description,
            "status": workflow_version.status,
            "workflow_status": workflow_version.workflow.status,
            "version_number": workflow_version.version_number,
            "final_output_key": workflow_version.final_output_key,
            "step_count": len(workflow_version.steps),
            "validation": validation,
            "path": (application.template_dir / "workflows" / f"{workflow_id}.yaml")
            .relative_to(application.template_dir)
            .as_posix(),
        }

    def _validate_workflow_version(self, workflow_version: WorkflowVersion) -> Dict[str, Any]:
        result = WorkflowVersionValidator().validate(workflow_version)
        return {"valid": result.valid, "errors": result.errors, "warnings": result.warnings}

    def _workflow_run_summary(self, run: WorkflowRun) -> Dict[str, Any]:
        return {
            "id": run.id,
            "workflow": {
                "name": run.workflow_version.workflow.name,
                "slug": run.workflow_version.workflow.slug,
                "version_number": run.workflow_version.version_number,
            },
            "status": run.status,
            "started_by": run.started_by,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_summary": run.error_summary,
            "step_count": len(run.step_runs),
            "artifact_count": len(run.artifacts),
        }

    def _send_metrics_response(self) -> None:
        try:
            jobs = self._architecture_job_store().list(limit=500)
            payload = render_prometheus_metrics(self.settings, jobs)
        except Exception as error:
            safe_reason = str(error).replace("\\", "\\\\").replace('"', '\\"')
            payload = (
                "# HELP buildbybricks_metrics_error Metrics collection error.\n"
                "# TYPE buildbybricks_metrics_error gauge\n"
                f'buildbybricks_metrics_error{{reason="{safe_reason}"}} 1\n'
            )

        self._send_text(payload, content_type="text/plain; version=0.0.4; charset=utf-8")

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

    def _parse_workflow_detail_route(self, remainder: str) -> Optional[str]:
        parts = remainder.strip("/").split("/")

        if len(parts) == 2 and parts[0] == "workflows" and parts[1]:
            return parts[1]

        return None

    def _parse_workflow_action_route(self, remainder: str) -> Optional[Dict[str, str]]:
        parts = remainder.strip("/").split("/")

        if (
            len(parts) == 3
            and parts[0] == "workflows"
            and parts[1]
            and parts[2] in {"validate", "test-runs", "runs"}
        ):
            return {"workflow_id": parts[1], "action": parts[2]}

        return None

    def _parse_workflow_run_route(self, remainder: str) -> Optional[Dict[str, str]]:
        parts = remainder.strip("/").split("/")

        if len(parts) == 3 and parts[0] == "workflows" and parts[1] and parts[2] == "runs":
            return {"workflow_id": parts[1]}

        if len(parts) == 4 and parts[0] == "workflows" and parts[1] and parts[2] == "runs" and parts[3]:
            return {"workflow_id": parts[1], "run_id": parts[3]}

        return None

    def _parse_architecture_job_route(self, remainder: str) -> Optional[str]:
        parts = remainder.strip("/").split("/")

        if len(parts) == 3 and parts[0] == "architecture-sheet" and parts[1] == "jobs" and parts[2]:
            return parts[2]

        return None

    def _parse_architecture_sheet_artifact_route(self, remainder: str) -> Optional[str]:
        parts = remainder.strip("/").split("/")

        if len(parts) == 2 and parts[0] == "architecture-sheets" and parts[1]:
            return parts[1]

        return None

    def _parse_architecture_job_events_route(self, remainder: str) -> Optional[str]:
        parts = remainder.strip("/").split("/")

        if (
            len(parts) == 4
            and parts[0] == "architecture-sheet"
            and parts[1] == "jobs"
            and parts[2]
            and parts[3] == "events"
        ):
            return parts[2]

        return None

    def _parse_architecture_job_action_route(self, remainder: str) -> Optional[Dict[str, str]]:
        parts = remainder.strip("/").split("/")

        if (
            len(parts) == 4
            and parts[0] == "architecture-sheet"
            and parts[1] == "jobs"
            and parts[2]
            and parts[3] in {"cancel", "retry"}
        ):
            return {"job_id": parts[2], "action": parts[3]}

        return None

    def _architecture_job_store(self) -> Any:
        if self.architecture_job_store is not None:
            return self.architecture_job_store

        self.architecture_job_store = PostgresArchitectureGenerationJobStore(self.settings.database_url)
        self.architecture_job_store.initialize()
        return self.architecture_job_store

    def _workflow_store(self) -> Any:
        if self.workflow_store is not None:
            return self.workflow_store

        self.workflow_store = PostgresWorkflowStore(self.settings.database_url)
        self.workflow_store.initialize()
        return self.workflow_store

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

    def _is_safe_workflow_id(self, workflow_id: str) -> bool:
        return bool(SAFE_WORKFLOW_ID_PATTERN.fullmatch(workflow_id))

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

    def _send_text(
        self,
        payload: str,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        body = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_sse_event(self, event_name: str, payload: Dict[str, Any]) -> bool:
        body = f"event: {event_name}\ndata: {json.dumps(payload)}\n\n".encode("utf-8")
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return False
        return True


def create_server(
    settings: Optional[Settings] = None,
    architecture_job_store: Any = None,
    workflow_store: Any = None,
) -> ThreadingHTTPServer:
    """Create a local HTTP server for API and frontend requests."""
    active_settings = settings or create_app_settings()
    frontend_dir = Path(active_settings.frontend_dir)
    frontend_dir.mkdir(parents=True, exist_ok=True)
    handler = partial(
        AgenticRagRequestHandler,
        settings=active_settings,
        architecture_job_store=architecture_job_store,
        workflow_store=workflow_store,
    )
    return ThreadingHTTPServer((active_settings.host, active_settings.port), handler)


def main() -> None:
    settings = create_app_settings()
    server = create_server(settings)
    print(f"{settings.app_name} listening on http://{settings.host}:{settings.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
