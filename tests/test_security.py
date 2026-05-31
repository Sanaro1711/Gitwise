"""Tests for secret redaction and safe LLM context."""

from __future__ import annotations

from gitwise.llm.context import _is_sensitive_path, build_repo_context
from gitwise.llm.sanitize import redact_remote_url, redact_secrets


def test_redact_api_key_in_text() -> None:
    text = "key=AIzaSyD1234567890abcdefghijklmnopqrstuv"
    out = redact_secrets(text)
    assert "AIza" not in out
    assert "REDACTED" in out


def test_redact_url_credentials() -> None:
    url = "https://user:secretpass@github.com/org/repo.git"
    assert "secretpass" not in redact_remote_url(url)
    assert "github.com/org/repo.git" in redact_remote_url(url)


def test_redact_token_assignment() -> None:
    text = "GEMINI_API_KEY=super-secret-value"
    out = redact_secrets(text)
    assert "super-secret-value" not in out


def test_sensitive_paths_filtered_from_status() -> None:
    assert _is_sensitive_path("?? .env")
    assert _is_sensitive_path(" M gemini_api_key")
    assert not _is_sensitive_path(" M README.md")


def test_build_context_not_in_repo(monkeypatch) -> None:
    from gitwise.models import RepoState
    from gitwise.repo.inspector import _NOT_IN_REPO

    class FakeInspector:
        def __init__(self, cwd=None) -> None:
            pass

        def inspect(self) -> RepoState:
            return _NOT_IN_REPO

    monkeypatch.setattr("gitwise.llm.context.RepoInspector", FakeInspector)
    state, ctx = build_repo_context()
    assert state.in_repo is False
    assert "not inside" in ctx.lower()
