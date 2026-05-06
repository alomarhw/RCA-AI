from pathlib import Path

from rca_ai.latex_indexer import LatexIndexer


def test_latex_indexer_extracts_sections_citations_and_includes(tmp_path: Path) -> None:
    (tmp_path / "main.tex").write_text(
        r"""
\documentclass{article}
\begin{document}
\section{Introduction}
We cite \cite{smith2024,doe2025}.
\input{method}
\begin{figure}\caption{System overview}\label{fig:system}\end{figure}
\end{document}
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "method.tex").write_text(
        r"""
\section{Method}
More text \citep{roe2026}.
\begin{table}\caption{Results}\label{tab:results}\end{table}
""".strip(),
        encoding="utf-8",
    )

    index = LatexIndexer().index_project("project-1", tmp_path)

    assert index.root_file == "main.tex"
    assert [section["title"] for section in index.sections] == ["Introduction", "Method"]
    assert index.citations == ["doe2025", "roe2026", "smith2024"]
    assert index.labels == ["fig:system", "tab:results"]
    assert index.figures == ["System overview"]
    assert index.tables == ["Results"]
