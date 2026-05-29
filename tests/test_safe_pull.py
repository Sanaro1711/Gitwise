"""Safe pull preflight and routing."""

from __future__ import annotations

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
    err = safe_pull._preflight(_state(has_upstream=False, upstream=None, upstream_ref=None))
    assert err is not None
    assert "upstream" in err.lower()


def test_preflight_blocks_rebase_in_progress() -> None:
    err = safe_pull._preflight(_state(rebase_in_progress=True))
    assert err is not None
    assert "rebase" in err.lower()


def test_preflight_ok() -> None:
    assert safe_pull._preflight(_state()) is None


def test_dry_run_includes_stash_when_dirty() -> None:
    import io
    from contextlib import redirect_stdout

    ctx = safe_pull.SafePullContext(
        cwd=safe_pull.Path("."),
        state=_state(modified_count=2, staged_count=0, untracked_count=0),
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        safe_pull._print_dry_run_steps(ctx)
    out = buf.getvalue()
    assert "stash" in out.lower()
    assert "fetch" in out.lower()
    assert "merge" in out.lower()
