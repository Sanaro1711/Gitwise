"""Pre-execution validation per recipe."""

from __future__ import annotations

from pathlib import Path

from gitwise.execution.types import PreCheckResult
from gitwise.models import CommandPlan, ParsedIntent, RepoState
from gitwise.repo import probes


def _target_name(intent: ParsedIntent) -> str | None:
    return (intent.name or intent.branch or "").strip() or None


# Words parsed as a "branch" from push phrases but are not real branch names.
_PUSH_BRANCH_NOISE = frozenset(
    {
        "to",
        "my",
        "this",
        "current",
        "work",
        "code",
        "origin",
        "upstream",
        "remote",
        "github",
        "gitlab",
        "changes",
        "commits",
        "branch",
    }
)


def _requested_push_branch(intent: ParsedIntent, state: RepoState) -> str | None:
    """Branch name if the user asked to push somewhere other than HEAD."""
    raw = (intent.branch or "").strip()
    if not raw or raw.lower() in _PUSH_BRANCH_NOISE:
        return None
    if state.branch and raw.lower() == state.branch.lower():
        return None
    return raw


def run_pre_checks(
    plan: CommandPlan,
    state: RepoState,
    intent: ParsedIntent,
    *,
    cwd: Path | str | None = None,
) -> PreCheckResult:
    """Validate before user confirms / commands run."""
    rid = plan.recipe_id
    warnings: list[str] = []

    if plan.confirmation_level == "deferred":
        return PreCheckResult(ok=True)

    # Read-only — no git mutation
    if plan.confirmation_level == "readonly":
        return PreCheckResult(ok=True)

    handler = _HANDLERS.get(rid, _pre_generic)
    result = handler(plan, state, intent, cwd=cwd)
    result.warnings.extend(warnings)
    for w in result.warnings:
        if w not in plan.warnings:
            plan.warnings.append(w)
    return result


def _block(title: str, message: str, *suggestions: str) -> PreCheckResult:
    return PreCheckResult(
        ok=False,
        title=title,
        message=message,
        suggestions=list(suggestions),
    )


def _warn(result: PreCheckResult, warning: str) -> PreCheckResult:
    if warning not in result.warnings:
        result.warnings.append(warning)
    return result


def _pre_generic(
    plan: CommandPlan,
    state: RepoState,
    intent: ParsedIntent,
    *,
    cwd=None,
) -> PreCheckResult:
    r = PreCheckResult(ok=True)
    if state.merge_or_rebase_in_progress and plan.recipe_id not in (
        "abort_merge_or_rebase",
        "show_status",
        "show_diff",
        "check_history",
    ):
        _warn(
            r,
            "A merge or rebase is in progress — finish or abort it before other operations.",
        )
    return r


def _pre_switch_branch(plan, state, intent, *, cwd=None) -> PreCheckResult:
    name = _target_name(intent)
    if not name:
        return _block(
            "Branch name required",
            "Say which branch to switch to.",
            'gw do "switch to \'your-branch\'"',
        )
    if not probes.local_branch_exists(name, cwd=cwd):
        branches = probes.list_local_branches(cwd=cwd)[:8]
        hint = ", ".join(branches) if branches else "(none)"
        return _block(
            "Branch does not exist",
            f"No local branch named '{name}'. Existing branches: {hint}",
            f'gw do "create branch \'{name}\'"',
            "gw do 'list branches'",
        )
    if name == state.branch:
        return _block(
            "Already on that branch",
            f"You are already on '{name}'.",
            "gw do 'whereami'",
        )
    return PreCheckResult(ok=True)


def _pre_create_branch(plan, state, intent, *, cwd=None) -> PreCheckResult:
    name = _target_name(intent)
    if not name:
        return _block(
            "Branch name required",
            "Say what to call the new branch.",
            'gw do "create branch \'feature-name\'"',
        )
    if probes.local_branch_exists(name, cwd=cwd):
        return _block(
            "Branch already exists",
            f"A local branch '{name}' already exists. Switch to it or pick another name.",
            f'gw do "switch to \'{name}\'"',
            f'gw do "delete branch \'{name}\'"',
        )
    return PreCheckResult(ok=True)


def _pre_delete_local_branch(plan, state, intent, *, cwd=None) -> PreCheckResult:
    name = _target_name(intent)
    if not name:
        return _block(
            "Branch name required",
            "Say which branch to delete.",
            'gw do "delete branch \'branch-name\'"',
        )
    if not probes.local_branch_exists(name, cwd=cwd):
        return _block(
            "Branch does not exist",
            f"No local branch named '{name}' to delete.",
            "gw do 'list branches'",
        )
    if name == state.branch:
        return _block(
            "Cannot delete current branch",
            f"You are on '{name}'. Switch to another branch first.",
            f'gw do "switch to \'{state.default_branch or "main"}\'"',
        )
    return PreCheckResult(ok=True)


