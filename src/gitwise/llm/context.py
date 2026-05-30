"""Build a safe, compact repository context for the LLM."""

from __future__ import annotations

import re
from pathlib import Path

from gitwise.models import RepoState
from gitwise.output import format_whereami
from gitwise.repo.git_runner import run_git_optional
from gitwise.repo.inspector import RepoInspector

_MAX_LOG_LINES = 8
_MAX_STATUS_LINES = 20
_MAX_BRANCHES = 15


def build_repo_context(*, cwd: Path | str | None = None) -> tuple[RepoState, str]:
    """Inspect repo and return state plus a redacted context string."""
    state = RepoInspector(cwd=cwd).inspect()
    if not state.in_repo:
        return state, "Not inside a git repository."

    sections = [
        "## Repository snapshot",
        _redact_whereami(format_whereami(state)),
        "",
        "## Recent commits (oneline, newest first)",
        _recent_log(cwd=cwd),
        "",
        "## Branches",
        _branch_summary(cwd=cwd),
        "",
        "## Working tree (short status)",
        _short_status(cwd=cwd),
    ]

    if state.merge_in_progress:
        sections.extend(["", "## Merge state", _merge_summary(cwd=cwd)])
    if state.has_stash:
        sections.extend(["", "## Stash", _stash_summary(cwd=cwd)])

    sections.extend(
        [
            "",
            "## Gitwise shortcuts available",
            "- gw save \"message\" — git add ., commit, push current branch",
            "- gw pull — safe pull with stash + conflict guide",
            "- gw do \"intent\" — ~30 recipe workflows with confirmation",
            "- gw undo last — interactive undo guide",
        ]
    )

    return state, "\n".join(sections)


def _redact_whereami(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("Remote URL:"):
            _, _, value = line.partition(":")
            line = f"Remote URL: {_redact_remote_url(value.strip())}"
        lines.append(line)
    return "\n".join(lines)


def _redact_remote_url(url: str) -> str:
    if not url or url == "(none)":
        return url or "(none)"
    # https://user:token@github.com/org/repo.git -> https://github.com/org/repo.git
    url = re.sub(r"https://[^@/]+@", "https://", url)
    # git@github.com:org/repo.git — no secrets, keep as-is
    return url


def _recent_log(*, cwd: Path | str | None) -> str:
    out = run_git_optional(
        ["log", f"-{_MAX_LOG_LINES}", "--oneline", "--decorate"],
        cwd=cwd,
    )
    return out or "(no commits yet)"


def _branch_summary(*, cwd: Path | str | None) -> str:
    local = run_git_optional(["branch", "--format=%(refname:short)"], cwd=cwd) or ""
    remote = run_git_optional(["branch", "-r", "--format=%(refname:short)"], cwd=cwd) or ""
    lines: list[str] = []
    for label, block in ("Local", local), ("Remote", remote):
        names = [n.strip() for n in block.splitlines() if n.strip()][: _MAX_BRANCHES]
        if names:
            lines.append(f"{label}: {', '.join(names)}")
    return "\n".join(lines) if lines else "(none)"


def _short_status(*, cwd: Path | str | None) -> str:
    out = run_git_optional(["status", "-sb"], cwd=cwd) or ""
    lines = out.splitlines()[:_MAX_STATUS_LINES]
    if len(out.splitlines()) > _MAX_STATUS_LINES:
        lines.append("... (truncated)")
    return "\n".join(lines) if lines else "(clean)"


def _merge_summary(*, cwd: Path | str | None) -> str:
    unmerged = run_git_optional(["diff", "--name-only", "--diff-filter=U"], cwd=cwd) or ""
    if unmerged.strip():
        files = unmerged.strip().splitlines()[:10]
        return "Conflicted files:\n" + "\n".join(f"  - {f}" for f in files)
    return "Merge in progress (no unmerged files listed)."


def _stash_summary(*, cwd: Path | str | None) -> str:
    out = run_git_optional(["stash", "list"], cwd=cwd) or ""
    lines = out.splitlines()[:3]
    return "\n".join(lines) if lines else "(empty)"
