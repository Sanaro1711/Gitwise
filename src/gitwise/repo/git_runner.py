"""Run git subprocesses safely (no shell, fixed args only)."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(Exception):
    """Git command failed or git is not available."""


def run_git(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = 30.0,
) -> str:
    """Run git with the given argument list; return stripped stdout."""
    cmd = ["git", *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git timed out: {' '.join(cmd)}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise GitError(stderr or f"git {' '.join(args)} failed (code {result.returncode})")

    return (result.stdout or "").strip()


def run_git_optional(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = 30.0,
) -> str | None:
    """Like run_git but returns None on failure (for optional probes)."""
    try:
        return run_git(args, cwd=cwd, timeout=timeout)
    except GitError:
        return None
