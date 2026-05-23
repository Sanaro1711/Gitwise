"""
Resolve push commands automatically from RepoState + intent.

-u is chosen from repo facts, not from memorizing phrases:
  - No upstream on the branch being pushed → git push -u <remote> <branch>
  - Upstream already set → git push <remote> <branch>
  - User explicitly asks for upstream / first push → -u even if redundant (git accepts)
"""

from __future__ import annotations

from dataclasses import dataclass

from gitwise.models import ParsedIntent, RepoState


@dataclass(frozen=True)
class PushPlan:
    """Resolved push command(s) and rationale."""

    commands: list[str]
    explanation: str
    uses_upstream_flag: bool
    remote: str
    branch: str


def needs_upstream_flag(state: RepoState, *, branch: str | None = None) -> bool:
    """
    True when git push should include -u for the branch being pushed.

    Uses tracking config for the *current* branch only (MVP). If you are on
    feature-x with no upstream, -u is required. If upstream is origin/feature-x, not.
    """
    if not state.in_repo or not state.branch:
        return False
    target = branch or state.branch
    if target != state.branch:
        # Pushing a different ref than HEAD: conservative — suggest -u if no upstream
        # on current branch isn't the right signal; caller may refine later.
        return not state.has_upstream
    return not state.has_upstream


def resolve_push(state: RepoState, intent: ParsedIntent) -> PushPlan:
    """
    Build the correct push command from live repo state and parsed intent.

    Examples:
      "push" on branch with upstream     → git push origin my-branch
      "push" on new branch, no upstream → git push -u origin my-branch
      "push this to main" on feature-x   → git push origin main (and -u if main has no upstream)
    """
    if not state.in_repo or not state.branch:
        raise ValueError("Cannot resolve push: not inside a git repository with a current branch")

    remote = intent.remote or state.remote or "origin"
    # Always publish the branch you are on (HEAD). Pushing another local ref while
    # checked out elsewhere is a common mistake — blocked in pre_checks instead.
    push_branch = state.branch

    use_u = needs_upstream_flag(state, branch=push_branch)
    if intent.wants_upstream:
        use_u = True

    if use_u:
        cmd = f"git push -u {remote} {push_branch}"
        reason = (
            f"Branch '{push_branch}' has no upstream tracking branch yet. "
            f"Using -u sets upstream to {remote}/{push_branch} for future push/pull."
        )
    else:
        cmd = f"git push {remote} {push_branch}"
        tracking = state.upstream or f"{remote}/{push_branch}"
        reason = (
            f"Branch '{push_branch}' already tracks {tracking}. "
            f"Pushing publishes your current branch's commits to the remote."
        )

    if state.behind > 0:
        reason += (
            f" Note: you are {state.behind} commit(s) behind the remote; "
            "push may be rejected until you pull or rebase."
        )

    return PushPlan(
        commands=[cmd],
        explanation=reason,
        uses_upstream_flag=use_u,
        remote=remote,
        branch=push_branch,
    )
