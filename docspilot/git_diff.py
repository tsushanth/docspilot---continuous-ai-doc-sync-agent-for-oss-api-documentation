"""Subprocess wrappers around `git` for extracting changes between two refs."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class FileDiff:
    path: str
    status: str  # "A", "M", "D", "R" (as reported by git --name-status)
    hunk: str  # unified diff text for this file only


def _run_git(repo: str, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def changed_files(repo: str, base: str, head: str) -> list[tuple[str, str]]:
    """Return list of (status, path) changed between base and head."""
    output = _run_git(repo, ["diff", "--name-status", f"{base}..{head}"])
    files = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        files.append((status[0], path))
    return files


def unified_diff(repo: str, base: str, head: str) -> str:
    """Return the full unified diff between base and head."""
    return _run_git(repo, ["diff", f"{base}..{head}"])


def file_hunks(repo: str, base: str, head: str) -> list[FileDiff]:
    """Return per-file unified diff hunks between base and head."""
    full_diff = unified_diff(repo, base, head)
    statuses = dict((path, status) for status, path in changed_files(repo, base, head))

    hunks: list[FileDiff] = []
    current_path = None
    current_lines: list[str] = []

    def flush():
        if current_path is not None:
            hunks.append(
                FileDiff(
                    path=current_path,
                    status=statuses.get(current_path, "M"),
                    hunk="\n".join(current_lines),
                )
            )

    for line in full_diff.splitlines():
        if line.startswith("diff --git "):
            flush()
            # "diff --git a/path b/path"
            parts = line.split(" ")
            b_path = parts[-1]
            current_path = b_path[2:] if b_path.startswith("b/") else b_path
            current_lines = [line]
        else:
            current_lines.append(line)
    flush()

    return hunks
