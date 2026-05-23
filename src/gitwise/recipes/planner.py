"""Build CommandPlan from match + repo state + intent."""

from __future__ import annotations

from pathlib import Path

from gitwise.matching.intent_parser import parse_intent
from gitwise.matching.matcher import IntentMatcher
from gitwise.matching.push_resolver import resolve_push
from gitwise.models import CommandPlan, MatchResult, ParsedIntent, RepoState
from gitwise.recipes.loader import PUSH_RECIPE_IDS, Recipe, load_recipes
from gitwise.recipes.render import render_commands, render_explanation
from gitwise.repo.inspector import RepoInspector

_CATEGORY_LABELS = {
    "sync": "Sync",
    "branch": "Branch",
    "stash": "Stash",
    "commit": "Commit",
    "undo": "Undo",
    "remote": "Remote",
    "history": "History",
    "github": "GitHub",
}


def plan_from_intent(
    intent_text: str,
    *,
    cwd: Path | str | None = None,
    matcher: IntentMatcher | None = None,
) -> tuple[CommandPlan | None, ParsedIntent, RepoState, str | None]:
    """
    Match intent and build a CommandPlan.

    Returns (plan, intent, state, error_message).
    """
    intent = parse_intent(intent_text)
    state = RepoInspector(cwd=cwd).inspect()
    matcher = matcher or IntentMatcher()

    outcome = matcher.match(intent, state, cwd=cwd)

    if outcome.ambiguous and outcome.best and outcome.candidates:
        lines = ["Ambiguous intent — multiple workflows match:"]
        for i, c in enumerate(outcome.candidates[:3], 1):
            lines.append(f"  {i}. {c.recipe_id} (score {c.score:.0f}, phrase: {c.phrase!r})")
        lines.append("Rephrase with more detail, e.g. push / pull / stash / commit.")
        return None, intent, state, "\n".join(lines)

    if not outcome.best:
        msg = _no_match_message(intent, state, outcome.blocked)
        return None, intent, state, msg

    return (
        build_plan(outcome.best, intent, state, cwd=cwd),
        intent,
        state,
        None,
    )


def build_plan(
    match: MatchResult,
    intent: ParsedIntent,
    state: RepoState,
    *,
    cwd=None,
) -> CommandPlan:
    recipes = {r.id: r for r in load_recipes()}
    recipe_id = match.recipe_id

    if recipe_id in PUSH_RECIPE_IDS:
        return _plan_push(intent, state, match, cwd=cwd)

    if intent.wants_force_push and state.has_upstream:
        recipe = recipes["force_push_safe"]
        return _plan_from_recipe(recipe, intent, state, match, cwd=cwd)

    recipe = recipes.get(recipe_id)
    if not recipe:
        raise KeyError(f"Unknown recipe: {recipe_id}")

    return _plan_from_recipe(recipe, intent, state, match, cwd=cwd)


def _plan_push(
    intent: ParsedIntent,
    state: RepoState,
    match: MatchResult,
    *,
    cwd=None,
) -> CommandPlan:
    if intent.wants_force_push and state.has_upstream:
        recipes = {r.id: r for r in load_recipes()}
        return _plan_from_recipe(recipes["force_push_safe"], intent, state, match, cwd=cwd)

    if not state.in_repo:
        raise ValueError("Cannot push outside a git repository")

    push = resolve_push(state, intent)
    recipe_id = match.recipe_id
    warnings: list[str] = []
    if state.behind > 0:
        warnings.append("You are behind the remote; push may be rejected until you pull.")

    return CommandPlan(
        recipe_id=recipe_id,
        category="Sync",
        explanation=push.explanation,
        commands=push.commands,
        danger=False,
        confirmation_level="standard",
        match_score=match.score,
        matched_phrase=match.phrase,
        warnings=warnings,
    )


def _plan_from_recipe(
    recipe: Recipe,
    intent: ParsedIntent,
    state: RepoState,
    match: MatchResult,
    *,
    cwd=None,
) -> CommandPlan:
    commands = list(render_commands(recipe, state, intent, cwd=cwd))
    explanation = render_explanation(recipe, state, intent)

    if recipe.id == "delete_local_branch" and intent.wants_force_delete:
        ctx_name = intent.name or intent.branch or ""
        commands = [f"git branch -D {ctx_name}"]

    if recipe.id == "commit_changes" and not intent.message:
        explanation += " Add a message: gw do 'commit \"your message\"'"

    warnings: list[str] = []
    if recipe.danger:
        warnings.append("This operation may permanently discard work.")

    return CommandPlan(
        recipe_id=recipe.id,
        category=_CATEGORY_LABELS.get(recipe.category, recipe.category.title()),
        explanation=explanation,
        commands=commands,
        danger=recipe.danger,
        confirmation_level=recipe.confirmation_level,
        match_score=match.score,
        matched_phrase=match.phrase,
        warnings=warnings,
    )


def _no_match_message(
    intent: ParsedIntent,
    state: RepoState,
    blocked: list[tuple[str, float, list[str]]],
) -> str:
    lines = ["No matching workflow for that intent."]
    if not state.in_repo:
        lines.append("You are not in a git repository. Try: gw do 'clone https://github.com/user/repo.git'")
    if blocked:
        top = sorted(blocked, key=lambda x: x[1], reverse=True)[:3]
        lines.append("")
        lines.append("Closest matches (blocked by repo state):")
        for rid, score, failures in top:
            lines.append(f"  - {rid} (score {score:.0f}): {'; '.join(failures)}")
    lines.append("")
    lines.append("Try: gw whereami — then rephrase, e.g. push / pull / stash / commit.")
    return "\n".join(lines)
