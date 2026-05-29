"""gw pull — guided safe pull with conflict help."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from gitwise.workflows.safe_pull import run_safe_pull


def run_pull(
    *,
    cwd: Path | None = None,
    from_branch: Optional[str] = None,
    dry_run: bool = False,
    yes: bool = False,
) -> int:
    return run_safe_pull(
        cwd=cwd,
        source_branch=from_branch,
        dry_run=dry_run,
        skip_confirm=yes,
    )