def _pre_delete_remote_branch(plan, state, intent, *, cwd=None) -> PreCheckResult:
    name = _target_name(intent)
    remote = intent.remote or state.remote or "origin"
    if not name:
        return _block(
            "Branch name required",
            "Say which remote branch to delete.",
            'gw do "delete branch \'branch-name\'"',
        )
    r = PreCheckResult(ok=True)
    if not probes.remote_branch_exists(remote, name, cwd=cwd):
        _warn(
            r,
            f"Remote branch '{remote}/{name}' was not found locally — it may already be gone on the server.",
        )
    return r


def _pre_rename_branch(plan, state, intent, *, cwd=None) -> PreCheckResult:
    name = _target_name(intent)
    if not name:
        return _block(
            "New name required",
            "Say the new branch name.",
            'gw do "rename branch \'new-name\'"',
        )
    if probes.local_branch_exists(name, cwd=cwd):
        return _block(
            "Name already taken",
            f"Branch '{name}' already exists.",
            "gw do 'list branches'",
        )
    return PreCheckResult(ok=True)


def _pre_merge_into_default(plan, state, intent, *, cwd=None) -> PreCheckResult:
    name = _target_name(intent)
    if not name:
        return _block(
            "Branch name required",
            "Say which branch to merge into the default branch.",
            f'gw do "merge branch \'{state.branch or "feature"}\' into main"',
        )
    if not probes.local_branch_exists(name, cwd=cwd):
        return _block(
            "Branch does not exist",
            f"Cannot merge — local branch '{name}' does not exist.",
            "gw do 'list branches'",
        )
    if name == state.default_branch:
        return _block(
            "Invalid merge",
            "You cannot merge the default branch into itself.",
        )
    return PreCheckResult(ok=True)


def _pre_discard_one_file(plan, state, intent, *, cwd=None) -> PreCheckResult:
    path = intent.path
    if not path:
        return _block(
            "File path required",
            "Say which file to discard.",
            'gw do "discard changes in \'path/to/file\'"',
        )
    if not probes.path_in_worktree(path, cwd=cwd):
        return _block(
            "File not found",
            f"'{path}' is not in your working tree.",
            "gw do 'show status'",
        )
    return PreCheckResult(ok=True)


