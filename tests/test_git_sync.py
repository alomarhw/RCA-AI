from pathlib import Path

from rca_ai.git_sync import OverleafGitSync


def test_overleaf_git_token_is_embedded_and_url_escaped(tmp_path: Path) -> None:
    sync = OverleafGitSync(tmp_path)

    url = sync._with_token("https://git.overleaf.com/project-id", "token/value")

    assert url == "https://git:token%2Fvalue@git.overleaf.com/project-id"


def test_overleaf_git_token_is_not_added_to_non_http_remotes(tmp_path: Path) -> None:
    sync = OverleafGitSync(tmp_path)

    url = sync._with_token("git@git.overleaf.com:project-id", "token")

    assert url == "git@git.overleaf.com:project-id"
