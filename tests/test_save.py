"""Tests for gw save planning and preflight."""

from __future__ import annotations

from gitwise.models import RepoState
from gitwise.workflows import save


def _state(**kwargs) -> RepoState:
    defaults = dict(
        in_repo=True,
        root="/r",
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


def test_build_save_plan_includes_push_with_upstream() -> None:
    plan = save.build_save_plan(_state(), "fixed pull conflict handling")
    assert plan.commands == [
        "git add .",
        'git commit -m "fixed pull conflict handling"',
        "git push origin feature",
    ]


def test_build_save_plan_adds_upstream_flag() -> None:
    plan = save.build_save_plan(
        _state(has_upstream=False, upstream=None, upstream_ref=None),
        "wip",
    )
    assert plan.commands[-1] == "git push -u origin feature"


def test_preflight_blocks_clean_tree() -> None:
    err = save.preflight_save(_state())
    assert err is not None
    assert "clean" in err.lower()


def test_preflight_allows_dirty_tree() -> None:
    err = save.preflight_save(_state(modified_count=2))
    assert err is None


def test_preflight_blocks_merge_in_progress() -> None:
    err = save.preflight_save(_state(modified_count=1, merge_in_progress=True))
    assert err is not None
    assert "merge" in err.lower()


def test_preflight_clean_ahead_suggests_push() -> None:
    err = save.preflight_save(_state(ahead=2))
    assert err is not None
    assert "push" in err.lower()
