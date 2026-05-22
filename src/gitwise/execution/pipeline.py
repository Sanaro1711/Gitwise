"""
Orchestration stub for: pre-checks → command → post-checks → failure handler.

Not wired to gw do yet. See docs/EXECUTION_PIPELINE.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gitwise.models import CommandPlan, RepoState


class PipelineStage(str, Enum):
    PRE_CHECK = "pre_check"
    COMMAND = "command"
    POST_CHECK = "post_check"
    FAILURE = "failure"


@dataclass
class ExecutionResult:
    """Outcome of a full pipeline run."""

    success: bool
    stage: PipelineStage
    message: str
    suggested_next: list[str]
    state: RepoState | None = None


def run_pipeline(
    plan: CommandPlan,
    state: RepoState,
    *,
    confirmed: bool = False,
) -> ExecutionResult:
    """
    Future entry point for gw do after user confirms.

    Today returns not-implemented; gw do will call this when the pipeline is built.
    """
    _ = (plan, state, confirmed)
    return ExecutionResult(
        success=False,
        stage=PipelineStage.PRE_CHECK,
        message="Execution pipeline not implemented yet.",
        suggested_next=["Use git commands manually, or wait for gw do with pipeline support."],
        state=state,
    )
