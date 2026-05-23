"""Matcher and planner integration."""

from __future__ import annotations

from gitwise.matching.intent_parser import parse_intent
from gitwise.matching.matcher import IntentMatcher
from gitwise.models import RepoState
from gitwise.recipes.planner import build_plan, plan_from_intent


def _state(**kwargs) -> RepoState:
    defaults = dict(
        in_repo=True,
        root="/tmp/r",
        repo_name="r",
        branch="feature",
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


def test_match_push_no_upstream() -> None:
    matcher = IntentMatcher()
    intent = parse_intent("push my work")
    outcome = matcher.match(intent, _state())
    assert outcome.best is not None
    assert outcome.best.recipe_id in ("push_new_branch_upstream", "push_current_branch")


def test_plan_push_adds_u_for_current_branch() -> None:
    state = _state(has_upstream=False)
    intent = parse_intent("push this to main")
    matcher = IntentMatcher()
    outcome = matcher.match(intent, state)
    assert outcome.best
    plan = build_plan(outcome.best, intent, state)
    assert "-u" in plan.commands[0]
    assert "feature" in plan.commands[0]
    assert "main" not in plan.commands[0]


def test_plan_push_no_u_when_upstream() -> None:
    state = _state(
        branch="feature",
        upstream="origin/feature",
        upstream_ref="origin/feature",
        has_upstream=True,
    )
    intent = parse_intent("push")
    matcher = IntentMatcher()
    outcome = matcher.match(intent, state)
    plan = build_plan(outcome.best, intent, state)
    assert "-u" not in plan.commands[0]


def test_plan_stash_dirty() -> None:
    state = _state(modified_count=2, untracked_count=0)
    plan, _, _, err = plan_from_intent("stash my changes", cwd=None)
    # cwd None uses real cwd - may not be in repo; use matcher directly
    intent = parse_intent("stash my changes")
    matcher = IntentMatcher()
    outcome = matcher.match(intent, state)
    assert outcome.best
    plan = build_plan(outcome.best, intent, state)
    assert "stash push" in plan.commands[0]
