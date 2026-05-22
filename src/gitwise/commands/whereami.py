"""gw whereami — full repo status breakdown."""

from __future__ import annotations

import sys
from pathlib import Path

from gitwise.output import format_whereami
from gitwise.repo.inspector import RepoInspector


def run_whereami(cwd: Path | None = None) -> int:
    """
    Inspect the repository at cwd and print status.
    Returns exit code 0 on success, 1 if not in a repo.
    """
    inspector = RepoInspector(cwd=cwd)
    state = inspector.inspect()
    print(format_whereami(state))
    return 0 if state.in_repo else 1
