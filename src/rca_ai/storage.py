"""Simple JSON storage used by the initial RCA-AI implementation."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

from rca_ai.models import Project


class JsonProjectStore:
    """Persist project metadata to a local JSON file.

    This is intentionally small and replaceable. A production deployment should
    swap this with PostgreSQL while keeping the same domain model boundaries.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[Project]:
        with self._lock:
            return [Project.from_dict(item) for item in self._read().get("projects", [])]

    def get_project(self, project_id: str) -> Project:
        for project in self.list_projects():
            if project.id == project_id:
                return project
        raise KeyError(f"Project not found: {project_id}")

    def save_project(self, project: Project) -> Project:
        with self._lock:
            data = self._read()
            projects = data.setdefault("projects", [])
            for index, item in enumerate(projects):
                if item["id"] == project.id:
                    projects[index] = project.to_dict()
                    self._write(data)
                    return project
            projects.append(project.to_dict())
            self._write(data)
            return project

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"projects": []}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temporary.replace(self.path)
