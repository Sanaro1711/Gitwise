"""Pull source resolution."""

from __future__ import annotations

from gitwise.matching.intent_parser import parse_intent
from gitwise.matching.pull_resolver import pull_source_branch, resolve_pull
from gitwise.models import RepoState


def _state(**kwargs) -> RepoState:
    defaults = dict(
        in_repo=True,
        root="/r",
        repo_name="r",
        branch="test-pull-conflict",
        remote="origin",
        remote_url="https://github.com/org/r.git",
        upstream=None,
        upstream_ref=None,
        default_branch="main",
        has_upstream=False,
        has_remote=True,
    )
    defaults.update(kwargs)
    return RepoState(**defaults)


def test_pull_default_uses_upstream() -> None:
    state = _state(
        upstream="origin/test-pull-conflict",
        upstream_ref="origin/test-pull-conflict",
        has_upstream=True,
    )
    plan = resolve_pull(state, parse_intent("pull latest"))
    assert plan.merge_ref == "origin/test-pull-conflict"
    assert plan.source_branch is None


def test_pull_from_branch_main() -> None:
    state = _state()
    intent = parse_intent("pull from branch 'main'")
    assert intent.branch == "main"
    plan = resolve_pull(state, intent)
    assert plan.merge_ref == "origin/main"
    assert plan.source_branch == "main"
    assert "origin/main" in plan.commands[1]


def test_pull_source_branch_helper() -> None:
    assert pull_source_branch(parse_intent("pull from 'main'")) == "main"
