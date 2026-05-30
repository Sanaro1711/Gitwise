"""gw ask command entry."""

from __future__ import annotations

from pathlib import Path

from gitwise.workflows.ask import run_ask


def run_ask_cmd(
    question: str,
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> int:
    return run_ask(question, cwd=cwd, dry_run=dry_run, yes=yes)
