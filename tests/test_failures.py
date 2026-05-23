"""Failure classification."""

from __future__ import annotations

from gitwise.execution.failures import classify_failure
from gitwise.models import RepoState


def _state() -> RepoState:
    return RepoState(
        in_repo=True,
        root="/r",
        repo_name="r",
        branch="main",
        remote="origin",
        remote_url=None,
        upstream="origin/main",
        upstream_ref="origin/main",
        default_branch="main",
        has_upstream=True,
        has_remote=True,
    )


def test_non_fast_forward() -> None:
    r = classify_failure(
        stderr="! [rejected] main -> main (non-fast-forward)",
        stdout="",
        command="git push origin main",
        recipe_id="push_auto",
        state=_state(),
    )
    assert r.kind == "non_fast_forward"
    assert r.suggestions


def test_branch_not_found() -> None:
    r = classify_failure(
        stderr="fatal: invalid reference: ghost",
        stdout="",
        command="git switch ghost",
        recipe_id="switch_branch",
        state=_state(),
    )
    assert r.kind in ("branch_not_found", "invalid_ref")


def test_permission_denied() -> None:
    r = classify_failure(
        stderr="Permission denied (publickey).",
        stdout="",
        command="git push",
        recipe_id="push_auto",
        state=_state(),
    )
    assert r.kind == "ssh_auth"
