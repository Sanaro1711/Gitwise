"""Post-execution verification per recipe."""

from __future__ import annotations

from pathlib import Path

from gitwise.execution.types import PostCheckResult
from gitwise.models import CommandPlan, ParsedIntent, RepoState
from gitwise.repo import probes


def _target_name(intent: ParsedIntent) -> str | None:
    return (intent.name or intent.branch or "").strip() or None


def run_post_checks(
    plan: CommandPlan,
    state_before: RepoState,
    state_after: RepoState,
    intent: ParsedIntent,
    *,
    cwd: Path | str | None = None,
) -> PostCheckResult:
    if plan.confirmation_level in ("deferred", "readonly"):
        return PostCheckResult(ok=True)

    handler = _HANDLERS.get(plan.recipe_id, _post_generic)
    return handler(plan, state_before, state_after, intent, cwd=cwd)


def _post_switch_branch(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    name = _target_name(intent)
    if name and state_after.branch != name:
        return PostCheckResult(
            ok=False,
            title="Switch may have failed",
            message=f"Expected branch '{name}' but you are on '{state_after.branch}'.",
            suggestions=["gw do 'show status'", "gw do 'list branches'"],
        )
    return PostCheckResult(ok=True)


def _post_create_branch(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    name = _target_name(intent)
    if name and state_after.branch != name:
        return PostCheckResult(
            ok=False,
            title="Branch not checked out",
            message=f"Branch '{name}' may exist but HEAD is on '{state_after.branch}'.",
            suggestions=[f'gw do "switch to \'{name}\'"'],
        )
    if name and not probes.local_branch_exists(name, cwd=cwd):
        return PostCheckResult(
            ok=False,
            title="Branch not created",
            message=f"Local branch '{name}' was not found after the command.",
        )
    return PostCheckResult(ok=True)


def _post_delete_local_branch(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    name = _target_name(intent)
    if name and probes.local_branch_exists(name, cwd=cwd):
        return PostCheckResult(
            ok=False,
            title="Branch still exists",
            message=f"Branch '{name}' was not deleted (may be unmerged — try force delete).",
            suggestions=[f'gw do "force delete branch \'{name}\'"'],
        )
    return PostCheckResult(ok=True)


def _post_commit(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    if state_after.has_staged and state_before.staged_count > 0:
        return PostCheckResult(
            ok=False,
            title="Commit may be incomplete",
            message="You still have staged changes after commit.",
            suggestions=["gw do 'show status'"],
        )
    return PostCheckResult(ok=True)


def _post_push(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    if state_before.ahead > 0 and state_after.ahead >= state_before.ahead:
        return PostCheckResult(
            ok=False,
            title="Push may not have published commits",
            message="You are still ahead of the remote after push.",
            suggestions=["gw do 'pull latest'", "gw do 'show status'"],
        )
    return PostCheckResult(ok=True)


def _post_pull(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    if state_before.behind > 0 and state_after.behind > 0:
        return PostCheckResult(
            ok=False,
            title="Pull may be incomplete",
            message="You are still behind the remote.",
            suggestions=["gw do 'fetch remote'", "gw do 'pull latest'"],
        )
    if state_after.merge_in_progress:
        return PostCheckResult(
            ok=False,
            title="Merge conflicts",
            message="Pull started a merge with conflicts.",
            suggestions=[
                "Resolve conflicted files, then git add and git commit",
                "gw do 'abort merge'",
            ],
        )
    return PostCheckResult(ok=True)


def _post_apply_stash(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    if "pop" in " ".join(plan.commands) and state_after.has_stash == state_before.has_stash:
        # pop removes stash; if stash count unchanged might be apply not pop - skip strict check
        pass
    return PostCheckResult(ok=True)


def _post_stash(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    if not state_after.has_stash and state_before.dirty_tree:
        return PostCheckResult(
            ok=False,
            title="Stash may have failed",
            message="No stash entry appeared after stashing.",
            suggestions=["gw do 'show status'"],
        )
    return PostCheckResult(ok=True)


def _post_generic(plan, state_before, state_after, intent, *, cwd=None) -> PostCheckResult:
    return PostCheckResult(ok=True)


_HANDLERS = {
    "switch_branch": _post_switch_branch,
    "create_branch": _post_create_branch,
    "delete_local_branch": _post_delete_local_branch,
    "commit_changes": _post_commit,
    "push_current_branch": _post_push,
    "push_new_branch_upstream": _post_push,
    "push_auto": _post_push,
    "force_push_safe": _post_push,
    "pull_latest": _post_pull,
    "apply_latest_stash": _post_apply_stash,
    "stash_changes": _post_stash,
    "stash_including_untracked": _post_stash,
}
