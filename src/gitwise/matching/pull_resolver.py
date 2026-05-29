"""Resolve pull merge source from RepoState + intent."""

from __future__ import annotations

from dataclasses import dataclass

from gitwise.models import ParsedIntent, RepoState


@dataclass(frozen=True)
class PullPlan:
    """Resolved fetch + merge targets."""

    remote: str
    merge_ref: str
    source_branch: str | None
    label: str
    explanation: str
    commands: list[str]


def pull_source_branch(intent: ParsedIntent) -> str | None:
    """Explicit remote branch to merge in, if the user named one."""
    name = (intent.branch or intent.name or "").strip()
    return name or None


def resolve_pull(state: RepoState, intent: ParsedIntent) -> PullPlan:
    """
    Build fetch + merge plan.

    Default: merge current branch's upstream (e.g. origin/feature).
    Explicit: gw do "pull from branch 'main'" → merge origin/main into HEAD.
    """
    if not state.in_repo or not state.branch:
        raise ValueError("Cannot resolve pull: not inside a git repository with a current branch")

    remote = intent.remote or state.remote or "origin"
    source = pull_source_branch(intent)

    if source:
        merge_ref = f"{remote}/{source}"
        label = merge_ref
        explanation = (
            f"Guided safe pull: fetches {remote}, merges {merge_ref} into your "
            f"current branch '{state.branch}' (no rebase). Use this to bring in "
            f"another branch's commits — e.g. main into a feature branch."
        )
    else:
        if not state.upstream_ref:
            raise ValueError(
                f"Branch '{state.branch}' has no upstream. "
                f'Specify a source: gw do "pull from branch \'main\'"'
            )
        merge_ref = state.upstream_ref
        label = state.upstream or merge_ref
        explanation = (
            f"Guided safe pull: fetches {remote}, merges {label} into '{state.branch}' "
            f"(your branch's upstream tracking branch, no rebase)."
        )

    commands = [
        f"git fetch {remote}",
        f"git merge {merge_ref} --no-edit",
    ]
    return PullPlan(
        remote=remote,
        merge_ref=merge_ref,
        source_branch=source,
        label=label,
        explanation=explanation,
        commands=commands,
    )
