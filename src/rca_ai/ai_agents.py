"""AI-assistance orchestration and safe deterministic fallbacks.

This module defines the seams for model-backed writing agents. The current
implementation returns reviewable, deterministic patches and comments so the
platform is runnable without requiring a model provider key.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from rca_ai.models import AIAssistRequest, ManuscriptIndex, SuggestedPatch


class ResearchWritingAgents:
    """Coordinate paper-planning, revision, reviewer, and citation agents."""

    def propose_patch(self, request: AIAssistRequest, project_path: Path, index: ManuscriptIndex) -> SuggestedPatch:
        target = project_path / request.target_file
        if not target.exists():
            raise FileNotFoundError(f"Target file not found: {request.target_file}")
        original = target.read_text(encoding="utf-8")
        revised = self._revise_text(original, request, index)
        diff = "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                revised.splitlines(keepends=True),
                fromfile=f"a/{request.target_file}",
                tofile=f"b/{request.target_file}",
            )
        )
        if not diff:
            diff = self._comment_only_diff(request.target_file, original)
        return SuggestedPatch(
            request_id=request.id,
            file_path=request.target_file,
            diff=diff,
            rationale=self._rationale(request, index),
            risk_level="low" if request.agent_type in {"reviewer", "clarity"} else "medium",
        )

    def reviewer_report(self, index: ManuscriptIndex) -> list[str]:
        """Generate actionable reviewer-style comments from the manuscript index."""

        comments: list[str] = []
        section_titles = {section["title"].lower() for section in index.sections}
        if "abstract" not in section_titles:
            comments.append("Add or strengthen the abstract so the contribution, method, and results are clear.")
        if not any("related" in title for title in section_titles):
            comments.append("Add a related-work section or make the literature positioning more explicit.")
        if len(index.citations) < 5:
            comments.append("Citation coverage appears thin; verify that key claims are source-backed.")
        if not index.figures:
            comments.append("Consider whether a system diagram, method figure, or results plot would improve readability.")
        if not comments:
            comments.append("The manuscript has the expected high-level structure; focus review on claim strength and evidence quality.")
        return comments

    def _revise_text(self, original: str, request: AIAssistRequest, index: ManuscriptIndex) -> str:
        if request.agent_type == "reviewer":
            report = "\n".join(f"% RCA-AI reviewer note: {comment}" for comment in self.reviewer_report(index))
            return f"{report}\n{original}" if not original.startswith("% RCA-AI reviewer note:") else original

        if request.agent_type == "outline":
            outline = self._outline(index)
            return f"{outline}\n\n{original}" if "RCA-AI proposed outline" not in original else original

        # Conservative clarity fallback: add an author-visible TODO rather than
        # rewriting scientific claims without model-backed context.
        todo = f"% RCA-AI suggestion: {request.prompt.strip()}"
        return f"{todo}\n{original}" if todo not in original else original

    def _outline(self, index: ManuscriptIndex) -> str:
        existing = ", ".join(section["title"] for section in index.sections) or "no sections detected"
        return (
            "% RCA-AI proposed outline\n"
            "% 1. State the research problem and why it matters.\n"
            "% 2. Summarize the gap in prior work with citations.\n"
            "% 3. Present the method and assumptions.\n"
            "% 4. Report evidence, experiments, or analysis.\n"
            "% 5. Discuss limitations and future work.\n"
            f"% Existing sections detected: {existing}"
        )

    def _rationale(self, request: AIAssistRequest, index: ManuscriptIndex) -> str:
        return (
            f"Agent '{request.agent_type}' generated a reviewable LaTeX diff for '{request.prompt}'. "
            f"The manuscript index contains {len(index.sections)} sections, "
            f"{len(index.citations)} citations, {len(index.figures)} figures, and {len(index.tables)} tables."
        )

    def _comment_only_diff(self, target_file: str, original: str) -> str:
        return "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                original.splitlines(keepends=True),
                fromfile=f"a/{target_file}",
                tofile=f"b/{target_file}",
            )
        )
