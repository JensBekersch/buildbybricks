"""Application entrypoint for the agentic RAG template."""

from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any, Dict, Optional

from agentic_rag_template.api.schemas import ChatRequest, ChatResponse
from agentic_rag_template.config import Settings


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
        if self.path == "/health":
            self._send_json({"status": "ok", "app": self.settings.app_name})
            return

        if self.path == "/":
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
