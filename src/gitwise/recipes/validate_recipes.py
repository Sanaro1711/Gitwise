#!/usr/bin/env python3
"""Validate recipes.yaml structure and content. Run: python validate_recipes.py"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED_FIELDS = {
    "id",
    "category",
    "phrases",
    "requires",
    "danger",
    "command",
    "explanation",
    "confirmation_level",
}
VALID_CATEGORIES = {
    "sync",
    "branch",
    "stash",
    "commit",
    "undo",
    "remote",
    "history",
    "github",
}
VALID_CONFIRMATION = {"standard", "elevated", "readonly", "deferred"}
MIN_PHRASES = 10
MIN_RECIPES = 30  # rough target; catalog may grow


def main() -> int:
    path = Path(__file__).parent / "recipes.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    recipes = data.get("recipes", [])
    errors: list[str] = []

    if len(recipes) < MIN_RECIPES:
        errors.append(f"Expected at least {MIN_RECIPES} recipes, found {len(recipes)}")

    ids = [r.get("id") for r in recipes]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate recipe ids detected")

    for i, recipe in enumerate(recipes):
        prefix = f"recipes[{i}] id={recipe.get('id', '?')}"
        missing = REQUIRED_FIELDS - set(recipe.keys())
        if missing:
            errors.append(f"{prefix}: missing fields {missing}")

        if recipe.get("category") not in VALID_CATEGORIES:
            errors.append(f"{prefix}: invalid category {recipe.get('category')}")

        if recipe.get("confirmation_level") not in VALID_CONFIRMATION:
            errors.append(
                f"{prefix}: invalid confirmation_level {recipe.get('confirmation_level')}"
            )

        phrases = recipe.get("phrases", [])
        if not isinstance(phrases, list) or len(phrases) < MIN_PHRASES:
            errors.append(f"{prefix}: need at least {MIN_PHRASES} phrases, got {len(phrases)}")

        cmd = recipe.get("command")
        if not (isinstance(cmd, str) or (isinstance(cmd, list) and all(isinstance(c, str) for c in cmd))):
            errors.append(f"{prefix}: command must be string or list of strings")

        if not isinstance(recipe.get("danger"), bool):
            errors.append(f"{prefix}: danger must be boolean")

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK: {len(recipes)} recipes validated.")
    print("IDs:", ", ".join(ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
