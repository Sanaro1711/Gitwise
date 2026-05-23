"""Orchestrate pre-checks → run → post-checks → failure handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gitwise.execution.failures import (
    classify_failure,
    format_failure_report,
    format_post_check_warning,
    format_pre_check_block,
)
from gitwise.execution.post_checks import run_post_checks
from gitwise.execution.pre_checks import run_pre_checks
from gitwise.execution.runner import RunResult, run_commands
from gitwise.execution.types import PreCheckResult
from gitwise.models import CommandPlan, ParsedIntent, RepoState
from gitwise.repo.inspector import RepoInspector


@dataclass
class PipelineResult:
    exit_code: int
    pre: PreCheckResult | None = None
    run_results: list[RunResult] | None = None


def run_pre_checks_for_plan(
    plan: CommandPlan,
    state: RepoState,
    intent: ParsedIntent,
    *,
    cwd: Path | str | None = None,
) -> PreCheckResult:
    """Run before confirmation; blocks bad plans early."""
    return run_pre_checks(plan, state, intent, cwd=cwd)


def execute_plan(
    plan: CommandPlan,
    state: RepoState,
    intent: ParsedIntent,
    *,
    cwd: Path | str | None = None,
) -> PipelineResult:
    """Run commands then post-checks / failure handling."""
    results = run_commands(plan.commands, cwd=cwd)
    inspector = RepoInspector(cwd=cwd)
    state_after = inspector.inspect()

    for r in results:
        if r.stdout:
            print(r.stdout, end="" if r.stdout.endswith("\n") else "\n")
        if r.stderr:
            print(r.stderr, end="" if r.stderr.endswith("\n") else "", file=__import__("sys").stderr)

    last = results[-1] if results else None
    if last and last.returncode != 0:
        report = classify_failure(
            stderr=last.stderr,
            stdout=last.stdout,
            command=last.command,
            recipe_id=plan.recipe_id,
            state=state_after,
        )
        print(format_failure_report(report, state_after))
        return PipelineResult(exit_code=last.returncode, run_results=results)

    post = run_post_checks(plan, state, state_after, intent, cwd=cwd)
    if not post.ok:
        print(format_post_check_warning(post))

    return PipelineResult(exit_code=0, run_results=results)
