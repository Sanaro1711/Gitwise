"""Safe pull preflight and routing."""

from __future__ import annotations

from pathlib import Path

from gitwise.matching.intent_parser import parse_intent
from gitwise.matching.pull_resolver import resolve_pull
from gitwise.models import RepoState
from gitwise.workflows import safe_pull


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


def test_preflight_blocks_no_upstream() -> None:
    state = _state(has_upstream=False, upstream=None, upstream_ref=None)
    pull = resolve_pull(state, parse_intent("pull from branch 'main'"))
    # explicit branch — should pass
    assert safe_pull._preflight(state, pull) is None

    with __import__("pytest").raises(ValueError):
        resolve_pull(state, parse_intent("pull latest"))


def test_preflight_blocks_rebase_in_progress() -> None:
    pull = resolve_pull(_state(), parse_intent("pull"))
    err = safe_pull._preflight(_state(rebase_in_progress=True), pull)
    assert err is not None
    assert "rebase" in err.lower()


def test_preflight_ok() -> None:
    pull = resolve_pull(_state(), parse_intent("pull"))
    assert safe_pull._preflight(_state(), pull) is None


def test_dry_run_includes_stash_when_dirty() -> None:
    import io
    from contextlib import redirect_stdout

    state = _state(modified_count=2, staged_count=0, untracked_count=0)
    pull = resolve_pull(state, parse_intent("pull from branch 'main'"))
    ctx = safe_pull.SafePullContext(cwd=Path("."), state=state, pull=pull)
    buf = io.StringIO()
    with redirect_stdout(buf):
        safe_pull._print_dry_run_steps(ctx)
    out = buf.getvalue()
    assert "stash" in out.lower()
    assert "fetch" in out.lower()
    assert "merge origin/main" in out.lower()
