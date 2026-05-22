"""Format CLI output for humans."""

from __future__ import annotations

from gitwise.models import RepoState


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    if n == 1:
        return f"1 {singular}"
    return f"{n} {plural or singular + 's'}"


def format_whereami(state: RepoState) -> str:
    """Render the whereami report matching the Gitwise spec."""
    if not state.in_repo:
        return "Not inside a git repository."

    lines: list[str] = []
    lines.append(f"Repo: {state.repo_name or 'unknown'}")
    lines.append(f"Branch: {state.branch or '(detached HEAD)'}")
    lines.append(f"Remote: {state.remote or '(none)'}")
    if state.upstream:
        lines.append(f"Upstream: {state.upstream}")
    else:
        lines.append("Upstream: (not set)")

    lines.append("")
    lines.append("Working tree:")
    if state.clean_tree:
        lines.append("  Clean — no uncommitted changes")
    else:
        if state.modified_count:
            lines.append(f"  {_plural(state.modified_count, 'modified file')}")
        if state.staged_count:
            lines.append(f"  {_plural(state.staged_count, 'staged file')}")
        if state.untracked_count:
            lines.append(f"  {_plural(state.untracked_count, 'untracked file')}")
        if not (state.modified_count or state.staged_count or state.untracked_count):
            lines.append("  (changes present)")

    lines.append("")
    lines.append("Sync state:")
    if not state.has_upstream:
        lines.append("  No upstream branch configured for this branch.")
        lines.append("  First push usually needs: git push -u <remote> <branch>")
    else:
        lines.append(
            f"  You are {_plural(state.ahead, 'commit')} ahead of remote."
            if state.ahead
            else "  You are 0 commits ahead of remote."
        )
        lines.append(
            f"  You are {_plural(state.behind, 'commit')} behind remote."
            if state.behind
            else "  You are 0 commits behind remote."
        )

    if state.merge_in_progress:
        lines.append("")
        lines.append("Note: Merge in progress.")
    if state.rebase_in_progress:
        lines.append("")
        lines.append("Note: Rebase in progress.")
    if state.has_stash:
        lines.append("")
        lines.append("Note: You have stash entries (git stash list).")

    return "\n".join(lines)
