"""Automatic -u resolution for push."""

from __future__ import annotations

from gitwise.matching.intent_parser import parse_intent
from gitwise.matching.push_resolver import needs_upstream_flag, resolve_push
from gitwise.models import RepoState


def _state(**kwargs) -> RepoState:
    defaults = dict(
        in_repo=True,
        root="/tmp/r",
        repo_name="r",
        branch="feature",
        remote="origin",
        remote_url="https://github.com/org/r.git",
        upstream="origin/feature",
        upstream_ref="origin/feature",
        default_branch="main",
        has_upstream=True,
        has_remote=True,
    )
    defaults.update(kwargs)
    return RepoState(**defaults)


def test_no_upstream_uses_dash_u() -> None:
    state = _state(upstream=None, upstream_ref=None, has_upstream=False)
    plan = resolve_push(state, parse_intent("push"))
    assert "-u" in plan.commands[0]
    assert plan.uses_upstream_flag is True


def test_has_upstream_no_dash_u() -> None:
    state = _state()
    plan = resolve_push(state, parse_intent("push"))
    assert "-u" not in plan.commands[0]
    assert "git push origin feature" == plan.commands[0]


def test_push_this_to_main() -> None:
    state = _state(branch="feature-x", upstream="origin/feature-x", upstream_ref="origin/feature-x")
    intent = parse_intent("push this to main")
    plan = resolve_push(state, intent)
    assert intent.branch == "main"
    assert "main" in plan.commands[0]
    assert "origin" in plan.commands[0]


def test_needs_upstream_flag_helper() -> None:
    assert needs_upstream_flag(_state()) is False
    assert needs_upstream_flag(_state(has_upstream=False, upstream=None, upstream_ref=None)) is True
