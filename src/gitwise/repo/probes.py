"""Read-only git probes for pre/post checks."""

from __future__ import annotations

from pathlib import Path

from gitwise.repo.git_runner import run_git_optional


def ref_exists(ref: str, *, cwd: Path | str | None = None) -> bool:
    return run_git_optional(["rev-parse", "--verify", ref], cwd=cwd) is not None


def local_branch_exists(name: str, *, cwd: Path | str | None = None) -> bool:
    return ref_exists(f"refs/heads/{name}", cwd=cwd)


def remote_branch_exists(
    remote: str, name: str, *, cwd: Path | str | None = None
) -> bool:
    return ref_exists(f"refs/remotes/{remote}/{name}", cwd=cwd)


def list_local_branches(*, cwd: Path | str | None = None) -> list[str]:
    out = run_git_optional(["branch", "--format=%(refname:short)"], cwd=cwd)
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def tag_exists(name: str, *, cwd: Path | str | None = None) -> bool:
    return ref_exists(f"refs/tags/{name}", cwd=cwd)


def has_commit_history(*, cwd: Path | str | None = None) -> bool:
    return run_git_optional(["rev-parse", "HEAD"], cwd=cwd) is not None


def parent_commit_exists(*, cwd: Path | str | None = None) -> bool:
    return ref_exists("HEAD~1", cwd=cwd)


def path_in_worktree(path: str, *, cwd: Path | str | None = None) -> bool:
    """True if path exists as tracked, modified, or untracked."""
    from pathlib import Path as P

    root = run_git_optional(["rev-parse", "--show-toplevel"], cwd=cwd)
    if not root:
        return False
    full = P(root) / path
    if full.exists():
        return True
    listed = run_git_optional(["ls-files", "--error-unmatch", path], cwd=cwd)
    return listed is not None


def clone_target_exists(url: str, *, cwd: Path | str | None = None) -> str | None:
    """Return directory name that clone would create, if it already exists."""
    from pathlib import Path as P
    import re

    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    if not name:
        return None
    base = P(cwd) if cwd else P.cwd()
    target = base / name
    return name if target.exists() else None
