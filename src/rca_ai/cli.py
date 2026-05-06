"""Command-line interface for the RCA-AI implementation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from rca_ai.platform import ResearchPaperPlatform


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RCA-AI research-paper writing assistant")
    parser.add_argument("--data-dir", default=os.environ.get("RCA_AI_DATA_DIR", ".rca-ai"))
    subcommands = parser.add_subparsers(dest="command", required=True)

    create = subcommands.add_parser("create-project", help="Register an Overleaf Git project")
    create.add_argument("name")
    create.add_argument("overleaf_git_url")
    create.add_argument("--default-branch", default="main")

    subcommands.add_parser("list-projects", help="List registered projects")

    clone = subcommands.add_parser("clone", help="Clone an Overleaf Git project")
    clone.add_argument("project_id")
    clone.add_argument("--token", default=os.environ.get("OVERLEAF_GIT_TOKEN"))

    pull = subcommands.add_parser("pull", help="Pull the latest Overleaf Git changes")
    pull.add_argument("project_id")

    index = subcommands.add_parser("index", help="Index a LaTeX manuscript")
    index.add_argument("project_id")
    index.add_argument("--root-file")

    suggest = subcommands.add_parser("suggest", help="Generate a reviewable AI patch")
    suggest.add_argument("project_id")
    suggest.add_argument("target_file")
    suggest.add_argument("prompt")
    suggest.add_argument("--agent-type", default="clarity")
    suggest.add_argument("--root-file")

    serve = subcommands.add_parser("serve", help="Run the minimal JSON HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)

    args = parser.parse_args(argv)
    platform = ResearchPaperPlatform(Path(args.data_dir))

    if args.command == "create-project":
        return _print(platform.create_project(args.name, args.overleaf_git_url, args.default_branch).to_dict())
    if args.command == "list-projects":
        return _print([project.to_dict() for project in platform.list_projects()])
    if args.command == "clone":
        return _print(platform.clone_project(args.project_id, token=args.token).to_dict())
    if args.command == "pull":
        return _print(platform.pull_project(args.project_id).to_dict())
    if args.command == "index":
        return _print(platform.index_project(args.project_id, root_file=args.root_file).to_dict())
    if args.command == "suggest":
        patch = platform.suggest_patch(
            args.project_id,
            agent_type=args.agent_type,
            prompt=args.prompt,
            target_file=args.target_file,
            root_file=args.root_file,
        )
        return _print(patch.to_dict())
    if args.command == "serve":
        from rca_ai.server import run_server

        run_server(platform, host=args.host, port=args.port)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _print(payload: Any) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
