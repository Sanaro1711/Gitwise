"""Tests for whereami formatting and command."""

from __future__ import annotations

from gitwise.models import RepoState
from gitwise.output import format_whereami


def test_format_whereami_clean_synced() -> None:
    state = RepoState(
        in_repo=True,
        root="/tmp/proj",
        repo_name="Gitwise",
        branch="main",
        remote="origin",
        remote_url="https://github.com/example/gitwise.git",
        upstream="origin/main",
        upstream_ref="origin/main",
        default_branch="main",
        ahead=0,
        behind=0,
        has_upstream=True,
        has_remote=True,
    )
    text = format_whereami(state)
    assert "Repo: Gitwise" in text
    assert "Branch: main" in text
    assert "Clean" in text
    assert "0 commits ahead" in text


def test_format_whereami_dirty_ahead() -> None:
    state = RepoState(
        in_repo=True,
        root="/tmp/proj",
        repo_name="Gmail_Searcher",
        branch="local-embeddings",
        remote="origin",
        remote_url=None,
        upstream="origin/local-embeddings",
        upstream_ref="origin/local-embeddings",
        default_branch="main",
        modified_count=3,
        untracked_count=1,
        ahead=2,
        behind=0,
        has_upstream=True,
        has_remote=True,
    )
    text = format_whereami(state)
    assert "3 modified files" in text
    assert "1 untracked file" in text
    assert "2 commits ahead" in text
    assert "0 commits behind" in text


def test_format_not_in_repo() -> None:
    state = RepoState(
        in_repo=False,
        root=None,
        repo_name=None,
        branch=None,
        remote=None,
        remote_url=None,
        upstream=None,
        upstream_ref=None,
        default_branch=None,
    )
    assert "Not inside" in format_whereami(state)


def test_parse_intent_push_to_main() -> None:
    from gitwise.matching.intent_parser import parse_intent

    intent = parse_intent('push this to main')
    assert "push" in intent.keywords
    assert intent.branch == "main"
