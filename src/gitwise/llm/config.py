"""Load Gemini API key from environment or local config file."""

from __future__ import annotations

import os
from pathlib import Path

_KEY_ENV = "GEMINI_API_KEY"
_KEY_FILE_NAMES = (
    Path.home() / ".gitwise" / "gemini_api_key",
    Path.home() / ".config" / "gitwise" / "gemini_api_key",
)


def api_key_help() -> str:
    return (
        "Gemini API key not found.\n\n"
        "Set it in ONE of these places (pick one):\n\n"
        "  1. Environment variable (recommended):\n"
        "       Windows PowerShell:  $env:GEMINI_API_KEY = \"your-key\"\n"
        "       Linux/macOS:         export GEMINI_API_KEY=\"your-key\"\n\n"
        "  2. Key file (one line, no quotes):\n"
        f"       {_KEY_FILE_NAMES[0]}\n"
        f"       or {_KEY_FILE_NAMES[1]}\n\n"
        "  3. Project .env file (gitignored):\n"
        "       GEMINI_API_KEY=your-key\n\n"
        "Get a free key at: https://aistudio.google.com/apikey\n"
        "Gitwise uses gemini-2.5-flash-lite (free tier) with a small context to minimize usage."
    )


def load_api_key(*, cwd: Path | str | None = None) -> str | None:
    """Return API key from env, .env in cwd, or ~/.gitwise/gemini_api_key."""
    env_key = os.environ.get(_KEY_ENV, "").strip()
    if env_key:
        return env_key

    work = Path(cwd) if cwd else Path.cwd()
    dotenv = work / ".env"
    if dotenv.is_file():
        key = _read_dotenv_key(dotenv)
        if key:
            return key

    for path in _KEY_FILE_NAMES:
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text

    return None


def require_api_key(*, cwd: Path | str | None = None) -> str:
    key = load_api_key(cwd=cwd)
    if not key:
        raise MissingApiKeyError(api_key_help())
    return key


class MissingApiKeyError(Exception):
    """Raised when no Gemini API key is configured."""


def _read_dotenv_key(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == _KEY_ENV:
            return value.strip().strip('"').strip("'")
    return None
