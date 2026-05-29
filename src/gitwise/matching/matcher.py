"""Fuzzy-match user intent to recipes using rapidfuzz."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from gitwise.models import MatchResult, ParsedIntent, RepoState
from gitwise.matching.intent_parser import text_for_matching
from gitwise.recipes.loader import PUSH_RECIPE_IDS, Recipe, load_recipes
from gitwise.recipes.requires import evaluate_requires

MIN_SCORE = 72.0
AMBIGUITY_MARGIN = 5.0

# Boost when primary_action from intent parser aligns with recipe
_ACTION_RECIPE_BOOST: dict[str, dict[str, float]] = {
    "push": {"push_current_branch": 12, "push_new_branch_upstream": 12},
    "force_push": {"force_push_safe": 25},
    "pull": {"pull_latest": 18},
    "fetch": {"fetch_remote": 22},
    "stash": {"stash_changes": 15, "apply_latest_stash": 10},
    "stash_untracked": {"stash_including_untracked": 25},
    "commit": {"commit_changes": 20},
    "stage": {"stage_all_changes": 22},
    "unstage": {"undo_staged": 22},
    "undo_commit": {"undo_last_commit_keep": 22},
    "discard_all": {"discard_all_local": 22},
    "discard_file": {"discard_one_file": 22},
    "merge": {"merge_into_default": 18},
    "rebase": {"rebase_onto_default": 18},
    "abort": {"abort_merge_or_rebase": 22},
    "clone": {"clone_repo": 25},
    "remote": {"set_remote_origin": 18},
    "branch_create": {"create_branch": 20},
    "branch_switch": {"switch_branch": 20},
    "branch_delete": {"delete_local_branch": 12, "delete_remote_branch": 12},
    "log": {"check_history": 20},
    "status": {"show_status": 22},
    "diff": {"show_diff": 20},
    "tag": {"create_tag": 20},
    "pr": {"create_github_pr": 20},
}

# Down-rank recipes when action clearly points elsewhere
_ACTION_RECIPE_PENALTY: dict[str, set[str]] = {
    "fetch": {"pull_latest"},
    "pull": {"fetch_remote"},
    "push": {"pull_latest", "fetch_remote"},
    "stash_untracked": {"stash_changes"},
}


@dataclass
class MatcherOutcome:
    best: MatchResult | None
    candidates: list[MatchResult]
    ambiguous: bool
    blocked: list[tuple[str, float, list[str]]]  # recipe_id, score, failures


class IntentMatcher:
    def __init__(self, recipes: list[Recipe] | None = None) -> None:
        self.recipes = recipes or load_recipes()
        self._phrase_index: list[tuple[str, str]] = []
        for recipe in self.recipes:
            for phrase in recipe.phrases:
                self._phrase_index.append((phrase, recipe.id))

    def match(
        self,
        intent: ParsedIntent,
        state: RepoState,
        *,
        cwd=None,
    ) -> MatcherOutcome:
        normalized = _normalize_intent(text_for_matching(intent.raw))
        if not normalized:
            return MatcherOutcome(None, [], False, [])

        raw_scores: list[tuple[str, str, float]] = []
        for phrase, recipe_id in self._phrase_index:
            score = fuzz.token_set_ratio(normalized, phrase.lower())
            score += _action_boost(intent, recipe_id)
            score -= _action_penalty(intent, recipe_id)
            raw_scores.append((recipe_id, phrase, score))

        # Best score per recipe
        per_recipe: dict[str, tuple[str, float]] = {}
        for recipe_id, phrase, score in raw_scores:
            if recipe_id not in per_recipe or score > per_recipe[recipe_id][1]:
                per_recipe[recipe_id] = (phrase, score)

        # Collapse push pair — keep higher scorer as representative
        per_recipe = _collapse_push_scores(per_recipe, intent, state, cwd=cwd)

        ranked = sorted(
            per_recipe.items(),
            key=lambda x: x[1][1],
            reverse=True,
        )

        eligible: list[MatchResult] = []
        blocked: list[tuple[str, float, list[str]]] = []

        for recipe_id, (phrase, score) in ranked:
            recipe = self._by_id(recipe_id)
            ok, failures = evaluate_requires(recipe.requires, state, intent, cwd=cwd)
            if ok:
                if score >= MIN_SCORE:
                    eligible.append(
                        MatchResult(recipe_id=recipe_id, score=score, phrase=phrase)
                    )
            else:
                blocked.append((recipe_id, score, failures))

        if not eligible:
            return MatcherOutcome(None, [], False, blocked)

        eligible.sort(key=lambda m: m.score, reverse=True)
        ambiguous = (
            len(eligible) > 1
            and eligible[0].score - eligible[1].score < AMBIGUITY_MARGIN
        )
        return MatcherOutcome(
            best=eligible[0],
            candidates=eligible[:5],
            ambiguous=ambiguous,
            blocked=blocked,
        )

    def _by_id(self, recipe_id: str) -> Recipe:
        for r in self.recipes:
            if r.id == recipe_id:
                return r
        raise KeyError(recipe_id)


def _normalize_intent(text: str) -> str:
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s/@.-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _action_boost(intent: ParsedIntent, recipe_id: str) -> float:
    if not intent.primary_action:
        return 0.0
    boosts = _ACTION_RECIPE_BOOST.get(intent.primary_action, {})
    bonus = boosts.get(recipe_id, 0.0)
    if intent.wants_force_push and recipe_id == "force_push_safe":
        bonus += 15
    if intent.wants_untracked_stash and recipe_id == "stash_including_untracked":
        bonus += 15
    if intent.wants_staged_diff and recipe_id == "show_diff":
        bonus += 12
    if intent.wants_upstream and recipe_id == "push_new_branch_upstream":
        bonus += 8
    return bonus


def _action_penalty(intent: ParsedIntent, recipe_id: str) -> float:
    if not intent.primary_action:
        return 0.0
    penalized = _ACTION_RECIPE_PENALTY.get(intent.primary_action, set())
    return 12.0 if recipe_id in penalized else 0.0


def _collapse_push_scores(
    per_recipe: dict[str, tuple[str, float]],
    intent: ParsedIntent,
    state: RepoState,
    *,
    cwd=None,
) -> dict[str, tuple[str, float]]:
    """Keep the best push recipe that passes requires (so -u is chosen via planner)."""
    push_scores = [
        (rid, data)
        for rid, data in per_recipe.items()
        if rid in PUSH_RECIPE_IDS
    ]
    if not push_scores:
        return per_recipe

    if intent.wants_force_push:
        return per_recipe

    matcher_recipes = {r.id: r for r in load_recipes()}

    def passes(rid: str) -> bool:
        recipe = matcher_recipes[rid]
        ok, _ = evaluate_requires(recipe.requires, state, intent, cwd=cwd)
        return ok

    eligible_push = [(rid, data) for rid, data in push_scores if passes(rid)]
    pick_from = eligible_push if eligible_push else push_scores
    best_id, best_data = max(pick_from, key=lambda x: x[1][1])
    out = {k: v for k, v in per_recipe.items() if k not in PUSH_RECIPE_IDS}
    out[best_id] = best_data
    return out
