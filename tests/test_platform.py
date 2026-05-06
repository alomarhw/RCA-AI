from pathlib import Path

from rca_ai.platform import ResearchPaperPlatform


def test_platform_registers_indexes_and_suggests_patch(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    platform = ResearchPaperPlatform(data_dir)
    project = platform.create_project("Demo Paper", "https://git.overleaf.com/demo", "main")
    project_path = data_dir / "workspaces" / project.id
    project_path.mkdir(parents=True)
    project.workspace_path = str(project_path)
    platform.store.save_project(project)

    (project_path / "main.tex").write_text(
        r"""
\documentclass{article}
\begin{document}
\section{Introduction}
This is a draft with \cite{paper2026}.
\end{document}
""".strip(),
        encoding="utf-8",
    )

    index = platform.index_project(project.id)
    patch = platform.suggest_patch(
        project.id,
        agent_type="reviewer",
        prompt="Review the manuscript for paper quality.",
        target_file="main.tex",
    )

    assert index.sections[0]["title"] == "Introduction"
    assert "RCA-AI reviewer note" in patch.diff
    assert patch.file_path == "main.tex"
    assert "Review the manuscript" in patch.rationale


def test_platform_creates_demo_project_that_can_be_indexed(tmp_path: Path) -> None:
    platform = ResearchPaperPlatform(tmp_path / "data")

    project = platform.create_demo_project("Interactive Demo")
    index = platform.index_project(project.id, root_file="main.tex")

    assert project.workspace_path is not None
    assert index.root_file == "main.tex"
    assert any(section["title"] == "Introduction" for section in index.sections)
    assert "demo2026" in index.citations
