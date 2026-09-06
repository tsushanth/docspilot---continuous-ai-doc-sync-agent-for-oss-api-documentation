"""Shared pytest fixtures.

Builds a throwaway git repo under a temp directory from the plain-file
snapshots in tests/fixtures/sample_repo/{before,after}/, so the repo (and its
.git dir) is never itself committed to this project's history.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sample_repo"


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def sample_repo(tmp_path):
    """Create a temp git repo with two commits: `before` state, then `after`
    state (simulating a merged PR that renamed a function without updating
    docs). Returns (repo_path, base_sha, head_sha).
    """
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    _run_git(repo, "init", "-q")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "DocsPilot Test")

    shutil.copytree(FIXTURE_DIR / "before", repo, dirs_exist_ok=True)
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "-q", "-m", "before: initial API and docs")
    base_sha = _run_git(repo, "rev-parse", "HEAD")

    shutil.copytree(FIXTURE_DIR / "after", repo, dirs_exist_ok=True)
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "-q", "-m", "after: rename get_user to fetch_user")
    head_sha = _run_git(repo, "rev-parse", "HEAD")

    return str(repo), base_sha, head_sha
