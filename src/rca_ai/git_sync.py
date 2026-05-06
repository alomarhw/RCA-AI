"""Overleaf Git synchronization primitives."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from rca_ai.models import Project, ProjectStatus, utc_now


@dataclass(slots=True)
class GitCommandResult:
    """Captured result from a Git command."""

    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    def assert_success(self) -> "GitCommandResult":
        if self.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(self.args)}\n{self.stderr}")
        return self


class OverleafGitSync:
    """Clone, pull, commit, and push Overleaf projects through Git."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def clone(self, project: Project, token: str | None = None) -> Project:
        destination = project.local_path(self.workspace_root)
        if destination.exists() and (destination / ".git").exists():
            project.status = ProjectStatus.CLONED
            project.workspace_path = str(destination)
            project.mark_updated()
            return project

        remote_url = self._with_token(project.overleaf_git_url, token)
        self._run(["git", "clone", remote_url, str(destination)], redact=token).assert_success()
        project.status = ProjectStatus.CLONED
        project.workspace_path = str(destination)
        project.last_synced_at = utc_now()
        project.mark_updated()
        return project

    def pull(self, project: Project) -> GitCommandResult:
        result = self._run(["git", "pull", "--ff-only"], cwd=project.local_path(self.workspace_root))
        result.assert_success()
        project.last_synced_at = utc_now()
        project.mark_updated()
        return result

    def create_branch(self, project: Project, branch_name: str) -> GitCommandResult:
        return self._run(["git", "checkout", "-B", branch_name], cwd=project.local_path(self.workspace_root)).assert_success()

    def commit_all(self, project: Project, message: str) -> GitCommandResult:
        path = project.local_path(self.workspace_root)
        self._run(["git", "add", "--all"], cwd=path).assert_success()
        return self._run(["git", "commit", "-m", message], cwd=path).assert_success()

    def push(self, project: Project, branch_name: str | None = None) -> GitCommandResult:
        branch = branch_name or project.default_branch
        return self._run(["git", "push", "origin", branch], cwd=project.local_path(self.workspace_root)).assert_success()

    def _run(
        self,
        args: list[str],
        cwd: Path | None = None,
        redact: str | None = None,
    ) -> GitCommandResult:
        env = os.environ.copy()
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        completed = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        safe_args = list(args)
        if redact:
            stdout = stdout.replace(redact, "***")
            stderr = stderr.replace(redact, "***")
            safe_args = [item.replace(redact, "***") for item in safe_args]
        return GitCommandResult(safe_args, completed.returncode, stdout, stderr)

    @staticmethod
    def _with_token(url: str, token: str | None) -> str:
        if not token:
            return url
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"}:
            return url
        if "@" in parts.netloc:
            return url
        netloc = f"git:{quote(token, safe='')}@{parts.netloc}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
