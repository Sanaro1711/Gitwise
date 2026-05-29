"""Intent parsing — single-quoted values."""

from __future__ import annotations

from gitwise.matching.intent_parser import parse_intent, text_for_matching


def test_push_this_to_main() -> None:
    i = parse_intent("push this to main")
    assert i.primary_action == "push"
    assert i.branch == "main"


def test_commit_single_quotes() -> None:
    i = parse_intent("commit 'fix login bug'")
    assert i.primary_action == "commit"
    assert i.message == "fix login bug"


def test_commit_this_code_single_quotes() -> None:
    i = parse_intent("commit this code with message 'Added the do feature'")
    assert i.message == "Added the do feature"


def test_create_branch_single_quotes() -> None:
    i = parse_intent("create branch 'feature/login'")
    assert i.primary_action == "branch_create"
    assert i.name == "feature/login"
    assert i.branch == "feature/login"


def test_delete_branch_single_quotes() -> None:
    i = parse_intent("delete branch 'old-hotfix'")
    assert i.primary_action == "branch_delete"
    assert i.name == "old-hotfix"


def test_switch_branch_single_quotes() -> None:
    i = parse_intent("switch to 'main'")
    assert i.name == "main"


def test_stash_message_single_quotes() -> None:
    i = parse_intent("stash changes with message 'wip refactor'")
    assert i.message == "wip refactor"


def test_discard_file_single_quotes() -> None:
    i = parse_intent("discard changes in 'src/app.py'")
    assert i.path == "src/app.py"


def test_clone_url_single_quotes() -> None:
    i = parse_intent("clone 'https://github.com/org/repo.git'")
    assert i.url == "https://github.com/org/repo.git"


def test_push_branch_single_quotes() -> None:
    i = parse_intent("push to 'main'")
    assert i.branch == "main"


def test_quoted_text_excluded_from_matching() -> None:
    assert text_for_matching("commit 'pull latest'") == "commit"
    assert text_for_matching("create branch 'stash everything'") == "create branch"


def test_commit_message_with_recipe_words_not_wrong_action() -> None:
    i = parse_intent("commit 'pull latest and push to main'")
    assert i.primary_action == "commit"
    assert i.message == "pull latest and push to main"
    assert "pull" not in i.keywords


def test_branch_name_with_stash_words_not_stash_action() -> None:
    i = parse_intent("create branch 'feature/stash-wip'")
    assert i.primary_action == "branch_create"
    assert i.name == "feature/stash-wip"


def test_pull_from_branch_single_quotes() -> None:
    i = parse_intent("pull from branch 'main'")
    assert i.primary_action == "pull"
    assert i.branch == "main"


def test_pull_branch_name_not_used_for_matching() -> None:
    assert text_for_matching("pull from branch 'stash everything'") == "pull from branch"
    i = parse_intent("pull from branch 'stash everything'")
    assert i.primary_action == "pull"
    assert i.branch == "stash everything"
