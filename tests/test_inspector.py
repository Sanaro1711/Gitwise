"""Tests for RepoInspector with mocked git output."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from gitwise.repo.inspector import RepoInspector


def _mock_git_responses(responses: dict[tuple[str, ...], str | None]):
    """Map git arg tuples to stdout; None simulates command failure."""

    def fake_run(args, *, cwd=None, timeout=30.0):
        key = tuple(args)
        if key not in responses:
            raise AssertionError(f"Unexpected git call: {args}")
        value = responses[key]
        if value is None:
            from gitwise.repo.git_runner import GitError

            raise GitError("mock failure")
        return value

    return fake_run


@patch("gitwise.repo.inspector.run_git_optional")
@patch("gitwise.repo.inspector.run_git")
def test_inspect_full_repo(mock_run, mock_optional, tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    mock_run.side_effect = _mock_git_responses(
        {
            ("rev-parse", "--show-toplevel"): str(tmp_path),
        }
    )

    def optional(args, *, cwd=None, timeout=30.0):
        key = tuple(args)
        table: dict[tuple[str, ...], str | None] = {
            ("rev-parse", "--is-inside-work-tree"): "true",
            ("branch", "--show-current"): "feature-x",
            ("remote",): "origin",
            ("config", "--get", "branch.feature-x.merge"): "refs/heads/feature-x",
            ("config", "--get", "branch.feature-x.remote"): "origin",
            ("symbolic-ref", "refs/remotes/origin/HEAD"): "refs/remotes/origin/main",
            ("status", "--porcelain"): " M file.txt\n?? new.txt\n",
            ("rev-list", "--left-right", "--count", "origin/feature-x...HEAD"): "1\t2",
            ("stash", "list"): "",
            ("remote", "get-url", "origin"): "https://github.com/example/my-repo.git",
        }
        if key not in table:
            return None
        return table[key]

    mock_optional.side_effect = optional

    state = RepoInspector(cwd=tmp_path).inspect()

    assert state.in_repo is True
    assert state.repo_name == "my-repo"
    assert state.branch == "feature-x"
    assert state.remote == "origin"
    assert state.upstream == "origin/feature-x"
    assert state.default_branch == "main"
    assert state.modified_count == 1
    assert state.untracked_count == 1
    assert state.ahead == 2
    assert state.behind == 1
    assert state.has_upstream is True


@patch("gitwise.repo.inspector.run_git_optional")
def test_not_in_repo(mock_optional) -> None:
    mock_optional.return_value = None
    state = RepoInspector().inspect()
    assert state.in_repo is False
