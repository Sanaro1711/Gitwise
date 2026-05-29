"""Read merge / conflict state from the repository."""

from __future__ import annotations

from pathlib import Path

from gitwise.repo.git_runner import run_git_optional


def unmerged_files(*, cwd: Path | str | None = None) -> list[str]:
    """Paths with unresolved merge conflicts."""
    out = run_git_optional(["diff", "--name-only", "--diff-filter=U"], cwd=cwd)
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def short_status(*, cwd: Path | str | None = None) -> str:
    """Porcelain status for display."""
    return run_git_optional(["status", "--short"], cwd=cwd) or "(no output)"


def file_diff(path: str, *, cwd: Path | str | None = None) -> str:
    """Combined diff for a path (includes conflict markers)."""
    return run_git_optional(["diff", path], cwd=cwd) or ""


def merge_head_branch(*, cwd: Path | str | None = None) -> str | None:
    """Remote side of an in-progress merge, if available."""
    return run_git_optional(["name-rev", "--name-only", "MERGE_HEAD"], cwd=cwd)


def latest_stash_ref(*, cwd: Path | str | None = None) -> str | None:
    out = run_git_optional(["stash", "list", "-1"], cwd=cwd)
    if not out:
        return None
    if out.startswith("stash@"):
        return out.split(":", 1)[0].strip()
    return "stash@{0}"
