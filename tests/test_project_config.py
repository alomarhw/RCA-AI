from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    from pip._vendor import tomli as tomllib


def test_pyproject_toml_is_valid_and_includes_web_assets() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert payload["project"]["name"] == "rca-ai"
    assert payload["project"]["scripts"]["rca-ai"] == "rca_ai.cli:main"
    assert payload["tool"]["setuptools"]["package-data"]["rca_ai"] == ["web/*"]
