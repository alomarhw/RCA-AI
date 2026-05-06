"""LaTeX manuscript indexing for RCA-AI."""

from __future__ import annotations

import re
from pathlib import Path

from rca_ai.models import ManuscriptIndex

_SECTION_RE = re.compile(r"\\(part|chapter|section|subsection|subsubsection)\*?\{([^{}]+)\}")
_CITE_RE = re.compile(r"\\(?:cite|citet|citep|autocite|parencite|textcite)(?:\[[^\]]*\])*\{([^{}]+)\}")
_LABEL_RE = re.compile(r"\\label\{([^{}]+)\}")
_INPUT_RE = re.compile(r"\\(?:input|include)\{([^{}]+)\}")
_FIGURE_RE = re.compile(r"\\begin\{figure\}(.*?)\\end\{figure\}", re.DOTALL)
_TABLE_RE = re.compile(r"\\begin\{table\}(.*?)\\end\{table\}", re.DOTALL)
_CAPTION_RE = re.compile(r"\\caption(?:\[[^\]]*\])?\{([^{}]+)\}")


class LatexIndexer:
    """Extract a lightweight manuscript index from a LaTeX project."""

    def index_project(self, project_id: str, project_path: Path, root_file: str | None = None) -> ManuscriptIndex:
        root = self._find_root(project_path, root_file)
        visited: set[Path] = set()
        combined = self._read_with_includes(root, visited)
        return ManuscriptIndex(
            project_id=project_id,
            root_file=str(root.relative_to(project_path)),
            sections=self._sections(combined),
            citations=self._citations(combined),
            labels=sorted(set(_LABEL_RE.findall(combined))),
            figures=self._captions(_FIGURE_RE.findall(combined)),
            tables=self._captions(_TABLE_RE.findall(combined)),
        )

    def _find_root(self, project_path: Path, root_file: str | None) -> Path:
        if root_file:
            candidate = project_path / root_file
            if not candidate.exists():
                raise FileNotFoundError(f"LaTeX root file not found: {candidate}")
            return candidate

        for name in ("main.tex", "paper.tex", "manuscript.tex"):
            candidate = project_path / name
            if candidate.exists():
                return candidate

        tex_files = sorted(project_path.glob("*.tex"))
        if not tex_files:
            raise FileNotFoundError(f"No .tex files found in {project_path}")
        return tex_files[0]

    def _read_with_includes(self, file_path: Path, visited: set[Path]) -> str:
        file_path = file_path.resolve()
        if file_path in visited:
            return ""
        visited.add(file_path)
        text = file_path.read_text(encoding="utf-8")

        def replace_include(match: re.Match[str]) -> str:
            include_path = match.group(1)
            nested = file_path.parent / include_path
            if nested.suffix != ".tex":
                nested = nested.with_suffix(".tex")
            if not nested.exists():
                return match.group(0)
            return self._read_with_includes(nested, visited)

        return _INPUT_RE.sub(replace_include, text)

    def _sections(self, text: str) -> list[dict[str, str]]:
        return [{"level": level, "title": title.strip()} for level, title in _SECTION_RE.findall(text)]

    def _citations(self, text: str) -> list[str]:
        keys: list[str] = []
        for group in _CITE_RE.findall(text):
            keys.extend(key.strip() for key in group.split(",") if key.strip())
        return sorted(set(keys))

    def _captions(self, environments: list[str]) -> list[str]:
        captions: list[str] = []
        for environment in environments:
            match = _CAPTION_RE.search(environment)
            captions.append(match.group(1).strip() if match else "")
        return captions
