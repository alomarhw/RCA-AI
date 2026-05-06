"""Application service layer for RCA-AI."""

from __future__ import annotations

from pathlib import Path

from rca_ai.ai_agents import ResearchWritingAgents
from rca_ai.git_sync import OverleafGitSync
from rca_ai.latex_indexer import LatexIndexer
from rca_ai.models import AIAssistRequest, ManuscriptIndex, Project, ProjectStatus, SuggestedPatch
from rca_ai.storage import JsonProjectStore


class ResearchPaperPlatform:
    """High-level API used by the CLI, HTTP server, and future workers."""

    def __init__(self, data_dir: Path | str = ".rca-ai") -> None:
        self.data_dir = Path(data_dir)
        self.workspace_root = self.data_dir / "workspaces"
        self.store = JsonProjectStore(self.data_dir / "projects.json")
        self.git = OverleafGitSync(self.workspace_root)
        self.indexer = LatexIndexer()
        self.agents = ResearchWritingAgents()

    def create_project(self, name: str, overleaf_git_url: str, default_branch: str = "main") -> Project:
        project = Project(name=name, overleaf_git_url=overleaf_git_url, default_branch=default_branch)
        return self.store.save_project(project)


    def create_demo_project(self, name: str = "Demo Research Paper") -> Project:
        """Create a local demo LaTeX project so users can try RCA-AI without Overleaf."""

        project = Project(
            name=name,
            overleaf_git_url="demo://local-overleaf-project",
            default_branch="main",
            status=ProjectStatus.CLONED,
        )
        project_path = self.workspace_root / project.id
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "main.tex").write_text(
            r"""\documentclass{article}
\title{RCA-AI Demo Paper}
\author{Research Team}
\begin{document}
\maketitle
\begin{abstract}
This short demo paper illustrates how RCA-AI indexes LaTeX and proposes review notes.
\end{abstract}
\section{Introduction}
Writing strong research papers requires clear motivation, evidence, and careful positioning against prior work \cite{demo2026}.
\section{Method}
Our prototype synchronizes projects, indexes manuscript structure, and creates reviewable suggestions.
\section{Results}
The demo workflow shows section extraction, citation detection, and reviewer-style feedback.
\begin{figure}
\caption{Demo RCA-AI workflow}
\label{fig:workflow}
\end{figure}
\bibliographystyle{plain}
\bibliography{refs}
\end{document}
""",
            encoding="utf-8",
        )
        (project_path / "refs.bib").write_text(
            """@misc{demo2026,
  title = {RCA-AI Demo Reference},
  author = {RCA-AI Team},
  year = {2026}
}
""",
            encoding="utf-8",
        )
        project.workspace_path = str(project_path)
        project.mark_updated()
        return self.store.save_project(project)

    def list_projects(self) -> list[Project]:
        return self.store.list_projects()

    def get_project(self, project_id: str) -> Project:
        return self.store.get_project(project_id)

    def clone_project(self, project_id: str, token: str | None = None) -> Project:
        project = self.get_project(project_id)
        project = self.git.clone(project, token=token)
        return self.store.save_project(project)

    def pull_project(self, project_id: str) -> Project:
        project = self.get_project(project_id)
        self.git.pull(project)
        return self.store.save_project(project)

    def index_project(self, project_id: str, root_file: str | None = None) -> ManuscriptIndex:
        project = self.get_project(project_id)
        index = self.indexer.index_project(project.id, project.local_path(self.workspace_root), root_file=root_file)
        project.status = ProjectStatus.INDEXED
        project.mark_updated()
        self.store.save_project(project)
        return index

    def suggest_patch(
        self,
        project_id: str,
        agent_type: str,
        prompt: str,
        target_file: str,
        root_file: str | None = None,
    ) -> SuggestedPatch:
        project = self.get_project(project_id)
        index = self.index_project(project_id, root_file=root_file)
        request = AIAssistRequest(
            project_id=project_id,
            agent_type=agent_type,
            prompt=prompt,
            target_file=target_file,
        )
        return self.agents.propose_patch(request, project.local_path(self.workspace_root), index)
