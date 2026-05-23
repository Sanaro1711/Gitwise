"""Execution pipeline: pre-checks, runner, post-checks, failure handling."""

from gitwise.execution.pipeline import execute_plan, run_pre_checks_for_plan

__all__ = ["execute_plan", "run_pre_checks_for_plan"]
