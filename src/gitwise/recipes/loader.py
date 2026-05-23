"""Load and validate recipes from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

RECIPES_PATH = Path(__file__).parent / "recipes.yaml"

PUSH_RECIPE_IDS = frozenset({"push_current_branch", "push_new_branch_upstream"})


@dataclass(frozen=True)
class Recipe:
    id: str
    category: str
    phrases: tuple[str, ...]
    requires: tuple[str, ...]
    danger: bool
    command: str | tuple[str, ...]
    explanation: str
    confirmation_level: str

    @property
    def commands_template(self) -> list[str]:
        if isinstance(self.command, str):
            return [self.command]
        return list(self.command)


def load_recipes(path: Path | None = None) -> list[Recipe]:
    path = path or RECIPES_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    recipes: list[Recipe] = []
    for raw in data.get("recipes", []):
        cmd = raw["command"]
        if isinstance(cmd, list):
            cmd = tuple(cmd)
        recipes.append(
            Recipe(
                id=raw["id"],
                category=raw["category"],
                phrases=tuple(raw["phrases"]),
                requires=tuple(raw.get("requires", [])),
                danger=bool(raw["danger"]),
                command=cmd,
                explanation=raw["explanation"].strip(),
                confirmation_level=raw["confirmation_level"],
            )
        )
    return recipes
