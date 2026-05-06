"""Minimal JSON API server for RCA-AI using only the Python standard library."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from rca_ai.platform import ResearchPaperPlatform


def run_server(platform: ResearchPaperPlatform, host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the RCA-AI JSON API server."""

    class Handler(RCAAIRequestHandler):
        app = platform

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"RCA-AI API listening on http://{host}:{port}")
    server.serve_forever()


class RCAAIRequestHandler(BaseHTTPRequestHandler):
    """Small HTTP handler for project management and manuscript assistance."""

    app: ResearchPaperPlatform

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json({"status": "ok"})
            return
        if parsed.path == "/projects":
            self._json([project.to_dict() for project in self.app.list_projects()])
            return
        if parsed.path.startswith("/projects/") and parsed.path.endswith("/index"):
            project_id = parsed.path.split("/")[2]
            query = parse_qs(parsed.query)
            root_file = query.get("root_file", [None])[0]
            self._json(self.app.index_project(project_id, root_file=root_file).to_dict())
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        try:
            payload = self._payload()
            if parsed.path == "/projects":
                project = self.app.create_project(
                    payload["name"],
                    payload["overleaf_git_url"],
                    payload.get("default_branch", "main"),
                )
                self._json(project.to_dict(), status=201)
                return
            if parsed.path.startswith("/projects/") and parsed.path.endswith("/clone"):
                project_id = parsed.path.split("/")[2]
                self._json(self.app.clone_project(project_id, token=payload.get("token")).to_dict())
                return
            if parsed.path.startswith("/projects/") and parsed.path.endswith("/suggest"):
                project_id = parsed.path.split("/")[2]
                patch = self.app.suggest_patch(
                    project_id,
                    agent_type=payload.get("agent_type", "clarity"),
                    prompt=payload["prompt"],
                    target_file=payload["target_file"],
                    root_file=payload.get("root_file"),
                )
                self._json(patch.to_dict())
                return
        except (KeyError, FileNotFoundError, RuntimeError) as exc:
            self._json({"error": str(exc)}, status=400)
            return
        self._json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        """Silence default request logging to avoid leaking URLs or tokens."""

    def _payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
