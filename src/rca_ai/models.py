"""Domain models for RCA-AI.

The models are intentionally dependency-free so they can be reused by the CLI,
API server, background workers, and tests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


class ProjectStatus(str, Enum):
    """Lifecycle state for an Overleaf-backed project."""

    CREATED = "created"
    CLONED = "cloned"
    INDEXED = "indexed"
    ERROR = "error"


class PatchStatus(str, Enum):
    """Validation or review state for an AI-generated patch."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass(slots=True)
class Project:
    """A research-paper project synchronized with an Overleaf Git remote."""

    name: str
    overleaf_git_url: str
    default_branch: str = "main"
    id: str = field(default_factory=lambda: str(uuid4()))
    status: ProjectStatus = ProjectStatus.CREATED
    workspace_path: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    last_synced_at: str | None = None

    def mark_updated(self) -> None:
        self.updated_at = utc_now()

    def local_path(self, workspace_root: Path) -> Path:
        """Return the local clone path for this project."""

        return Path(self.workspace_path) if self.workspace_path else workspace_root / self.id

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Project":
        data = dict(payload)
        data["status"] = ProjectStatus(data.get("status", ProjectStatus.CREATED))
        return cls(**data)


@dataclass(slots=True)
class ManuscriptIndex:
    """Section, citation, figure, table, and label metadata extracted from LaTeX."""

    project_id: str
    root_file: str
    sections: list[dict[str, str]]
    citations: list[str]
    labels: list[str]
    figures: list[str]
    tables: list[str]
    indexed_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AIAssistRequest:
    """A request for AI support on a manuscript."""

    project_id: str
    agent_type: str
    prompt: str
    target_file: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class SuggestedPatch:
    """Reviewable AI suggestion represented as a unified diff."""

    request_id: str
    file_path: str
    diff: str
    rationale: str
    risk_level: str = "medium"
    status: PatchStatus = PatchStatus.PROPOSED
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload
