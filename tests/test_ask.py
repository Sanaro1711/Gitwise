"""Tests for gw ask LLM integration."""

from __future__ import annotations

import json
from pathlib import Path

from gitwise.llm.config import load_api_key
from gitwise.llm.sanitize import redact_remote_url
from gitwise.llm.response import parse_ask_response
from gitwise.llm.validator import validate_llm_plan
from gitwise.models import RepoState


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
        modified_count=2,
        staged_count=0,
        untracked_count=0,
        has_upstream=True,
        has_remote=True,
    )
    defaults.update(kwargs)
    return RepoState(**defaults)


def test_redact_remote_url_strips_credentials() -> None:
    url = "https://user:secret@github.com/org/repo.git"
    assert "secret" not in redact_remote_url(url)
    assert "github.com/org/repo.git" in redact_remote_url(url)


def test_parse_explain_response() -> None:
    raw = json.dumps({"mode": "explain", "answer": "You are ahead of remote.", "plan": None})
    parsed = parse_ask_response(raw)
    assert parsed.mode == "explain"
    assert parsed.plan is None


def test_parse_plan_response() -> None:
    raw = json.dumps(
        {
            "mode": "plan",
            "answer": "Stage, commit, and push.",
            "plan": {
                "summary": "Save work",
                "commands": ["git add .", 'git commit -m "wip"', "git push origin feature"],
                "gitwise_intent": "push",
            },
        }
    )
    parsed = parse_ask_response(raw)
    assert parsed.mode == "plan"
    assert parsed.plan is not None
    assert len(parsed.plan.commands) == 3


def test_validate_save_plan_matches() -> None:
    llm_cmds = ["git add .", 'git commit -m "save changes"', "git push origin feature"]
    result = validate_llm_plan(
        llm_cmds,
        question="save all my code in the safest way",
        state=_state(),
    )
    assert result.status == "validated"
    assert result.gitwise_plan is not None
    assert result.gitwise_plan.recipe_id == "save"


def test_validate_blocks_unsafe_commands() -> None:
    result = validate_llm_plan(
        ["git config credential.helper store"],
        question="store password",
        state=_state(),
    )
    assert result.status == "unsafe"


def test_validate_push_intent() -> None:
    result = validate_llm_plan(
        ["git push origin feature"],
        question="push",
        state=_state(),
    )
    assert result.status == "validated"


def test_load_api_key_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    assert load_api_key() == "test-key-123"


def test_load_api_key_from_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    key_file = tmp_path / "gemini_api_key"
    key_file.write_text("file-key\n", encoding="utf-8")
    monkeypatch.setattr(
        "gitwise.llm.config._KEY_FILE_NAMES",
        (key_file,),
    )
    assert load_api_key(cwd=tmp_path) == "file-key"
