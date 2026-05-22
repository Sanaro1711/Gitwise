"""Gitwise CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from gitwise import __version__
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


# Future: gw do, gw explain, gw fix

if __name__ == "__main__":
    app()
