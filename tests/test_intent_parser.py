"""Intent parsing edge cases."""

from __future__ import annotations

from gitwise.matching.intent_parser import parse_intent


def test_push_this_to_main() -> None:
    i = parse_intent("push this to main")
    assert i.primary_action == "push"
    assert i.branch == "main"


def test_push_without_to() -> None:
    i = parse_intent("upload my commits")
    assert i.primary_action == "push"


def test_commit_message() -> None:
    i = parse_intent('commit "fix login bug"')
    assert i.primary_action == "commit"
    assert i.message == "fix login bug"


def test_stash_untracked() -> None:
    i = parse_intent("stash everything including untracked")
    assert i.primary_action in ("stash_untracked", "stash")
    assert i.wants_untracked_stash


def test_clone_url() -> None:
    i = parse_intent("clone https://github.com/org/repo.git")
    assert i.primary_action == "clone"
    assert "github.com" in (i.url or "")


def test_discard_file_path() -> None:
    i = parse_intent("discard changes in src/app.py")
    assert i.path == "src/app.py"
    assert i.primary_action == "discard_file"


def test_force_push() -> None:
    i = parse_intent("force push safely after rebase")
    assert i.wants_force_push
    assert i.primary_action == "force_push"


def test_uncommit_synonym() -> None:
    i = parse_intent("uncommit last commit keep changes")
    assert i.primary_action == "undo_commit"
