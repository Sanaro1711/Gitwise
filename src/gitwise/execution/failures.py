"""Classify git stderr and suggest recovery steps."""

from __future__ import annotations

import re
from dataclasses import dataclass

from gitwise.execution.types import FailureReport
from gitwise.models import RepoState
from gitwise.output import format_whereami


@dataclass
class _Pattern:
    kind: str
    title: str
    regex: re.Pattern[str]
    explanation: str
    suggestions: list[str]


def _p(
    kind: str,
    title: str,
    pattern: str,
    explanation: str,
    *suggestions: str,
) -> _Pattern:
    return _Pattern(
        kind=kind,
        title=title,
        regex=re.compile(pattern, re.I | re.M),
        explanation=explanation,
        suggestions=list(suggestions),
    )


_PATTERNS: list[_Pattern] = [
    _p(
        "branch_not_found",
        "Branch not found",
        r"unknown revision|pathspec .* did not match|not a valid object name|branch .* not found",
        "Git could not find the branch or commit you referenced.",
        'gw do "list branches"',
        "gw do 'whereami'",
    ),
    _p(
        "invalid_ref",
        "Invalid reference",
        r"not a valid ref|ambiguous argument",
        "The branch, tag, or revision name is invalid or ambiguous.",
        "gw do 'list branches'",
    ),
    _p(
        "non_fast_forward",
        "Push rejected (non-fast-forward)",
        r"non-fast-forward|rejected.*failed to push|fetch first",
        "The remote has commits you do not have locally. A plain push cannot update the remote until you integrate those changes.",
        'gw do "pull latest"',
        'gw do "push" after pull',
    ),
    _p(
        "push_rejected",
        "Push rejected",
        r"\[rejected\]|! \[rejected\]",
        "The server refused this push.",
        'gw do "pull latest"',
        "gw do 'whereami'",
    ),
    _p(
        "no_upstream",
        "No upstream branch",
        r"no upstream branch|has no upstream branch|set upstream",
        "Your current branch is not linked to a remote tracking branch.",
        f'gw do "push" (Gitwise will add -u if needed)',
    ),
    _p(
        "dirty_worktree",
        "Uncommitted changes",
        r"please commit your changes or stash|would be overwritten by checkout|would be overwritten by merge|your local changes to the following files",
        "You have local changes that block this operation.",
        'gw do "stash changes"',
        'gw do "commit \'message\'"',
    ),
    _p(
        "merge_conflict",
        "Merge conflict",
        r"merge conflict|CONFLICT \(|automatic merge failed|fix conflicts and then commit",
        "Git could not merge cleanly — the same lines were changed in both places.",
        "Edit conflicted files, then: gw do 'stage all' and gw do \"commit 'merge'\"",
        "gw do 'abort merge'",
    ),
    _p(
        "rebase_conflict",
        "Rebase conflict",
        r"could not apply|resolve all conflicts|rebase in progress",
        "Rebase stopped because of conflicts on one or more commits.",
        "Fix files, git add, then git rebase --continue",
        "gw do 'abort rebase'",
    ),
    _p(
        "ssh_auth",
        "SSH authentication failed",
        r"permission denied \(publickey\)|git@.*: Permission denied",
        "Git could not authenticate with the remote using SSH.",
        "Add your SSH key to GitHub/GitLab and test: ssh -T git@github.com",
    ),
    _p(
        "https_auth",
        "HTTPS authentication failed",
        r"authentication failed|could not read Username|invalid username or password|403|401",
        "Git could not log in to the remote over HTTPS.",
        "Update credentials in Windows Credential Manager or use a personal access token",
    ),
    _p(
        "remote_not_found",
        "Remote repository not found",
        r"repository not found|could not read from remote|remote error",
        "The remote URL may be wrong or you may not have access.",
        "Check: gw do 'whereami' and git remote -v",
    ),
    _p(
        "remote_exists",
        "Remote already exists",
        r"remote .* already exists",
        "A remote with that name is already configured.",
        'gw do "set remote origin \'url\'" (updates URL if origin exists)',
    ),
    _p(
        "cannot_delete_current",
        "Cannot delete current branch",
        r"cannot delete branch .* checked out|used by worktree",
        "You cannot delete the branch you are currently on.",
        f'gw do "switch to \'main\'" then delete',
    ),
    _p(
        "not_fully_merged",
        "Branch not fully merged",
        r"not fully merged|not merged",
        "Git refused to delete a branch that has not been merged (safe delete).",
        'Say "force delete branch" or use: git branch -D <name>',
    ),
    _p(
        "nothing_to_commit",
        "Nothing to commit",
        r"nothing to commit|no changes added to commit",
        "There are no staged changes to commit.",
        "gw do 'stage all'",
        "gw do 'show status'",
    ),
    _p(
        "stash_empty",
        "No stash entries",
        r"no stash entries|no stash found",
        "The stash list is empty.",
        'gw do "stash changes"',
    ),
    _p(
        "already_exists",
        "Already exists",
        r"already exists",
        "That branch, tag, file, or remote name already exists.",
        "gw do 'list branches'",
    ),
    _p(
        "network",
        "Network error",
        r"could not resolve host|connection timed out|unable to access|Failed to connect",
        "Git could not reach the remote server.",
        "Check your internet connection and remote URL",
    ),
    _p(
        "detached_head",
        "Detached HEAD",
        r"detached HEAD|HEAD detached",
        "You are not on a branch — some operations need a branch checkout first.",
        'gw do "switch to \'main\'"',
    ),
    _p(
        "refspec_mismatch",
        "Refspec does not match",
        r"src refspec .* does not match|couldn't find remote ref",
        "The branch name does not exist on the remote or locally.",
        'gw do "push" with correct branch name',
        "gw do 'list branches'",
    ),
]


