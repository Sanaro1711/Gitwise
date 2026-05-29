"""Gitwise CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from gitwise import __version__
from gitwise.commands.do_cmd import run_do
from gitwise.commands.pull_cmd import run_pull
from gitwise.commands.whereami import run_whereami

app = typer.Typer(
    name="gw",
    help="Gitwise — Git workflow assistant. Inspects your repo and runs safe git commands.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"gitwise {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Gitwise only runs git in the current working directory you choose."""


@app.command("whereami")
def whereami(
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-C",
        help="Directory to inspect (default: current directory).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
) -> None:
    """Show a full breakdown of the current git repository state."""
    code = run_whereami(cwd=path)
    raise typer.Exit(code=code)


@app.command("do")
def do(
    intent: str = typer.Argument(..., help='What you want to do, e.g. "push this to main"'),
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-C",
        help="Repository directory (default: current directory).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show the plan without running git.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt (use with care).",
    ),
) -> None:
    """Run a git workflow from plain English (with explanation and confirmation)."""
    code = run_do(intent, cwd=path, dry_run=dry_run, yes=yes)
    raise typer.Exit(code=code)


@app.command("pull")
def pull(
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-C",
        help="Repository directory (default: current directory).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show the safe-pull plan without running git.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt.",
    ),
) -> None:
    """Guided pull: stash if needed, fetch, merge (no rebase), conflict help, restore stash."""
    code = run_pull(cwd=path, dry_run=dry_run, yes=yes)
    raise typer.Exit(code=code)


if __name__ == "__main__":
    app()
