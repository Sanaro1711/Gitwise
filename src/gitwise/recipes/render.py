"""Render recipe commands and explanations with context."""

from __future__ import annotations

import re

from gitwise.models import ParsedIntent, RepoState
from gitwise.recipes.loader import Recipe

_DEFAULT_STASH_MESSAGE = "gitwise stash"


def build_context(state: RepoState, intent: ParsedIntent) -> dict[str, str]:
    remote = intent.remote or state.remote or "origin"
    branch = state.branch or ""
    name = intent.name or intent.branch or branch
    return {
        "repo_name": state.repo_name or "repository",
        "branch": branch,
        "remote": remote,
        "upstream": state.upstream or f"{remote}/{branch}",
        "default_branch": state.default_branch or "main",
        "url": intent.url or "",
        "path": intent.path or "",
        "name": name,
        "message": intent.message or _DEFAULT_STASH_MESSAGE,
    }


def render_text(template: str, ctx: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return ctx.get(key, match.group(0))

    return re.sub(r"\{(\w+)\}", repl, template)


def render_commands(
    recipe: Recipe,
    state: RepoState,
    intent: ParsedIntent,
    *,
    cwd=None,
) -> list[str]:
    ctx = build_context(state, intent)
    commands = [render_text(c, ctx) for c in recipe.commands_template]

    if recipe.id == "set_remote_origin":
        from gitwise.recipes.requires import _has_remote_named

        if _has_remote_named(state, "origin", cwd):
            commands = [render_text("git remote set-url origin {url}", ctx)]

    if recipe.id == "abort_merge_or_rebase":
        if state.rebase_in_progress:
            commands = ["git rebase --abort"]
        elif state.merge_in_progress:
            commands = ["git merge --abort"]

    if recipe.id == "show_diff" and intent.wants_staged_diff:
        commands = ["git diff --staged"]

    return commands


def render_explanation(
    recipe: Recipe,
    state: RepoState,
    intent: ParsedIntent,
) -> str:
    ctx = build_context(state, intent)
    return render_text(recipe.explanation, ctx)
