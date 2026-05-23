"""gw do — match intent, show plan, confirm, run."""

from __future__ import annotations

import sys
from pathlib import Path

from gitwise.execution.runner import run_commands
from gitwise.recipes.planner import plan_from_intent


def _confirm(plan, *, assume_yes: bool = False) -> bool:
    if assume_yes:
        return True

    level = plan.confirmation_level
    if level == "deferred":
        return False

    if level == "elevated" and plan.danger:
        typer_prompt = "Type 'yes' to confirm you understand the risk: "
        try:
            answer = input(typer_prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return False
        return answer == "yes"

    try:
        answer = input("Proceed? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False
    return answer in ("y", "yes")


def _print_plan(plan) -> None:
    print(f"Category: {plan.category}")
    print(f"Matched: {plan.recipe_id} (score: {plan.match_score:.0f})")
    if plan.matched_phrase:
        print(f"Phrase: {plan.matched_phrase!r}")
    print()
    print("Why:")
    for line in plan.explanation.strip().splitlines():
        print(f"  {line}")
    print()
    if plan.warnings:
        print("Warnings:")
        for w in plan.warnings:
            print(f"  ! {w}")
        print()
    print("Commands:")
    for cmd in plan.commands:
        print(f"  $ {cmd}")
    print()


def run_do(
    intent_text: str,
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> int:
    plan, intent, state, error = plan_from_intent(intent_text, cwd=cwd)

    if error:
        print(error, file=sys.stderr)
        return 1

    assert plan is not None

    _print_plan(plan)

    if plan.confirmation_level == "deferred":
        print("This workflow is not executed automatically (GitHub PR / gh integration).")
        print("Run the suggested command manually when ready.")
        return 0

    if dry_run:
        print("(dry-run — no commands executed)")
        return 0

    if not _confirm(plan, assume_yes=yes):
        print("Cancelled.")
        return 0

    results = run_commands(plan.commands, cwd=cwd)
    for r in results:
        if r.stdout:
            print(r.stdout, end="" if r.stdout.endswith("\n") else "\n")
        if r.stderr:
            print(r.stderr, end="" if r.stderr.endswith("\n") else "", file=sys.stderr)

    last = results[-1]
    if last.returncode != 0:
        print(f"\nCommand failed (exit {last.returncode}): {last.command}", file=sys.stderr)
        print("Post-run checks and failure suggestions coming in a future update.", file=sys.stderr)
        return last.returncode

    print("\nDone.")
    return 0
