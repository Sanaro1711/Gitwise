"""gw diff command entry."""

from __future__ import annotations

from pathlib import Path

from gitwise.workflows.diff_report import run_diff


def run_diff_cmd(
    from_ref: str,
    to_ref: str | None = None,
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
) -> int:
    return run_diff(from_ref, to_ref, cwd=cwd, dry_run=dry_run)
