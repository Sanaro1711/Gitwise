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
    # Branch ref to push: explicit target (e.g. main) or current branch
    push_branch = intent.branch or state.branch

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
        if push_branch == state.branch:
            tracking = state.upstream or f"{remote}/{push_branch}"
            reason = (
                f"Branch '{push_branch}' already tracks {tracking}. "
                f"Pushing publishes local commits to the remote without changing tracking."
            )
        else:
            reason = (
                f"Pushes branch '{push_branch}' to {remote} (you are currently on '{state.branch}'). "
                f"Upstream tracking for '{push_branch}' is unchanged."
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
