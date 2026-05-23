"""Evaluate recipe requires[] against RepoState and ParsedIntent."""

from __future__ import annotations

from gitwise.models import ParsedIntent, RepoState
def check_requires(
    predicate: str,
    state: RepoState,
    intent: ParsedIntent,
    *,
    cwd=None,
) -> tuple[bool, str]:
    """Return (ok, reason_if_failed)."""
    name = intent.name or intent.branch

    checks: dict[str, tuple[bool, str]] = {
        "in_repo": (state.in_repo, "Not inside a git repository."),
        "not_in_repo": (not state.in_repo, "Already inside a git repository."),
        "has_remote": (state.has_remote, "No git remote configured."),
        "no_remote_origin": (
            state.in_repo and not _has_remote_named(state, "origin", cwd),
            "Remote 'origin' already exists.",
        ),
        "has_upstream": (state.has_upstream, "Current branch has no upstream tracking branch."),
        "no_upstream": (not state.has_upstream, "Current branch already has an upstream."),
        "clean_tree": (state.clean_tree, "Working tree has uncommitted changes."),
        "dirty_tree": (state.dirty_tree, "Working tree is clean — nothing to stash or discard."),
        "has_staged": (state.has_staged, "No staged changes."),
        "has_uncommitted": (state.has_uncommitted, "No unstaged or untracked changes."),
        "ahead_of_remote": (state.ahead > 0, "Not ahead of remote."),
        "behind_remote": (state.behind > 0, "Not behind remote."),
        "has_stash": (state.has_stash, "No stash entries."),
        "on_default_branch": (
            _on_default_branch(state),
            "Not on the default branch.",
        ),
        "not_on_default_branch": (
            not _on_default_branch(state),
            "Already on the default branch.",
        ),
        "merge_in_progress": (state.merge_in_progress, "No merge in progress."),
        "rebase_in_progress": (state.rebase_in_progress, "No rebase in progress."),
        "merge_or_rebase_in_progress": (
            state.merge_or_rebase_in_progress,
            "No merge or rebase in progress.",
        ),
        "intent_has_branch": (bool(name), "Specify a branch name in your request."),
        "intent_has_name": (bool(name), "Specify a name (branch, tag, etc.) in your request."),
        "intent_has_url": (bool(intent.url), "Include a repository URL (https:// or git@)."),
        "intent_has_path": (bool(intent.path), "Specify a file path in your request."),
        "intent_has_message": (
            bool(intent.message),
            'Include a message in quotes, e.g. commit "fix bug".',
        ),
    }

    if predicate not in checks:
        return False, f"Unknown require predicate: {predicate}"

    ok, reason = checks[predicate]
    return ok, "" if ok else reason


def evaluate_requires(
    requires: tuple[str, ...],
    state: RepoState,
    intent: ParsedIntent,
    *,
    cwd=None,
) -> tuple[bool, list[str]]:
    """All must pass."""
    failures: list[str] = []
    for pred in requires:
        ok, reason = check_requires(pred, state, intent, cwd=cwd)
        if not ok:
            failures.append(f"{pred}: {reason}")
    return len(failures) == 0, failures


def _on_default_branch(state: RepoState) -> bool:
    if not state.branch or not state.default_branch:
        return state.branch in ("main", "master")
    return state.branch == state.default_branch


def _has_remote_named(state: RepoState, name: str, cwd) -> bool:
    if not state.in_repo:
        return False
    from gitwise.repo.git_runner import run_git_optional

    listing = run_git_optional(["remote"], cwd=cwd)
    return bool(listing and name in listing.splitlines())
