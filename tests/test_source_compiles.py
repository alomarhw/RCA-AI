import py_compile
from pathlib import Path


def test_source_files_compile() -> None:
    for source_file in Path("src").rglob("*.py"):
        py_compile.compile(str(source_file), doraise=True)


def test_cli_help_builds_without_duplicate_subcommands() -> None:
    from rca_ai.cli import main

    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