def classify_failure(
    *,
    stderr: str,
    stdout: str,
    command: str,
    recipe_id: str,
    state: RepoState,
) -> FailureReport:
    combined = f"{stderr}\n{stdout}".strip()
    combined = _sanitize(combined)

    for pat in _PATTERNS:
        if pat.regex.search(combined):
            suggestions = list(pat.suggestions)
            _enrich_suggestions(suggestions, pat.kind, recipe_id, state)
            return FailureReport(
                kind=pat.kind,
                title=pat.title,
                explanation=pat.explanation,
                suggestions=suggestions,
                git_output=_truncate(combined),
            )

    return FailureReport(
        kind="unknown",
        title="Git command failed",
        explanation="Git returned an error that Gitwise does not classify yet.",
        suggestions=[
            "gw do 'whereami'",
            "Re-run with -n to review the plan",
            "Paste the error into: gw fix \"<error text>\" (when available)",
        ],
        git_output=_truncate(combined),
    )


def _enrich_suggestions(
    suggestions: list[str], kind: str, recipe_id: str, state: RepoState
) -> None:
    if kind == "no_upstream" and state.branch:
        suggestions[0] = f'gw do "push"  # publishes {state.branch} and sets upstream'
    if kind == "branch_not_found" and recipe_id == "switch_branch":
        suggestions.insert(0, 'gw do "create branch \'name\'"')


def _sanitize(text: str) -> str:
    """Remove likely credential fragments from output."""
    lines = []
    for line in text.splitlines():
        lower = line.lower()
        if "password" in lower and "=" in line:
            continue
        lines.append(line)
    return "\n".join(lines)


def _truncate(text: str, max_len: int = 1200) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n... (truncated)"


def format_failure_report(report: FailureReport, state: RepoState) -> str:
    lines = [
        "",
        f"=== {report.title} ===",
        "",
        report.explanation,
        "",
    ]
    if report.git_output:
        lines.append("Git reported:")
        for line in report.git_output.splitlines()[:15]:
            lines.append(f"  {line}")
        lines.append("")

    if report.suggestions:
        lines.append("Suggested next moves:")
        for i, s in enumerate(report.suggestions, 1):
            lines.append(f"  {i}. {s}")
        lines.append("")

    if state.in_repo:
        lines.append("Your repo now:")
        for line in format_whereami(state).splitlines():
            lines.append(f"  {line}")

    return "\n".join(lines)


def format_pre_check_block(result) -> str:
    from gitwise.execution.types import PreCheckResult

    assert isinstance(result, PreCheckResult)
    lines = [f"\n=== {result.title} ===\n", result.message, ""]
    if result.suggestions:
        lines.append("Try instead:")
        for i, s in enumerate(result.suggestions, 1):
            lines.append(f"  {i}. {s}")
    return "\n".join(lines)


def format_post_check_warning(result) -> str:
    lines = [f"\nNote: {result.title}", result.message]
    if result.suggestions:
        for s in result.suggestions:
            lines.append(f"  - {s}")
    return "\n".join(lines)
