"""Gitwise CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from gitwise import __version__
from gitwise.commands.do_cmd import run_do
from gitwise.commands.pull_cmd import run_pull
from gitwise.commands.whereami import run_whereami
from gitwise.help_text import APP_HELP
from gitwise.workflows.save import run_save
from gitwise.workflows.undo_last import run_undo_last

app = typer.Typer(
    name="gw",
    help=APP_HELP,
    no_args_is_help=True,
    rich_markup_mode=None,
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


@app.command("save")
def save(
    message: str = typer.Argument(..., help='Commit message, e.g. "fixed pull conflict handling"'),
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
    """Stage all changes, commit with your message, and push the current branch."""
    code = run_save(message, cwd=path, dry_run=dry_run, yes=yes)
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
    from_branch: Optional[str] = typer.Option(
        None,
        "--from",
        "-b",
        help="Remote branch to merge into your current branch (e.g. main).",
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
    code = run_pull(cwd=path, from_branch=from_branch, dry_run=dry_run, yes=yes)
    raise typer.Exit(code=code)


@app.command("undo")
def undo(
    scope: str = typer.Argument(
        "last",
        help='What to undo (currently only "last" is supported).',
    ),
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
        help="Show undo options without running git.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt (use with care).",
    ),
) -> None:
    """Explain undo options and help you pick the safest choice for your situation."""
    if scope != "last":
        typer.echo('Only "last" is supported right now: gw undo last', err=True)
        raise typer.Exit(code=1)
    code = run_undo_last(cwd=path, dry_run=dry_run, yes=yes)
    raise typer.Exit(code=code)


if __name__ == "__main__":
    app()
