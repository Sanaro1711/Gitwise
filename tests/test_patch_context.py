"""Tests for safe patch building for gw diff."""

from __future__ import annotations

from gitwise.llm.patch_context import is_sensitive_path


def test_sensitive_paths_blocked() -> None:
    assert is_sensitive_path(".env")
    assert is_sensitive_path("config/gemini_api_key")
    assert not is_sensitive_path("src/gitwise/cli.py")