def _pre_commit(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if not intent.message:
        return _block(
            "Commit message required",
            "Include a message in single quotes.",
            'gw do "commit \'your message\'"',
        )
    if not state.has_staged:
        return _block(
            "Nothing staged",
            "Stage changes before committing.",
            "gw do 'stage all'",
            "gw do 'show status'",
        )
    return PreCheckResult(ok=True)


def _pre_apply_stash(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if not state.has_stash:
        return _block(
            "No stash entries",
            "There is nothing in the stash list.",
            "gw do 'stash changes'",
        )
    return PreCheckResult(ok=True)


def _pre_undo_commit(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if not probes.parent_commit_exists(cwd=cwd):
        return _block(
            "Cannot undo",
            "This repository has no parent commit (nothing to reset to).",
        )
    return PreCheckResult(ok=True)


def _pre_clone(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if state.in_repo:
        return _block(
            "Already in a repository",
            "Clone must be run outside an existing git repo (use a parent folder).",
        )
    url = intent.url
    if not url:
        return _block(
            "URL required",
            "Provide a repository URL.",
            'gw do "clone \'https://github.com/user/repo.git\'"',
        )
    existing = probes.clone_target_exists(url, cwd=cwd)
    if existing:
        return _block(
            "Target folder exists",
            f"A folder '{existing}' already exists here. Remove it or clone elsewhere.",
        )
    return PreCheckResult(ok=True)


def _pre_set_remote(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if not intent.url:
        return _block(
            "URL required",
            "Provide the remote repository URL.",
            'gw do "set remote origin \'https://github.com/user/repo.git\'"',
        )
    return PreCheckResult(ok=True)


def _pre_create_tag(plan, state, intent, *, cwd=None) -> PreCheckResult:
    name = _target_name(intent)
    if not name:
        return _block(
            "Tag name required",
            "Say what to call the tag.",
            'gw do "create tag \'v1.0.0\'"',
        )
    if probes.tag_exists(name, cwd=cwd):
        return _block(
            "Tag already exists",
            f"Tag '{name}' already exists. Pick another name or delete the old tag first.",
        )
    return PreCheckResult(ok=True)


def _pre_abort_merge_rebase(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if not state.merge_or_rebase_in_progress:
        return _block(
            "Nothing to abort",
            "No merge or rebase is in progress.",
            "gw do 'show status'",
        )
    return PreCheckResult(ok=True)


def _pre_rebase(plan, state, intent, *, cwd=None) -> PreCheckResult:
    r = PreCheckResult(ok=True)
    if state.dirty_tree:
        _warn(r, "You have uncommitted changes — stash or commit before rebasing.")
    if state.merge_in_progress:
        return _block(
            "Merge in progress",
            "Finish or abort the merge before rebasing.",
            "gw do 'abort merge'",
        )
    return r


def _pre_push(plan, state, intent, *, cwd=None) -> PreCheckResult:
    r = PreCheckResult(ok=True)

    other = _requested_push_branch(intent, state)
    if other and state.branch:
        return _block(
            "Push only your current branch",
            (
                f"You are on '{state.branch}', but this intent looks like a push to '{other}'. "
                f"Gitwise only publishes the branch you have checked out so your commits stay "
                f"where you expect on the remote. Switch to '{other}' first if that is the "
                f"branch you mean to update, then run push."
            ),
            f'gw do "switch to \'{other}\'"',
            'gw do "push"',
            "gw do 'whereami'",
        )

    if state.behind > 0:
        _warn(
            r,
            f"You are {state.behind} commit(s) behind the remote — push may be rejected until you pull.",
        )
    if not state.has_remote:
        return _block(
            "No remote configured",
            "Add a remote before pushing.",
            'gw do "set remote origin \'https://github.com/user/repo.git\'"',
        )
    return r


def _pre_pull(plan, state, intent, *, cwd=None) -> PreCheckResult:
    r = PreCheckResult(ok=True)
    if state.dirty_tree:
        _warn(
            r,
            "Uncommitted changes will be safely stashed before pull and restored afterward.",
        )

    source = (intent.branch or intent.name or "").strip()
    if not state.has_upstream and not source:
        return _block(
            "No upstream branch",
            "Your branch does not track a remote branch yet.",
            'gw do "pull from branch \'main\'"  # merge a specific remote branch',
            f'gw do "push"  # or push to set upstream for \'{state.branch}\'',
        )

    if source:
        remote = intent.remote or state.remote or "origin"
        if source == state.branch:
            _warn(
                r,
                f"Merging {remote}/{source} into '{state.branch}' — same branch name on remote.",
            )
        elif not probes.remote_branch_exists(remote, source, cwd=cwd):
            _warn(
                r,
                f"Remote branch '{remote}/{source}' not found locally yet — fetch will retrieve it.",
            )
    return r


def _pre_discard_all(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if not state.dirty_tree:
        return _block(
            "Nothing to discard",
            "Your working tree is already clean.",
            "gw do 'show status'",
        )
    return PreCheckResult(ok=True)


def _pre_stage_all(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if not state.has_uncommitted and state.untracked_count == 0:
        return _block(
            "Nothing to stage",
            "No unstaged or untracked changes to add.",
            "gw do 'show status'",
        )
    return PreCheckResult(ok=True)


def _pre_stash(plan, state, intent, *, cwd=None) -> PreCheckResult:
    if not state.dirty_tree:
        return _block(
            "Nothing to stash",
            "Working tree is clean.",
            "gw do 'show status'",
        )
    return PreCheckResult(ok=True)


_HANDLERS: dict = {
    "switch_branch": _pre_switch_branch,
    "create_branch": _pre_create_branch,
    "delete_local_branch": _pre_delete_local_branch,
    "delete_remote_branch": _pre_delete_remote_branch,
    "rename_branch": _pre_rename_branch,
    "merge_into_default": _pre_merge_into_default,
    "discard_one_file": _pre_discard_one_file,
    "discard_all_local": _pre_discard_all,
    "commit_changes": _pre_commit,
    "apply_latest_stash": _pre_apply_stash,
    "undo_last_commit_keep": _pre_undo_commit,
    "clone_repo": _pre_clone,
    "set_remote_origin": _pre_set_remote,
    "create_tag": _pre_create_tag,
    "abort_merge_or_rebase": _pre_abort_merge_rebase,
    "rebase_onto_default": _pre_rebase,
    "push_current_branch": _pre_push,
    "push_new_branch_upstream": _pre_push,
    "push_auto": _pre_push,
    "force_push_safe": _pre_push,
    "pull_latest": _pre_pull,
    "stage_all_changes": _pre_stage_all,
    "stash_changes": _pre_stash,
    "stash_including_untracked": _pre_stash,
    "fetch_remote": lambda *a, **k: PreCheckResult(ok=True),
    "list_branches": lambda *a, **k: PreCheckResult(ok=True),
    "show_status": lambda *a, **k: PreCheckResult(ok=True),
    "show_diff": lambda *a, **k: PreCheckResult(ok=True),
    "check_history": lambda *a, **k: PreCheckResult(ok=True),
    "undo_staged": lambda *a, **k: PreCheckResult(ok=True),
    "create_github_pr": lambda *a, **k: PreCheckResult(ok=True),
}
