"""Run confirmed git command(s)."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


def run_commands(
    commands: list[str],
    *,
    cwd: Path | str | None = None,
) -> list[RunResult]:
    """Execute commands sequentially; stop on first failure."""
    results: list[RunResult] = []
    work_dir = Path(cwd) if cwd else None

    for cmd in commands:
        args = shlex.split(cmd, posix=False)
        proc = subprocess.run(
            args,
            cwd=work_dir,
            capture_output=True,
            shell=False,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        result = RunResult(
            command=cmd,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
        results.append(result)
        if proc.returncode != 0:
            break
    return results
