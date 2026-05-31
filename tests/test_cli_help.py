"""CLI help includes comprehensive usage guide."""

from __future__ import annotations

from typer.testing import CliRunner

from gitwise.cli import app
from gitwise.help_text import APP_HELP


def test_app_help_text_covers_commands() -> None:
    assert "gw save" in APP_HELP
    assert "gw undo last" in APP_HELP
    assert "gw pull" in APP_HELP
    assert "gw do" in APP_HELP
    assert "gw ask" in APP_HELP
    assert "gw diff" in APP_HELP
    assert "SECURITY" in APP_HELP


def test_gw_help_shows_usage() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "save" in result.stdout.lower()
    assert "undo" in result.stdout.lower()
    assert "whereami" in result.stdout.lower()
    assert "ask" in result.stdout.lower()
