"""Tests for gw undo last option building."""

from __future__ import annotations

from gitwise.models import RepoState
from gitwise.workflows import undo_last


def _state(**kwargs) -> RepoState:
    defaults = dict(
        in_repo=True,
        root="/r",
        repo_name="r",
        branch="feature",
        remote="origin",
        remote_url=None,
        upstream="origin/feature",
        upstream_ref="origin/feature",
        default_branch="main",
        has_upstream=True,
        has_remote=True,
    )
    defaults.update(kwargs)
    return RepoState(**defaults)


def test_build_options_includes_reset_when_history_exists(monkeypatch) -> None:
    monkeypatch.setattr(undo_last.probes, "parent_commit_exists", lambda **_: True)
    options = undo_last.build_undo_options(_state())
    keys = {o.key for o in options}
    assert "soft_reset" in keys
    assert "mixed_reset" in keys
    assert "hard_reset" in keys
    assert "revert_commit" in keys


def test_build_options_includes_unstage_when_staged() -> None:
    options = undo_last.build_undo_options(_state(staged_count=2))
    assert any(o.key == "unstage" for o in options)


def test_build_options_includes_abort_merge() -> None:
    options = undo_last.build_undo_options(_state(merge_in_progress=True))
    assert options[0].key == "abort_merge"


def test_build_options_includes_discard_when_dirty() -> None:
    options = undo_last.build_undo_options(_state(modified_count=1))
    assert any(o.key == "discard_all" for o in options)


def test_preflight_blocks_when_nothing_to_undo(monkeypatch) -> None:
    monkeypatch.setattr(undo_last.probes, "parent_commit_exists", lambda **_: False)
    err = undo_last.preflight_undo(_state())
    assert err is not None
    assert "nothing to undo" in err.lower()
