"""Pre-check validation."""

from __future__ import annotations

from gitwise.execution.pre_checks import run_pre_checks
from gitwise.matching.intent_parser import parse_intent
from gitwise.models import CommandPlan, RepoState


def _plan(recipe_id: str) -> CommandPlan:
    return CommandPlan(
        recipe_id=recipe_id,
        category="Branch",
        explanation="test",
        commands=["git switch nope"],
        confirmation_level="standard",
    )


def _state(**kwargs) -> RepoState:
    defaults = dict(
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
    defaults.update(kwargs)
    return RepoState(**defaults)


def test_switch_branch_missing_blocks() -> None:
    intent = parse_intent("switch to 'ghost-branch'")
    pre = run_pre_checks(_plan("switch_branch"), _state(), intent)
    assert not pre.ok
    assert "no local branch" in pre.message.lower()
    assert pre.suggestions


def test_switch_already_on_branch() -> None:
    intent = parse_intent("switch to 'main'")
    pre = run_pre_checks(_plan("switch_branch"), _state(branch="main"), intent)
    assert not pre.ok
    assert "already" in pre.message.lower()


def test_commit_no_message_blocks() -> None:
    intent = parse_intent("commit")
    pre = run_pre_checks(
        _plan("commit_changes"),
        _state(staged_count=1),
        intent,
    )
    assert not pre.ok
